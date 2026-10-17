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
from transformers import BertModel, BertTokenizerFast

# ---------------------------------------------------------------------------
# Constants & Mappings
# ---------------------------------------------------------------------------
ASPECTS = ['Service', 'Facility', 'Experience', 'Amenity', 'Loyalty', 'Branding']
SENTIMENTS = ['Negative', 'Positive', 'Neutral']

ASPECT_TRANSLATIONS = {
    'Service': {'en': 'Customer Service & Staff', 'vi': 'Dịch vụ & Nhân viên'},
    'Facility': {'en': 'Rooms & Facilities', 'vi': 'Cơ sở vật chất & Phòng ốc'},
    'Experience': {'en': 'Overall Guest Experience', 'vi': 'Trải nghiệm tổng quan'},
    'Amenity': {'en': 'Amenities & Dining', 'vi': 'Tiện ích, Ẩm thực & Bể bơi'},
    'Loyalty': {'en': 'Guest Loyalty & Recommendation', 'vi': 'Sự trung thành & Đề xuất'},
    'Branding': {'en': 'Brand Prestige & Reputation', 'vi': 'Uy tín & Thương hiệu'}
}

SENTIMENT_TRANSLATIONS = {
    'Negative': {'en': 'Negative (Complaint)', 'vi': 'Tiêu cực (Phàn nàn)'},
    'Positive': {'en': 'Positive (Praise)', 'vi': 'Tích cực (Khen ngợi)'},
    'Neutral': {'en': 'Neutral (Mixed / Factual)', 'vi': 'Trung tính (Khách quan)'}
}

ASPECT_KEYWORDS = {
    'Service': [
        'service', 'staff', 'employee', 'waiter', 'reception', 'check-in', 'checkout', 'attitude', 'helpful', 'friendly', 'slow', 'hospitality',
        'dịch vụ', 'phục vụ', 'nhân viên', 'lễ tân', 'thái độ', 'chu đáo', 'nhiệt tình', 'tiếp đón', 'hỗ trợ', 'chăm sóc'
    ],
    'Facility': [
        'facility', 'room', 'bed', 'bathroom', 'shower', 'clean', 'dirty', 'air conditioner', 'ac', 'tv', 'balcony', 'sheet', 'towel', 'maintenance',
        'cơ sở vật chất', 'phòng', 'phòng ốc', 'giường', 'vệ sinh', 'nhà tắm', 'vòi sen', 'tiện nghi', 'thoáng mát', 'rộng rãi'
    ],
    'Experience': [
        'experience', 'stay', 'trip', 'atmosphere', 'vibe', 'view', 'vacation', 'noise', 'quiet', 'overall', 'general',
        'trải nghiệm', 'kỳ nghỉ', 'không khí', 'yên tĩnh', 'ấn tượng', 'hài lòng', 'cảnh quan', 'nghỉ dưỡng'
    ],
    'Amenity': [
        'amenity', 'amenities', 'pool', 'swimming pool', 'gym', 'fitness', 'breakfast', 'buffet', 'food', 'restaurant', 'spa', 'wifi', 'parking',
        'bể bơi', 'hồ bơi', 'ăn sáng', 'tiện ích', 'nhà hàng', 'món ăn', 'ẩm thực', 'buffet', 'phòng gym'
    ],
    'Loyalty': [
        'loyalty', 'recommend', 'return', 'come back', 'again', 'visit again', 'book again', 'next trip', 'worth',
        'quay lại', 'giới thiệu', 'đáng giá', 'trở lại', 'ủng hộ', 'đặt phòng tiếp'
    ],
    'Branding': [
        'brand', 'branding', 'reputation', 'luxury', 'advertised', 'photos', 'standard',
        'thương hiệu', 'danh tiếng', 'tiêu chuẩn', 'đẳng cấp', 'quảng cáo', 'uy tín'
    ]
}

LOCATION_KEYWORDS = [
    'where', 'location', 'address', 'located', 'situated', 'map', 'directions', 'find',
    'ở đâu', 'địa chỉ', 'vị trí', 'nằm ở', 'nằm tại', 'chỗ nào', 'tọa lạc'
]

STAR_KEYWORDS = [
    'mấy sao', 'bao nhiêu sao', 'số sao', 'chuẩn sao', 'hạng sao', 'xếp hạng sao', 'tiêu chuẩn sao', 'đạt sao',
    'star', 'stars', 'how many stars', 'star rating', 'classification', 'hotel star', 'star level', 'xếp hạng'
]

COUNT_KEYWORDS = [
    'bao nhiêu đánh giá', 'bao nhiêu review', 'bao nhiêu nhận xét', 'số lượng đánh giá',
    'số lượng review', 'bao nhiêu người', 'có nhiều đánh giá', 'có nhiều review',
    'how many reviews', 'total reviews', 'review count', 'number of reviews', 'mấy review', 'mấy đánh giá'
]

COREFERENCE_PRONOUNS = [
    'it', 'this hotel', 'that hotel', 'the hotel', 'here', 'there', 'the property',
    'khách sạn này', 'khách sạn đó', 'chỗ này', 'chỗ đó', 'nó', 'ở đây', 'nơi này', 'ks này', 'ks đó'
]

VIETNAMESE_MARKERS = [
    'không', 'thế nào', 'ở đâu', 'ra sao', 'có', 'cho tôi', 'của', 'và', 'là', 'như',
    'khách sạn', 'phòng', 'nhân viên', 'dịch vụ', 'ăn sáng', 'bể bơi', 'đẹp', 'sạch'
]

CATEGORY_WORDS = {
    'khach san', 'ks', 'k s', 'hotel', 'resort', 'khu nghi duong',
    'spa', 'homestay', 'villa', 'hostel', 'nha khach', 'guesthouse',
    'inn', 'motel', 'suite', 'suites', 'residence', 'apartment', 'can ho'
}

LOCATION_MAP = {
    'ha noi': 'hà nội', 'hn': 'hà nội', 'hanoi': 'hà nội',
    'ho chi minh': 'tp. hcm', 'sai gon': 'tp. hcm', 'saigon': 'tp. hcm', 'hcm': 'tp. hcm', 'tphcm': 'tp. hcm',
    'da nang': 'đà nẵng', 'danang': 'đà nẵng',
    'phu quoc': 'kiên giang', 'phuquoc': 'kiên giang', 'kien giang': 'kiên giang',
    'nha trang': 'khánh hòa', 'nhatrang': 'khánh hòa', 'khanh hoa': 'khánh hòa',
    'hoi an': 'quảng nam', 'hoian': 'quảng nam', 'quang nam': 'quảng nam',
    'hue': 'thừa thiên huế', 'thua thien hue': 'thừa thiên huế',
    'da lat': 'lâm đồng', 'dalat': 'lâm đồng', 'lam dong': 'lâm đồng',
    'vung tau': 'bà rịa', 'vungtau': 'bà rịa', 'ba ria': 'bà rịa',
    'ha long': 'quảng ninh', 'halong': 'quảng ninh', 'quang ninh': 'quảng ninh',
    'sapa': 'lào cai', 'sa pa': 'lào cai', 'phan thiet': 'bình thuận', 'mui ne': 'bình thuận'
}

LOCATION_TOKENS = set()
for loc_phrase in LOCATION_MAP.keys():
    for tok in loc_phrase.split():
        LOCATION_TOKENS.add(tok)

NOISE_WORDS = {
    'xin chao', 'chao ban', 'chao em', 'chao anh', 'chao chi', 'hello', 'hi', 'hey', 'ban la ai',
    'cho minh hoi', 'cho hoi', 'cho em hoi', 'ban oi', 'ad oi', 'alo',
    'review', 'danh gia', 'o dau', 'tai dau', 'o', 'tai', 'cho nao',
    'nhu the nao', 'the nao', 'co tot khong', 'chat luong', 'dich vu',
    'phong', 'an sang', 'be boi', 'gia phong', 'co', 'khong', 'sao', 'nao',
    'rat', 'qua', 'lam', 'cua', 'va', 'la', 'nhung', 'voi', 'duoc', 've',
    'ban', 'minh', 'toi', 'em', 'anh', 'chi', 'ai', 'gi', 'nay', 'do', 'kia'
}

def strip_vietnamese(text: str) -> str:
    """Chuẩn hóa văn bản tiếng Việt: loại bỏ dấu thanh, chuyển đ/Đ -> d, xóa ký tự đặc biệt."""
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = text.replace('đ', 'd').replace('Đ', 'd')
    text = re.sub(r'[^\w\s]', ' ', text)
    return ' '.join(text.split())

def is_vietnamese_query(text: str) -> bool:
    t_lower = text.lower()
    if re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', t_lower):
        return True
    return any(re.search(r'\b' + re.escape(w) + r'\b', t_lower) for w in VIETNAMESE_MARKERS)

# ---------------------------------------------------------------------------
# Model Architecture: HotelAspectQA_BERT with 10-Feature Dense Context Fusion
# (Exact match with Training_Kaggle.ipynb and model/model.pt)
# ---------------------------------------------------------------------------
class HotelAspectQA_BERT(nn.Module):
    def __init__(self, model_name="bert-base-uncased", num_aspects=6, num_sentiments=3, num_features=10):
        super().__init__()
        self.num_aspects = num_aspects
        self.num_sentiments = num_sentiments
        self.num_features = num_features

        self.bert = BertModel.from_pretrained(model_name)
        h_dim = self.bert.config.hidden_size  # 768

        # 10 Engineered Features Projection Layer (Mục 5 Project.ipynb)
        self.feature_proj = nn.Sequential(
            nn.Linear(self.num_features, 64),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(64, h_dim)
        )

        # 1. Span Extraction Head (Token-level: start & end logits)
        self.qa_outputs = nn.Linear(h_dim, 2)

        # 2. Aspect Classification Head (Sequence-level: 6 aspects)
        self.aspect_classifier = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(h_dim, h_dim // 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(h_dim // 2, self.num_aspects)
        )

        # 3. Sentiment Classification Head (Sequence-level: 3 sentiments)
        self.sentiment_classifier = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(h_dim, h_dim // 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(h_dim // 2, self.num_sentiments)
        )

        # 4. Answerability Verification Head (Binary logit)
        self.has_answer_classifier = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(h_dim, 1)
        )

    def forward(self, input_ids, attention_mask, token_type_ids=None, dense_features=None):
        bert_outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            return_dict=True
        )

        sequence_rep = bert_outputs.last_hidden_state  # (B, L, 768)
        pooled_rep = bert_outputs.pooler_output        # (B, 768)

        # Residual-style context fusion with 10 features
        if dense_features is not None:
            feat_emb = self.feature_proj(dense_features)  # (B, 768)
            fused_rep = pooled_rep + feat_emb             # (B, 768)
        else:
            fused_rep = pooled_rep

        # Span extraction logits
        logits = self.qa_outputs(sequence_rep)         # (B, L, 2)
        start_logits, end_logits = logits.split(1, dim=-1)
        start_logits = start_logits.squeeze(-1)        # (B, L)
        end_logits = end_logits.squeeze(-1)            # (B, L)

        aspect_logits = self.aspect_classifier(fused_rep)        # (B, 6)
        sentiment_logits = self.sentiment_classifier(fused_rep)  # (B, 3)
        has_ans_logits = self.has_answer_classifier(fused_rep).squeeze(-1)  # (B,)

        return {
            'start_logits': start_logits,
            'end_logits': end_logits,
            'aspect_logits': aspect_logits,
            'sentiment_logits': sentiment_logits,
            'has_answer_logits': has_ans_logits,
            'has_ans_logits': has_ans_logits
        }

# ---------------------------------------------------------------------------
# Global Hotel Knowledge Base Loader
# ---------------------------------------------------------------------------
HOTEL_DATABASE = {}

def load_hotel_database():
    global HOTEL_DATABASE
    search_paths = [
        'data/feature/TripAdvisor_Feature.json',
        'data/dataset/TripAdvisor_EN.json',
        '../data/feature/TripAdvisor_Feature.json',
        '../data/dataset/TripAdvisor_EN.json'
    ]
    data_file = None
    for p in search_paths:
        if os.path.exists(p):
            data_file = p
            break

    if not data_file:
        print("[Warning] Dataset file not found in default paths. HOTEL_DATABASE is empty.")
        return

    print(f"Loading hotel knowledge base from: {data_file}...")
    with open(data_file, 'r', encoding='utf-8') as f:
        items = json.load(f)

    for idx, item in enumerate(items, 1):
        data_block = item.get('data', {})
        text = data_block.get('text', '').strip()
        if not text:
            continue

        meta = data_block.get('meta_info', {})
        h_name = meta.get('hotel name', meta.get('normalized_title', 'The Hotel')).strip()
        h_address = meta.get('hotel address', 'Vietnam').strip()
        h_location = meta.get('location', '').strip()
        h_star = meta.get('star', '').strip()
        score = float(meta.get('score', 3.0))

        h_key = h_name.lower()
        if h_key not in HOTEL_DATABASE:
            HOTEL_DATABASE[h_key] = {
                'hotel_name': h_name,
                'hotel_address': h_address,
                'location': h_location,
                'star': h_star,
                'score': score,
                'reviews': []
            }

        feat_dict = item.get('features')
        if feat_dict and 'feat_aspect_count' in feat_dict:
            feat_vec = [
                float(feat_dict.get('feat_aspect_count', 0)) / 6.0,
                float(ASPECTS.index(feat_dict.get('feat_dominant_aspect', 'Service')) if feat_dict.get('feat_dominant_aspect') in ASPECTS else 0) / 5.0,
                float(feat_dict.get('feat_net_sentiment_score', 0.0)),
                float(feat_dict.get('feat_sentiment_conflict', 0)),
                float(feat_dict.get('feat_evidence_density', 0.0)),
                float(feat_dict.get('feat_avg_rationale_len', 0.0)) / 100.0,
                float(feat_dict.get('feat_has_cross_overlap', 0)),
                float(feat_dict.get('feat_service_sentiment', 0)),
                float(feat_dict.get('feat_facility_sentiment', 0)),
                float(feat_dict.get('feat_temporal_aspect_sentiment', 0.0))
            ]
        else:
            feat_vec = [0.5, 0.0, 0.5, 0.0, 0.3, 0.3, 0.0, 1.0, 1.0, 0.2]

        year = int(meta.get('year', 0)) if str(meta.get('year', '')).isdigit() else 2015
        month = int(meta.get('month', 0)) if str(meta.get('month', '')).isdigit() else 1
        date_str = meta.get('date', f"{year}-{month:02d}")
        rev_score = float(meta.get('score', score)) if str(meta.get('score', '')).replace('.', '', 1).isdigit() else score
        ref_id = meta.get('ref_id', f"rev_{idx}")

        m_val = year * 12 + month
        if 'max_m' not in HOTEL_DATABASE[h_key] or m_val > HOTEL_DATABASE[h_key]['max_m']:
            HOTEL_DATABASE[h_key]['max_m'] = m_val

        present_aspects = set()
        for ann in item.get('annotations', []):
            for res in ann.get('result', []):
                if res.get('from_name') == 'entities':
                    lbls = res.get('value', {}).get('labels', [])
                    if lbls and lbls[0] in ASPECTS:
                        present_aspects.add(lbls[0])
        t_low = text.lower()
        for asp, kws in ASPECT_KEYWORDS.items():
            if any(re.search(r'\b' + re.escape(kw) + r'\b', t_low) for kw in kws):
                present_aspects.add(asp)

        HOTEL_DATABASE[h_key]['reviews'].append({
            'review_id': idx,
            'ref_id': ref_id,
            'text': text,
            'features': feat_vec,
            'year': year,
            'month': month,
            'date': date_str,
            'score': rev_score,
            'present_aspects': list(present_aspects),
            'raw_features': feat_dict
        })

    print(f"Indexed {len(HOTEL_DATABASE):,} unique hotels with {len(items):,} reviews.")

# Tự động nạp CSDL khách sạn khi module được import
load_hotel_database()

# ---------------------------------------------------------------------------
# Robust Hotel Entity Matcher (Inverted Index + Distinctive Brand Tokens + Location Bonus)
# ---------------------------------------------------------------------------
class RobustHotelMatcher:
    """Bộ nhận diện thực thể tên khách sạn siêu tốc và chính xác cao."""
    def __init__(self, hotel_database: dict):
        self.db = hotel_database
        self.inverted_index = defaultdict(set)
        self.hotel_profiles = {}
        self.coref_patterns = [
            'khach san nay', 'khach san do', 'cho nay', 'cho do', 'o day', 'o do',
            'noi nay', 'ks nay', 'ks do', 'resort nay', 'resort do',
            've no', 'tai no', 'o no', 'cua no',
            'this hotel', 'that hotel', 'the hotel', 'here', 'there', 'about it', 'at it'
        ]
        self._build_index()

    def _build_index(self):
        for h_key, data in self.db.items():
            raw_norm = strip_vietnamese(data['hotel_name'])
            clean_brand = raw_norm
            for cat in sorted(CATEGORY_WORDS, key=len, reverse=True):
                clean_brand = re.sub(r'\b' + re.escape(cat) + r'\b', ' ', clean_brand)

            h_loc_norm = strip_vietnamese(data.get('location', '') + ' ' + data.get('hotel_address', ''))
            all_tokens = [t for t in clean_brand.split() if len(t) >= 2 and t not in NOISE_WORDS]
            brand_tokens = [t for t in all_tokens if t not in LOCATION_TOKENS]
            if not brand_tokens:
                brand_tokens = all_tokens

            self.hotel_profiles[h_key] = {
                'hotel_name': data['hotel_name'],
                'norm_name': raw_norm,
                'brand_str': ' '.join(brand_tokens),
                'brand_tokens': set(brand_tokens),
                'location_str': h_loc_norm
            }
            for t in brand_tokens:
                self.inverted_index[t].add(h_key)

        # Sắp xếp hồ sơ khách sạn theo độ dài tên giảm dần để ưu tiên tên cụ thể / chi nhánh dài hơn
        self.sorted_profiles = sorted(
            self.hotel_profiles.items(),
            key=lambda x: len(x[1]['norm_name']),
            reverse=True
        )

    def match(self, query: str, active_hotel_key: Optional[str] = None) -> Tuple[Optional[str], float, bool]:
        q_norm = strip_vietnamese(query)

        # 1. Nhận diện địa danh trong câu hỏi để khử nhập nhằng (Disambiguation)
        q_loc = None
        for loc_phrase, canon in sorted(LOCATION_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(r'\b' + re.escape(loc_phrase) + r'\b', q_norm):
                q_loc = strip_vietnamese(canon)
                break

        # 2. Khớp thực thể tường minh trước (Explicit Entity Extraction)
        # 2.1. Khớp chuỗi tên chính xác theo thứ tự dài nhất trước với word boundary
        for h_key, prof in self.sorted_profiles:
            if len(prof['norm_name']) >= 4 and re.search(r'\b' + re.escape(prof['norm_name']) + r'\b', q_norm):
                if q_loc:
                    if q_loc in prof['location_str']:
                        return h_key, 1.0, False
                else:
                    return h_key, 1.0, False

        # 2.2. Trích xuất token thương hiệu định danh (Brand tokens) và tìm qua Inverted Index
        q_clean = q_norm
        for cat in CATEGORY_WORDS:
            q_clean = re.sub(r'\b' + re.escape(cat) + r'\b', ' ', q_clean)
        for noise in NOISE_WORDS:
            q_clean = re.sub(r'\b' + re.escape(noise) + r'\b', ' ', q_clean)

        q_tokens = [t for t in q_clean.split() if len(t) >= 2]
        q_brand_tokens = [t for t in q_tokens if t not in LOCATION_TOKENS]
        if not q_brand_tokens:
            q_brand_tokens = q_tokens

        candidates = set()
        for t in q_brand_tokens:
            if t in self.inverted_index:
                candidates.update(self.inverted_index[t])

        if candidates:
            best_key, best_score = None, -1e9
            q_brand_set = set(q_brand_tokens)
            q_brand_text = ' '.join(q_brand_tokens)

            for cand_key in candidates:
                prof = self.hotel_profiles[cand_key]
                c_brand_tokens = prof['brand_tokens']
                inter = len(c_brand_tokens & q_brand_set)
                if inter == 0:
                    continue

                recall = inter / len(c_brand_tokens) if c_brand_tokens else 0
                precision = inter / len(q_brand_set) if q_brand_set else 0
                f1_token = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                seq_sim = difflib.SequenceMatcher(None, q_brand_text, prof['brand_str']).ratio()

                score = 0.6 * f1_token + 0.4 * seq_sim

                # Thưởng/phạt địa danh để chọn đúng chi nhánh khách sạn
                if q_loc:
                    if q_loc in prof['location_str']:
                        score += 0.50
                    else:
                        score -= 0.30

                if score > best_score:
                    best_score = score
                    best_key = cand_key

            if best_score >= 0.45:
                return best_key, best_score, False

        # 3. Chỉ khi KHÔNG tìm thấy thực thể khách sạn tường minh mới kiểm tra đại từ hồi chỉ (Coreference)
        is_coref = any(re.search(r'\b' + re.escape(p) + r'\b', q_norm) for p in self.coref_patterns)
        if is_coref and active_hotel_key and active_hotel_key in self.db:
            return active_hotel_key, 1.0, True

        return None, 0.0, False


# ---------------------------------------------------------------------------
# Multi-Review Recency-Weighted Aggregator (Feature 10 Engine)
# ---------------------------------------------------------------------------
class MultiReviewAggregator:
    """Bộ tổng hợp đa đánh giá sử dụng Feature 10 (Trọng số thời gian suy giảm hàm mũ)."""
    def __init__(self, model, tokenizer, device, lambda_decay=0.03):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.lambda_decay = lambda_decay

    def select_candidate_reviews(self, target_hotel: dict, target_aspect: str, top_k=4) -> List[dict]:
        reviews = target_hotel.get('reviews', [])
        if not reviews:
            return []

        max_m = target_hotel.get('max_m', 2015 * 12 + 1)
        kws = ASPECT_KEYWORDS.get(target_aspect, [])

        scored_reviews = []
        for r in reviews:
            rev_m = r.get('year', 2015) * 12 + r.get('month', 1)
            delta_months = max(0, max_m - rev_m)
            # Feature 10: w = exp(-lambda * delta_months)
            w_time = math.exp(-self.lambda_decay * delta_months)

            # Đếm số lượng từ khóa khía cạnh xuất hiện trong review
            text_lower = r['text'].lower()
            kw_hits = sum(1 for kw in kws if kw in text_lower)

            # Điểm xếp hạng kết hợp độ liên quan khía cạnh và độ mới của review
            rank_score = (kw_hits * 1.5) + (w_time * 2.0)
            scored_reviews.append({
                'review': r,
                'rank_score': rank_score,
                'recency_weight': w_time,
                'delta_months': delta_months
            })

        scored_reviews.sort(key=lambda x: x['rank_score'], reverse=True)
        return scored_reviews[:top_k]

    def run_batched_inference(self, candidates: List[dict], user_query: str, target_hotel_name: str, target_aspect: str, is_vi: bool) -> dict:
        if not candidates:
            return {}

        contexts = [c['review']['text'] for c in candidates]
        dense_features = [c['review']['features'] for c in candidates]
        weights = [c['recency_weight'] for c in candidates]
        deltas = [c['delta_months'] for c in candidates]
        raw_reviews = [c['review'] for c in candidates]

        model_query = f"How is the {target_aspect.lower()} at {target_hotel_name}?" if is_vi else user_query
        queries = [model_query] * len(contexts)

        inputs = self.tokenizer(
            queries,
            contexts,
            max_length=256,
            truncation='only_second',
            padding='max_length',
            return_offsets_mapping=True,
            return_tensors='pt'
        )

        offset_mappings = inputs.pop('offset_mapping').tolist()
        input_ids = inputs['input_ids'].to(self.device)
        attention_mask = inputs['attention_mask'].to(self.device)
        token_type_ids = inputs['token_type_ids'].to(self.device) if 'token_type_ids' in inputs else None
        feat_tensor = torch.tensor(dense_features, dtype=torch.float, device=self.device)

        with torch.no_grad():
            outputs = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
                dense_features=feat_tensor
            )

        start_logits = outputs['start_logits'].cpu().numpy()
        end_logits = outputs['end_logits'].cpu().numpy()

        has_ans_raw = outputs.get('has_answer_logits', outputs.get('has_ans_logits'))
        if has_ans_raw.squeeze().dim() > 0:
            has_ans_probs = torch.sigmoid(has_ans_raw.squeeze()).cpu().numpy().tolist()
        else:
            has_ans_probs = [float(torch.sigmoid(has_ans_raw.squeeze()).item())]
        if isinstance(has_ans_probs, float):
            has_ans_probs = [has_ans_probs]

        aspect_preds = outputs['aspect_logits'].argmax(-1).cpu().numpy().tolist()
        sentiment_preds = outputs['sentiment_logits'].argmax(-1).cpu().numpy().tolist()

        review_results = []
        for i in range(len(contexts)):
            ctx_text = contexts[i]
            offsets = offset_mappings[i]
            tt = token_type_ids[i].cpu().numpy() if token_type_ids is not None else None
            s_l, e_l = start_logits[i], end_logits[i]

            best_s, best_e, best_sc = 0, 0, -1e9
            for s in range(1, len(s_l)):
                if tt is not None and tt[s] != 1:
                    continue
                for e in range(s, min(s + 40, len(e_l))):
                    if tt is not None and tt[e] != 1:
                        break
                    sc = s_l[s] + e_l[e]
                    if sc > best_sc:
                        best_sc, best_s, best_e = sc, s, e

            if best_e >= best_s and best_sc > -1e9 and best_s < len(offsets) and best_e < len(offsets):
                cs, ce = offsets[best_s][0], offsets[best_e][1]
                extracted_span = ctx_text[cs:ce].strip()
                span_text = extracted_span if ce > cs and len(extracted_span) >= 3 else ctx_text[:140].strip() + "..."
            else:
                span_text = ctx_text[:140].strip() + "..."

            sent_idx = sentiment_preds[i]
            sent_name = SENTIMENTS[sent_idx] if sent_idx < len(SENTIMENTS) else 'Neutral'
            sent_val = 1.0 if sent_name == 'Positive' else (-1.0 if sent_name == 'Negative' else 0.0)

            review_results.append({
                'review_id': raw_reviews[i].get('review_id'),
                'date': raw_reviews[i].get('date', '2015-09'),
                'year': raw_reviews[i].get('year', 2015),
                'score': raw_reviews[i].get('score', 4.0),
                'text': ctx_text,
                'span': span_text,
                'sentiment': sent_name,
                'sentiment_val': sent_val,
                'confidence': float(has_ans_probs[i]) if i < len(has_ans_probs) else 0.8,
                'recency_weight': float(weights[i]),
                'weight_pct': int(round(weights[i] * 100)),
                'delta_months': int(deltas[i])
            })

        return self.aggregate_temporal_sentiment(review_results, is_vi)

    def aggregate_temporal_sentiment(self, results: List[dict], is_vi: bool) -> dict:
        if not results:
            return {}

        total_weight = 0.0
        weighted_sent_sum = 0.0
        pos_w, neg_w, neu_w = 0.0, 0.0, 0.0

        for r in results:
            eff_w = r['recency_weight'] * max(0.25, r['confidence'])
            total_weight += eff_w
            weighted_sent_sum += eff_w * r['sentiment_val']
            if r['sentiment'] == 'Positive':
                pos_w += eff_w
            elif r['sentiment'] == 'Negative':
                neg_w += eff_w
            else:
                neu_w += eff_w

        s_agg = weighted_sent_sum / total_weight if total_weight > 0 else 0.0
        pos_ratio = pos_w / total_weight if total_weight > 0 else 0.0
        neg_ratio = neg_w / total_weight if total_weight > 0 else 0.0

        # Phân tích xu hướng theo trục thời gian (sắp xếp tăng dần theo năm/tháng)
        sorted_by_date = sorted(results, key=lambda x: (x['year'], x['date']))
        mid = len(sorted_by_date) // 2
        past_reviews = sorted_by_date[:mid] if mid > 0 else sorted_by_date
        recent_reviews = sorted_by_date[mid:] if mid > 0 else sorted_by_date

        past_sent = sum(r['sentiment_val'] for r in past_reviews) / len(past_reviews)
        recent_sent = sum(r['sentiment_val'] for r in recent_reviews) / len(recent_reviews)

        if recent_sent > past_sent + 0.4:
            trend = "improving"
            trend_label = "Cải thiện rõ rệt gần đây" if is_vi else "Notable Recent Improvement"
        elif recent_sent < past_sent - 0.4:
            trend = "degrading"
            trend_label = "Có dấu hiệu suy giảm gần đây" if is_vi else "Recent Decline Noted"
        elif pos_ratio >= 0.65:
            trend = "stable_positive"
            trend_label = "Đồng thuận tích cực cao" if is_vi else "Strong Positive Consensus"
        elif neg_ratio >= 0.65:
            trend = "stable_negative"
            trend_label = "Phản ánh tiêu cực đồng nhất" if is_vi else "Consistent Complaints"
        else:
            trend = "mixed"
            trend_label = "Ý kiến đan xen / đa chiều" if is_vi else "Mixed / Balanced Impressions"

        return {
            'aggregate_sentiment_score': round(s_agg, 3),
            'consensus_sentiment': 'Positive' if s_agg >= 0.20 else ('Negative' if s_agg <= -0.20 else 'Neutral'),
            'positive_ratio': round(pos_ratio, 2),
            'negative_ratio': round(neg_ratio, 2),
            'trend': trend,
            'trend_label': trend_label,
            'reviews': results
        }


# ---------------------------------------------------------------------------
# Conversational Natural Language Answer Synthesizer (NLG Engine)
# ---------------------------------------------------------------------------
class ConversationalNLGSynthesizer:
    """Bộ tạo câu trả lời đàm thoại tự nhiên với kho ngữ liệu biến thể linh hoạt, chống lặp khuôn mẫu."""
    @staticmethod
    def synthesize(target_hotel: dict, aspect: str, agg_result: dict, is_vi: bool) -> str:
        hotel_name = target_hotel['hotel_name']
        aspect_title = ASPECT_TRANSLATIONS.get(aspect, {}).get('vi' if is_vi else 'en', aspect)
        overall_sent = agg_result['consensus_sentiment']
        trend = agg_result['trend']
        pos_pct = int(agg_result['positive_ratio'] * 100)
        neg_pct = int(agg_result['negative_ratio'] * 100)
        reviews = agg_result.get('reviews', [])

        most_recent = max(reviews, key=lambda x: x['recency_weight']) if reviews else None
        recent_date = most_recent['date'] if most_recent else 'Gần đây'
        recent_score = most_recent['score'] if most_recent else 4.0
        recent_span = most_recent.get('span', '') if most_recent else ''

        raw_star = str(target_hotel.get('star', '')).replace('-star', '').replace('star', '').strip()
        star_desc = f"{raw_star} sao" if (raw_star and raw_star != '0' and is_vi) else (f"{raw_star}-star" if raw_star else ("Tiêu chuẩn quốc tế" if is_vi else "Standard"))
        hotel_score = target_hotel.get('score', 4.0)

        total_revs = len(target_hotel.get('reviews', []))
        aspect_rev_count = sum(1 for r in target_hotel.get('reviews', []) if aspect in r.get('present_aspects', []))
        aspect_pct = (aspect_rev_count / total_revs * 100) if total_revs > 0 else 0

        if is_vi:
            count_variants = [
                f"Khách sạn đạt chuẩn **{star_desc}** (đánh giá `{hotel_score:.1f}/5.0` sao), có **{aspect_rev_count}/{total_revs} bài đánh giá liên quan đến {aspect_title}** (chiếm **{aspect_pct:.1f}%** tổng số đánh giá).",
                f"Được xếp hạng **{star_desc}** với điểm bình chọn `{hotel_score:.1f}/5.0` sao, hệ thống ghi nhận **{aspect_rev_count} trên tổng số {total_revs} phản hồi** đề cập trực tiếp đến {aspect_title} (**{aspect_pct:.1f}%**).",
                f"Theo dữ liệu thực tế ({star_desc}, `{hotel_score:.1f}/5.0` sao), có **{aspect_rev_count}/{total_revs} lượt khách** thảo luận về khía cạnh {aspect_title} (tương đương **{aspect_pct:.1f}%** khối lượng phản hồi)."
            ]
            count_info = random.choice(count_variants)

            if overall_sent == 'Positive':
                pos_headlines = [
                    f"Về khía cạnh **{aspect_title}**, khách sạn **{hotel_name}** nhận được sự hài lòng rất cao từ du khách với **{pos_pct}% phản hồi tích cực** (đã áp dụng trọng số Feature 10 ưu tiên đánh giá mới).",
                    f"Tổng hợp ý kiến từ các đợt lưu trú gần đây tại **{hotel_name}**, khía cạnh **{aspect_title}** được đánh giá rất tốt với tỷ lệ hài lòng lên đến **{pos_pct}%**.",
                    f"Trải nghiệm của du khách về **{aspect_title}** tại **{hotel_name}** để lại ấn tượng đậm nét với **{pos_pct}% đánh giá khen ngợi**.",
                    f"Dữ liệu đánh giá thực tế cho thấy **{hotel_name}** ghi điểm mạnh mẽ ở khía cạnh **{aspect_title}**, đạt **{pos_pct}% ý kiến tích cực**."
                ]
                headline = random.choice(pos_headlines)

                if trend == 'improving':
                    trend_sentences = [
                        "Đáng chú ý, các phản hồi trong thời gian gần đây cho thấy chất lượng dịch vụ đã có sự cải thiện và nâng cấp rõ nét so với các giai đoạn trước.",
                        "Đặc biệt, những đánh giá gần nhất phản ánh bước chuyển biến tích cực rõ rệt về cung cách phục vụ và trải nghiệm thực tế.",
                        "Xu hướng thời gian cho thấy khách sạn đã liên tục lắng nghe góp ý và hoàn thiện chất lượng vượt bậc trong các đợt lưu trú gần đây."
                    ]
                else:
                    trend_sentences = [
                        "Phần lớn khách lưu trú đều khen ngợi sự chuẩn mực, tính chuyên nghiệp và trải nghiệm thoải mái tại đây.",
                        "Khách sạn duy trì phong độ phục vụ ổn định, mang đến sự an tâm và hài lòng bền vững cho du khách.",
                        "Cộng đồng du khách nhất quán đánh giá cao tính chỉn chu, nhiệt tình và chất lượng đáng tin cậy."
                    ]
                trend_sentence = random.choice(trend_sentences)

            elif overall_sent == 'Negative':
                neg_headlines = [
                    f"Đối với khía cạnh **{aspect_title}**, khách sạn **{hotel_name}** hiện còn một số vấn đề khiến khách hàng chưa hài lòng (**{neg_pct}% đánh giá phàn nàn**).",
                    f"Ghi nhận thực tế về **{aspect_title}** tại **{hotel_name}** cho thấy mức độ hài lòng chưa cao với **{neg_pct}% phản hồi góp ý/chê trách**.",
                    f"Về phương diện **{aspect_title}**, du khách tại **{hotel_name}** phản ánh nhiều trải nghiệm chưa đạt kỳ vọng (**{neg_pct}% ý kiến phàn nàn**)."
                ]
                headline = random.choice(neg_headlines)

                if trend == 'degrading':
                    trend_sentences = [
                        "Các phản hồi gần đây ghi nhận sự sụt giảm về chất lượng phục vụ so với kỳ vọng trước đó của du khách.",
                        "Đáng lưu ý, các đánh giá mới nhất phản ánh sự thiếu ổn định và có dấu hiệu đi xuống so với các năm trước.",
                        "Nhiều khách hàng thời gian gần đây bày tỏ sự thất vọng vì trải nghiệm không còn tương xứng với danh tiếng."
                    ]
                else:
                    trend_sentences = [
                        "Nhiều du khách phản ánh những trải nghiệm chưa thật sự tương xứng với tiêu chuẩn khách sạn.",
                        "Khách sạn ghi nhận một số phản hồi phê bình về khâu tổ chức và cần được cải thiện kịp thời.",
                        "Du khách lưu ý một vài điểm trừ còn tồn đọng trong quá trình trải nghiệm dịch vụ."
                    ]
                trend_sentence = random.choice(trend_sentences)

            else:
                neu_headlines = [
                    f"Về **{aspect_title}** tại **{hotel_name}**, trải nghiệm của khách lưu trú ở mức trung tính và có sự phân hóa đa chiều giữa các đợt lưu trú.",
                    f"Ý kiến đánh giá về **{aspect_title}** ở **{hotel_name}** khá cân bằng, ghi nhận cả ưu điểm lẫn một số hạn chế nhỏ.",
                    f"Nhìn chung, khía cạnh **{aspect_title}** tại **{hotel_name}** đáp ứng ở mức vừa phải, đan xen giữa đánh giá khen và góp ý."
                ]
                headline = random.choice(neu_headlines)
                trend_sentences = [
                    "Khách hàng ghi nhận các điểm sáng đáng giá, tuy nhiên vẫn còn một số chi tiết cần tiếp tục hoàn thiện thêm.",
                    "Trải nghiệm thực tế phụ thuộc nhiều vào thời điểm lưu trú và loại phòng lựa chọn.",
                    "Du khách đánh giá mức độ tương xứng cơ bản với chi phí, bên cạnh vài điểm cần nâng cấp."
                ]
                trend_sentence = random.choice(trend_sentences)

            recency_variants = [
                f"Ghi nhận theo đánh giá mới nhất ({recent_date}): khách cho điểm `{recent_score:.1f}/5.0` sao.",
                f"Theo phản hồi gần đây nhất được ghi nhận ({recent_date}), khách hàng chấm điểm `{recent_score:.1f}/5.0` sao.",
                f"Đợt lưu trú gần nhất vào tháng {recent_date} nhận được số điểm `{recent_score:.1f}/5.0` sao từ du khách."
            ]
            recency_note = random.choice(recency_variants)

            # Nhúng câu dẫn chứng đắt giá vào câu trả lời tự nhiên
            quote_embed = ""
            if recent_span and len(recent_span) >= 8 and not recent_span.endswith('...'):
                quote_embed = f"\n\n> *\"{recent_span}\"* — (Trích nhận xét từ khách lưu trú đợt {recent_date})"

            answer = (
                f"{headline}\n\n"
                f"📊 {count_info}\n\n"
                f"{trend_sentence} {recency_note}{quote_embed}\n\n"
                f"• **Xu hướng trải nghiệm:** {agg_result['trend_label']} (Điểm cảm xúc trọng số: `{agg_result['aggregate_sentiment_score']:+.2f}`)"
            )
        else:
            count_variants_en = [
                f"Rated **{star_desc}** (`{hotel_score:.1f}/5.0` stars) with **{aspect_rev_count}/{total_revs} reviews mentioning {aspect_title}** (**{aspect_pct:.1f}%** of total volume).",
                f"Holding an official **{star_desc}** standard (`{hotel_score:.1f}/5.0` rating), indexed with **{aspect_rev_count} out of {total_revs} verified reviews** focusing on {aspect_title} (**{aspect_pct:.1f}%**).",
                f"Statistical review metrics indicate **{aspect_rev_count}/{total_revs} travelers** explicitly discussed {aspect_title} (**{aspect_pct:.1f}%** share)."
            ]
            count_info_en = random.choice(count_variants_en)

            if overall_sent == 'Positive':
                pos_headlines_en = [
                    f"Regarding **{aspect_title}**, **{hotel_name}** receives strong guest satisfaction with **{pos_pct}% positive feedback** (weighted toward recent visits via Feature 10).",
                    f"Synthesized traveler feedback highlights high acclaim for **{aspect_title}** at **{hotel_name}**, achieving a **{pos_pct}% satisfaction rating**.",
                    f"Guests consistently praise **{aspect_title}** at **{hotel_name}**, with **{pos_pct}% of verified impressions being enthusiastic**."
                ]
                headline = random.choice(pos_headlines_en)
                trend_sentence = (
                    "Recent reviews demonstrate noticeable service upgrades and heightened attentiveness compared to earlier seasons."
                    if trend == 'improving' else
                    "Guests consistently praise the dependable quality and welcoming atmosphere."
                )
            elif overall_sent == 'Negative':
                neg_headlines_en = [
                    f"In terms of **{aspect_title}**, **{hotel_name}** has faced critical feedback (**{neg_pct}% dissatisfaction rate**).",
                    f"Customer reviews reveal notable shortcomings regarding **{aspect_title}** at **{hotel_name}** (**{neg_pct}% complaints**).",
                    f"Travelers report room for improvement in **{aspect_title}** at **{hotel_name}** (**{neg_pct}% negative sentiments**)."
                ]
                headline = random.choice(neg_headlines_en)
                trend_sentence = (
                    "Recent guest notes highlight a decline in consistency compared to past standards."
                    if trend == 'degrading' else
                    "Several travelers reported shortcomings that did not match their expectations."
                )
            else:
                neu_headlines_en = [
                    f"For **{aspect_title}** at **{hotel_name}**, guest impressions are balanced with mixed viewpoints across different trips.",
                    f"Feedback on **{aspect_title}** at **{hotel_name}** presents a moderate, balanced consensus with both positives and minor caveats.",
                    f"Guest perspectives on **{aspect_title}** at **{hotel_name}** are varied, reflecting mixed experiences depending on stay period."
                ]
                headline = random.choice(neu_headlines_en)
                trend_sentence = "Guests appreciate notable highlights while pointing out specific areas that could be enhanced."

            recency_note = f"According to the latest review ({recent_date}), the guest rated `{recent_score:.1f}/5.0` stars."
            quote_embed = ""
            if recent_span and len(recent_span) >= 8 and not recent_span.endswith('...'):
                quote_embed = f"\n\n> *\"{recent_span}\"* — (Direct traveler quote from {recent_date} stay)"

            answer = (
                f"{headline}\n\n"
                f"📊 {count_info_en}\n\n"
                f"{trend_sentence} {recency_note}{quote_embed}\n\n"
                f"• **Trend Verdict:** {agg_result['trend_label']} (Weighted sentiment score: `{agg_result['aggregate_sentiment_score']:+.2f}`)"
            )

        return answer


# ---------------------------------------------------------------------------
# Conversational QA Bot Engine
# ---------------------------------------------------------------------------
class DialogueState:
    def __init__(self):
        self.active_hotel_key = None
        self.active_hotel_name = None
        self.active_aspect = None
        self.history = []

    def reset(self):
        self.active_hotel_key = None
        self.active_hotel_name = None
        self.active_aspect = None
        self.history.clear()


class SessionManager:
    """Quản lý ngữ cảnh hội thoại đa luồng cho từng phiên làm việc (session_id)."""
    def __init__(self):
        self._lock = threading.Lock()
        self._sessions = {}

    def get_state(self, session_id: str) -> DialogueState:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = DialogueState()
            return self._sessions[session_id]

    def reset_state(self, session_id: str):
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].reset()


class ConversationalQABot:
    def __init__(self, model_path="model/model.pt"):
        self.device = torch.device('cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu'))
        self.session_manager = SessionManager()
        self.state = self.session_manager.get_state("default")
        self.model_loaded = False
        self.model_path = model_path
        self.model_name = "bert-base-uncased"

        print(f"Initializing BERT Tokenizer ({self.model_name})...")
        self.tokenizer = BertTokenizerFast.from_pretrained(self.model_name)

        print("Initializing Model Architecture...")
        self.model = HotelAspectQA_BERT(model_name=self.model_name)
        self.load_checkpoint(model_path)
        self.model.to(self.device)
        self.model.eval()

        print("Building Robust Hotel Matcher Index...")
        self.matcher = RobustHotelMatcher(HOTEL_DATABASE)
        self.aggregator = MultiReviewAggregator(self.model, self.tokenizer, self.device)

    def load_checkpoint(self, path):
        # Kiểm tra bảo mật đường dẫn (chống path traversal ngoài thư mục ứng dụng)
        allowed_dir = os.path.realpath(os.getcwd())
        search_paths = [
            path,
            os.path.join("model", os.path.basename(path)) if path else None,
            "model/model.pt",
            "model.pt",
            "model/hotel_aspect_qa_model/model.pt",
            "model/hotel_aspect_qa_model/pytorch_model.bin"
        ]
        resolved_path = None
        for p in search_paths:
            if p and os.path.exists(p) and os.path.isfile(p):
                real_p = os.path.realpath(p)
                if real_p.startswith(allowed_dir):
                    resolved_path = real_p
                    break

        if resolved_path:
            try:
                try:
                    checkpoint = torch.load(resolved_path, map_location=self.device, weights_only=True)
                except (TypeError, ValueError):
                    checkpoint = torch.load(resolved_path, map_location=self.device)

                if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                    self.model.load_state_dict(checkpoint['model_state_dict'], strict=False)
                elif isinstance(checkpoint, dict):
                    self.model.load_state_dict(checkpoint, strict=False)
                self.model_loaded = True
                self.model_path = resolved_path
                print(f"Successfully loaded checkpoint: {resolved_path}")
                return True, f"Loaded weights successfully from {resolved_path}"
            except Exception as e:
                print(f"Error loading checkpoint {resolved_path}: {e}")
                self.model_loaded = False
                return False, f"Error loading checkpoint: {str(e)}"
        else:
            self.model_loaded = False
            self.model_path = path or "model/model.pt"
            return False, f"Checkpoint not found at '{path}'. Place model.pt into 'model/' folder."

    def detect_intent_and_aspect(self, query: str, active_aspect: Optional[str] = None) -> Tuple[str, Optional[str]]:
        q_lower = query.lower()
        if any(re.search(r'\b' + re.escape(w) + r'\b', q_lower) for w in LOCATION_KEYWORDS):
            return 'location', None

        if any(re.search(r'\b' + re.escape(w) + r'\b', q_lower) for w in STAR_KEYWORDS):
            return 'star', None

        aspect_scores = defaultdict(int)
        for asp, kws in ASPECT_KEYWORDS.items():
            for kw in kws:
                if kw in q_lower:
                    aspect_scores[asp] += 1

        if any(re.search(r'\b' + re.escape(w) + r'\b', q_lower) for w in COUNT_KEYWORDS):
            best_asp = max(aspect_scores.keys(), key=lambda a: aspect_scores[a]) if aspect_scores else (active_aspect or 'Service')
            return 'count', best_asp

        if aspect_scores:
            best_asp = max(aspect_scores.keys(), key=lambda a: aspect_scores[a])
            return 'aspect_qa', best_asp

        return 'aspect_qa', active_aspect or 'Experience'

    def answer_query(self, user_query: str, session_id: str = "default") -> dict:
        is_vi = is_vietnamese_query(user_query)
        state = self.session_manager.get_state(session_id)
        self.state = state

        # Xử lý lời chào hỏi / giới thiệu ban đầu của người dùng
        greetings = ['xin chao', 'chao ban', 'chao em', 'chao anh', 'chao', 'hello', 'hi', 'hey', 'alo', 'ban la ai', 'who are you', 'what can you do']
        q_norm = strip_vietnamese(user_query)
        if any(q_norm == g or q_norm.startswith(g + ' ') for g in greetings) and not any(k in q_norm for k in ['hotel', 'khach san', 'resort', 'ks']):
            greeting_msg = (
                "Xin chào! Tôi là trợ lý AI chuyên giải đáp thông tin và phân tích đánh giá về 2,622 khách sạn tại Việt Nam.\n\n"
                "Bạn có thể hỏi tôi bất kỳ điều gì bằng ngôn ngữ tự nhiên, ví dụ:\n"
                "• *\"Khách sạn Pullman Hà Nội mấy sao và ở đâu?\"*\n"
                "• *\"Có bao nhiêu đánh giá về dịch vụ ở Pullman Hà Nội?\"*\n"
                "• *\"Chất lượng phòng ốc tại Salinda Phú Quốc dạo gần đây thế nào?\"*\n\n"
                "Hãy cho tôi biết tên khách sạn bạn đang quan tâm nhé!"
                if is_vi else
                "Hello! I am an AI assistant specializing in hotel review intelligence for 2,622 hotels in Vietnam.\n\n"
                "You can ask me anything in natural language, for example:\n"
                "• *\"What is the star rating and address of Pullman Hanoi?\"*\n"
                "• *\"How many reviews mention service at Pullman Hanoi?\"*\n"
                "• *\"How is the room quality at Salinda Resort Phu Quoc recently?\"*\n\n"
                "Please tell me which hotel you would like to explore!"
            )
            return {
                "text": greeting_msg,
                "direct_answer": greeting_msg,
                "hotel": None,
                "aspect": None,
                "sentiment": None,
                "confidence": 1.0,
                "evidence": None,
                "citations": [],
                "original_reviews": [],
                "context_applied": False
            }

        hotel_key, match_score, was_coref = self.matcher.match(user_query, state.active_hotel_key)
        intent, target_aspect = self.detect_intent_and_aspect(user_query, state.active_aspect)

        if not hotel_key:
            msg = (
                "Vui lòng đề cập tên khách sạn để tôi có thể hỗ trợ bạn (ví dụ: Pullman Hà Nội, Mường Thanh, Salinda Phú Quốc...)."
                if is_vi else
                "Please mention a hotel name so I can assist you (e.g., Pullman Hanoi, Muong Thanh, Salinda Phu Quoc...)."
            )
            return {
                "text": msg,
                "direct_answer": msg,
                "hotel": None,
                "aspect": None,
                "sentiment": None,
                "confidence": None,
                "evidence": None,
                "citations": [],
                "original_reviews": [],
                "context_applied": False
            }

        target_hotel = HOTEL_DATABASE[hotel_key]
        state.active_hotel_key = hotel_key
        state.active_hotel_name = target_hotel['hotel_name']
        if target_aspect:
            state.active_aspect = target_aspect

        raw_star = str(target_hotel.get('star', '')).replace('-star', '').replace('star', '').strip()
        star_desc = f"{raw_star} sao" if (raw_star and raw_star != '0' and is_vi) else (f"{raw_star}-star" if raw_star else ("Tiêu chuẩn quốc tế" if is_vi else "Standard"))
        total_revs = len(target_hotel.get('reviews', []))
        score = target_hotel.get('score', 4.0)

        # Xử lý Intent Số sao khách sạn (Star Rating Intent)
        if intent == 'star':
            if is_vi:
                star_variants = [
                    (
                        f"Khách sạn **{target_hotel['hotel_name']}** đạt chuẩn xếp hạng **{star_desc}** với điểm đánh giá tổng thể từ du khách là **`{score:.1f}/5.0` sao**.\n\n"
                        f"• **Địa chỉ:** `{target_hotel.get('hotel_address', '')}`\n"
                        f"• **Khu vực:** `{target_hotel.get('location', '')}`\n"
                        f"• **Dữ liệu đánh giá:** Hiện có tổng cộng **{total_revs} bài đánh giá** chi tiết trong hệ thống."
                    ),
                    (
                        f"Theo tiêu chuẩn xếp hạng ngành khách sạn, **{target_hotel['hotel_name']}** là cơ sở lưu trú đạt chuẩn **{star_desc}**, được cộng đồng du khách bình chọn mức điểm trung bình **`{score:.1f}/5.0` sao**.\n\n"
                        f"📍 Tọa lạc tại: `{target_hotel.get('hotel_address', '')}` ({target_hotel.get('location', '')}).\n"
                        f"📊 Cơ sở dữ liệu hiện lưu trữ **{total_revs} bài phản hồi** từ du khách thực tế."
                    ),
                    (
                        f"Về quy mô và tiêu chuẩn dịch vụ, **{target_hotel['hotel_name']}** được công nhận hạng sao **{star_desc}** và nhận được mức độ hài lòng bình quân **`{score:.1f}/5.0` sao**.\n\n"
                        f"• **Vị trí:** `{target_hotel.get('hotel_address', '')}`\n"
                        f"• **Tổng phản hồi đã kiểm chứng:** **{total_revs} đánh giá**."
                    )
                ]
                direct_ans = random.choice(star_variants)
            else:
                star_variants_en = [
                    (
                        f"**{target_hotel['hotel_name']}** holds an official rating of **{star_desc}** with an overall guest rating of **`{score:.1f}/5.0` stars**.\n\n"
                        f"• **Address:** `{target_hotel.get('hotel_address', '')}`\n"
                        f"• **Region:** `{target_hotel.get('location', '')}`\n"
                        f"• **Review Volume:** Currently indexed with **{total_revs} verified reviews**."
                    ),
                    (
                        f"Classified under the **{star_desc}** hospitality standard, **{target_hotel['hotel_name']}** carries a cumulative traveler score of **`{score:.1f}/5.0` stars**.\n\n"
                        f"📍 Location: `{target_hotel.get('hotel_address', '')}` ({target_hotel.get('location', '')}).\n"
                        f"📊 Backed by **{total_revs} authentic customer reviews**."
                    )
                ]
                direct_ans = random.choice(star_variants_en)

            return {
                "text": direct_ans,
                "direct_answer": direct_ans,
                "hotel": target_hotel['hotel_name'],
                "aspect": "Branding",
                "sentiment": "Positive" if score >= 4.0 else "Neutral",
                "confidence": 1.0,
                "evidence": f"Xếp hạng: {star_desc} | Điểm số: {score:.1f}/5.0",
                "citations": [],
                "original_reviews": [],
                "star_desc": star_desc,
                "score": score,
                "total_reviews": total_revs,
                "context_applied": was_coref
            }

        # Xử lý Intent Hỏi về Số lượng đánh giá (Review Count Intent)
        if intent == 'count':
            aspect_title = ASPECT_TRANSLATIONS.get(target_aspect, {}).get('vi' if is_vi else 'en', target_aspect or 'Service')
            aspect_rev_count = sum(1 for r in target_hotel.get('reviews', []) if target_aspect in r.get('present_aspects', []))
            aspect_pct = (aspect_rev_count / total_revs * 100) if total_revs > 0 else 0

            if is_vi:
                count_variants = [
                    (
                        f"Thông tin số lượng đánh giá về khách sạn **{target_hotel['hotel_name']}** ({star_desc}, `{score:.1f}/5.0` sao):\n\n"
                        f"• **Tổng số đánh giá trong CSDL:** **{total_revs} bài đánh giá**.\n"
                        f"• **Số đánh giá về khía cạnh {aspect_title}:** **{aspect_rev_count} bài đánh giá** (chiếm **{aspect_pct:.1f}%** tổng số phản hồi).\n\n"
                        f"Hệ thống đã sẵn sàng trích xuất dẫn chứng cụ thể từ các đánh giá này theo thời gian thực."
                    ),
                    (
                        f"Thống kê phản hồi người dùng cho thấy **{target_hotel['hotel_name']}** ({star_desc}, `{score:.1f}/5.0` sao) hiện ghi nhận:\n\n"
                        f"📊 **{aspect_rev_count} trên tổng số {total_revs} bài đánh giá** đề cập trực tiếp đến **{aspect_title}** (**{aspect_pct:.1f}%**).\n\n"
                        f"Bạn có thể yêu cầu trích xuất chi tiết bằng chứng và xu hướng đánh giá gần đây bất kỳ lúc nào!"
                    ),
                    (
                        f"Dữ liệu phản hồi thực tế của khách sạn **{target_hotel['hotel_name']}** ({star_desc}):\n\n"
                        f"• **Quy mô mẫu:** **{total_revs} đánh giá** đã được kiểm chứng.\n"
                        f"• **Tỷ trọng khía cạnh {aspect_title}:** **{aspect_rev_count} bài** (chiếm **{aspect_pct:.1f}%** tổng khối lượng phản hồi).\n\n"
                        f"Mô hình AI đã sẵn sàng phân tích cảm xúc và trích xuất câu nhận xét cụ thể."
                    )
                ]
                direct_ans = random.choice(count_variants)
            else:
                count_variants_en = [
                    (
                        f"Review volume metrics for **{target_hotel['hotel_name']}** ({star_desc}, rated `{score:.1f}/5.0`):\n\n"
                        f"• **Total Indexed Reviews:** **{total_revs} reviews**.\n"
                        f"• **Reviews Mentioning {aspect_title}:** **{aspect_rev_count} reviews** (**{aspect_pct:.1f}%** of total volume).\n\n"
                        f"Ready to extract concrete rationale spans and analyze sentiment trends."
                    ),
                    (
                        f"Verified feedback distribution for **{target_hotel['hotel_name']}** ({star_desc}):\n\n"
                        f"📊 **{aspect_rev_count} out of {total_revs} reviews** discuss **{aspect_title}** (**{aspect_pct:.1f}%** share).\n\n"
                        f"Ready to evaluate neural aspect sentiment and temporal trends."
                    )
                ]
                direct_ans = random.choice(count_variants_en)

            return {
                "text": direct_ans,
                "direct_answer": direct_ans,
                "hotel": target_hotel['hotel_name'],
                "aspect": target_aspect,
                "sentiment": "Neutral",
                "confidence": 1.0,
                "evidence": f"{aspect_rev_count}/{total_revs} reviews",
                "citations": [],
                "original_reviews": [],
                "star_desc": star_desc,
                "score": score,
                "aspect_count": aspect_rev_count,
                "total_reviews": total_revs,
                "aspect_pct": round(aspect_pct, 1),
                "context_applied": was_coref
            }

        # Xử lý Intent Vị trí / Địa chỉ -> Tích hợp Google Maps API Card
        if intent == 'location':
            raw_star = str(target_hotel.get('star', '')).replace('-star', '').replace('star', '').strip()
            star_desc = f"{raw_star} sao" if (raw_star and raw_star != '0' and is_vi) else (f"{raw_star}-star" if raw_star else "Standard")

            hotel_name = target_hotel['hotel_name']
            hotel_address = target_hotel['hotel_address']
            score = target_hotel['score']

            # Tạo link Google Maps và embed iframe (Hoạt động không cần API key thông qua Google Maps Embed)
            maps_query = f"{hotel_name}, {hotel_address}"
            q_encoded = urllib.parse.quote(maps_query)
            embed_url = f"https://maps.google.com/maps?q={q_encoded}&t=&z=15&ie=UTF8&iwloc=&output=embed"
            search_url = f"https://www.google.com/maps/search/?api=1&query={q_encoded}"

            if is_vi:
                loc_variants = [
                    (
                        f"Khách sạn **{hotel_name}** ({star_desc}, Đánh giá `{score:.1f}/5.0` sao) tọa lạc tại địa chỉ:\n"
                        f"📍 **{hotel_address}** (Khu vực: {target_hotel.get('location', '')})."
                    ),
                    (
                        f"Về vị trí, **{hotel_name}** ({star_desc}, xếp hạng `{score:.1f}/5.0` sao) nằm tại:\n"
                        f"📍 **{hotel_address}** (Địa bàn: {target_hotel.get('location', '')}).\n"
                        f"Bạn có thể xem bản đồ tương tác và đường đi trực tiếp phía dưới."
                    ),
                    (
                        f"Bạn có thể tìm thấy khách sạn **{hotel_name}** ({star_desc}, điểm `{score:.1f}/5.0` sao) tại địa chỉ chuẩn xác:\n"
                        f"📍 **{hotel_address}** ({target_hotel.get('location', '')})."
                    )
                ]
                direct_ans = random.choice(loc_variants)
            else:
                loc_variants_en = [
                    (
                        f"**{hotel_name}** ({star_desc}, Rated `{score:.1f}/5.0`) is located at:\n"
                        f"📍 **{hotel_address}** (Region: {target_hotel.get('location', '')})."
                    ),
                    (
                        f"You can find **{hotel_name}** ({star_desc}, `{score:.1f}/5.0` stars) at:\n"
                        f"📍 **{hotel_address}** (Area: {target_hotel.get('location', '')}).\n"
                        f"Interactive Google Maps and navigation directions are embedded below."
                    )
                ]
                direct_ans = random.choice(loc_variants_en)

            return {
                "text": direct_ans,
                "direct_answer": direct_ans,
                "hotel": hotel_name,
                "aspect": "Location",
                "sentiment": "Neutral",
                "confidence": 1.0,
                "evidence": hotel_address,
                "citations": [],
                "original_reviews": [],
                "context_applied": was_coref,
                "map_card": {
                    "hotel_name": hotel_name,
                    "address": hotel_address,
                    "location": target_hotel.get('location', ''),
                    "star": star_desc,
                    "score": score,
                    "embed_url": embed_url,
                    "search_url": search_url
                }
            }

        # Xử lý Aspect QA Đa đánh giá với Feature 10
        candidates = self.aggregator.select_candidate_reviews(target_hotel, target_aspect, top_k=4)
        if not candidates:
            msg = f"Chưa có đủ đánh giá chi tiết cho **{target_hotel['hotel_name']}** về khía cạnh này." if is_vi else f"No detailed reviews available for **{target_hotel['hotel_name']}** on this aspect."
            return {
                "text": msg,
                "direct_answer": msg,
                "hotel": target_hotel['hotel_name'],
                "aspect": target_aspect,
                "sentiment": "Neutral",
                "confidence": 0.5,
                "evidence": None,
                "citations": [],
                "original_reviews": [],
                "context_applied": was_coref
            }

        # Chạy suy luận mạng nơ-ron đa review đồng thời
        agg_result = self.aggregator.run_batched_inference(
            candidates,
            user_query,
            target_hotel['hotel_name'],
            target_aspect,
            is_vi
        )

        # Tổng hợp câu trả lời tự nhiên
        direct_answer = ConversationalNLGSynthesizer.synthesize(target_hotel, target_aspect, agg_result, is_vi)

        # Chuẩn bị danh sách trích dẫn dẫn chứng (Citations)
        citations = []
        for r in agg_result.get('reviews', []):
            citations.append({
                'span': r['span'],
                'date': r['date'],
                'score': r['score'],
                'sentiment': r['sentiment'],
                'recency_weight': r['recency_weight'],
                'weight_pct': r['weight_pct']
            })

        # Chuẩn bị danh sách đánh giá gốc đầy đủ (được ẩn dưới dạng collapsible trong UI)
        original_reviews = []
        for r in agg_result.get('reviews', []):
            original_reviews.append({
                'review_id': r['review_id'],
                'date': r['date'],
                'score': r['score'],
                'sentiment': r['sentiment'],
                'text': r['text'],
                'weight_pct': r['weight_pct']
            })

        # Fallback text cho các client markdown thông thường
        aspect_label = ASPECT_TRANSLATIONS.get(target_aspect, {}).get('vi' if is_vi else 'en', target_aspect)
        coref_note = " *(Đã liên kết ngữ cảnh từ câu trước)*" if was_coref else ""
        fallback_text = (
            f"{direct_answer}\n\n"
            f"**Dẫn chứng tiêu biểu:**\n> \"{citations[0]['span'] if citations else ''}\"\n\n"
            f"• **Khía cạnh:** {aspect_label}\n"
            f"• **Cảm xúc tổng thể:** {agg_result.get('consensus_sentiment')}{coref_note}"
        )

        aspect_rev_count = sum(1 for r in target_hotel.get('reviews', []) if target_aspect in r.get('present_aspects', []))
        aspect_pct = (aspect_rev_count / total_revs * 100) if total_revs > 0 else 0

        return {
            "text": fallback_text,
            "direct_answer": direct_answer,
            "hotel": target_hotel['hotel_name'],
            "aspect": target_aspect,
            "sentiment": agg_result.get('consensus_sentiment'),
            "confidence": 0.95,
            "evidence": citations[0]['span'] if citations else None,
            "citations": citations,
            "original_reviews": original_reviews,
            "trend_label": agg_result.get('trend_label'),
            "star_desc": star_desc,
            "score": score,
            "aspect_count": aspect_rev_count,
            "total_reviews": total_revs,
            "aspect_pct": round(aspect_pct, 1),
            "context_applied": was_coref
        }

# Global Bot Instance
BOT = None


# ---------------------------------------------------------------------------
# Modern Floating Glass UI (HTML5 / CSS3 / JS)
# ---------------------------------------------------------------------------
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hotel Aspect QA - Conversational Intelligence</title>
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
            
            /* Dark Theme (Default) */
            --bg-canvas: #090d16;
            --bg-glass-card: rgba(18, 24, 38, 0.65);
            --bg-glass-card-hover: rgba(26, 34, 52, 0.75);
            --bg-glass-sidebar: rgba(13, 18, 30, 0.75);
            --bg-glass-bubble-bot: rgba(22, 30, 48, 0.8);
            --bg-glass-bubble-user: linear-gradient(135deg, rgba(37, 99, 235, 0.9), rgba(59, 130, 246, 0.9));
            --border-glass: rgba(255, 255, 255, 0.08);
            --border-glass-subtle: rgba(255, 255, 255, 0.04);
            --border-glass-focus: rgba(96, 165, 250, 0.4);
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-primary: #3b82f6;
            --accent-glow: rgba(59, 130, 246, 0.25);
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --orb-1: rgba(59, 130, 246, 0.15);
            --orb-2: rgba(139, 92, 246, 0.12);
            --orb-3: rgba(16, 185, 129, 0.08);
            --shadow-float: 0 16px 36px -8px rgba(0, 0, 0, 0.5), 0 4px 12px -2px rgba(0, 0, 0, 0.3);
            --shadow-subtle: 0 8px 24px -4px rgba(0, 0, 0, 0.35);
        }

        [data-theme="light"] {
            /* Light Theme */
            --bg-canvas: #f8fafc;
            --bg-glass-card: rgba(255, 255, 255, 0.7);
            --bg-glass-card-hover: rgba(255, 255, 255, 0.9);
            --bg-glass-sidebar: rgba(248, 250, 252, 0.8);
            --bg-glass-bubble-bot: rgba(255, 255, 255, 0.85);
            --bg-glass-bubble-user: linear-gradient(135deg, #2563eb, #3b82f6);
            --border-glass: rgba(15, 23, 42, 0.08);
            --border-glass-subtle: rgba(15, 23, 42, 0.04);
            --border-glass-focus: rgba(37, 99, 235, 0.4);
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --accent-primary: #2563eb;
            --accent-glow: rgba(37, 99, 235, 0.15);
            --accent-emerald: #059669;
            --accent-amber: #d97706;
            --accent-rose: #e11d48;
            --orb-1: rgba(37, 99, 235, 0.08);
            --orb-2: rgba(147, 51, 234, 0.06);
            --orb-3: rgba(5, 150, 105, 0.05);
            --shadow-float: 0 16px 36px -8px rgba(15, 23, 42, 0.1), 0 4px 12px -2px rgba(15, 23, 42, 0.06);
            --shadow-subtle: 0 8px 24px -4px rgba(15, 23, 42, 0.08);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: var(--font-main);
            transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
        }

        body {
            background-color: var(--bg-canvas);
            color: var(--text-primary);
            height: 100vh;
            width: 100vw;
            display: flex;
            overflow: hidden;
            position: relative;
        }

        /* Ambient Glowing Background Orbs */
        .ambient-orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(90px);
            pointer-events: none;
            z-index: 0;
            opacity: 0.8;
            animation: pulseOrb 12s ease-in-out infinite alternate;
        }
        .orb-top-left {
            width: 480px;
            height: 480px;
            top: -120px;
            left: -100px;
            background: var(--orb-1);
        }
        .orb-bottom-right {
            width: 540px;
            height: 540px;
            bottom: -150px;
            right: -100px;
            background: var(--orb-2);
            animation-delay: -4s;
        }
        .orb-center {
            width: 360px;
            height: 360px;
            top: 40%;
            left: 45%;
            background: var(--orb-3);
            animation-delay: -8s;
        }
        @keyframes pulseOrb {
            0% { transform: scale(1) translate(0, 0); }
            100% { transform: scale(1.15) translate(30px, -20px); }
        }

        /* App Layout Container */
        .app-layout {
            position: relative;
            z-index: 1;
            display: flex;
            width: 100%;
            height: 100vh;
            height: 100dvh;
            padding: 16px;
            gap: 16px;
            box-sizing: border-box;
        }

        /* Floating Glass Sidebar (Zero Top Bar, Clean & Minimal) */
        aside.floating-sidebar {
            width: 340px;
            min-width: 320px;
            height: 100%;
            background: var(--bg-glass-sidebar);
            backdrop-filter: blur(28px) saturate(190%);
            -webkit-backdrop-filter: blur(28px) saturate(190%);
            border: 1px solid var(--border-glass);
            border-radius: 24px;
            box-shadow: var(--shadow-float);
            display: flex;
            flex-direction: column;
            padding: 20px 18px;
            gap: 16px;
            overflow-y: auto;
            scrollbar-width: thin;
            scrollbar-color: var(--border-glass) transparent;
        }
        aside.floating-sidebar::-webkit-scrollbar {
            width: 5px;
        }
        aside.floating-sidebar::-webkit-scrollbar-track {
            background: transparent;
        }
        aside.floating-sidebar::-webkit-scrollbar-thumb {
            background: var(--border-glass);
            border-radius: 10px;
        }
        .sidebar-footer {
            margin-top: auto;
            padding-top: 6px;
        }

        /* Sidebar Brand */
        .brand-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-glass-subtle);
        }
        .brand-title-wrap {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .brand-logo-icon {
            width: 38px;
            height: 38px;
            background: linear-gradient(135deg, var(--accent-primary), #8b5cf6);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            box-shadow: 0 4px 12px var(--accent-glow);
        }
        .brand-title {
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: var(--text-primary);
        }
        .brand-subtitle {
            font-size: 0.72rem;
            font-weight: 500;
            color: var(--text-muted);
            letter-spacing: 0.02em;
            text-transform: uppercase;
        }

        /* Theme Switch Button */
        .theme-toggle-btn {
            background: var(--bg-glass-card);
            border: 1px solid var(--border-glass);
            color: var(--text-secondary);
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        .theme-toggle-btn:hover {
            color: var(--text-primary);
            border-color: var(--border-glass-focus);
            transform: translateY(-1px);
        }

        /* Sidebar Section */
        .sidebar-section {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .section-label {
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Checkpoint Loader Card */
        .glass-card {
            background: var(--bg-glass-card);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--border-glass);
            border-radius: 16px;
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            box-shadow: var(--shadow-subtle);
        }
        .status-badge-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 0.74rem;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 20px;
            border: 1px solid transparent;
        }
        .status-badge.active {
            background: rgba(16, 185, 129, 0.12);
            color: var(--accent-emerald);
            border-color: rgba(16, 185, 129, 0.3);
        }
        .status-badge.untrained {
            background: rgba(245, 158, 11, 0.12);
            color: var(--accent-amber);
            border-color: rgba(245, 158, 11, 0.3);
        }
        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: currentColor;
        }

        .input-group {
            display: flex;
            gap: 6px;
        }
        .glass-input {
            flex: 1;
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid var(--border-glass);
            color: var(--text-primary);
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 0.82rem;
            outline: none;
            font-family: var(--font-mono);
        }
        [data-theme="light"] .glass-input {
            background: rgba(255, 255, 255, 0.8);
        }
        .glass-input:focus {
            border-color: var(--accent-primary);
        }
        .glass-btn {
            background: var(--accent-primary);
            color: #ffffff;
            border: none;
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }
        .glass-btn:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }
        .glass-btn-secondary {
            background: var(--bg-glass-card);
            color: var(--text-secondary);
            border: 1px solid var(--border-glass);
        }
        .glass-btn-secondary:hover {
            color: var(--text-primary);
            border-color: var(--border-glass-focus);
            background: var(--bg-glass-card-hover);
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        .stat-item {
            background: var(--bg-glass-card);
            border: 1px solid var(--border-glass-subtle);
            border-radius: 12px;
            padding: 10px;
            text-align: center;
        }
        .stat-val {
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        .stat-lbl {
            font-size: 0.68rem;
            color: var(--text-muted);
            text-transform: uppercase;
            font-weight: 500;
        }

        /* Aspects Pill Cloud */
        .aspect-cloud {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .aspect-chip {
            font-size: 0.72rem;
            padding: 4px 10px;
            border-radius: 20px;
            background: var(--bg-glass-card);
            border: 1px solid var(--border-glass);
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 4px;
        }

        /* Suggestions List */
        .suggestions-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .suggestion-item {
            background: var(--bg-glass-card);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            padding: 8px 12px;
            font-size: 0.76rem;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
            text-align: left;
            line-height: 1.35;
        }
        .suggestion-item:hover {
            color: var(--text-primary);
            border-color: var(--accent-primary);
            background: var(--bg-glass-card-hover);
            transform: translateX(2px);
        }

        /* Sidebar Footer */
        .sidebar-footer {
            margin-top: auto;
            padding-top: 12px;
            border-top: 1px solid var(--border-glass-subtle);
        }

        /* Floating Main Chat Canvas */
        main.floating-chat-canvas {
            flex: 1;
            height: 100%;
            display: flex;
            flex-direction: column;
            position: relative;
            background: var(--bg-glass-sidebar);
            backdrop-filter: blur(28px) saturate(190%);
            -webkit-backdrop-filter: blur(28px) saturate(190%);
            border: 1px solid var(--border-glass);
            border-radius: 24px;
            box-shadow: var(--shadow-float);
            overflow: hidden;
        }

        /* Message Scroll View */
        .chat-messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 28px 40px 100px 40px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            scroll-behavior: smooth;
        }
        .chat-messages-container::-webkit-scrollbar {
            width: 6px;
        }
        .chat-messages-container::-webkit-scrollbar-thumb {
            background: var(--border-glass);
            border-radius: 6px;
        }

        /* Message Bubbles */
        .chat-row {
            display: flex;
            gap: 14px;
            width: 100%;
            max-width: 860px;
            margin: 0 auto;
            animation: messageFloatIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        @keyframes messageFloatIn {
            0% { opacity: 0; transform: translateY(12px) scale(0.98); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        .chat-row.user {
            justify-content: flex-end;
        }

        .avatar-box {
            width: 36px;
            height: 36px;
            min-width: 36px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid var(--border-glass);
        }
        .avatar-box.bot {
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.2), rgba(139, 92, 246, 0.2));
            color: var(--accent-primary);
        }
        .avatar-box.user {
            background: linear-gradient(135deg, var(--accent-primary), #60a5fa);
            color: #ffffff;
        }

        .bubble-content {
            padding: 16px 20px;
            border-radius: 18px;
            line-height: 1.6;
            font-size: 0.92rem;
            position: relative;
            box-shadow: var(--shadow-subtle);
        }
        .chat-row.bot .bubble-content {
            background: var(--bg-glass-bubble-bot);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border-glass);
            color: var(--text-primary);
            border-top-left-radius: 4px;
            max-width: 78%;
        }
        .chat-row.user .bubble-content {
            background: var(--bg-glass-bubble-user);
            color: #ffffff;
            border-top-right-radius: 4px;
            max-width: 70%;
        }
        .chat-row.bot .bubble-content.welcome-bubble {
            max-width: 100%;
        }
        .welcome-suggestions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 8px;
            margin-top: 12px;
        }
        .suggestion-chip {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-glass);
            color: var(--text-primary);
            padding: 8px 12px;
            border-radius: var(--radius-sm, 8px);
            font-size: 0.82rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            text-align: left;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            font-family: inherit;
        }
        [data-theme="light"] .suggestion-chip {
            background: rgba(0, 0, 0, 0.03);
            border-color: rgba(0, 0, 0, 0.08);
        }
        .suggestion-chip:hover {
            background: var(--accent-glow);
            border-color: var(--accent-primary);
            color: var(--accent-primary);
            transform: translateY(-1px);
        }
        .suggestion-chip .chip-icon {
            font-size: 0.95rem;
            flex-shrink: 0;
        }

        .qa-card-meta {
            margin-top: 14px;
            padding-top: 12px;
            border-top: 1px solid var(--border-glass-subtle);
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
        }
        .meta-tag {
            font-size: 0.72rem;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 20px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            border: 1px solid var(--border-glass);
        }
        .meta-tag.aspect {
            background: rgba(59, 130, 246, 0.12);
            color: #60a5fa;
            border-color: rgba(59, 130, 246, 0.3);
        }
        .meta-tag.positive {
            background: rgba(16, 185, 129, 0.12);
            color: #34d399;
            border-color: rgba(16, 185, 129, 0.3);
        }
        .meta-tag.negative {
            background: rgba(244, 63, 94, 0.12);
            color: #fb7185;
            border-color: rgba(244, 63, 94, 0.3);
        }
        .meta-tag.neutral {
            background: rgba(148, 163, 184, 0.12);
            color: #cbd5e1;
            border-color: rgba(148, 163, 184, 0.3);
        }
        .meta-tag.coref {
            background: rgba(168, 85, 247, 0.12);
            color: #c084fc;
            border-color: rgba(168, 85, 247, 0.3);
        }

        .quote-evidence {
            margin: 10px 0;
            padding: 10px 14px;
            background: rgba(0, 0, 0, 0.2);
            border-left: 3px solid var(--accent-primary);
            border-radius: 0 10px 10px 0;
            font-style: italic;
            color: var(--text-secondary);
            line-height: 1.5;
        }

        /* Google Maps Interactive Card */
        .map-card-container {
            margin-top: 14px;
            background: rgba(0, 0, 0, 0.25);
            border: 1px solid var(--border-glass);
            border-radius: 16px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding: 14px;
        }
        [data-theme="light"] .map-card-container {
            background: rgba(0, 0, 0, 0.03);
            border-color: rgba(0, 0, 0, 0.08);
        }
        .map-hotel-info {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .map-hotel-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--text-primary);
        }
        .map-hotel-tags {
            display: flex;
            gap: 8px;
            align-items: center;
            font-size: 0.78rem;
        }
        .map-address-line {
            font-size: 0.85rem;
            color: var(--text-secondary);
            display: flex;
            align-items: flex-start;
            gap: 6px;
            line-height: 1.4;
        }
        .map-frame-wrapper {
            position: relative;
            width: 100%;
            height: 220px;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border-glass-subtle);
        }
        .map-frame-wrapper iframe {
            width: 100%;
            height: 100%;
            border: 0;
        }
        .map-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .map-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 14px;
            border-radius: 10px;
            font-size: 0.82rem;
            font-weight: 600;
            text-decoration: none;
            background: var(--accent-primary);
            color: #ffffff;
            transition: all 0.2s ease;
            cursor: pointer;
            border: none;
        }
        .map-btn:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }
        .map-btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-primary);
            border: 1px solid var(--border-glass);
        }
        [data-theme="light"] .map-btn-secondary {
            background: rgba(0, 0, 0, 0.05);
        }

        /* Evidence Citations Section */
        .evidence-section {
            margin-top: 14px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .evidence-header {
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .evidence-card {
            background: rgba(0, 0, 0, 0.22);
            border-left: 3px solid var(--accent-primary);
            border-radius: 0 12px 12px 0;
            padding: 10px 14px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        [data-theme="light"] .evidence-card {
            background: rgba(0, 0, 0, 0.03);
        }
        .evidence-meta-row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
            font-size: 0.76rem;
            color: var(--text-muted);
        }
        .evidence-badge {
            padding: 2px 7px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.72rem;
        }
        .evidence-badge.time-weight {
            background: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }
        .evidence-badge.positive {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
        }
        .evidence-badge.negative {
            background: rgba(244, 63, 94, 0.15);
            color: #fb7185;
        }
        .evidence-badge.neutral {
            background: rgba(148, 163, 184, 0.15);
            color: #94a3b8;
        }
        .evidence-quote-text {
            font-style: italic;
            color: var(--text-primary);
            line-height: 1.5;
            font-size: 0.88rem;
        }

        /* Collapsible Original Reviews Container */
        details.original-reviews-toggle {
            margin-top: 14px;
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid var(--border-glass);
            border-radius: 14px;
            overflow: hidden;
            transition: all 0.25s ease;
        }
        [data-theme="light"] details.original-reviews-toggle {
            background: rgba(0, 0, 0, 0.02);
            border-color: rgba(0, 0, 0, 0.08);
        }
        details.original-reviews-toggle summary {
            padding: 10px 14px;
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            user-select: none;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: background 0.2s ease, color 0.2s ease;
        }
        details.original-reviews-toggle summary::-webkit-details-marker {
            display: none;
        }
        details.original-reviews-toggle summary:hover {
            background: rgba(255, 255, 255, 0.04);
            color: var(--text-primary);
        }
        details.original-reviews-toggle[open] summary {
            border-bottom: 1px solid var(--border-glass-subtle);
            color: var(--accent-primary);
        }
        .original-reviews-content {
            padding: 12px 14px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-height: 380px;
            overflow-y: auto;
        }
        .review-full-item {
            padding: 10px 12px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-glass-subtle);
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        [data-theme="light"] .review-full-item {
            background: rgba(255, 255, 255, 0.8);
        }
        .review-full-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 6px;
            font-size: 0.76rem;
            color: var(--text-muted);
        }
        .review-full-body {
            font-size: 0.85rem;
            color: var(--text-secondary);
            line-height: 1.5;
            white-space: pre-wrap;
        }
        [data-theme="light"] .quote-evidence {
            background: rgba(0, 0, 0, 0.04);
        }

        /* Floating Pill Input Bar */
        .floating-input-wrapper {
            position: absolute;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            width: 80%;
            max-width: 820px;
            z-index: 10;
        }
        .floating-input-bar {
            background: var(--bg-glass-card);
            backdrop-filter: blur(28px) saturate(200%);
            -webkit-backdrop-filter: blur(28px) saturate(200%);
            border: 1px solid var(--border-glass);
            border-radius: 28px;
            box-shadow: var(--shadow-float);
            padding: 6px 8px 6px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: all 0.2s;
        }
        .floating-input-bar:focus-within {
            border-color: var(--border-glass-focus);
            box-shadow: 0 20px 40px -8px var(--accent-glow), var(--shadow-float);
        }
        .prompt-input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-primary);
            font-size: 0.95rem;
            padding: 10px 0;
        }
        .prompt-input::placeholder {
            color: var(--text-muted);
        }
        .send-btn {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: var(--accent-primary);
            border: none;
            color: #ffffff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            flex-shrink: 0;
        }
        .send-btn:hover {
            transform: scale(1.05);
            background: #2563eb;
        }
        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        /* Typing Dots */
        .typing-dots {
            display: flex;
            align-items: center;
            gap: 5px;
            padding: 8px 12px;
        }
        .typing-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--text-muted);
            animation: typingBounce 1.4s infinite ease-in-out both;
        }
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes typingBounce {
            0%, 80%, 100% { transform: scale(0); opacity: 0.4; }
            40% { transform: scale(1); opacity: 1; }
        }

        /* SVG Icons */
        .icon-svg {
            width: 18px;
            height: 18px;
            fill: none;
            stroke: currentColor;
            stroke-width: 2;
            stroke-linecap: round;
            stroke-linejoin: round;
        }
        .icon-svg.sm { width: 14px; height: 14px; }
        .icon-svg.lg { width: 22px; height: 22px; }

        /* Toast Notifications */
        .toast-container {
            position: fixed;
            top: 24px;
            right: 24px;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 8px;
            pointer-events: none;
        }
        .toast {
            background: var(--bg-glass-card);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            padding: 10px 16px;
            color: var(--text-primary);
            font-size: 0.84rem;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: var(--shadow-float);
            animation: toastIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            pointer-events: auto;
        }
        .toast.success {
            border-color: rgba(16, 185, 129, 0.4);
            color: var(--accent-emerald);
        }
        .toast.error {
            border-color: rgba(244, 63, 94, 0.4);
            color: var(--accent-rose);
        }
        @keyframes toastIn {
            from { opacity: 0; transform: translateY(-10px) scale(0.95); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes toastOut {
            from { opacity: 1; transform: translateY(0) scale(1); }
            to { opacity: 0; transform: translateY(-10px) scale(0.95); }
        }

        /* Responsive Breakpoints */
        @media (max-width: 900px) {
            .app-layout {
                flex-direction: column;
                height: 100vh;
                padding: 10px;
                gap: 10px;
                overflow-y: auto;
            }
            aside.floating-sidebar {
                width: 100%;
                min-width: unset;
                height: auto;
                max-height: 42vh;
            }
            main.floating-chat-canvas {
                min-height: 56vh;
            }
            .chat-messages-container {
                padding: 16px 14px 90px 14px;
            }
            .floating-input-wrapper {
                width: 92%;
                bottom: 12px;
            }
        }
    </style>
</head>
<body>
    <div class="toast-container" id="toast-container"></div>
    <div class="ambient-orb orb-top-left"></div>
    <div class="ambient-orb orb-bottom-right"></div>
    <div class="ambient-orb orb-center"></div>

    <div class="app-layout">
        <!-- Floating Glass Sidebar -->
        <aside class="floating-sidebar">
            <div class="brand-header">
                <div class="brand-title-wrap">
                    <div class="brand-logo-icon">
                        <svg class="icon-svg lg" viewBox="0 0 24 24">
                            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                        </svg>
                    </div>
                    <div>
                        <div class="brand-title">AspectQA</div>
                        <div class="brand-subtitle">Hotel Intelligence</div>
                    </div>
                </div>
                <button class="theme-toggle-btn" id="theme-btn" title="Toggle Light/Dark Theme">
                    <svg class="icon-svg" id="theme-icon-moon" viewBox="0 0 24 24">
                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                    </svg>
                    <svg class="icon-svg" id="theme-icon-sun" style="display:none;" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="5"/>
                        <line x1="12" y1="1" x2="12" y2="3"/>
                        <line x1="12" y1="21" x2="12" y2="23"/>
                        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                        <line x1="1" y1="12" x2="3" y2="12"/>
                        <line x1="21" y1="12" x2="23" y2="12"/>
                        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                    </svg>
                </button>
            </div>

            <!-- Model Weights Checkpoint Manager -->
            <div class="sidebar-section">
                <div class="section-label">
                    <svg class="icon-svg sm" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>
                    Model Checkpoint (model/)
                </div>
                <div class="glass-card">
                    <div class="status-badge-row">
                        <span class="status-badge untrained" id="model-status-badge">
                            <span class="status-dot"></span>
                            <span id="model-status-text">Checking status...</span>
                        </span>
                        <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);" id="model-device-text">CUDA/CPU</span>
                    </div>
                    <div class="input-group">
                        <input type="text" class="glass-input" id="checkpoint-path-input" value="model/model.pt" placeholder="model/model.pt">
                        <button class="glass-btn" id="load-model-btn" title="Load Weights">
                            <svg class="icon-svg sm" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Load
                        </button>
                    </div>
                </div>
            </div>

            <!-- Knowledge Base Summary -->
            <div class="sidebar-section">
                <div class="section-label">
                    <svg class="icon-svg sm" viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                    Knowledge Base
                </div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-val" id="stat-hotel-count">2,622</div>
                        <div class="stat-lbl">Hotels Indexed</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-val">6</div>
                        <div class="stat-lbl">Aspect Domains</div>
                    </div>
                </div>
                <div class="aspect-cloud">
                    <span class="aspect-chip">Service</span>
                    <span class="aspect-chip">Facility</span>
                    <span class="aspect-chip">Experience</span>
                    <span class="aspect-chip">Amenity</span>
                    <span class="aspect-chip">Loyalty</span>
                    <span class="aspect-chip">Branding</span>
                </div>
            </div>

            <!-- Natural Language Capabilities Guide -->
            <div class="sidebar-section">
                <div class="section-label">
                    <svg class="icon-svg sm" viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                    Hỏi đáp Ngôn ngữ Tự do
                </div>
                <div style="font-size: 0.78rem; color: var(--text-secondary); line-height: 1.45; display: flex; flex-direction: column; gap: 6px;">
                    <div style="padding: 6px 10px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-glass); border-radius: var(--radius-sm);">
                        <strong style="color: var(--text-primary); display: block; margin-bottom: 2px;">📍 Vị trí & Google Maps:</strong>
                        Hỏi địa chỉ/vị trí bất kỳ khách sạn nào để xem bản đồ tương tác trực tiếp.
                    </div>
                    <div style="padding: 6px 10px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-glass); border-radius: var(--radius-sm);">
                        <strong style="color: var(--text-primary); display: block; margin-bottom: 2px;">⭐ Xếp hạng sao & Số lượng:</strong>
                        Hỏi khách sạn mấy sao hoặc có bao nhiêu đánh giá về khía cạnh cụ thể.
                    </div>
                    <div style="padding: 6px 10px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-glass); border-radius: var(--radius-sm);">
                        <strong style="color: var(--text-primary); display: block; margin-bottom: 2px;">⚡ Phân tích Đa đánh giá (Feature 10):</strong>
                        Ưu tiên đánh giá gần đây để tổng hợp câu trả lời tự nhiên và trích dẫn gốc.
                    </div>
                    <div style="padding: 6px 10px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-glass); border-radius: var(--radius-sm);">
                        <strong style="color: var(--text-primary); display: block; margin-bottom: 2px;">💬 Hội thoại đa lượt:</strong>
                        Dùng đại từ "khách sạn này", "ở đó thế nào" mà không cần gõ lại tên.
                    </div>
                </div>
            </div>

            <div class="sidebar-footer">
                <button class="glass-btn glass-btn-secondary" id="clear-btn" style="width: 100%; justify-content: center; gap: 8px;">
                    <svg class="icon-svg sm" viewBox="0 0 24 24"><polyline points="1 4 1 10 7 10"/><polyline points="23 20 23 14 17 14"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/></svg>
                    <span>Làm mới hội thoại (Reset)</span>
                </button>
            </div>
        </aside>

        <!-- Floating Main Chat Canvas -->
        <main class="floating-chat-canvas">
            <div class="chat-messages-container" id="chat-box">
                <div class="chat-row bot">
                    <div class="avatar-box bot">
                        <svg class="icon-svg" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                    </div>
                    <div class="bubble-content welcome-bubble">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
                            <strong style="font-size: 1.02rem; color: var(--text-primary);">Xin chào! Chào mừng bạn đến với Hotel Aspect QA Assistant</strong>
                            <span style="font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; background: rgba(59, 130, 246, 0.15); color: var(--accent-primary); font-weight: 600; border: 1px solid rgba(59, 130, 246, 0.3);">v2.0 Neural</span>
                        </div>
                        <p style="color: var(--text-secondary); font-size: 0.88rem; line-height: 1.55; margin-bottom: 12px;">
                            Hệ thống hỗ trợ 100% <strong>ngôn ngữ tự nhiên tự do</strong> bằng Tiếng Việt hoặc Tiếng Anh, chạy trực tiếp trên checkpoint <code>model.pt</code>.<br>
                            Bạn có thể tự do gõ câu hỏi bất kỳ, hoặc chọn nhanh các câu hỏi gợi ý bên dưới:
                        </p>
                        <div class="welcome-suggestions-grid">
                            <button type="button" class="suggestion-chip" onclick="sendSuggested('Khách sạn Pullman Hà Nội mấy sao và ở đâu?')">
                                <span class="chip-icon">📍</span>
                                <span>Pullman Hà Nội mấy sao và ở đâu?</span>
                            </button>
                            <button type="button" class="suggestion-chip" onclick="sendSuggested('Chất lượng dịch vụ và nhân viên ở Pullman Hà Nội dạo gần đây thế nào?')">
                                <span class="chip-icon">⚡</span>
                                <span>Dịch vụ & nhân viên Pullman gần đây?</span>
                            </button>
                            <button type="button" class="suggestion-chip" onclick="sendSuggested('Có bao nhiêu đánh giá về phòng ốc ở khách sạn này?')">
                                <span class="chip-icon">💬</span>
                                <span>Bao nhiêu đánh giá về phòng ở khách sạn này?</span>
                            </button>
                            <button type="button" class="suggestion-chip" onclick="sendSuggested('Salinda Resort Phú Quốc phục vụ ăn uống có ngon không?')">
                                <span class="chip-icon">⭐</span>
                                <span>Salinda Resort ăn uống có ngon không?</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="floating-input-wrapper">
                <form class="floating-input-bar" id="chat-form">
                    <input type="text" class="prompt-input" id="prompt-input" placeholder="Ask about any hotel or aspect..." autocomplete="off">
                    <button type="submit" class="send-btn" id="send-btn" title="Send Query">
                        <svg class="icon-svg" viewBox="0 0 24 24">
                            <line x1="22" y1="2" x2="11" y2="13"/>
                            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                        </svg>
                    </button>
                </form>
            </div>
        </main>
    </div>

    <script>
        const chatBox = document.getElementById('chat-box');
        const chatForm = document.getElementById('chat-form');
        const promptInput = document.getElementById('prompt-input');
        const sendBtn = document.getElementById('send-btn');
        const themeBtn = document.getElementById('theme-btn');
        const themeIconMoon = document.getElementById('theme-icon-moon');
        const themeIconSun = document.getElementById('theme-icon-sun');
        const loadModelBtn = document.getElementById('load-model-btn');
        const checkpointInput = document.getElementById('checkpoint-path-input');
        const modelBadge = document.getElementById('model-status-badge');
        const modelText = document.getElementById('model-status-text');
        const modelDeviceText = document.getElementById('model-device-text');
        const clearBtn = document.getElementById('clear-btn');
        const statHotelCount = document.getElementById('stat-hotel-count');

        // Theme Toggle
        let currentTheme = localStorage.getItem('aspectqa_theme') || 'dark';
        applyTheme(currentTheme);

        themeBtn.addEventListener('click', () => {
            currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
            applyTheme(currentTheme);
            localStorage.setItem('aspectqa_theme', currentTheme);
        });

        function applyTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            if (theme === 'light') {
                themeIconMoon.style.display = 'none';
                themeIconSun.style.display = 'block';
            } else {
                themeIconMoon.style.display = 'block';
                themeIconSun.style.display = 'none';
            }
        }

        async function updateStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                statHotelCount.textContent = Number(data.hotels_indexed).toLocaleString();
                modelDeviceText.textContent = data.device.toUpperCase();

                if (data.model_loaded) {
                    modelBadge.className = 'status-badge active';
                    modelText.textContent = 'Active: ' + (data.model_path.split('/').pop() || 'model.pt');
                } else {
                    modelBadge.className = 'status-badge untrained';
                    modelText.textContent = 'Awaiting model/model.pt';
                }
            } catch (err) {
                console.error('Failed to get status:', err);
            }
        }
        updateStatus();

        loadModelBtn.addEventListener('click', async () => {
            const path = checkpointInput.value.trim() || 'model/model.pt';
            loadModelBtn.disabled = true;
            try {
                const res = await fetch('/api/load_model', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({model_path: path})
                });
                const data = await res.json();
                if (data.success) {
                    showToast(data.message, 'success');
                } else {
                    showToast(data.message, 'error');
                }
                updateStatus();
            } catch (err) {
                showToast('Failed to load checkpoint: ' + err, 'error');
            } finally {
                loadModelBtn.disabled = false;
            }
        });

        let clientSessionId = 'sess_' + Math.random().toString(36).substring(2, 12);

        const WELCOME_CARD_HTML = `
            <div class="chat-row bot">
                <div class="avatar-box bot">
                    <svg class="icon-svg" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                </div>
                <div class="bubble-content welcome-bubble">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
                        <strong style="font-size: 1.02rem; color: var(--text-primary);">Xin chào! Chào mừng bạn đến với Hotel Aspect QA Assistant</strong>
                        <span style="font-size: 0.72rem; padding: 2px 8px; border-radius: 12px; background: rgba(59, 130, 246, 0.15); color: var(--accent-primary); font-weight: 600; border: 1px solid rgba(59, 130, 246, 0.3);">v2.0 Neural</span>
                    </div>
                    <p style="color: var(--text-secondary); font-size: 0.88rem; line-height: 1.55; margin-bottom: 12px;">
                        Hệ thống hỗ trợ 100% <strong>ngôn ngữ tự nhiên tự do</strong> bằng Tiếng Việt hoặc Tiếng Anh, chạy trực tiếp trên checkpoint <code>model.pt</code>.<br>
                        Bạn có thể tự do gõ câu hỏi bất kỳ, hoặc chọn nhanh các câu hỏi gợi ý bên dưới:
                    </p>
                    <div class="welcome-suggestions-grid">
                        <button type="button" class="suggestion-chip" onclick="sendSuggested('Khách sạn Pullman Hà Nội mấy sao và ở đâu?')">
                            <span class="chip-icon">📍</span>
                            <span>Pullman Hà Nội mấy sao và ở đâu?</span>
                        </button>
                        <button type="button" class="suggestion-chip" onclick="sendSuggested('Chất lượng dịch vụ và nhân viên ở Pullman Hà Nội dạo gần đây thế nào?')">
                            <span class="chip-icon">⚡</span>
                            <span>Dịch vụ & nhân viên Pullman gần đây?</span>
                        </button>
                        <button type="button" class="suggestion-chip" onclick="sendSuggested('Có bao nhiêu đánh giá về phòng ốc ở khách sạn này?')">
                            <span class="chip-icon">💬</span>
                            <span>Bao nhiêu đánh giá về phòng ở khách sạn này?</span>
                        </button>
                        <button type="button" class="suggestion-chip" onclick="sendSuggested('Salinda Resort Phú Quốc phục vụ ăn uống có ngon không?')">
                            <span class="chip-icon">⭐</span>
                            <span>Salinda Resort ăn uống có ngon không?</span>
                        </button>
                    </div>
                </div>
            </div>
        `;

        window.sendSuggested = function(text) {
            promptInput.value = text;
            handleSend(text);
        };

        function renderWelcome() {
            chatBox.innerHTML = WELCOME_CARD_HTML;
            chatBox.scrollTop = 0;
        }

        clearBtn.addEventListener('click', async () => {
            clearBtn.disabled = true;
            try {
                await fetch('/api/clear', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({session_id: clientSessionId})
                });
                clientSessionId = 'sess_' + Math.random().toString(36).substring(2, 12);
                renderWelcome();
                promptInput.value = '';
                promptInput.focus();
                showToast('Đã làm mới phiên hội thoại thành công (Reset)', 'success');
            } catch (err) {
                showToast('Lỗi khi làm mới phiên: ' + err, 'error');
            } finally {
                clearBtn.disabled = false;
            }
        });

        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = promptInput.value.trim();
            if (!text) return;
            handleSend(text);
        });

        async function handleSend(text) {
            promptInput.value = '';
            appendUserMessage(text);
            const typingEl = appendTypingIndicator();
            sendBtn.disabled = true;

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({query: text, session_id: clientSessionId})
                });
                const data = await res.json();
                typingEl.remove();
                appendBotResponse(data);
            } catch (err) {
                typingEl.remove();
                appendErrorMessage('Network or server error: ' + err);
            } finally {
                sendBtn.disabled = false;
                promptInput.focus();
            }
        }

        function appendUserMessage(text) {
            const row = document.createElement('div');
            row.className = 'chat-row user';
            row.innerHTML = `
                <div class="bubble-content">${escapeHtml(text)}</div>
                <div class="avatar-box user">
                    <svg class="icon-svg" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                </div>
            `;
            chatBox.appendChild(row);
            scrollToBottom();
        }

        function appendTypingIndicator() {
            const row = document.createElement('div');
            row.className = 'chat-row bot';
            row.innerHTML = `
                <div class="avatar-box bot">
                    <svg class="icon-svg" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                </div>
                <div class="bubble-content">
                    <div class="typing-dots">
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                    </div>
                </div>
            `;
            chatBox.appendChild(row);
            scrollToBottom();
            return row;
        }

        function appendBotResponse(data) {
            const row = document.createElement('div');
            row.className = 'chat-row bot';

            let metaHtml = '';
            if (data.aspect) {
                metaHtml += `<span class="meta-tag aspect">Domain: ${escapeHtml(data.aspect)}</span>`;
            }
            if (data.sentiment) {
                const sCls = data.sentiment.toLowerCase();
                metaHtml += `<span class="meta-tag ${sCls}">Sentiment: ${escapeHtml(data.sentiment)}</span>`;
            }
            if (data.star_desc) {
                metaHtml += `<span class="meta-tag" style="background:rgba(245,158,11,0.15);color:#fbbf24;border-color:rgba(245,158,11,0.3);">★ ${escapeHtml(data.star_desc)}</span>`;
            }
            if (data.aspect_count !== undefined && data.total_reviews !== undefined) {
                metaHtml += `<span class="meta-tag" style="background:rgba(16,185,129,0.15);color:#34d399;border-color:rgba(16,185,129,0.3);">📊 ${data.aspect_count}/${data.total_reviews} Đánh giá (${data.aspect_pct}%)</span>`;
            }
            if (data.trend_label) {
                metaHtml += `<span class="meta-tag coref" style="background:rgba(59,130,246,0.12);color:#60a5fa;border-color:rgba(59,130,246,0.3);">⚡ ${escapeHtml(data.trend_label)}</span>`;
            }
            if (data.context_applied) {
                metaHtml += `<span class="meta-tag coref">Context Resolved</span>`;
            }

            // 1. Câu trả lời đàm thoại trực tiếp
            const answerText = data.direct_answer || data.text || '';
            let contentHtml = `<div>${formatMarkdown(answerText)}</div>`;

            // 2. Thẻ Google Maps tương tác (khi hỏi vị trí/địa chỉ)
            if (data.map_card) {
                const mc = data.map_card;
                const starBadge = mc.star ? `<span class="badge star" style="background:rgba(245,158,11,0.15);color:#fbbf24;padding:2px 6px;border-radius:4px;font-weight:600;">★ ${escapeHtml(mc.star)}</span>` : '';
                const scoreBadge = mc.score ? `<span class="badge score" style="background:rgba(16,185,129,0.15);color:#34d399;padding:2px 6px;border-radius:4px;font-weight:600;">Rating ${mc.score}/5.0</span>` : '';
                
                contentHtml += `
                    <div class="map-card-container">
                        <div class="map-hotel-info">
                            <div class="map-hotel-title">${escapeHtml(mc.hotel_name)}</div>
                            <div class="map-hotel-tags">
                                ${starBadge} ${scoreBadge}
                            </div>
                            <div class="map-address-line">
                                <span>📍</span>
                                <span>${escapeHtml(mc.address)}</span>
                            </div>
                        </div>
                        <div class="map-frame-wrapper">
                            <iframe 
                                src="${escapeHtml(mc.embed_url)}" 
                                loading="lazy" 
                                referrerpolicy="no-referrer-when-downgrade">
                            </iframe>
                        </div>
                        <div class="map-actions">
                            <a href="${escapeHtml(mc.search_url)}" target="_blank" class="map-btn">
                                <svg class="icon-svg" style="width:14px;height:14px;" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"/></svg>
                                Mở trong Google Maps (Open in Maps)
                            </a>
                            <button class="map-btn map-btn-secondary" data-address="${escapeHtml(mc.address)}" onclick="copyHotelAddress(this)">
                                <svg class="icon-svg" style="width:14px;height:14px;" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                                Sao chép địa chỉ
                            </button>
                        </div>
                    </div>
                `;
            }

            // 3. Dẫn chứng trích xuất từ đánh giá khách hàng (Key Evidence Citations)
            if (data.citations && data.citations.length > 0) {
                let citationsHtml = `
                    <div class="evidence-section">
                        <div class="evidence-header">
                            <span>📌</span>
                            <span>Dẫn chứng trích xuất từ đánh giá khách hàng (Key Evidence Citations)</span>
                        </div>
                `;
                for (const c of data.citations) {
                    const sentClass = (c.sentiment || '').toLowerCase();
                    const weightPct = c.weight_pct !== undefined ? `${c.weight_pct}%` : '';
                    citationsHtml += `
                        <div class="evidence-card">
                            <div class="evidence-meta-row">
                                <span>📅 ${escapeHtml(c.date || '')}</span>
                                <span>⭐ ${c.score || ''}/5.0</span>
                                <span class="evidence-badge ${sentClass}">${escapeHtml(c.sentiment || '')}</span>
                                ${weightPct ? `<span class="evidence-badge time-weight">⚡ Trọng số thời gian: ${weightPct}</span>` : ''}
                            </div>
                            <div class="evidence-quote-text">"${escapeHtml(c.span)}"</div>
                        </div>
                    `;
                }
                citationsHtml += `</div>`;
                contentHtml += citationsHtml;
            }

            // 4. Khối ẩn chứa đánh giá gốc (Collapsible Original Reviews - Nhấn để mở xem)
            if (data.original_reviews && data.original_reviews.length > 0) {
                let reviewsHtml = `
                    <details class="original-reviews-toggle">
                        <summary>
                            <span>🔍 Xem toàn bộ đánh giá gốc (View original reviews) • ${data.original_reviews.length} đánh giá</span>
                            <span style="font-size:0.75rem;opacity:0.7;">▼ Nhấn để mở</span>
                        </summary>
                        <div class="original-reviews-content">
                `;
                for (let idx = 0; idx < data.original_reviews.length; idx++) {
                    const r = data.original_reviews[idx];
                    const sentClass = (r.sentiment || '').toLowerCase();
                    const weightPct = r.weight_pct !== undefined ? `${r.weight_pct}%` : '';
                    reviewsHtml += `
                        <div class="review-full-item">
                            <div class="review-full-header">
                                <span style="font-weight:600;">Đánh giá #${idx + 1} &bull; 📅 ${escapeHtml(r.date || '')}</span>
                                <div>
                                    <span style="margin-right:6px;">⭐ ${r.score || ''}/5.0</span>
                                    <span class="evidence-badge ${sentClass}">${escapeHtml(r.sentiment || '')}</span>
                                    ${weightPct ? `<span class="evidence-badge time-weight">Trọng số: ${weightPct}</span>` : ''}
                                </div>
                            </div>
                            <div class="review-full-body">${escapeHtml(r.text || '')}</div>
                        </div>
                    `;
                }
                reviewsHtml += `
                        </div>
                    </details>
                `;
                contentHtml += reviewsHtml;
            }

            row.innerHTML = `
                <div class="avatar-box bot">
                    <svg class="icon-svg" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                </div>
                <div class="bubble-content">
                    ${contentHtml}
                    ${metaHtml ? `<div class="qa-card-meta">${metaHtml}</div>` : ''}
                </div>
            `;
            chatBox.appendChild(row);
            scrollToBottom();
        }

        function appendErrorMessage(msg) {
            const row = document.createElement('div');
            row.className = 'chat-row bot';
            row.innerHTML = `
                <div class="avatar-box bot" style="color: var(--accent-rose);">
                    <svg class="icon-svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                </div>
                <div class="bubble-content" style="border-color: rgba(244, 63, 94, 0.3);">
                    ${escapeHtml(msg)}
                </div>
            `;
            chatBox.appendChild(row);
            scrollToBottom();
        }

        function scrollToBottom() {
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function showToast(msg, type = 'info') {
            const container = document.getElementById('toast-container');
            if (!container) return;
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = msg;
            container.appendChild(toast);
            setTimeout(() => {
                toast.style.animation = 'toastOut 0.3s forwards';
                setTimeout(() => toast.remove(), 300);
            }, 3500);
        }

        function copyHotelAddress(btn) {
            const addr = btn.getAttribute('data-address') || '';
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(addr).then(() => {
                    showToast('Đã sao chép địa chỉ!', 'success');
                }).catch(() => {
                    showToast('Không thể sao chép địa chỉ', 'error');
                });
            } else {
                const ta = document.createElement('textarea');
                ta.value = addr;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                ta.remove();
                showToast('Đã sao chép địa chỉ!', 'success');
            }
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function formatMarkdown(str) {
            if (!str) return '';
            let formatted = escapeHtml(str);
            // Blockquote / Quote evidence formatting
            formatted = formatted.replace(/(?:^|\n)(&gt;|>)\s*(".*?"|[\s\S]*?)(?=\n\n|\n•|$)/g, '<div class="quote-evidence">$2</div>');
            // Bold & Italic & Code
            formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
            formatted = formatted.replace(/`([^`]+)`/g, '<code style="font-family:var(--font-mono);background:rgba(0,0,0,0.2);padding:2px 6px;border-radius:4px;">$1</code>');
            // Bullet points
            formatted = formatted.replace(/(?:^|\n)•\s*(.*?)(?=\n|$)/g, '<div style="margin: 3px 0 3px 4px; display: flex; align-items: baseline; gap: 6px;"><span style="color:var(--accent-primary);">•</span><span>$1</span></div>');
            // Paragraph breaks
            formatted = formatted.replace(/\n\n/g, '<br><br>');
            formatted = formatted.replace(/\n/g, '<br>');
            return formatted;
        }
    </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# HTTP Request Handler
# ---------------------------------------------------------------------------
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class QAChatHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)

        if url.path == '/' or url.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))

        elif url.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            payload = {
                'hotels_indexed': len(HOTEL_DATABASE),
                'model_loaded': BOT.model_loaded if BOT else False,
                'model_path': BOT.model_path if BOT else 'model/model.pt',
                'device': str(BOT.device) if BOT else 'cpu',
                'aspects': ASPECTS
            }
            self.wfile.write(json.dumps(payload).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 1_000_000:
            self.send_error(413, "Payload Too Large")
            return

        post_data = self.rfile.read(content_length)

        try:
            body = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            body = {}

        session_id = body.get('session_id', 'default')

        if url.path == '/api/chat':
            try:
                user_query = body.get('query', '').strip()
                if not user_query:
                    response = {
                        "text": "Empty query received.",
                        "hotel": None,
                        "aspect": None,
                        "sentiment": None,
                        "confidence": 0,
                        "evidence": None,
                        "context_applied": False
                    }
                else:
                    response = BOT.answer_query(user_query, session_id=session_id)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

        elif url.path == '/api/load_model':
            try:
                m_path = body.get('model_path', 'model/model.pt').strip()
                success, msg = BOT.load_checkpoint(m_path)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': success, 'message': msg}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'message': str(e)}).encode('utf-8'))

        elif url.path == '/api/clear':
            try:
                if BOT:
                    BOT.session_manager.reset_state(session_id)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return

# ---------------------------------------------------------------------------
# Server Entrypoint
# ---------------------------------------------------------------------------
def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


def main():
    global BOT
    parser = argparse.ArgumentParser(description="Hotel Aspect QA Conversational Web Server")
    parser.add_argument('--port', type=int, default=7860, help="Port to serve on")
    parser.add_argument('--model', type=str, default='model/model.pt', help="Path to model checkpoint")
    args = parser.parse_args()

    # Load 2,622 Hotels Knowledge Base
    load_hotel_database()

    # Initialize Bot & Neural Architecture
    BOT = ConversationalQABot(model_path=args.model)

    active_port = args.port
    while not is_port_available(active_port) and active_port < args.port + 30:
        active_port += 1

    server = ThreadedHTTPServer(('0.0.0.0', active_port), QAChatHandler)
    url = f"http://localhost:{active_port}"

    print("=" * 75)
    print("🏨 ASPECT-BASED HOTEL CONVERSATIONAL QA WEB SERVER")
    print("=" * 75)
    print(f" Web UI URL : {url}")
    print(f" Hardware   : {BOT.device}")
    print(f" Knowledge  : {len(HOTEL_DATABASE):,} hotels indexed")
    print(f" Checkpoint : {'Active (' + BOT.model_path + ')' if BOT.model_loaded else 'Awaiting ' + args.model}")
    print("=" * 75)
    print("Press Ctrl+C to shut down gracefully.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()


if __name__ == '__main__':
    main()
