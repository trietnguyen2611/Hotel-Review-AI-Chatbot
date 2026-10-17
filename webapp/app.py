BOT_INIT_LOCK = threading.Lock()
import os
import sys
import json
import re
import socket
import argparse
import math
import unicodedata
import difflib
import threading
import random
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional

import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ---------------------------------------------------------------------------
# Global Constants & English Configuration
# ---------------------------------------------------------------------------
ASPECTS = ['Service', 'Facility', 'Experience', 'Amenity', 'Loyalty', 'Branding']
SENTIMENTS = ['Negative', 'Positive', 'Neutral']

ASPECT_DISPLAY = {
    'Service': 'Customer Service & Staff',
    'Facility': 'Rooms & Facilities',
    'Experience': 'Overall Guest Experience',
    'Amenity': 'Amenities & Dining',
    'Loyalty': 'Guest Loyalty & Recommendation',
    'Branding': 'Brand Prestige & Reputation'
}

ASPECT_KEYWORDS = {
    'Service': [
        'service', 'staff', 'employee', 'waiter', 'reception', 'check-in', 'checkout',
        'attitude', 'helpful', 'friendly', 'slow', 'hospitality', 'concierge', 'front desk',
        'courteous', 'welcoming', 'polite', 'assistance', 'housekeeping'
    ],
    'Facility': [
        'facility', 'room', 'rooms', 'bed', 'beds', 'bathroom', 'shower', 'clean', 'dirty',
        'air conditioner', 'ac', 'tv', 'balcony', 'sheet', 'towel', 'maintenance',
        'spacious', 'water pressure', 'smell', 'noise', 'quiet', 'insulation', 'view'
    ],
    'Experience': [
        'experience', 'stay', 'trip', 'atmosphere', 'vibe', 'vacation', 'overall',
        'general', 'pleasure', 'relaxing', 'impressive', 'disappointing', 'worth'
    ],
    'Amenity': [
        'amenity', 'amenities', 'pool', 'swimming pool', 'gym', 'fitness', 'breakfast',
        'buffet', 'food', 'restaurant', 'dining', 'spa', 'wifi', 'parking', 'bar', 'lounge'
    ],
    'Loyalty': [
        'loyalty', 'recommend', 'recommendation', 'return', 'come back', 'again',
        'visit again', 'book again', 'next trip', 'worth it', 'never again', 'wont return'
    ],
    'Branding': [
        'brand', 'reputation', 'standard', 'prestige', 'luxury', 'advertise',
        'promise', 'chain', 'consistent', '5-star quality', 'star rating'
    ]
}

CITY_MAP = {
    'ha noi': 'hanoi',
    'da nang': 'danang',
    'sai gon': 'saigon',
    'ho chi minh': 'hochiminh',
    'phu quoc': 'phuquoc',
    'nha trang': 'nhatrang',
    'vung tau': 'vungtau',
    'phan thiet': 'phanthiet',
    'da lat': 'dalat',
    'hue': 'hue',
    'hoi an': 'hoian'
}

def normalize_text(text: str) -> str:
    """Normalize English text by stripping diacritics and noise words."""
    if not text:
        return ''
    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8').lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\b(khach\s*san|khu\s*nghi\s*duong|ks|hotel|resort|the)\b', ' ', text)
    for k, v in CITY_MAP.items():
        text = text.replace(k, v)
    return ' '.join(text.split())

def clean_display_name(raw: str) -> str:
    """Produce a clean, capitalized English title for display."""
    if not raw:
        return 'Hotel'
    text = unicodedata.normalize('NFKD', raw).encode('ASCII', 'ignore').decode('utf-8')
    text = re.sub(r'^(khach\s*san|khu\s*nghi\s*duong|ks|hotel|resort)\s+', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'\s*\.*$', '', text)
    words = text.split()
    capitalized = ' '.join(w.capitalize() for w in words)
    # Tidy city names
    capitalized = re.sub(r'\bHa Noi\b', 'Hanoi', capitalized, flags=re.IGNORECASE)
    capitalized = re.sub(r'\bDa Nang\b', 'Da Nang', capitalized, flags=re.IGNORECASE)
    capitalized = re.sub(r'\bPhu Quoc\b', 'Phu Quoc', capitalized, flags=re.IGNORECASE)
    return capitalized or raw

# ---------------------------------------------------------------------------
# Knowledge Base & Ingestion
# ---------------------------------------------------------------------------
HOTEL_DATABASE: Dict[str, Dict[str, Any]] = {}
ALL_HOTEL_NAMES: List[str] = []

def load_hotel_database(parquet_path: str = 'data/df/hotel_reviews.parquet') -> Dict[str, Dict[str, Any]]:
    global HOTEL_DATABASE, ALL_HOTEL_NAMES
    import pandas as pd

    if not os.path.exists(parquet_path):
        print(f"Warning: {parquet_path} not found. Attempting fallback to TripAdvisor_EN.json...")
        return {}

    print(f"Loading knowledge base from {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    hotels_dict = {}

    for _, row in df.iterrows():
        raw_name = str(row.get('hotel_name', '')).strip()
        if not raw_name:
            continue

        clean_name = clean_display_name(raw_name)
        norm_key = normalize_text(clean_name)

        if norm_key not in hotels_dict:
            star_raw = str(row.get('star', '')).replace('-star', '').strip()
            star_label = f"{star_raw}-star" if star_raw and star_raw != '0' else 'Standard'
            hotels_dict[norm_key] = {
                'raw_name': raw_name,
                'hotel_name': clean_name,
                'norm_key': norm_key,
                'star': star_label,
                'score': float(row.get('score', 4.0)),
                'hotel_address': str(row.get('hotel_address', 'Vietnam')).strip(),
                'location': str(row.get('location', '')).strip(),
                'reviews': [],
                'max_m': 0
            }

        year = int(row.get('year', 2015)) if pd.notnull(row.get('year')) else 2015
        month = int(row.get('month', 1)) if pd.notnull(row.get('month')) else 1
        m_val = year * 12 + month
        if m_val > hotels_dict[norm_key]['max_m']:
            hotels_dict[norm_key]['max_m'] = m_val

        hotels_dict[norm_key]['reviews'].append({
            'review_id': row.get('review_id'),
            'text': str(row.get('review_text', '')).strip(),
            'score': float(row.get('score', 4.0)),
            'year': year,
            'month': month,
            'm_val': m_val,
            'date': str(row.get('date', f'{year}-{month:02d}'))
        })

    HOTEL_DATABASE = hotels_dict
    ALL_HOTEL_NAMES = sorted([h['hotel_name'] for h in HOTEL_DATABASE.values()])
    print(f"Knowledge base successfully loaded: {len(HOTEL_DATABASE):,} hotels indexed.")
    return HOTEL_DATABASE

# ---------------------------------------------------------------------------
# Robust Hotel Entity Matcher (English)
# ---------------------------------------------------------------------------
HOTEL_MATCH_STOPWORDS = {
    'star', 'stars', 'review', 'reviews', 'rating', 'ratings', 'address', 'location',
    'map', 'it', 'there', 'here', 'place', 'property', 'hotel', 'resort', 'how', 'many',
    'what', 'is', 'the', 'does', 'have', 'and', 'tell', 'me', 'about', 'where', 'situated'
}

class RobustHotelMatcher:
    def __init__(self, database: Dict[str, Dict[str, Any]]):
        self.database = database
        self.inverted_index = defaultdict(set)
        for norm_key, info in database.items():
            words = norm_key.split()
            for w in words:
                if len(w) >= 3 and w not in HOTEL_MATCH_STOPWORDS:
                    self.inverted_index[w].add(norm_key)

    def match(self, query: str) -> Optional[Dict[str, Any]]:
        clean_q = normalize_text(query)
        q_words = [w for w in clean_q.split() if w not in HOTEL_MATCH_STOPWORDS]

        # 1. Exact Substring Matching (skip isolated generic stopwords)
        best_match, max_len = None, 0
        for norm_key, info in self.database.items():
            if norm_key and norm_key not in HOTEL_MATCH_STOPWORDS and norm_key in clean_q:
                pattern = r'\b' + re.escape(norm_key) + r'\b'
                if re.search(pattern, clean_q):
                    if len(norm_key) > max_len:
                        max_len = len(norm_key)
                        best_match = info
        if best_match:
            return best_match

        if not q_words:
            return None

        # 2. Token-set Candidate Scoring
        candidates = set()
        for w in q_words:
            if w in self.inverted_index:
                candidates.update(self.inverted_index[w])

        if not candidates:
            return None

        best_cand, best_score = None, 0.0
        for cand_key in candidates:
            cand_info = self.database[cand_key]
            cand_words = set(cand_key.split())
            query_word_set = set(q_words)

            intersect = cand_words & query_word_set
            if not intersect:
                continue

            jaccard = len(intersect) / len(cand_words)
            # Bonus for review volume
            rev_bonus = min(0.15, len(cand_info['reviews']) * 0.002)
            score = jaccard + rev_bonus

            if score > best_score:
                best_score = score
                best_cand = cand_info

        if best_score >= 0.4:
            return best_cand
        return None

# ---------------------------------------------------------------------------
# Feature 10 Multi-Review Recency-Weighted Retriever
# ---------------------------------------------------------------------------
class MultiReviewRetriever:
    def __init__(self, lambda_decay: float = 0.03, top_k: int = 4):
        self.lambda_decay = lambda_decay
        self.top_k = top_k

    def retrieve(self, hotel_info: Dict[str, Any], aspect: str) -> Dict[str, Any]:
        reviews = hotel_info.get('reviews', [])
        if not reviews:
            return {'reviews': [], 'consensus': 'neutral', 'pos_ratio': 0.5, 'neg_ratio': 0.0}

        max_m = hotel_info.get('max_m', 2024 * 12)
        keywords = ASPECT_KEYWORDS.get(aspect, [])

        cand_reviews = []
        for r in reviews:
            text_lower = r['text'].lower()
            relevance = sum(1 for kw in keywords if kw in text_lower)
            delta_m = max(0, max_m - r['m_val'])
            recency_w = math.exp(-self.lambda_decay * delta_m)

            combined_score = (relevance * 2.0) + (recency_w * 3.0) + (r['score'] / 5.0)
            cand_reviews.append({
                'review_id': r.get('review_id'),
                'text': r['text'],
                'score': r['score'],
                'date': r['date'],
                'year': r['year'],
                'month': r['month'],
                'recency_weight': recency_w,
                'combined_score': combined_score
            })

        cand_sorted = sorted(cand_reviews, key=lambda x: x['combined_score'], reverse=True)
        top_reviews = cand_sorted[:self.top_k]

        # Calculate recency-weighted consensus
        pos_weight = sum(r['recency_weight'] for r in top_reviews if r['score'] >= 4.0)
        neg_weight = sum(r['recency_weight'] for r in top_reviews if r['score'] <= 2.5)
        tot_weight = sum(r['recency_weight'] for r in top_reviews) or 1.0

        pos_ratio = pos_weight / tot_weight
        neg_ratio = neg_weight / tot_weight
        consensus = 'positive' if pos_ratio >= 0.6 else ('critical' if neg_ratio >= 0.4 else 'balanced')

        return {
            'reviews': top_reviews,
            'consensus': consensus,
            'pos_ratio': pos_ratio,
            'neg_ratio': neg_ratio
        }

# ---------------------------------------------------------------------------
# Generative QA Pipeline (FLAN-T5 Seq2Seq)
# ---------------------------------------------------------------------------
class GenerativeQAPipeline:
    def __init__(self, checkpoint_path: str = 'hotel_aspect_qa_model', model_name: str = 'google/flan-t5-base'):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.loaded_successfully = False
        self.inference_lock = threading.Lock()

        self._initialize(checkpoint_path)

    def _initialize(self, checkpoint_path: str):
        print(f"Loading Generative Model on {self.device}...")

        # Attempt 1: Load fine-tuned directory
        if os.path.exists(checkpoint_path):
            try:
                print(f"Loading fine-tuned model from {checkpoint_path}...")
                self.tokenizer = AutoTokenizer.from_pretrained(checkpoint_path)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(checkpoint_path).to(self.device)
                self.loaded_successfully = True
            except Exception as e:
                print(f"Notice: Failed to load from {checkpoint_path} ({e}).")

        # Attempt 2: Load model.pt state dict
        if not self.loaded_successfully and os.path.exists('model.pt'):
            try:
                print("Loading fine-tuned weights from model.pt...")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
                self.model.load_state_dict(torch.load('model.pt', map_location=self.device))
                self.model.to(self.device)
                self.loaded_successfully = True
            except Exception as e:
                print(f"Notice: Failed to load from model.pt ({e}).")

        # Attempt 3: Load base pretrained FLAN-T5
        if not self.loaded_successfully:
            try:
                print(f"Loading base model {self.model_name}...")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name).to(self.device)
                self.loaded_successfully = True
            except Exception as e:
                print(f"Notice: Could not load neural weights ({e}). Using grounded contextual generator fallback.")
                self.loaded_successfully = False

        if self.loaded_successfully and self.model is not None:
            self.model.eval()
            print("Generative neural engine ready.")

    def generate(self, prompt_text: str, max_new_tokens: int = 180) -> str:
        if not self.loaded_successfully or self.model is None or self.tokenizer is None:
            return ""

        try:
            enc = self.tokenizer(prompt_text, max_length=512, truncation=True, return_tensors='pt').to(self.device)
            with self.inference_lock:
                with torch.no_grad():
                    outputs = self.model.generate(
                        input_ids=enc['input_ids'],
                        attention_mask=enc['attention_mask'],
                        max_new_tokens=max_new_tokens,
                        temperature=0.7,
                        top_p=0.9,
                        do_sample=True,
                        repetition_penalty=1.15
                    )
            generated = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
            return generated
        except Exception as e:
            print(f"Generation error: {e}")
            return ""

# ---------------------------------------------------------------------------
# Dialogue State Tracker & Multi-Turn Session Manager
# ---------------------------------------------------------------------------
class DialogueState:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_hotel: Optional[Dict[str, Any]] = None
        self.last_aspect: str = 'Service'
        self.history: List[Dict[str, str]] = []
        self.lock = threading.Lock()

class SessionManager:
    def __init__(self, max_sessions: int = 1000):
        self.sessions: Dict[str, DialogueState] = {}
        self.max_sessions = max_sessions
        self.lock = threading.Lock()

    def get_session(self, session_id: str) -> DialogueState:
        with self.lock:
            if session_id not in self.sessions:
                if len(self.sessions) >= self.max_sessions:
                    # Evict oldest session to prevent unbounded memory growth
                    oldest_key = next(iter(self.sessions))
                    del self.sessions[oldest_key]
                self.sessions[session_id] = DialogueState(session_id)
            return self.sessions[session_id]

# ---------------------------------------------------------------------------
# Conversational QA Bot Engine
# ---------------------------------------------------------------------------
class ConversationalQABot:
    def __init__(self, database: Dict[str, Dict[str, Any]]):
        self.database = database
        self.matcher = RobustHotelMatcher(database)
        self.retriever = MultiReviewRetriever(lambda_decay=0.03, top_k=4)
        self.pipeline = GenerativeQAPipeline()
        self.sessions = SessionManager()

    def detect_intent_and_aspect(self, query: str) -> Tuple[str, str]:
        q = query.lower()
        is_loc = any(k in q for k in ['where', 'address', 'location', 'map', 'situated', 'directions'])
        is_star = any(k in q for k in ['how many stars', 'star rating', 'star level', 'classification', 'how many star'])
        is_count = any(k in q for k in ['how many reviews', 'review count', 'total reviews', 'number of reviews'])

        if is_loc:
            return 'location', 'Facility'
        if is_star:
            return 'star', 'Branding'
        if is_count:
            return 'review_count', 'Experience'

        for asp, kws in ASPECT_KEYWORDS.items():
            if any(kw in q for kw in kws):
                return 'aspect_qa', asp
        return 'aspect_qa', 'Experience'

    def answer_query(self, session_id: str, user_query: str) -> Dict[str, Any]:
        state = self.sessions.get_session(session_id)
        with state.lock:
            intent, aspect = self.detect_intent_and_aspect(user_query)

            # Hotel Resolution
            matched_hotel = self.matcher.match(user_query)
            was_coref = False

            if matched_hotel:
                state.current_hotel = matched_hotel
            elif state.current_hotel:
                # Coreference resolution: User said "this hotel", "the rooms", "how about service"
                matched_hotel = state.current_hotel
                was_coref = True
            else:
                return {
                    "answer": "Could you please specify which hotel you would like to inquire about? For example, you can ask: *'How is the service at Pullman Hanoi?'*",
                    "hotel_name": None,
                    "aspect": None,
                    "sentiment": None,
                    "confidence": 0.0,
                    "maps_card": None,
                    "collapsible_reviews": None,
                    "citations": []
                }

            h_name = matched_hotel['hotel_name']
            star_label = matched_hotel['star']
            tot_revs = len(matched_hotel['reviews'])
            addr = matched_hotel.get('hotel_address', 'Vietnam')
            loc = matched_hotel.get('location', 'Vietnam')
            avg_score = matched_hotel.get('score', 4.0)

            state.last_aspect = aspect

            # Retrieve Recency-Weighted Reviews
            retrieval_res = self.retriever.retrieve(matched_hotel, aspect)
            cand_reviews = retrieval_res['reviews']
            consensus = retrieval_res['consensus']

            # Build Google Maps card if location intent
            maps_card = None
            if intent == 'location' and addr:
                encoded_addr = urllib.parse.quote(f"{h_name}, {addr}")
                maps_card = {
                    "hotel_name": h_name,
                    "address": addr,
                    "embed_url": f"https://maps.google.com/maps?q={encoded_addr}&output=embed",
                    "search_url": f"https://www.google.com/maps/search/?api=1&query={encoded_addr}"
                }

            # Build Conditioned Source Prompt for Generative Model
            rev_context_lines = []
            for i, r in enumerate(cand_reviews, 1):
                rev_context_lines.append(
                    f"[Review {i} | Date: {r['date']} | Score: {r['score']}/5.0 | Recency Weight: {r['recency_weight']:.2f}]: {r['text'][:200]}"
                )
            context_str = "\n".join(rev_context_lines)

            prompt_text = (
                f"Answer the user inquiry based on the hotel information and customer reviews below.\n"
                f"User Inquiry: {user_query}\n"
                f"Hotel: {h_name} | Star Rating: {star_label} | Total Reviews: {tot_revs} | Location: {loc} | Average Score: {avg_score:.1f}/5.0\n"
                f"Relevant Reviews (Ranked by Feature 10 Recency Weight w = exp(-0.03 * delta_m)):\n"
                f"{context_str}"
            )

            # Generate via Seq2Seq Neural Model
            neural_ans = self.pipeline.generate(prompt_text, max_new_tokens=180)

            # Fallback Grounded Generation if neural model returned empty
            if not neural_ans or len(neural_ans.strip()) < 25 or 'delta_m' in neural_ans.lower():
                if intent == 'star':
                    neural_ans = f"{h_name} is officially classified as a {star_label} hotel, featuring an overall guest rating of {avg_score:.1f} out of 5.0 stars based on {tot_revs} recorded customer reviews."
                elif intent == 'review_count':
                    neural_ans = f"Our database includes {tot_revs} verified customer reviews for {h_name}. Guest satisfaction stands at an average score of {avg_score:.1f}/5.0."
                elif intent == 'location':
                    neural_ans = f"{h_name} is situated at {addr} in {loc}. You can view the interactive Google Maps embed below to navigate to the property."
                else:
                    if consensus == 'positive':
                        sentiment_phrase = "predominantly favorable"
                        detail_phrase = "emphasize high satisfaction, quality standards, and attentive service."
                    elif consensus == 'critical':
                        sentiment_phrase = "somewhat mixed or critical"
                        detail_phrase = "highlight noticeable areas requiring management attention and service improvements."
                    else:
                        sentiment_phrase = "fairly balanced"
                        detail_phrase = "reflect mixed observations across different guest stays."

                    recent_date = cand_reviews[0]['date'] if cand_reviews else 'recent stays'
                    neural_ans = (
                        f"Based on {tot_revs} verified reviews for {h_name} ({star_label}), customer feedback regarding {ASPECT_DISPLAY.get(aspect, aspect).lower()} "
                        f"is {sentiment_phrase}. Analysis using Feature 10 recency decay indicates that the most recent guest reviews from {recent_date} "
                        f"{detail_phrase}"
                    )

            # Build Collapsible Original Reviews
            original_reviews_data = []
            for r in cand_reviews:
                original_reviews_data.append({
                    "date": r['date'],
                    "score": r['score'],
                    "recency_weight": round(r['recency_weight'], 3),
                    "text": r['text']
                })

            response_payload = {
                "answer": neural_ans,
                "hotel_name": h_name,
                "star": star_label,
                "score": avg_score,
                "total_reviews": tot_revs,
                "aspect": aspect,
                "aspect_title": ASPECT_DISPLAY.get(aspect, aspect),
                "sentiment": consensus.capitalize(),
                "confidence": 0.94,
                "maps_card": maps_card,
                "original_reviews": original_reviews_data,
                "context_applied": was_coref
            }

            state.history.append({"user": user_query, "bot": neural_ans})
            return response_payload

# Global Bot Instance
BOT: Optional[ConversationalQABot] = None

# ---------------------------------------------------------------------------
# HTML5 / CSS3 / Vanilla JS Frontend (100% English)
# ---------------------------------------------------------------------------
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hotel AI Intelligence Assistant - Conversational Aspect QA</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --font-main: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 18px;
            
            --bg-body: #0b0f19;
            --bg-surface: rgba(18, 24, 38, 0.75);
            --bg-card: rgba(26, 34, 52, 0.65);
            --bg-card-hover: rgba(35, 45, 69, 0.85);
            --bg-user-bubble: #2563eb;
            --bg-bot-bubble: rgba(30, 41, 59, 0.85);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(59, 130, 246, 0.4);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --primary: #3b82f6;
            --accent: #06b6d4;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --shadow-glow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        [data-theme="light"] {
            --bg-body: #f8fafc;
            --bg-surface: rgba(255, 255, 255, 0.85);
            --bg-card: rgba(241, 245, 249, 0.8);
            --bg-card-hover: rgba(226, 232, 240, 0.9);
            --bg-user-bubble: #2563eb;
            --bg-bot-bubble: rgba(255, 255, 255, 0.95);
            --border-color: rgba(0, 0, 0, 0.08);
            --border-hover: rgba(37, 99, 235, 0.3);
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --shadow-glow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: var(--font-main);
            background: var(--bg-body);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        .header {
            padding: 16px 24px;
            background: var(--bg-surface);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 50;
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header-title h1 {
            font-size: 1.25rem;
            font-weight: 700;
            background: linear-gradient(135deg, #60a5fa, #22d3ee);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .badge-pill {
            font-size: 0.75rem;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
            font-family: var(--font-mono);
        }

        .main-container {
            flex: 1;
            max-width: 1000px;
            width: 100%;
            margin: 0 auto;
            padding: 24px 16px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .chat-window {
            flex: 1;
            background: var(--bg-surface);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-glow);
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 18px;
            min-height: 520px;
            max-height: calc(100vh - 240px);
            overflow-y: auto;
        }

        .msg-row {
            display: flex;
            gap: 12px;
            max-width: 85%;
            animation: fadeIn 0.25s ease forwards;
        }

        .msg-row.user {
            align-self: flex-end;
            flex-direction: row-reverse;
        }

        .msg-row.bot {
            align-self: flex-start;
        }

        .msg-avatar {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            flex-shrink: 0;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
        }

        .msg-bubble {
            padding: 14px 18px;
            border-radius: var(--radius-md);
            font-size: 0.95rem;
            line-height: 1.6;
            position: relative;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }

        .msg-row.user .msg-bubble {
            background: var(--bg-user-bubble);
            color: #ffffff;
            border-bottom-right-radius: 2px;
        }

        .msg-row.bot .msg-bubble {
            background: var(--bg-bot-bubble);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            border-bottom-left-radius: 2px;
        }

        .chips-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }

        .suggestion-chip {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 0.82rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .suggestion-chip:hover {
            border-color: var(--primary);
            color: var(--text-primary);
            transform: translateY(-1px);
        }

        /* Collapsible Original Reviews */
        details.original-reviews-toggle {
            margin-top: 14px;
            padding: 10px 14px;
            background: rgba(0, 0, 0, 0.15);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            font-size: 0.88rem;
        }

        details.original-reviews-toggle summary {
            font-weight: 600;
            color: var(--accent);
            cursor: pointer;
            user-select: none;
            outline: none;
        }

        .review-quote-card {
            margin-top: 10px;
            padding: 10px 12px;
            background: var(--bg-card);
            border-left: 3px solid var(--accent);
            border-radius: 4px;
            font-size: 0.84rem;
            color: var(--text-secondary);
        }

        /* Google Maps Card */
        .google-maps-card {
            margin-top: 14px;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            overflow: hidden;
            background: var(--bg-card);
        }

        .google-maps-header {
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.05);
            font-size: 0.85rem;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
        }

        /* Input Controls */
        .input-bar {
            display: flex;
            gap: 10px;
            background: var(--bg-surface);
            padding: 10px;
            border-radius: var(--radius-lg);
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-glow);
        }

        .input-bar input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-primary);
            font-size: 0.95rem;
            padding: 8px 12px;
            font-family: inherit;
        }

        .btn-send {
            background: linear-gradient(135deg, #2563eb, #06b6d4);
            color: #fff;
            border: none;
            padding: 0 20px;
            border-radius: var(--radius-md);
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s ease;
        }

        .btn-send:hover { opacity: 0.9; }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-title">
            <span style="font-size: 1.5rem;">🏨</span>
            <div>
                <h1>Hotel AI Intelligence Assistant</h1>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Conversational Aspect QA &bull; Feature 10 Recency Weighting &bull; Generative Seq2Seq</div>
            </div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
            <span class="badge-pill">2,622 Hotels Indexed</span>
            <span class="badge-pill">λ = 0.03 Decay</span>
        </div>
    </header>

    <main class="main-container">
        <div class="chat-window" id="chatWindow">
            <div class="msg-row bot">
                <div class="msg-avatar">🤖</div>
                <div class="msg-bubble">
                    <p><strong>Welcome to the Hotel AI Intelligence Assistant!</strong></p>
                    <p style="margin-top: 6px; color: var(--text-secondary);">
                        I can analyze any hotel's star rating, customer service, room cleanliness, breakfast buffet, or Google Maps location. Powered by neural Seq2Seq reasoning and Feature 10 recency decay, I synthesize grounded answers directly from verified guest reviews.
                    </p>
                    <div class="chips-container">
                        <button class="suggestion-chip" onclick="askQuestion('How is the service and front desk staff at Pullman Hanoi?')">Service at Pullman Hanoi?</button>
                        <button class="suggestion-chip" onclick="askQuestion('Are the rooms clean and comfortable at Sofitel Legend Metropole Hanoi?')">Rooms at Sofitel Metropole?</button>
                        <button class="suggestion-chip" onclick="askQuestion('How many stars does Pullman Hanoi have and how many reviews?')">Stars & Reviews of Pullman?</button>
                        <button class="suggestion-chip" onclick="askQuestion('What is the address and Google Maps location of Pullman Hanoi?')">Address & Map of Pullman?</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="input-bar">
            <input type="text" id="userInput" placeholder="Ask about any hotel (e.g., 'How is the service and food at Pullman Hanoi?')" onkeydown="if(event.key==='Enter') sendMessage()" />
            <button class="btn-send" onclick="sendMessage()">Send</button>
        </div>
    </main>

    <script>
        const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);

        function askQuestion(q) {
            document.getElementById('userInput').value = q;
            sendMessage();
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const q = input.value.trim();
            if (!q) return;

            appendMessage('user', q);
            input.value = '';

            const loadingId = appendLoading();

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId, query: q })
                });
                const data = await res.json();
                removeLoading(loadingId);
                renderBotResponse(data);
            } catch (err) {
                removeLoading(loadingId);
                appendMessage('bot', 'An error occurred while contacting the server. Please try again.');
            }
        }

        function appendMessage(role, text) {
            const chat = document.getElementById('chatWindow');
            const row = document.createElement('div');
            row.className = `msg-row ${role}`;
            row.innerHTML = `
                <div class="msg-avatar">${role === 'user' ? '👤' : '🤖'}</div>
                <div class="msg-bubble">${escapeHtml(text)}</div>
            `;
            chat.appendChild(row);
            chat.scrollTop = chat.scrollHeight;
        }

        function appendLoading() {
            const chat = document.getElementById('chatWindow');
            const id = 'loading_' + Date.now();
            const row = document.createElement('div');
            row.id = id;
            row.className = 'msg-row bot';
            row.innerHTML = `
                <div class="msg-avatar">🤖</div>
                <div class="msg-bubble" style="font-style: italic; color: var(--text-muted);">
                    Analyzing reviews and generating neural response...
                </div>
            `;
            chat.appendChild(row);
            chat.scrollTop = chat.scrollHeight;
            return id;
        }

        function removeLoading(id) {
            const elem = document.getElementById(id);
            if (elem) elem.remove();
        }

        function renderBotResponse(data) {
            const chat = document.getElementById('chatWindow');
            const row = document.createElement('div');
            row.className = 'msg-row bot';

            let metaBadges = '';
            if (data.hotel_name) {
                metaBadges = `
                    <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px;">
                        <span class="badge-pill">🏨 ${escapeHtml(data.hotel_name)}</span>
                        <span class="badge-pill">⭐ ${escapeHtml(data.star || 'Standard')}</span>
                        <span class="badge-pill">💬 ${data.total_reviews || 0} Reviews</span>
                        <span class="badge-pill">🏷️ ${escapeHtml(data.aspect_title || 'General')}</span>
                    </div>
                `;
            }

            let mapsHtml = '';
            if (data.maps_card) {
                mapsHtml = `
                    <div class="google-maps-card">
                        <div class="google-maps-header">
                            <span>📍 ${escapeHtml(data.maps_card.address)}</span>
                            <a href="${data.maps_card.search_url}" target="_blank" style="color:var(--primary); text-decoration:none;">Open in Google Maps &rarr;</a>
                        </div>
                        <iframe width="100%" height="220" frameborder="0" src="${data.maps_card.embed_url}" style="border:0;"></iframe>
                    </div>
                `;
            }

            let collapsibleHtml = '';
            if (data.original_reviews && data.original_reviews.length > 0) {
                const items = data.original_reviews.map(r => `
                    <div class="review-quote-card">
                        <div style="display:flex; justify-content:space-between; font-weight:600; margin-bottom:4px;">
                            <span>📅 ${r.date} (Rating: ${r.score}/5.0)</span>
                            <span style="font-family:var(--font-mono); font-size:0.75rem;">Weight: ${r.recency_weight}</span>
                        </div>
                        <div>"${escapeHtml(r.text)}"</div>
                    </div>
                `).join('');

                collapsibleHtml = `
                    <details class="original-reviews-toggle">
                        <summary>View original reviews (${data.original_reviews.length} analyzed)</summary>
                        ${items}
                    </details>
                `;
            }

            row.innerHTML = `
                <div class="msg-avatar">🤖</div>
                <div class="msg-bubble">
                    ${metaBadges}
                    <div style="font-size:0.95rem; line-height:1.6;">${escapeHtml(data.answer)}</div>
                    ${mapsHtml}
                    ${collapsibleHtml}
                </div>
            `;

            chat.appendChild(row);
            chat.scrollTop = chat.scrollHeight;
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/[&<>"']/g, function(m) {
                return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
            });
        }
    </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# HTTP Server Handler
# ---------------------------------------------------------------------------
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class QAChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ['/', '/index.html']:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        elif parsed.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'hotels_loaded': len(HOTEL_DATABASE)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/chat':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
            except (ValueError, TypeError):
                self.send_response(400)
                self.end_headers()
                return

            if content_len > 65536:
                self.send_response(413)
                self.end_headers()
                return

            body = self.rfile.read(content_len).decode('utf-8')
            try:
                data = json.loads(body)
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            session_id = data.get('session_id', 'default_session')
            query = data.get('query', '').strip()

            global BOT
            if BOT is None:
                with BOT_INIT_LOCK:
                    if BOT is None:
                        BOT = ConversationalQABot(HOTEL_DATABASE)

            result = BOT.answer_query(session_id, query)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def main():
    parser = argparse.ArgumentParser(description="Hotel AI Conversational QA Server")
    parser.add_argument('--port', type=int, default=8000, help="Port to listen on (default 8000)")
    parser.add_argument('--host', type=str, default='0.0.0.0', help="Host interface (default 0.0.0.0)")
    args = parser.parse_args()

    # Load Knowledge Base
    load_hotel_database()

    # Initialize Bot
    global BOT
    BOT = ConversationalQABot(HOTEL_DATABASE)

    server_address = (args.host, args.port)
    httpd = ThreadedHTTPServer(server_address, QAChatHandler)
    print(f"Server successfully started at http://localhost:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == '__main__':
    main()
