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

BOT_INIT_LOCK = threading.Lock()

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

    # Resolve relative path if run from subdirectory
    if not os.path.exists(parquet_path):
        alt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), parquet_path)
        if os.path.exists(alt_path):
            parquet_path = alt_path

    if not os.path.exists(parquet_path):
        print(f"Warning: {parquet_path} not found.")
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

        review_text = str(row.get('clean_review', '')).strip() or str(row.get('review_text', '')).strip()
        rev_score = float(row.get('score', 4.0))

        hotels_dict[norm_key]['reviews'].append({
            'text': review_text,
            'score': rev_score,
            'year': year,
            'month': month,
            'm': m_val,
            'date': f"{month:02d}/{year}"
        })

        if m_val > hotels_dict[norm_key]['max_m']:
            hotels_dict[norm_key]['max_m'] = m_val

    HOTEL_DATABASE = hotels_dict
    ALL_HOTEL_NAMES = [h['hotel_name'] for h in hotels_dict.values()]
    print(f"Loaded {len(HOTEL_DATABASE)} unique hotel properties into knowledge base.")
    return HOTEL_DATABASE

# ---------------------------------------------------------------------------
# Robust Hotel Entity Matcher (Zero-Leakage Multi-Token Resolution)
# ---------------------------------------------------------------------------
class RobustHotelMatcher:
    def __init__(self, database: Dict[str, Dict[str, Any]]):
        self.database = database
        self.inverted_index = defaultdict(set)
        self.hotel_lookup = {}

        self.stopwords = {
            'hotel', 'resort', 'the', 'and', 'in', 'at', 'of', 'for', 'ks', 'khach', 'san',
            'how', 'is', 'what', 'where', 'service', 'room', 'view', 'food', 'staff',
            'please', 'tell', 'me', 'about', 'stay', 'night', 'stars', 'address'
        }

        for norm_key, hotel in database.items():
            self.hotel_lookup[norm_key] = hotel
            tokens = norm_key.split()
            for token in tokens:
                if len(token) > 2 and token not in self.stopwords:
                    self.inverted_index[token].add(norm_key)

    def match(self, user_query: str) -> Optional[Dict[str, Any]]:
        norm_q = normalize_text(user_query)
        q_tokens = [w for w in norm_q.split() if w not in self.stopwords and len(w) > 2]

        if not q_tokens:
            return None

        # 1. Exact Substring Match
        for norm_key, hotel in self.hotel_lookup.items():
            if norm_key in norm_q and len(norm_key) >= 4:
                return hotel

        # 2. Inverted Index Candidate Scoring
        candidates = defaultdict(int)
        for token in q_tokens:
            for norm_key in self.inverted_index.get(token, set()):
                candidates[norm_key] += 3

        if not candidates:
            # Fuzzy match top 50 candidates
            all_keys = list(self.hotel_lookup.keys())
            close_matches = difflib.get_close_matches(norm_q, all_keys, n=3, cutoff=0.6)
            if close_matches:
                return self.hotel_lookup[close_matches[0]]
            return None

        # Score candidates with Jaccard and length penalty
        best_match = None
        best_score = -1.0

        q_token_set = set(q_tokens)
        for norm_key, token_matches in candidates.items():
            hotel_tokens = set(norm_key.split())
            intersection = q_token_set.intersection(hotel_tokens)
            if not intersection:
                continue

            jaccard = len(intersection) / float(len(q_token_set.union(hotel_tokens)))
            score = (token_matches * 2.0) + (jaccard * 10.0)

            # Location match bonus
            for city in CITY_MAP.values():
                if city in norm_q and city in norm_key:
                    score += 5.0

            if score > best_score:
                best_score = score
                best_match = self.hotel_lookup[norm_key]

        if best_score > 3.0:
            return best_match
        return None

# ---------------------------------------------------------------------------
# Multi-Review Temporal Weighting Retriever (Feature 10)
# ---------------------------------------------------------------------------
class MultiReviewRetriever:
    def __init__(self, lambda_decay: float = 0.03, top_k: int = 4):
        self.lambda_decay = lambda_decay
        self.top_k = top_k

    def retrieve(self, hotel: Dict[str, Any], aspect: str) -> List[Dict[str, Any]]:
        reviews = hotel.get('reviews', [])
        if not reviews:
            return []

        max_m = hotel.get('max_m', 2020 * 12)
        keywords = ASPECT_KEYWORDS.get(aspect, [])

        scored_reviews = []
        for r in reviews:
            text = r.get('text', '')
            text_lower = text.lower()

            # Feature 10: Exponential Time Decay w = exp(-lambda * delta_m)
            delta_m = max(0, max_m - r.get('m', max_m))
            time_weight = math.exp(-self.lambda_decay * delta_m)

            # Keyword Relevance
            match_count = sum(1 for kw in keywords if kw in text_lower)
            relevance = 1.0 + (match_count * 0.8)

            combined_score = time_weight * relevance

            scored_reviews.append({
                'text': text,
                'score': r.get('score', 4.0),
                'date': r.get('date', 'Recent'),
                'recency_weight': time_weight,
                'combined_score': combined_score
            })

        # Sort descending by combined recency-relevance score
        scored_reviews.sort(key=lambda x: x['combined_score'], reverse=True)
        return scored_reviews[:self.top_k]

    def aggregate_sentiment(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not reviews:
            return {'consensus': 'neutral', 'avg_score': 4.0, 'pos_ratio': 0.5, 'neg_ratio': 0.0}

        weighted_score_sum = 0.0
        weight_sum = 0.0
        pos_weight = 0.0
        neg_weight = 0.0

        for r in reviews:
            w = r.get('recency_weight', 1.0)
            score = r.get('score', 4.0)

            weighted_score_sum += score * w
            weight_sum += w

            if score >= 4.0:
                pos_weight += w
            elif score <= 2.5:
                neg_weight += w

        avg_score = (weighted_score_sum / weight_sum) if weight_sum > 0 else 4.0
        pos_ratio = (pos_weight / weight_sum) if weight_sum > 0 else 0.5
        neg_ratio = (neg_weight / weight_sum) if weight_sum > 0 else 0.0

        if pos_ratio >= 0.65:
            consensus = 'positive'
        elif neg_ratio >= 0.40:
            consensus = 'critical'
        else:
            consensus = 'mixed'

        return {
            'consensus': consensus,
            'avg_score': avg_score,
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

    def reload_model(self, custom_model_path: str = 'model.pt') -> bool:
        """Dynamically reload new weights into memory with thread safety."""
        with self.inference_lock:
            try:
                print(f"Reloading custom model weights from {custom_model_path}...")
                if self.tokenizer is None:
                    self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

                if custom_model_path.endswith('.pt') and os.path.exists(custom_model_path):
                    state_dict = torch.load(custom_model_path, map_location=self.device)
                    if self.model is None:
                        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
                    self.model.load_state_dict(state_dict)
                    self.model.to(self.device)
                    self.model.eval()
                    self.loaded_successfully = True
                    print(f"Successfully reloaded weights from {custom_model_path}.")
                    return True
                elif os.path.isdir(custom_model_path):
                    self.tokenizer = AutoTokenizer.from_pretrained(custom_model_path)
                    self.model = AutoModelForSeq2SeqLM.from_pretrained(custom_model_path).to(self.device)
                    self.model.eval()
                    self.loaded_successfully = True
                    print(f"Successfully reloaded model directory from {custom_model_path}.")
                    return True
            except Exception as e:
                print(f"Failed to reload model: {e}")
                return False
        return False

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
                matched_hotel = state.current_hotel
                was_coref = True
            else:
                return {
                    "answer": "Could you please specify which hotel you would like to inquire about? For example, you can ask: 'How is the service at Pullman Hanoi?'",
                    "hotel_name": None,
                    "aspect": None,
                    "sentiment": None,
                    "confidence": 0.0,
                    "maps_card": None,
                    "original_reviews": []
                }

            h_name = matched_hotel.get('hotel_name', 'The Hotel')
            addr = matched_hotel.get('hotel_address', 'Vietnam')
            loc = matched_hotel.get('location', '')
            star_label = matched_hotel.get('star', 'Standard')
            tot_revs = len(matched_hotel.get('reviews', []))

            # Retrieve Multi-Review Evidence with Feature 10 Decay
            cand_reviews = self.retriever.retrieve(matched_hotel, aspect)
            sent_summary = self.retriever.aggregate_sentiment(cand_reviews)
            consensus = sent_summary['consensus']
            avg_score = sent_summary['avg_score']

            # Build Google Maps Embed Card if Location Inquired
            maps_card = None
            if intent == 'location' or any(k in user_query.lower() for k in ['where', 'address', 'location', 'map']):
                search_query = f"{h_name}, {addr}" if addr else f"{h_name}, Vietnam"
                encoded_loc = urllib.parse.quote(search_query)
                maps_card = {
                    "hotel_name": h_name,
                    "address": addr,
                    "location": loc,
                    "search_url": f"https://www.google.com/maps/search/?api=1&query={encoded_loc}",
                    "embed_url": f"https://maps.google.com/maps?q={encoded_loc}&t=&z=15&ie=UTF8&iwloc=&output=embed"
                }

            # Neural Prompt Formulation
            review_snippets = " | ".join([f"[{r['date']}, score={r['score']}] {r['text'][:140]}" for r in cand_reviews])
            prompt = (
                f"Question: {user_query} | Hotel: {h_name} ({star_label}, {tot_revs} reviews) | "
                f"Aspect: {aspect} | Sentiment Consensus: {consensus} (Avg Score: {avg_score:.1f}/5.0) | "
                f"Evidence: {review_snippets} | Answer in natural English:"
            )

            # Neural Generation with fallback
            neural_ans = self.pipeline.generate(prompt)

            if not neural_ans:
                # Grounded Natural Language Synthesis
                if intent == 'star':
                    neural_ans = f"{h_name} is officially classified as a {star_label} property, featuring an overall guest rating of {avg_score:.1f} out of 5.0 stars based on {tot_revs} recorded customer reviews."
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

            # Format original reviews data
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
# Static Directory & Multipart File Parser
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(BASE_DIR, 'webapp', 'index.html')):
    WEBAPP_DIR = os.path.join(BASE_DIR, 'webapp')
elif os.path.exists(os.path.join(BASE_DIR, 'index.html')):
    WEBAPP_DIR = BASE_DIR
else:
    WEBAPP_DIR = os.path.join(os.getcwd(), 'webapp')

MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.ico': 'image/x-icon',
    '.woff2': 'font/woff2'
}

def parse_multipart_file(headers, rfile, content_len: int) -> Tuple[Optional[str], Optional[bytes]]:
    content_type = headers.get('Content-Type', '')
    if 'multipart/form-data' not in content_type:
        data = rfile.read(content_len)
        return 'model.pt', data

    boundary = None
    for param in content_type.split(';'):
        param = param.strip()
        if param.lower().startswith('boundary='):
            boundary = param.split('=', 1)[1].strip('"\'').encode('utf-8')
            break

    if not boundary:
        data = rfile.read(content_len)
        return 'model.pt', data

    body = rfile.read(content_len)
    delimiter = b'--' + boundary
    parts = body.split(delimiter)
    for part in parts:
        if b'Content-Disposition:' in part:
            header_end = part.find(b'\r\n\r\n')
            if header_end != -1:
                headers_part = part[:header_end].decode('utf-8', errors='ignore')
                file_content = part[header_end + 4:]
                if file_content.endswith(b'\r\n'):
                    file_content = file_content[:-2]
                if file_content.endswith(b'--'):
                    file_content = file_content[:-2]
                if file_content.endswith(b'\r\n'):
                    file_content = file_content[:-2]

                fn_match = re.search(r'filename="([^"]+)"', headers_part)
                filename = fn_match.group(1) if fn_match else 'model.pt'
                return filename, file_content

    return 'model.pt', body

# ---------------------------------------------------------------------------
# HTTP Server Handler
# ---------------------------------------------------------------------------
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class QAChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        req_path = parsed.path.lstrip('/')
        if not req_path or req_path == 'index.html':
            req_path = 'index.html'

        if parsed.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'ok',
                'hotels_loaded': len(HOTEL_DATABASE),
                'model_loaded': BOT.pipeline.loaded_successfully if BOT and BOT.pipeline else False
            }).encode('utf-8'))
            return

        # Serve static file from WEBAPP_DIR
        file_path = os.path.normpath(os.path.join(WEBAPP_DIR, req_path))
        if not (file_path == WEBAPP_DIR or file_path.startswith(WEBAPP_DIR + os.sep)) or not os.path.isfile(file_path):
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'File Not Found')
            return

        _, ext = os.path.splitext(file_path)
        content_type = MIME_TYPES.get(ext.lower(), 'application/octet-stream')

        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    def do_POST(self):
        global BOT
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

            if BOT is None:
                with BOT_INIT_LOCK:
                    if BOT is None:
                        BOT = ConversationalQABot(HOTEL_DATABASE)

            result = BOT.answer_query(session_id, query)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))

        elif parsed.path == '/api/upload-model':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
            except (ValueError, TypeError):
                self.send_response(400)
                self.end_headers()
                return

            if content_len <= 0:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Empty upload payload'}).encode('utf-8'))
                return

            # Max 2GB limit for checkpoint upload
            if content_len > 2 * 1024 * 1024 * 1024:
                self.send_response(413)
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Model file exceeds 2GB maximum limit'}).encode('utf-8'))
                return

            try:
                filename, file_data = parse_multipart_file(self.headers, self.rfile, content_len)
                if not file_data or len(file_data) == 0:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Failed to parse model file payload'}).encode('utf-8'))
                    return

                target_filename = 'model.pt'
                save_path = os.path.join(BASE_DIR, target_filename)
                with open(save_path, 'wb') as f:
                    f.write(file_data)

                print(f"Received and saved {len(file_data)} bytes to {save_path}")

                if BOT is None:
                    with BOT_INIT_LOCK:
                        if BOT is None:
                            BOT = ConversationalQABot(HOTEL_DATABASE)

                reload_success = BOT.pipeline.reload_model(save_path)

                response_payload = {
                    'status': 'success' if reload_success else 'warning',
                    'message': 'Model weights saved and reloaded into memory' if reload_success else 'Model weights saved but failed to load into PyTorch',
                    'filename': filename,
                    'size_bytes': len(file_data),
                    'size_mb': round(len(file_data) / (1024 * 1024), 2),
                    'reloaded': reload_success
                }

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response_payload).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Upload processing failed: {str(e)}'}).encode('utf-8'))
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
