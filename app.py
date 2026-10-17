import os
import sys
import json
import re
import socket
import argparse
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from collections import defaultdict
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
        'phục vụ', 'nhân viên', 'lễ tân', 'thái độ', 'chu đáo', 'nhiệt tình', 'tiếp đón', 'hỗ trợ'
    ],
    'Facility': [
        'facility', 'room', 'bed', 'bathroom', 'shower', 'clean', 'dirty', 'air conditioner', 'ac', 'tv', 'balcony', 'sheet', 'towel', 'maintenance',
        'cơ sở vật chất', 'phòng', 'giường', 'vệ sinh', 'nhà tắm', 'vòi sen', 'tiện nghi', 'thoáng mát', 'rộng rãi'
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
        'brand', 'branding', 'reputation', 'star', 'pullman', 'marriott', 'muong thanh', 'luxury', 'advertised', 'photos', 'standard',
        'thương hiệu', 'danh tiếng', 'tiêu chuẩn', 'sao', 'đẳng cấp', 'quảng cáo', 'uy tín'
    ]
}

LOCATION_KEYWORDS = [
    'where', 'location', 'address', 'located', 'situated', 'map', 'directions', 'find',
    'ở đâu', 'địa chỉ', 'vị trí', 'nằm ở', 'nằm tại', 'chỗ nào', 'tọa lạc'
]

COREFERENCE_PRONOUNS = [
    'it', 'this hotel', 'that hotel', 'the hotel', 'here', 'there', 'the property',
    'khách sạn này', 'khách sạn đó', 'chỗ này', 'chỗ đó', 'nó', 'ở đây', 'nơi này', 'ks này', 'ks đó'
]

VIETNAMESE_MARKERS = [
    'không', 'thế nào', 'ở đâu', 'ra sao', 'có', 'cho tôi', 'của', 'và', 'là', 'như',
    'khách sạn', 'phòng', 'nhân viên', 'dịch vụ', 'ăn sáng', 'bể bơi', 'đẹp', 'sạch'
]

def is_vietnamese_query(text: str) -> bool:
    t_lower = text.lower()
    # Check for Vietnamese diacritics
    if re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', t_lower):
        return True
    # Check for common marker words
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

        HOTEL_DATABASE[h_key]['reviews'].append({
            'review_id': idx,
            'text': text,
            'features': feat_vec
        })

    print(f"Indexed {len(HOTEL_DATABASE):,} unique hotels with {len(items):,} reviews.")

# ---------------------------------------------------------------------------
# Conversational QA Engine
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


class ConversationalQABot:
    def __init__(self, model_path="model/model.pt"):
        self.device = torch.device('cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu'))
        self.state = DialogueState()
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

    def load_checkpoint(self, path):
        # Check candidate locations
        search_paths = [
            path,
            os.path.join("model", os.path.basename(path)) if path else None,
            "model/model.pt",
            "model.pt",
            "../model/model.pt",
            "model/hotel_aspect_qa_model/model.pt",
            "model/hotel_aspect_qa_model/pytorch_model.bin"
        ]
        resolved_path = None
        for p in search_paths:
            if p and os.path.exists(p) and os.path.isfile(p):
                resolved_path = p
                break

        if resolved_path:
            try:
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

    def resolve_hotel_entity(self, query):
        q_clean = query.strip().lower()

        # Check for coreference pronouns
        is_coref = any(re.search(r'\b' + re.escape(p) + r'\b', q_clean) for p in COREFERENCE_PRONOUNS)
        if is_coref and self.state.active_hotel_key:
            return self.state.active_hotel_key, True

        # Search exact match in HOTEL_DATABASE
        best_match = None
        max_overlap = 0

        for h_key, data in HOTEL_DATABASE.items():
            if h_key in q_clean:
                if len(h_key) > max_overlap:
                    max_overlap = len(h_key)
                    best_match = h_key

        if best_match:
            return best_match, False

        # Substring token match
        for h_key in HOTEL_DATABASE.keys():
            tokens = [t for t in h_key.split() if len(t) > 3 and t not in ['hotel', 'resort', 'spa']]
            if tokens and any(t in q_clean for t in tokens):
                matched_count = sum(1 for t in tokens if t in q_clean)
                if matched_count >= 2 or (len(tokens) == 1 and matched_count == 1):
                    return h_key, False

        # Fallback to current context
        if self.state.active_hotel_key:
            return self.state.active_hotel_key, True

        return None, False

    def detect_intent_and_aspect(self, query):
        q_lower = query.lower()
        if any(re.search(r'\b' + re.escape(w) + r'\b', q_lower) for w in LOCATION_KEYWORDS):
            return 'location', None

        aspect_scores = defaultdict(int)
        for asp, kws in ASPECT_KEYWORDS.items():
            for kw in kws:
                if kw in q_lower:
                    aspect_scores[asp] += 1

        if aspect_scores:
            best_asp = max(aspect_scores.keys(), key=lambda a: aspect_scores[a])
            return 'aspect_qa', best_asp

        return 'aspect_qa', self.state.active_aspect or 'Experience'

    def answer_query(self, user_query):
        is_vi = is_vietnamese_query(user_query)
        hotel_key, was_coref = self.resolve_hotel_entity(user_query)
        intent, target_aspect = self.detect_intent_and_aspect(user_query)

        if not hotel_key:
            if HOTEL_DATABASE:
                hotel_key = next(iter(HOTEL_DATABASE))
            else:
                msg = "Vui lòng đề cập tên khách sạn để trích xuất đánh giá chính xác." if is_vi else "Please mention a hotel name so I can retrieve verified reviews."
                return {
                    "text": msg,
                    "hotel": None,
                    "aspect": None,
                    "sentiment": None,
                    "confidence": None,
                    "evidence": None,
                    "context_applied": False
                }

        target_hotel = HOTEL_DATABASE[hotel_key]
        self.state.active_hotel_key = hotel_key
        self.state.active_hotel_name = target_hotel['hotel_name']
        if target_aspect:
            self.state.active_aspect = target_aspect

        # Handle Location Intent
        if intent == 'location':
            raw_star = str(target_hotel.get('star', '')).replace('-star', '').replace('star', '').strip()
            if raw_star and raw_star != '0':
                star_desc = f"{raw_star} sao" if is_vi else f"{raw_star}-star"
            else:
                star_desc = "Tiêu chuẩn" if is_vi else "Standard"

            if is_vi:
                reply_text = (
                    f"**{target_hotel['hotel_name']}** ({star_desc}, Đánh giá {target_hotel['score']:.1f}/5.0) tọa lạc tại:\n"
                    f"📍 `{target_hotel['hotel_address']}`"
                )
            else:
                reply_text = (
                    f"**{target_hotel['hotel_name']}** ({star_desc}, Rated {target_hotel['score']:.1f}/5.0) is located at:\n"
                    f"📍 `{target_hotel['hotel_address']}`"
                )
            return {
                "text": reply_text,
                "hotel": target_hotel['hotel_name'],
                "aspect": "Location",
                "sentiment": "Neutral",
                "confidence": 1.0,
                "evidence": target_hotel['hotel_address'],
                "context_applied": was_coref
            }

        # Retrieve relevant review for Aspect QA
        reviews = target_hotel.get('reviews', [])
        if not reviews:
            msg = f"Chưa có đánh giá chi tiết cho **{target_hotel['hotel_name']}**." if is_vi else f"No detailed reviews available for **{target_hotel['hotel_name']}**."
            return {
                "text": msg,
                "hotel": target_hotel['hotel_name'],
                "aspect": target_aspect,
                "sentiment": "Neutral",
                "confidence": 0.5,
                "evidence": None,
                "context_applied": was_coref
            }

        # Select most relevant review for the target aspect
        best_review = reviews[0]
        max_matches = -1
        kws = ASPECT_KEYWORDS.get(target_aspect, [])
        for r in reviews[:20]:
            cnt = sum(1 for kw in kws if kw in r['text'].lower())
            if cnt > max_matches:
                max_matches = cnt
                best_review = r

        context_text = best_review['text']
        dense_feat_vec = best_review['features']

        # Neural Inference with HotelAspectQA_BERT
        model_query = f"How is the {target_aspect.lower()} at {target_hotel['hotel_name']}?" if is_vi else user_query
        inputs = self.tokenizer(
            model_query,
            context_text,
            max_length=256,
            truncation='only_second',
            padding='max_length',
            return_offsets_mapping=True,
            return_tensors='pt'
        )

        offset_mapping = inputs.pop('offset_mapping')[0].tolist()
        input_ids = inputs['input_ids'].to(self.device)
        attention_mask = inputs['attention_mask'].to(self.device)
        token_type_ids = inputs['token_type_ids'].to(self.device) if 'token_type_ids' in inputs else None
        feat_tensor = torch.tensor([dense_feat_vec], dtype=torch.float, device=self.device)

        with torch.no_grad():
            preds = self.model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
                dense_features=feat_tensor
            )

        start_logits = preds['start_logits'][0].cpu().numpy()
        end_logits = preds['end_logits'][0].cpu().numpy()
        tt = token_type_ids[0].cpu().numpy() if token_type_ids is not None else None

        has_ans_raw = preds.get('has_answer_logits', preds.get('has_ans_logits'))
        if has_ans_raw.squeeze().dim() > 0:
            has_ans_prob = float(torch.sigmoid(has_ans_raw.squeeze())[0].item())
        else:
            has_ans_prob = float(torch.sigmoid(has_ans_raw.squeeze()).item())

        pred_aspect = ASPECTS[preds['aspect_logits'][0].argmax(-1).item()]
        pred_sentiment = SENTIMENTS[preds['sentiment_logits'][0].argmax(-1).item()]

        # Extract Evidence Span from raw review text constrained to context tokens
        best_score = -1e9
        best_s, best_e = 0, 0
        seq_len = len(start_logits)

        if tt is not None:
            for s in range(1, seq_len):
                if tt[s] != 1:
                    continue
                for e in range(s, min(s + 45, seq_len)):
                    if tt[e] != 1:
                        break
                    sc = start_logits[s] + end_logits[e]
                    if sc > best_score:
                        best_score = sc
                        best_s, best_e = s, e

        if best_e >= best_s and best_score > -1e9 and best_s < len(offset_mapping) and best_e < len(offset_mapping):
            char_s = offset_mapping[best_s][0]
            char_e = offset_mapping[best_e][1]
            if char_e > char_s and (char_e - char_s) > 10:
                answer_span = context_text[char_s:char_e].strip()
            else:
                answer_span = context_text[:160].strip() + ("..." if len(context_text) > 160 else "")
        else:
            answer_span = context_text[:160].strip() + ("..." if len(context_text) > 160 else "")

        aspect_label = ASPECT_TRANSLATIONS.get(pred_aspect, {}).get('vi' if is_vi else 'en', pred_aspect)
        sentiment_label = SENTIMENT_TRANSLATIONS.get(pred_sentiment, {}).get('vi' if is_vi else 'en', pred_sentiment)

        if is_vi:
            coref_note = " *(Đã liên kết ngữ cảnh từ câu trước)*" if was_coref else ""
            formatted_response = (
                f"Trích xuất từ đánh giá của khách hàng về **{target_hotel['hotel_name']}**{coref_note}:\n\n"
                f"> \"{answer_span}\"\n\n"
                f"• **Khía cạnh:** {aspect_label}\n"
                f"• **Cảm xúc:** {sentiment_label}"
            )
        else:
            coref_note = " *(Context linked from prior turn)*" if was_coref else ""
            formatted_response = (
                f"Extracted evidence from guest reviews for **{target_hotel['hotel_name']}**{coref_note}:\n\n"
                f"> \"{answer_span}\"\n\n"
                f"• **Aspect Domain:** {aspect_label}\n"
                f"• **Guest Sentiment:** {sentiment_label}"
            )

        return {
            "text": formatted_response,
            "hotel": target_hotel['hotel_name'],
            "aspect": pred_aspect,
            "sentiment": pred_sentiment,
            "confidence": round(has_ans_prob, 3),
            "evidence": answer_span,
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
            width: 100vw;
            height: 100vh;
            padding: 16px;
            gap: 16px;
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
            padding: 24px 20px;
            gap: 20px;
            overflow-y: auto;
            scrollbar-width: none;
        }
        aside.floating-sidebar::-webkit-scrollbar {
            display: none;
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

        /* Message Scroll View with Edge Fade Mask */
        .chat-messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 32px 48px 100px 48px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            scroll-behavior: smooth;
            
            mask-image: linear-gradient(to bottom, transparent 0%, black 28px, black calc(100% - 28px), transparent 100%);
            -webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 28px, black calc(100% - 28px), transparent 100%);
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

            <!-- Suggested Multi-Turn Queries -->
            <div class="sidebar-section">
                <div class="section-label">
                    <svg class="icon-svg sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                    Suggested Prompts
                </div>
                <div class="suggestions-list">
                    <button type="button" class="suggestion-item" onclick="sendSuggested('Where is Muong Thanh hotel located?')">
                        <strong>Turn 1:</strong> Where is Muong Thanh hotel located?
                    </button>
                    <button type="button" class="suggestion-item" onclick="sendSuggested('How are the rooms in that hotel?')">
                        <strong>Turn 2:</strong> How are the rooms in that hotel?
                    </button>
                    <button type="button" class="suggestion-item" onclick="sendSuggested('How is the customer service there?')">
                        <strong>Turn 3:</strong> How is the customer service there?
                    </button>
                    <button type="button" class="suggestion-item" onclick="sendSuggested('How is the breakfast at Pullman Hanoi?')">
                        <strong>Turn 4:</strong> How is the breakfast at Pullman Hanoi?
                    </button>
                </div>
            </div>

            <div class="sidebar-footer">
                <button class="glass-btn glass-btn-secondary" id="clear-btn" style="width: 100%; justify-content: center;">
                    <svg class="icon-svg sm" viewBox="0 0 24 24"><polyline points="1 4 1 10 7 10"/><polyline points="23 20 23 14 17 14"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/></svg>
                    Reset Dialogue State
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
                    <div class="bubble-content">
                        <strong>Welcome to AspectQA Hotel Intelligence</strong>
                        <p style="margin-top: 6px; color: var(--text-secondary);">
                            Multi-task conversational QA system trained across all <strong>2,622 hotels</strong> in Vietnam.
                            Ask questions about hotel locations or the 6 core aspect domains:
                            <em>Service, Facility, Experience, Amenity, Loyalty,</em> and <em>Branding</em>.
                        </p>
                        <p style="margin-top: 6px; font-size: 0.8rem; color: var(--text-muted);">
                            Original guest review evidence is retrieved and exact rationale spans are extracted. Contextual pronouns (<em>"khách sạn đó"</em>, <em>"that hotel"</em>, <em>"there"</em>) are resolved across multi-turn dialogue.
                        </p>
                    </div>
                </div>
            </div>

            <div class="floating-input-wrapper">
                <form class="floating-input-bar" id="chat-form">
                    <input type="text" class="prompt-input" id="prompt-input" placeholder="Ask about any hotel or aspect (e.g. 'How are the rooms at Muong Thanh?')..." autocomplete="off">
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

        clearBtn.addEventListener('click', async () => {
            await fetch('/api/clear', {method: 'POST'});
            chatBox.innerHTML = `
                <div class="chat-row bot">
                    <div class="avatar-box bot">
                        <svg class="icon-svg" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                    </div>
                    <div class="bubble-content">
                        <strong>Dialogue State Reset</strong>
                        <p style="margin-top: 4px; color: var(--text-secondary);">Context memory cleared. You may start a fresh conversation with any of the 2,622 hotels.</p>
                    </div>
                </div>
            `;
            showToast('Dialogue context reset successfully', 'success');
        });

        window.sendSuggested = function(text) {
            promptInput.value = text;
            handleSend(text);
        };

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
                    body: JSON.stringify({query: text})
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
                metaHtml += `<span class="meta-tag aspect">Domain: ${data.aspect}</span>`;
            }
            if (data.sentiment) {
                const sCls = data.sentiment.toLowerCase();
                metaHtml += `<span class="meta-tag ${sCls}">Sentiment: ${data.sentiment}</span>`;
            }
            if (data.context_applied) {
                metaHtml += `<span class="meta-tag coref">Context Resolved</span>`;
            }

            row.innerHTML = `
                <div class="avatar-box bot">
                    <svg class="icon-svg" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                </div>
                <div class="bubble-content">
                    <div>${formatMarkdown(data.text)}</div>
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
        post_data = self.rfile.read(content_length)

        try:
            body = json.loads(post_data.decode('utf-8')) if post_data else {}
        except Exception:
            body = {}

        if url.path == '/api/chat':
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
                response = BOT.answer_query(user_query)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))

        elif url.path == '/api/load_model':
            m_path = body.get('model_path', 'model/model.pt').strip()
            success, msg = BOT.load_checkpoint(m_path)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'success': success, 'message': msg}).encode('utf-8'))

        elif url.path == '/api/clear':
            if BOT:
                BOT.state.reset()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode('utf-8'))

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
