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
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModel, EncoderDecoderModel
from transformers.modeling_outputs import BaseModelOutput

try:
    from safetensors.torch import load_file as safetensors_load_file
except ImportError:
    safetensors_load_file = None

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

def clean_vietnamese_text(text: str) -> str:
    """Normalize Vietnamese text to clean ASCII/English, stripping combining diacritics."""
    if not text:
        return ''
    text = str(text).replace('Đ', 'D').replace('đ', 'd')
    norm = unicodedata.normalize('NFKD', text)
    ascii_text = ''.join(c for c in norm if not unicodedata.combining(c))
    ascii_text = ascii_text.replace('\xa0', ' ').strip()
    return ascii_text

def normalize_text(text: str) -> str:
    """Normalize English text by stripping diacritics and noise words."""
    if not text:
        return ''
    text = clean_vietnamese_text(text).lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\b(khach\s*san|khu\s*nghi\s*duong|ks|hotel|resort|the)\b', ' ', text)
    for k, v in CITY_MAP.items():
        text = text.replace(k, v)
    return ' '.join(text.split())

CITY_CANONICAL_MAP = {
    'ha noi': 'Hanoi',
    'da nang': 'Da Nang',
    'sai gon': 'Ho Chi Minh City',
    'ho chi minh': 'Ho Chi Minh City',
    'phu quoc': 'Phu Quoc',
    'nha trang': 'Nha Trang',
    'vung tau': 'Vung Tau',
    'phan thiet': 'Phan Thiet',
    'da lat': 'Da Lat',
    'hue': 'Hue',
    'hoi an': 'Hoi An',
    'sapa': 'Sa Pa',
    'ha long': 'Ha Long'
}

def clean_location(loc_raw: str) -> str:
    """Produce clean English city/province name."""
    if not loc_raw:
        return 'Vietnam'
    ascii_loc = clean_vietnamese_text(loc_raw).lower()
    for k, v in CITY_CANONICAL_MAP.items():
        if k in ascii_loc:
            return v
    return clean_vietnamese_text(loc_raw).title() or 'Vietnam'

def clean_address(addr_raw: str) -> str:
    """Convert Vietnamese address terms to clean English terms."""
    if not addr_raw:
        return 'Vietnam'
    ascii_addr = clean_vietnamese_text(addr_raw)
    ascii_addr = re.sub(r'\bduong\b', 'Street', ascii_addr, flags=re.IGNORECASE)
    ascii_addr = re.sub(r'\bquan\b', 'District', ascii_addr, flags=re.IGNORECASE)
    ascii_addr = re.sub(r'\bphuong\b', 'Ward', ascii_addr, flags=re.IGNORECASE)
    ascii_addr = re.sub(r'\btp\.?\b', 'City', ascii_addr, flags=re.IGNORECASE)
    return ascii_addr

def clean_display_name(raw: str) -> str:
    """Produce a clean, capitalized English title for display."""
    if not raw:
        return 'Hotel'
    ascii_name = clean_vietnamese_text(raw)
    text = re.sub(r'^(khach\s*san|khu\s*nghi\s*duong|ks|hotel|resort|the)\s+', '', ascii_name, flags=re.IGNORECASE).strip()
    text = re.sub(r'\s*\.*$', '', text)
    words = text.split()
    capitalized = ' '.join(w.capitalize() for w in words)
    capitalized = re.sub(r'\bHa Noi\b', 'Hanoi', capitalized, flags=re.IGNORECASE)
    capitalized = re.sub(r'\bDa Nang\b', 'Da Nang', capitalized, flags=re.IGNORECASE)
    capitalized = re.sub(r'\bPhu Quoc\b', 'Phu Quoc', capitalized, flags=re.IGNORECASE)
    capitalized = re.sub(r'\bSai Gon\b', 'Ho Chi Minh City', capitalized, flags=re.IGNORECASE)
    capitalized = re.sub(r'\bNha Trang\b', 'Nha Trang', capitalized, flags=re.IGNORECASE)
    return capitalized or ascii_name or 'Hotel'

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
                'hotel_address': clean_address(str(row.get('hotel_address', 'Vietnam')).strip()),
                'location': clean_location(str(row.get('location', '')).strip()),
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
            'how', 'is', 'what', 'where', 'who', 'why', 'when', 'are', 'was', 'were', 'do', 'does',
            'service', 'room', 'view', 'food', 'staff', 'please', 'tell', 'me', 'about', 'stay',
            'night', 'stars', 'star', 'address', 'location', 'can', 'you', 'i', 'we', 'my', 'your',
            'assist', 'help', 'hello', 'hi', 'hey', 'alo', 'there', 'here', 'this', 'that', 'with',
            'luxury', 'recommend', 'recommendation', 'best', 'good', 'bad', 'top', 'clean',
            'breakfast', 'pool', 'spa', 'gym', 'bed', 'price', 'any', 'some', 'much', 'many',
            'which', 'nearby', 'near', 'around', 'center', 'city'
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

        is_recommend_prompt = any(w in norm_q for w in ['recommend', 'suggest', 'where to stay', 'which hotel', 'best hotels', 'top hotels'])

        # 1. Exact Substring Match (requiring whole words and non-generic distinct tokens)
        for norm_key, hotel in self.hotel_lookup.items():
            distinct_tokens = [t for t in norm_key.split() if t not in self.stopwords and len(t) > 2]
            if not distinct_tokens:
                continue
            pattern = r'\b' + re.escape(norm_key) + r'\b'
            if re.search(pattern, norm_q):
                if len(distinct_tokens) >= 2 or (len(distinct_tokens) == 1 and len(distinct_tokens[0]) >= 6):
                    if not is_recommend_prompt or len(distinct_tokens) >= 2:
                        return hotel

        # 2. Inverted Index Candidate Scoring
        candidates = defaultdict(int)
        for token in q_tokens:
            for norm_key in self.inverted_index.get(token, set()):
                candidates[norm_key] += 3

        if not candidates:
            return None

        # Score candidates with token coverage and Jaccard
        best_match = None
        best_score = -1.0

        q_token_set = set(q_tokens)
        for norm_key, token_matches in candidates.items():
            hotel_tokens = set(w for w in norm_key.split() if w not in self.stopwords and len(w) > 2)
            if not hotel_tokens:
                continue
            intersection = q_token_set.intersection(hotel_tokens)
            if not intersection:
                continue

            coverage = len(intersection) / float(len(hotel_tokens))
            jaccard = len(intersection) / float(len(q_token_set.union(hotel_tokens)))
            score = (len(intersection) * 4.0) + (coverage * 6.0) + (jaccard * 5.0)

            # Location match bonus
            for city in CITY_MAP.values():
                if city in norm_q and city in norm_key:
                    score += 2.0

            if score > best_score:
                best_score = score
                best_match = self.hotel_lookup[norm_key]

        if best_score >= 6.5 and not is_recommend_prompt:
            return best_match
        elif best_score >= 9.0 and is_recommend_prompt:
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
# Multi-Task BERT & Generative QA Pipelines
# ---------------------------------------------------------------------------
class BertMultiTaskQA(nn.Module):
    """
    Multi-Task Extractive BERT QA model (modelv1.pt checkpoint)
    Backbone: bert-base-uncased with Aspect, Sentiment, and Extractive Span Heads.
    """
    def __init__(self, base_name: str = 'bert-base-uncased'):
        super().__init__()
        self.bert = AutoModel.from_pretrained(base_name)
        hidden_size = self.bert.config.hidden_size  # 768
        self.feature_proj = nn.Sequential(
            nn.Linear(10, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, hidden_size)
        )
        self.qa_outputs = nn.Linear(hidden_size, 2)
        self.aspect_classifier = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(hidden_size, 384),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(384, 6)
        )
        self.sentiment_classifier = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(hidden_size, 384),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(384, 3)
        )
        self.has_answer_classifier = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(hidden_size, 1)
        )

    def forward(self, input_ids, attention_mask=None, token_type_ids=None):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
        sequence_output = outputs[0]
        pooled_output = outputs[1]

        qa_logits = self.qa_outputs(sequence_output)
        start_logits, end_logits = qa_logits.split(1, dim=-1)
        start_logits = start_logits.squeeze(-1)
        end_logits = end_logits.squeeze(-1)

        aspect_logits = self.aspect_classifier(pooled_output)
        sentiment_logits = self.sentiment_classifier(pooled_output)
        has_answer_logits = self.has_answer_classifier(pooled_output)

        return {
            'start_logits': start_logits,
            'end_logits': end_logits,
            'aspect_logits': aspect_logits,
            'sentiment_logits': sentiment_logits,
            'has_answer_logits': has_answer_logits
        }


class HotelAspectQA_GenerativeBERT(nn.Module):
    """
    Unified Architecture combining:
    1. Pretrained BERT Encoder with 10-Feature Dense Context Fusion (Residual).
    2. KDD 2025 PLMR Aspect Rationale Generator (soft mask m_a).
    3. Aspect, Sentiment & 5-Level Ordinal Rating Heads (Weighted CORN Loss).
    4. Autoregressive BERT Decoder (BERT2BERT) for End-to-End Natural Answer Generation.
    """
    def __init__(self, model_name: str = 'bert-base-uncased', num_features: int = 10, num_aspects: int = 6, num_sentiments: int = 3, num_classes: int = 5):
        super().__init__()
        self.seq2seq = EncoderDecoderModel.from_encoder_decoder_pretrained(model_name, model_name)
        self.seq2seq.config.decoder_start_token_id = 101
        self.seq2seq.config.pad_token_id = 0
        self.seq2seq.config.eos_token_id = 102
        if hasattr(self.seq2seq, 'generation_config') and self.seq2seq.generation_config is not None:
            self.seq2seq.generation_config.decoder_start_token_id = 101
            self.seq2seq.generation_config.pad_token_id = 0
            self.seq2seq.generation_config.eos_token_id = 102

        h_dim = self.seq2seq.config.encoder.hidden_size

        self.feature_proj = nn.Sequential(
            nn.Linear(num_features, 64),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(64, h_dim)
        )
        self.rationale_generator = nn.Sequential(
            nn.Linear(h_dim, 128),
            nn.ReLU(),
            nn.Linear(128, num_aspects),
            nn.Sigmoid()
        )
        self.aspect_classifier = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(h_dim, 256),
            nn.GELU(),
            nn.Linear(256, num_aspects)
        )
        self.sentiment_classifier = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(h_dim, 256),
            nn.GELU(),
            nn.Linear(256, num_sentiments)
        )
        self.rating_predictor = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(h_dim, 256),
            nn.GELU(),
            nn.Linear(256, num_classes - 1)
        )

    def forward(self, input_ids, attention_mask=None, dense_features=None, labels=None):
        encoder_outputs = self.seq2seq.encoder(input_ids=input_ids, attention_mask=attention_mask)
        seq_rep = encoder_outputs.last_hidden_state
        pooled_rep = seq_rep[:, 0, :]
        if dense_features is not None:
            feat_emb = self.feature_proj(dense_features)
            fused_cls = pooled_rep + feat_emb
            fused_seq = seq_rep + feat_emb.unsqueeze(1) * 0.1
        else:
            fused_cls = pooled_rep
            fused_seq = seq_rep

        masks = self.rationale_generator(fused_seq)
        if attention_mask is not None:
            masks = masks * attention_mask.unsqueeze(-1).float()

        aspect_logits = self.aspect_classifier(fused_cls)
        sentiment_logits = self.sentiment_classifier(fused_cls)
        rating_logits = self.rating_predictor(fused_cls)

        encoder_container = BaseModelOutput(last_hidden_state=fused_seq)
        seq2seq_outputs = self.seq2seq(
            encoder_outputs=encoder_container,
            attention_mask=attention_mask,
            labels=labels
        )
        return {
            'gen_loss': seq2seq_outputs.loss if labels is not None else None,
            'gen_logits': seq2seq_outputs.logits,
            'aspect_logits': aspect_logits,
            'sentiment_logits': sentiment_logits,
            'rating_logits': rating_logits,
            'masks': masks
        }

    def generate_answer(self, tokenizer, prompt_text: str, dense_features=None, max_new_tokens: int = 150, device=None) -> str:
        self.eval()
        dev = device if device is not None else next(self.parameters()).device
        enc = tokenizer(prompt_text, max_length=384, truncation=True, return_tensors='pt').to(dev)
        cls_id = tokenizer.cls_token_id or 101
        pad_id = tokenizer.pad_token_id or 0
        sep_id = tokenizer.sep_token_id or 102
        with torch.no_grad():
            encoder_outputs = self.seq2seq.encoder(input_ids=enc['input_ids'], attention_mask=enc['attention_mask'])
            seq_rep = encoder_outputs.last_hidden_state
            if dense_features is not None:
                if not isinstance(dense_features, torch.Tensor):
                    dense_features = torch.tensor(dense_features, dtype=torch.float)
                if dense_features.ndim == 1:
                    dense_features = dense_features.unsqueeze(0)
                feat_emb = self.feature_proj(dense_features.to(dev))
                fused_seq = seq_rep + feat_emb.unsqueeze(1) * 0.1
            else:
                fused_seq = seq_rep
            encoder_container = BaseModelOutput(last_hidden_state=fused_seq)
            gen_ids = self.seq2seq.generate(
                encoder_outputs=encoder_container,
                attention_mask=enc['attention_mask'],
                max_new_tokens=max_new_tokens,
                num_beams=3,
                no_repeat_ngram_size=3,
                length_penalty=1.0,
                early_stopping=True,
                decoder_start_token_id=cls_id,
                pad_token_id=pad_id,
                eos_token_id=sep_id
            )
        return tokenizer.decode(gen_ids[0], skip_special_tokens=True).strip()


def clean_state_dict(raw_state_dict):
    """
    Cleans PyTorch checkpoints by stripping DataParallel ('module.')
    and wrapper ('model.') prefixes, and unboxing nested dict containers.
    """
    if not isinstance(raw_state_dict, dict):
        return raw_state_dict

    for key in ['state_dict', 'model_state_dict', 'model']:
        if key in raw_state_dict and isinstance(raw_state_dict[key], dict):
            raw_state_dict = raw_state_dict[key]
            break

    cleaned = {}
    for k, v in raw_state_dict.items():
        clean_k = k
        if clean_k.startswith('module.'):
            clean_k = clean_k[7:]
        if clean_k.startswith('model.'):
            clean_k = clean_k[6:]
        cleaned[clean_k] = v
    return cleaned


class GenerativeQAPipeline:
    def __init__(self, checkpoint_path: str = 'hotel_aspect_qa_model', model_name: str = 'google/flan-t5-base'):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.model_type = 'seq2seq'  # 'seq2seq' or 'extractive_bert'
        self.loaded_successfully = False
        self.active_model_name = 'model_v2.pt'
        self.inference_lock = threading.Lock()

        self._initialize(checkpoint_path)

    def _initialize(self, checkpoint_path: str):
        print(f"Loading Generative Model on {self.device}...")

        # Priority 1: Search for fine-tuned checkpoints in order (Generative v2 first)
        cand_candidates = [
            os.path.join(BASE_DIR, 'model', 'model_v2_bart.pt'),
            os.path.join(BASE_DIR, 'model_v2_bart.pt'),
            os.path.join(BASE_DIR, 'model', 'model_v2.pt'),
            os.path.join(BASE_DIR, 'model_v2.pt'),
            os.path.join(BASE_DIR, 'model.pt'),
            os.path.join(BASE_DIR, 'model', 'model_v1.pt'),
            os.path.join(BASE_DIR, checkpoint_path),
            checkpoint_path,
            os.path.join(BASE_DIR, 'model', 'modelv1.pt')
        ]
        for p in cand_candidates:
            if os.path.exists(p):
                if self.reload_model(p):
                    return

        # Priority 2: Fallback to base pretrained FLAN-T5
        if not self.loaded_successfully:
            try:
                print(f"Loading base pretrained model {self.model_name}...")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name).to(self.device)
                self.model.eval()
                self.model_type = 'seq2seq'
                self.loaded_successfully = True
                self.active_model_name = 'FLAN-T5 Base'
                print(f"Base generative neural engine ready: {self.active_model_name}")
            except Exception as e:
                print(f"Notice: Could not load base neural weights ({e}). Grounded contextual generator will act as fallback.")
                self.loaded_successfully = False

    def reload_model(self, custom_model_path: str = 'model.pt') -> bool:
        """Dynamically reload new weights into memory with thread safety."""
        with self.inference_lock:
            try:
                print(f"Reloading custom model weights from {custom_model_path}...")
                if not os.path.exists(custom_model_path):
                    print(f"Notice: Path {custom_model_path} does not exist.")
                    return False

                # 1. Directory format (HuggingFace saved folder)
                if os.path.isdir(custom_model_path):
                    self.tokenizer = AutoTokenizer.from_pretrained(custom_model_path)
                    self.model = AutoModelForSeq2SeqLM.from_pretrained(custom_model_path).to(self.device)
                    self.model_type = 'seq2seq'
                    self.model.eval()
                    self.loaded_successfully = True
                    self.active_model_name = os.path.basename(custom_model_path)
                    print(f"Successfully reloaded model directory from {custom_model_path}.")
                    return True

                # 2. Checkpoint file (.pt, .bin, .safetensors)
                state_dict = None
                if custom_model_path.endswith('.safetensors'):
                    if safetensors_load_file is not None:
                        state_dict = safetensors_load_file(custom_model_path, device=str(self.device))
                    else:
                        raise RuntimeError("safetensors package is required to load .safetensors checkpoint")
                else:
                    state_dict = torch.load(custom_model_path, map_location=self.device)

                cleaned_dict = clean_state_dict(state_dict)

                # Architecture detection:
                # 1. Generative BERT (BERT2BERT / HotelAspectQA_GenerativeBERT)
                is_gen_bert = any('seq2seq.' in k or 'encoder.bert.' in k or 'decoder.bert.' in k for k in cleaned_dict.keys())
                # 2. BART Seq2Seq
                is_bart = any('model.encoder.layers' in k or 'model.decoder.layers' in k for k in cleaned_dict.keys()) or 'bart' in custom_model_path.lower()
                # 3. Extractive Multi-Task BERT
                is_extractive_bert = any(k.startswith('bert.') or 'qa_outputs.weight' in k for k in cleaned_dict.keys()) and not is_gen_bert

                if is_gen_bert:
                    print(f"Detected HotelAspectQA_GenerativeBERT architecture in {custom_model_path}")
                    self.tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
                    m_bert = HotelAspectQA_GenerativeBERT()
                    m_bert.seq2seq.config.decoder_start_token_id = self.tokenizer.cls_token_id
                    m_bert.seq2seq.config.pad_token_id = self.tokenizer.pad_token_id
                    m_bert.seq2seq.config.eos_token_id = self.tokenizer.sep_token_id
                    if hasattr(m_bert.seq2seq, 'generation_config') and m_bert.seq2seq.generation_config is not None:
                        m_bert.seq2seq.generation_config.decoder_start_token_id = self.tokenizer.cls_token_id
                        m_bert.seq2seq.generation_config.pad_token_id = self.tokenizer.pad_token_id
                        m_bert.seq2seq.generation_config.eos_token_id = self.tokenizer.sep_token_id
                    missing, unexpected = m_bert.load_state_dict(cleaned_dict, strict=False)
                    print(f"Loaded Generative BERT. Missing: {len(missing)}, Unexpected: {len(unexpected)}")
                    self.model = m_bert.to(self.device)
                    self.model.eval()
                    self.model_type = 'generative_bert'
                elif is_bart:
                    print(f"Detected BART Seq2Seq architecture in {custom_model_path}")
                    self.tokenizer = AutoTokenizer.from_pretrained('facebook/bart-base')
                    bart_m = AutoModelForSeq2SeqLM.from_pretrained('facebook/bart-base')
                    missing, unexpected = bart_m.load_state_dict(cleaned_dict, strict=False)
                    print(f"Loaded BART Seq2Seq. Missing: {len(missing)}, Unexpected: {len(unexpected)}")
                    self.model = bart_m.to(self.device)
                    self.model.eval()
                    self.model_type = 'seq2seq'
                elif is_extractive_bert:
                    print(f"Detected Extractive Multi-Task BERT architecture in {custom_model_path}")
                    self.tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
                    bert_m = BertMultiTaskQA('bert-base-uncased')
                    missing, unexpected = bert_m.load_state_dict(cleaned_dict, strict=False)
                    print(f"Loaded BERT state_dict. Missing keys: {len(missing)}, Unexpected keys: {len(unexpected)}")
                    self.model = bert_m.to(self.device)
                    self.model.eval()
                    self.model_type = 'extractive_bert'
                else:
                    print(f"Detected Generative Seq2Seq (FLAN-T5) architecture in {custom_model_path}")
                    self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                    t5_m = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
                    missing, unexpected = t5_m.load_state_dict(cleaned_dict, strict=False)
                    print(f"Loaded T5 state_dict. Missing keys: {len(missing)}, Unexpected keys: {len(unexpected)}")
                    self.model = t5_m.to(self.device)
                    self.model.eval()
                    self.model_type = 'seq2seq'

                self.loaded_successfully = True
                self.active_model_name = os.path.basename(custom_model_path)
                print(f"Successfully reloaded {self.model_type} weights from {custom_model_path}.")
                return True
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Failed to reload model {custom_model_path}: {e}")
                return False

    def generate(self, prompt_text: str, max_new_tokens: int = 180, context_text: Optional[str] = None) -> str:
        if not self.loaded_successfully or self.model is None or self.tokenizer is None:
            return ""

        try:
            with self.inference_lock:
                if self.model_type == 'generative_bert':
                    if hasattr(self.model, 'generate_answer'):
                        ans = self.model.generate_answer(self.tokenizer, prompt_text, max_new_tokens=max_new_tokens, device=self.device)
                    else:
                        enc = self.tokenizer(prompt_text, max_length=512, truncation=True, return_tensors='pt').to(self.device)
                        with torch.no_grad():
                            outputs = self.model.seq2seq.generate(
                                input_ids=enc['input_ids'],
                                attention_mask=enc['attention_mask'],
                                max_new_tokens=max_new_tokens,
                                num_beams=3,
                                no_repeat_ngram_size=3
                            )
                        ans = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
                    if ans:
                        return ans
                    return ""
                elif self.model_type == 'extractive_bert':
                    q = prompt_text
                    ctx = context_text or prompt_text
                    inputs = self.tokenizer(q, ctx, max_length=512, truncation=True, return_tensors='pt').to(self.device)
                    with torch.no_grad():
                        out = self.model(**inputs)
                        s_logits = out['start_logits'][0].clone()
                        e_logits = out['end_logits'][0].clone()
                        token_types = inputs.get('token_type_ids', None)

                        # Mask CLS token and all question tokens (token_type_ids == 0) so answer comes strictly from context
                        seq_len = inputs['input_ids'].shape[1]
                        for idx in range(seq_len):
                            if token_types is not None and token_types[0][idx] == 0:
                                s_logits[idx] = -1e4
                                e_logits[idx] = -1e4
                            elif idx == 0:
                                s_logits[idx] = -1e4
                                e_logits[idx] = -1e4

                        best_score = -1e4
                        best_s, best_e = 0, 0
                        for s in range(1, seq_len):
                            if s_logits[s] <= -1e3:
                                continue
                            for e in range(s, min(seq_len, s + 50)):
                                if e_logits[e] <= -1e3:
                                    continue
                                sc = s_logits[s].item() + e_logits[e].item()
                                if sc > best_score:
                                    best_score = sc
                                    best_s, best_e = s, e

                        if best_s > 0 and best_s <= best_e:
                            extracted = self.tokenizer.decode(inputs['input_ids'][0][best_s:best_e+1], skip_special_tokens=True).strip()
                            if extracted and len(extracted) > 3:
                                return extracted
                    return ""
                else:
                    enc = self.tokenizer(prompt_text, max_length=512, truncation=True, return_tensors='pt').to(self.device)
                    with torch.no_grad():
                        outputs = self.model.generate(
                            input_ids=enc['input_ids'],
                            attention_mask=enc['attention_mask'],
                            max_new_tokens=max_new_tokens,
                            num_beams=2,
                            no_repeat_ngram_size=2,
                            repetition_penalty=1.15
                        )
                    ans = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
                    if ans:
                        return ans

                    # Secondary fallback with sampling if beam search was empty
                    with torch.no_grad():
                        outputs = self.model.generate(
                            input_ids=enc['input_ids'],
                            attention_mask=enc['attention_mask'],
                            max_new_tokens=max_new_tokens,
                            temperature=0.7,
                            top_p=0.9,
                            do_sample=True
                        )
                    return self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        except Exception as e:
            print(f"Neural generation notice: {e}")
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

    def search_database_by_criteria(self, query: str, top_n: int = 3) -> List[Tuple[Dict[str, Any], str]]:
        """Retrieve top matching hotel properties and review excerpts based on location, amenities, and ratings."""
        clean_q = clean_vietnamese_text(query).lower()

        target_city = None
        for k, v in CITY_CANONICAL_MAP.items():
            if k in clean_q or v.lower() in clean_q:
                target_city = v.lower()
                break

        aspect_kws = []
        for asp, kws in ASPECT_KEYWORDS.items():
            for kw in kws:
                if kw in clean_q:
                    aspect_kws.append(kw)

        candidates = []
        for norm_key, hotel in self.database.items():
            loc = hotel.get('location', '').lower()
            addr = hotel.get('hotel_address', '').lower()

            if target_city and (target_city not in loc and target_city not in addr and target_city not in norm_key):
                continue

            score = hotel.get('score', 4.0)
            reviews = hotel.get('reviews', [])
            rev_count = len(reviews)

            kw_hits = 0
            best_rev = ""
            for r in reviews:
                t_lower = r.get('text', '').lower()
                matches = sum(1 for kw in aspect_kws if kw in t_lower)
                if matches > kw_hits:
                    kw_hits = matches
                    best_rev = r.get('text', '')[:140]

            if not best_rev and reviews:
                best_rev = reviews[0].get('text', '')[:140]

            rank_score = (score * 2.5) + (min(rev_count, 60) * 0.1) + (kw_hits * 2.0)
            candidates.append((rank_score, hotel, best_rev))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [(c[1], c[2]) for c in candidates[:top_n]]

    def answer_query(self, session_id: str, user_query: str) -> Dict[str, Any]:
        state = self.sessions.get_session(session_id)
        with state.lock:
            clean_q = clean_vietnamese_text(user_query).strip() or user_query.strip()
            intent, aspect = self.detect_intent_and_aspect(user_query)

            # Hotel Resolution
            matched_hotel = self.matcher.match(user_query)
            was_coref = False

            if matched_hotel:
                state.current_hotel = matched_hotel
            elif state.current_hotel and any(w in clean_q.lower() for w in [
                'it', 'hotel', 'resort', 'service', 'star', 'location', 'address', 'room',
                'breakfast', 'pool', 'stay', 'price', 'here', 'there', 'this'
            ] + [kw for kws in ASPECT_KEYWORDS.values() for kw in kws]):
                matched_hotel = state.current_hotel
                was_coref = True

            # ------------------------------------------------------------------
            # Scenario A: A specific hotel property is identified
            # ------------------------------------------------------------------
            if matched_hotel:
                h_name = matched_hotel.get('hotel_name', 'The Hotel')
                addr = matched_hotel.get('hotel_address', 'Vietnam')
                loc = matched_hotel.get('location', 'Vietnam')
                star_label = matched_hotel.get('star', 'Standard')
                tot_revs = len(matched_hotel.get('reviews', []))

                # Retrieve Multi-Review Evidence with Feature 10 Decay
                cand_reviews = self.retriever.retrieve(matched_hotel, aspect)
                sent_summary = self.retriever.aggregate_sentiment(cand_reviews)
                consensus = sent_summary['consensus']
                avg_score = sent_summary['avg_score']

                # Build Google Maps Embed Card if Location Inquired
                maps_card = None
                if intent == 'location' or any(k in clean_q.lower() for k in ['where', 'address', 'location', 'map', 'o dau', 'dia chi']):
                    search_query = f"{h_name}, {addr}" if addr else f"{h_name}, Vietnam"
                    encoded_loc = urllib.parse.quote(search_query)
                    maps_card = {
                        "hotel_name": h_name,
                        "address": addr,
                        "location": loc,
                        "search_url": f"https://www.google.com/maps/search/?api=1&query={encoded_loc}",
                        "embed_url": f"https://maps.google.com/maps?q={encoded_loc}&t=&z=15&ie=UTF8&iwloc=&output=embed"
                    }

                # Format evidence context
                rev_lines = [
                    f"[Review {i+1} | Date: {r['date']} | Score: {r['score']}/5.0 | Recency Weight: {r['recency_weight']:.2f}]: {r['text'][:200]}"
                    for i, r in enumerate(cand_reviews)
                ]
                rev_context = "\n".join(rev_lines) if rev_lines else "No specific customer reviews available."

                # Conditioned Prompt matching training architecture
                chat_hist_str = "None"
                if state.history:
                    last_turn = state.history[-1]
                    chat_hist_str = f"User: {last_turn.get('user', '')}\nAssistant: {last_turn.get('bot', '')}"

                prompt = (
                    f"Answer the user inquiry based on the hotel information and customer reviews below.\n"
                    f"Chat History: {chat_hist_str}\n"
                    f"User Inquiry: {clean_q}\n"
                    f"Hotel: {h_name} | Star Rating: {star_label} | Total Reviews: {tot_revs} | Location: {loc} | Address: {addr} | Average Score: {avg_score:.1f}/5.0\n"
                    f"Relevant Reviews (Ranked by Feature 10 Recency Weight w = exp(-0.03 * delta_m)):\n"
                    f"{rev_context}"
                )

                bert_context = f"{h_name} is a {star_label} property in {loc}, {addr}. Overall rating is {avg_score:.1f}/5.0 stars with {tot_revs} reviews. {rev_context}"
                neural_ans = self.pipeline.generate(clean_q if self.pipeline.model_type == 'extractive_bert' else prompt, context_text=bert_context)
                if not neural_ans:
                    neural_ans = f"{h_name} is a {star_label} property in {loc}, with {tot_revs} reviews documented. Average guest satisfaction is rated {avg_score:.1f} out of 5.0 stars."

                # Format original reviews data for UI
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
                    "score": round(avg_score, 1),
                    "total_reviews": tot_revs,
                    "aspect": aspect,
                    "aspect_title": ASPECT_DISPLAY.get(aspect, aspect),
                    "sentiment": consensus.capitalize(),
                    "confidence": 0.95,
                    "maps_card": maps_card,
                    "original_reviews": original_reviews_data,
                    "context_applied": was_coref
                }

                state.history.append({"user": user_query, "bot": neural_ans})
                return response_payload

            # ------------------------------------------------------------------
            # Scenario B: No specific hotel matched -> Dynamic Database Retrieval
            # ------------------------------------------------------------------
            candidate_hotels = self.search_database_by_criteria(user_query, top_n=3)

            is_recommendation = bool(candidate_hotels) and any(
                w in clean_q.lower() for w in [
                    'hotel', 'resort', 'stay', 'recommend', 'where', 'place', 'khach san',
                    'good', 'best', 'top', 'pool', 'breakfast', 'room', 'luxury', 'beach', 'view'
                ] + list(CITY_CANONICAL_MAP.keys())
            )

            if is_recommendation:
                hotel_lines = []
                orig_revs = []
                top_h = candidate_hotels[0][0]
                for i, (h, rev_quote) in enumerate(candidate_hotels, 1):
                    hotel_lines.append(
                        f"[{i}] {h['hotel_name']} ({h['star']}, Score: {h['score']}/5.0, {h['location']}, Address: {h['hotel_address']}). Guest review: \"{rev_quote}\""
                    )
                    orig_revs.append({
                        "date": "Recent",
                        "score": h['score'],
                        "recency_weight": 1.0,
                        "text": f"{h['hotel_name']} ({h['location']}): {rev_quote}"
                    })
                ctx = "\n".join(hotel_lines)
                prompt = (
                    f"Answer the user inquiry based on the retrieved hotel database records and customer reviews below.\n"
                    f"User Inquiry: {clean_q}\n"
                    f"Retrieved Properties from Knowledge Base:\n"
                    f"{ctx}\n"
                    f"Answer in natural conversational language:"
                )

                bert_ctx = f"Recommended hotels in Vietnam: {ctx}"
                neural_ans = self.pipeline.generate(clean_q if self.pipeline.model_type == 'extractive_bert' else prompt, context_text=bert_ctx)
                if not neural_ans:
                    neural_ans = f"Based on verified guest reviews, recommended accommodations include {top_h.get('hotel_name')} ({top_h.get('star', 'Standard')}) in {top_h.get('location', 'Vietnam')}, rated {top_h.get('score', 4.0):.1f}/5.0 stars."

                response_payload = {
                    "answer": neural_ans,
                    "hotel_name": top_h.get('hotel_name'),
                    "star": top_h.get('star'),
                    "score": round(top_h.get('score', 4.0), 1),
                    "total_reviews": len(top_h.get('reviews', [])),
                    "aspect": aspect,
                    "aspect_title": "Recommendations",
                    "sentiment": "Positive",
                    "confidence": 0.90,
                    "maps_card": None,
                    "original_reviews": orig_revs,
                    "context_applied": False
                }
                state.history.append({"user": user_query, "bot": neural_ans})
                return response_payload

            # ------------------------------------------------------------------
            # Scenario C: General Inquiry or Greeting -> Conversational Generation
            # ------------------------------------------------------------------
            gen_prompt = (
                f"You are a helpful AI assistant specializing in hotel reviews, travel and accommodations in Vietnam. "
                f"Answer the user inquiry directly in helpful, natural conversational language:\n"
                f"User Inquiry: {clean_q}\n"
                f"Answer:"
            )
            neural_ans = self.pipeline.generate(gen_prompt, context_text="AI Assistant for hotel accommodations and verified guest reviews across Vietnam.")
            if not neural_ans:
                neural_ans = "Hello, I am your AI assistant specializing in hotel reviews, service quality, and accommodations across Vietnam. How can I help you today?"

            response_payload = {
                "answer": neural_ans,
                "hotel_name": None,
                "star": None,
                "score": None,
                "total_reviews": None,
                "aspect": None,
                "aspect_title": None,
                "sentiment": None,
                "confidence": 0.85,
                "maps_card": None,
                "original_reviews": [],
                "context_applied": False
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
    
    # RFC 2046: Initial boundary starts with --boundary, delimiter between parts is \r\n--boundary
    init_delim = b'--' + boundary
    if body.startswith(init_delim):
        body = body[len(init_delim):]
        if body.startswith(b'\r\n'):
            body = body[2:]

    delim = b'\r\n--' + boundary
    parts = body.split(delim)
    for part in parts:
        if b'Content-Disposition:' in part:
            header_end = part.find(b'\r\n\r\n')
            if header_end != -1:
                headers_part = part[:header_end].decode('utf-8', errors='ignore')
                file_content = part[header_end + 4:]

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
            active_m = getattr(BOT.pipeline, 'active_model_name', 'model_v2.pt') if BOT and BOT.pipeline else 'Seq2Seq Engine'
            self.wfile.write(json.dumps({
                'status': 'ok',
                'hotels_loaded': len(HOTEL_DATABASE),
                'model_loaded': BOT.pipeline.loaded_successfully if BOT and BOT.pipeline else False,
                'active_model': active_m
            }).encode('utf-8'))
            return

        if parsed.path == '/api/models':
            models = []
            active_m = getattr(BOT.pipeline, 'active_model_name', '') if BOT and BOT.pipeline else ''

            # Scan model/ directory
            model_dir = os.path.join(BASE_DIR, 'model')
            if os.path.exists(model_dir):
                for fname in sorted(os.listdir(model_dir)):
                    if fname.endswith(('.pt', '.bin', '.safetensors')):
                        fpath = os.path.join(model_dir, fname)
                        size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 1)
                        is_active = (fname == active_m) or (not active_m and fname == 'model_v2.pt')
                        models.append({
                            'name': fname,
                            'path': f"model/{fname}",
                            'size_mb': size_mb,
                            'active': is_active,
                            'is_active': is_active
                        })

            # Check root model.pt if exists
            root_model = os.path.join(BASE_DIR, 'model.pt')
            if os.path.exists(root_model) and not any(m['name'] == 'model.pt' for m in models):
                models.append({
                    'name': 'model.pt',
                    'path': 'model.pt',
                    'size_mb': round(os.path.getsize(root_model) / (1024 * 1024), 1),
                    'active': active_m == 'model.pt',
                    'is_active': active_m == 'model.pt'
                })

            if not any(m['active'] for m in models) and models:
                models[0]['active'] = True
                active_m = models[0]['name']

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'models': models,
                'active_model': active_m or (models[0]['name'] if models else 'Default')
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

            if not isinstance(data, dict):
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
        elif parsed.path == '/api/select-model':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_len).decode('utf-8')
                data = json.loads(body)
                model_name = data.get('model_name') or data.get('name') or data.get('model_path')
                if not model_name:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Missing model_name parameter'}).encode('utf-8'))
                    return

                # Strict sanitization against path traversal: only basename
                clean_name = os.path.basename(model_name)
                candidate_paths = [
                    os.path.join(BASE_DIR, 'model', clean_name),
                    os.path.join(BASE_DIR, clean_name)
                ]
                target_path = None
                for p in candidate_paths:
                    if os.path.exists(p) and (p.endswith(('.pt', '.bin', '.safetensors')) or os.path.isdir(p)):
                        target_path = p
                        break

                if not target_path:
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': f'Model {clean_name} not found in model/ directory'}).encode('utf-8'))
                    return

                if BOT is None:
                    with BOT_INIT_LOCK:
                        if BOT is None:
                            BOT = ConversationalQABot(HOTEL_DATABASE)

                success = BOT.pipeline.reload_model(target_path)
                selected_name = os.path.basename(target_path)
                if success:
                    BOT.pipeline.active_model_name = selected_name
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'status': 'success',
                        'active_model': selected_name,
                        'message': f'Model {selected_name} loaded successfully'
                    }).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': f'Failed to reload model weights from {selected_name}'}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
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
