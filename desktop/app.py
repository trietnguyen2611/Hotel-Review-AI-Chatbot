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
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Auto-relaunch inside project virtual environment if dependencies are missing in current python
try:
    import torch
    import transformers
except ImportError:
    base_dir = PROJECT_ROOT
    if sys.platform == 'win32':
        venv_py = os.path.join(base_dir, '.venv', 'Scripts', 'python.exe')
    else:
        venv_py = os.path.join(base_dir, '.venv', 'bin', 'python')
    if os.path.exists(venv_py) and os.path.abspath(sys.executable) != os.path.abspath(venv_py):
        print(f"[Launcher] Switching to project virtual environment: {venv_py}")
        os.execv(venv_py, [venv_py] + sys.argv)
    else:
        raise

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
    'Amenity': [
        'amenity', 'amenities', 'pool', 'swimming pool', 'swimming', 'swim', 'be boi', 'bể bơi', 'ho boi', 'hồ bơi',
        'gym', 'fitness', 'phong gym', 'phòng gym', 'tap the duc', 'tập thể dục',
        'breakfast', 'buffet', 'food', 'restaurant', 'dining', 'dish', 'dishes', 'coffee', 'tea',
        'an sang', 'ăn sáng', 'bua sang', 'bữa sáng', 'nha hang', 'nhà hàng', 'do an', 'đồ ăn', 'mon an', 'món ăn',
        'thuc don', 'thực đơn', 'buffet sang', 'buffet sáng', 'ca phe', 'cà phê', 'nuoc uong', 'nước uống',
        'spa', 'massage', 'sauna', 'xong hoi', 'xông hơi', 'tam hoi', 'tắm hơi',
        'wifi', 'internet', 'mang', 'mạng', 'toc do mang', 'tốc độ mạng',
        'parking', 'do xe', 'đỗ xe', 'bai do xe', 'bãi đỗ xe', 'gui xe', 'gửi xe',
        'bar', 'rooftop', 'lounge', 'cocktail', 'quay bar', 'quầy bar', 'sky bar'
    ],
    'Service': [
        'service', 'staff', 'employee', 'waiter', 'reception', 'receptionist', 'check-in', 'checkout',
        'attitude', 'helpful', 'friendly', 'slow', 'hospitality', 'concierge', 'front desk',
        'courteous', 'welcoming', 'polite', 'assistance', 'housekeeping', 'manager',
        'nhan vien', 'nhân viên', 'phuc vu', 'phục vụ', 'le tan', 'lễ tân', 'tiep tan', 'tiếp tân',
        'thai do', 'thái độ', 'nhiet tinh', 'nhiệt tình', 'than thien', 'thân thiện', 'chu dao', 'chu đáo',
        'chao don', 'chào đón', 'ho tro', 'hỗ trợ', 'don phong', 'dọn phòng', 'quan ly', 'quản lý',
        'chuyen nghiep', 'chuyên nghiệp', 'nhanh nhen', 'nhanh nhẹn', 'cham chap', 'chậm chạp'
    ],
    'Facility': [
        'facility', 'facilities', 'room', 'rooms', 'bed', 'beds', 'bathroom', 'shower', 'bathtub',
        'clean', 'cleanliness', 'dirty', 'air conditioner', 'ac', 'tv', 'balcony', 'sheet', 'towel',
        'maintenance', 'spacious', 'water pressure', 'smell', 'noise', 'quiet', 'insulation', 'view',
        'elevator', 'lift', 'stairs', 'building',
        'phong', 'phòng', 'phong ngu', 'phòng ngủ', 'giuong', 'giường', 'nem', 'nệm', 'chan ga', 'chăn ga',
        've sinh', 'vệ sinh', 'toilet', 'nha tam', 'nhà tắm', 'bon tam', 'bồn tắm', 'voi sen', 'vòi sen',
        'nuoc nong', 'nước nóng', 'sach se', 'sạch sẽ', 'ban', 'bẩn', 'mui', 'mùi', 'dieu hoa', 'điều hòa',
        'may lanh', 'máy lạnh', 'tivi', 'ti vi', 'ban cong', 'ban công', 'tam nhin', 'tầm nhìn',
        'on ao', 'ồn ào', 'yen tinh', 'yên tĩnh', 'cach am', 'cách âm', 'thang may', 'thang máy',
        'co so vat chat', 'cơ sở vật chất', 'trang thiet bi', 'trang thiết bị', 'rong rai', 'rộng rãi', 'chat chep', 'chật chội'
    ],
    'Loyalty': [
        'loyalty', 'recommend', 'recommendation', 'return', 'come back', 'again', 'stay again',
        'visit again', 'book again', 'next trip', 'next time', 'worth it', 'never again', 'wont return',
        'quay lai', 'quay lại', 'tro lai', 'trở lại', 'gioi thieu', 'giới thiệu', 'ung ho', 'ủng hộ',
        'lan sau', 'lần sau', 'tiep tuc', 'tiếp tục', 'dang tien', 'đáng tiền', 'hai long', 'hài lòng',
        'that vong', 'thất vọng', 'se quay lai', 'sẽ quay lại', 'khong quay lai', 'không quay lại'
    ],
    'Branding': [
        'brand', 'reputation', 'standard', 'prestige', 'luxury', 'chain', 'boutique', 'authentic',
        'expectations', 'value for money', 'price', 'cost', 'expensive', 'cheap', 'budget',
        '5-star quality', 'star rating', 'classification',
        'gia', 'giá', 'gia ca', 'giá cả', 'gia phong', 'giá phòng', 'dat', 'đắt', 're', 'rẻ',
        'chi phi', 'chi phí', 'thuong hieu', 'thương hiệu', 'dang cap', 'đẳng cấp', 'sang trong', 'sang trọng',
        'tieu chuan', 'tiêu chuẩn', 'danh tieng', 'danh tiếng', 'hang sao', 'hạng sao', '5 sao', '4 sao',
        'uy tin', 'uy tín'
    ],
    'Experience': [
        'experience', 'stay', 'trip', 'atmosphere', 'vibe', 'vacation', 'overall',
        'general', 'pleasure', 'relaxing', 'impressive', 'disappointing', 'holiday', 'feeling', 'impression',
        'trai nghiem', 'trải nghiệm', 'chuyen di', 'chuyến đi', 'ky nghi', 'kỳ nghỉ', 'khong khi', 'không khí',
        'tong the', 'tổng thể', 'cam nhan', 'cảm nhận', 'thu gian', 'thư giãn', 'tuyet voi', 'tuyệt vời'
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
    'tp. hcm': 'Ho Chi Minh City',
    'tp hcm': 'Ho Chi Minh City',
    'tp.hcm': 'Ho Chi Minh City',
    'hcm': 'Ho Chi Minh City',
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

PROVINCES_METADATA: List[Dict[str, Any]] = []

CITY_ALIASES = {
    'hanoi': ['hanoi', 'ha noi'],
    'ha noi': ['hanoi', 'ha noi'],
    'tp. hcm': ['tp. hcm', 'tp hcm', 'tp.hcm', 'ho chi minh', 'hcm', 'saigon', 'ho chi minh city'],
    'tp hcm': ['tp. hcm', 'tp hcm', 'tp.hcm', 'ho chi minh', 'hcm', 'saigon', 'ho chi minh city'],
    'ho chi minh': ['tp. hcm', 'tp hcm', 'tp.hcm', 'ho chi minh', 'hcm', 'saigon', 'ho chi minh city'],
    'ho chi minh city': ['tp. hcm', 'tp hcm', 'tp.hcm', 'ho chi minh', 'hcm', 'saigon', 'ho chi minh city'],
    'saigon': ['tp. hcm', 'tp hcm', 'tp.hcm', 'ho chi minh', 'hcm', 'saigon', 'ho chi minh city'],
    'quang nam': ['quang nam', 'hoi an'],
    'hoi an': ['quang nam', 'hoi an'],
    'da nang': ['da nang', 'danang'],
    'khanh hoa': ['khanh hoa', 'nha trang'],
    'nha trang': ['khanh hoa', 'nha trang'],
    'hue': ['hue', 'thua thien'],
    'kien giang': ['kien giang', 'phu quoc'],
    'phu quoc': ['kien giang', 'phu quoc'],
    'lam dong': ['lam dong', 'da lat', 'dalat'],
    'da lat': ['lam dong', 'da lat', 'dalat'],
    'binh thuan': ['binh thuan', 'phan thiet', 'mui ne'],
    'hai phong': ['hai phong', 'cat ba'],
    'quang binh': ['quang binh', 'dong hoi'],
    'vung tau': ['vung tau', 'ba ria'],
    'ninh binh': ['ninh binh', 'tam coc', 'trang an'],
    'quang ninh': ['quang ninh', 'ha long'],
    'can tho': ['can tho'],
    'ha giang': ['ha giang', 'dong van']
}

QUERY_KEYWORD_MAP: Dict[str, Dict[str, Any]] = {
    'pool': {
        'aspect': 'Amenity',
        'terms': ['pool', 'swimming', 'swim', 'ho boi', 'be boi', 'rooftop pool'],
        'display': 'swimming pool'
    },
    'breakfast': {
        'aspect': 'Amenity',
        'terms': ['breakfast', 'buffet', 'bua sang', 'an sang', 'dining', 'food', 'restaurant', 'mon an', 'do an', 'nha hang'],
        'display': 'breakfast & dining'
    },
    'spa': {
        'aspect': 'Amenity',
        'terms': ['spa', 'massage', 'sauna', 'xong hoi', 'tam hoi'],
        'display': 'spa & wellness'
    },
    'gym': {
        'aspect': 'Amenity',
        'terms': ['gym', 'fitness', 'phong gym', 'tap the duc', 'workout'],
        'display': 'fitness center / gym'
    },
    'wifi': {
        'aspect': 'Amenity',
        'terms': ['wifi', 'wi-fi', 'internet', 'mang', 'toc do mang'],
        'display': 'wifi connection'
    },
    'bar': {
        'aspect': 'Amenity',
        'terms': ['bar', 'rooftop', 'cocktail', 'lounge', 'sky bar', 'quay bar', 'drinks', 'do uong'],
        'display': 'bar & lounge'
    },
    'parking': {
        'aspect': 'Amenity',
        'terms': ['parking', 'do xe', 'bai do xe', 'gui xe', 'cho dau xe'],
        'display': 'parking facilities'
    },
    'beach': {
        'aspect': 'Experience',
        'terms': ['beach', 'sea', 'ocean', 'coast', 'bien', 'bai bien', 'gan bien'],
        'display': 'beach access'
    },
    'room': {
        'aspect': 'Facility',
        'terms': ['room', 'rooms', 'bed', 'beds', 'bedroom', 'phong', 'phong ngu', 'giuong', 'nem', 'chan ga'],
        'display': 'rooms & beds'
    },
    'bathroom': {
        'aspect': 'Facility',
        'terms': ['bathroom', 'shower', 'bathtub', 'toilet', 'nha tam', 'bon tam', 'voi sen', 've sinh', 'nuoc nong'],
        'display': 'bathroom & shower'
    },
    'cleanliness': {
        'aspect': 'Facility',
        'terms': ['clean', 'cleanliness', 'dirty', 'smell', 'odor', 'sach se', 'ban', 'mui'],
        'display': 'cleanliness'
    },
    'ac': {
        'aspect': 'Facility',
        'terms': ['air condition', 'air conditioning', 'ac', 'dieu hoa', 'may lanh'],
        'display': 'air conditioning'
    },
    'view': {
        'aspect': 'Facility',
        'terms': ['view', 'balcony', 'tam nhin', 'ban cong', 'huong nhin', 'canh dep'],
        'display': 'view & balcony'
    },
    'noise': {
        'aspect': 'Facility',
        'terms': ['noise', 'noisy', 'quiet', 'insulation', 'soundproof', 'on ao', 'yen tinh', 'cach am'],
        'display': 'noise level'
    },
    'staff': {
        'aspect': 'Service',
        'terms': ['staff', 'service', 'reception', 'receptionist', 'attitude', 'helpful', 'friendly', 'polite', 'nhan vien', 'le tan', 'tiep tan', 'thai do', 'nhiet tinh', 'than thien'],
        'display': 'staff & customer service'
    },
    'checkin': {
        'aspect': 'Service',
        'terms': ['check-in', 'checkout', 'check out', 'nhan phong', 'tra phong', 'thu tuc'],
        'display': 'check-in & check-out'
    },
    'price': {
        'aspect': 'Branding',
        'terms': ['price', 'cost', 'expensive', 'cheap', 'budget', 'value', 'gia', 'gia ca', 'gia phong', 'dat', 're', 'chi phi', 'dang tien'],
        'display': 'pricing & value'
    },
    'star': {
        'aspect': 'Branding',
        'terms': ['star', 'stars', 'may sao', 'hang sao', '5 sao', '4 sao', 'tieu chuan', 'dang cap'],
        'display': 'star rating'
    },
    'loyalty': {
        'aspect': 'Loyalty',
        'terms': ['again', 'return', 'come back', 'recommend', 'rebook', 'next trip', 'quay lai', 'tro lai', 'gioi thieu', 'ung ho', 'se quay lai'],
        'display': 'guest recommendation'
    },
    'location': {
        'aspect': 'Facility',
        'terms': ['location', 'address', 'where', 'near', 'nearby', 'center', 'centre', 'vi tri', 'dia chi', 'o dau', 'gan', 'trung tam'],
        'display': 'location & accessibility'
    }
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
    text = re.sub(r'^(khach\s*san|khu\s*nghi\s*duong|nha\s*khach|ks|hotel|resort|the)\s+', '', ascii_name, flags=re.IGNORECASE).strip()
    text = re.sub(r'\s*\.*$', '', text)
    words = text.split()
    capitalized = ' '.join(w.capitalize() for w in words)
    capitalized = re.sub(r'\bHa Noi\b', 'Hanoi', capitalized, flags=re.IGNORECASE)
    capitalized = re.sub(r'\bDa Nang\b', 'Da Nang', capitalized, flags=re.IGNORECASE)
    capitalized = re.sub(r'\bPhu Quoc\b', 'Phu Quoc', capitalized, flags=re.IGNORECASE)
    capitalized = re.sub(r'\bSai Gon\b', 'Ho Chi Minh City', capitalized, flags=re.IGNORECASE)
    capitalized = re.sub(r'\bNha Trang\b', 'Nha Trang', capitalized, flags=re.IGNORECASE)
    has_type = any(t in capitalized.lower() for t in ['hotel', 'resort', 'villa', 'suites', 'homestay', 'apartment', 'lodge', 'inn', 'hostel', 'palace', 'guesthouse'])
    return capitalized if has_type else f"{capitalized} Hotel"

# ---------------------------------------------------------------------------
# Review Text Utilities (Pure Neural Generation - Zero Canned Templates)
# ---------------------------------------------------------------------------
def clean_quote(quote: str, max_chars: int = 140) -> str:
    """Sanitize and trim a review snippet without cutting mid-word."""
    if not quote:
        return ""
    q = quote.strip().replace('"', '').replace("'", "").replace('\n', ' ')
    q = re.sub(r'\s+', ' ', q).strip()
    if len(q) > max_chars:
        q = q[:max_chars].rsplit(' ', 1)[0] + '...'
    return q


# ---------------------------------------------------------------------------
# Knowledge Base & Ingestion
# ---------------------------------------------------------------------------
HOTEL_DATABASE: Dict[str, Dict[str, Any]] = {}
ALL_HOTEL_NAMES: List[str] = []


# ---------------------------------------------------------------------------
# HOTEL IMAGE INTEGRATION
# Load hotel images from data/dataset/hotel_image.json
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HOTEL_IMAGE_FILE = os.path.join(
    BASE_DIR,
    "data",
    "dataset",
    "hotel_image.json"
)


def normalize_hotel_image_name(name: str) -> str:
    """Normalize hotel names for matching."""
    import re
    import unicodedata

    name = unicodedata.normalize("NFKD", str(name or ""))
    name = "".join(
        char for char in name
        if not unicodedata.combining(char)
    )
    name = re.sub(r"[^a-zA-Z0-9]+", " ", name.lower())

    return " ".join(name.split())


def load_hotel_image_map() -> Dict[str, str]:
    """Load hotel image URLs from the JSON file."""
    import json

    if not os.path.isfile(HOTEL_IMAGE_FILE):
        print(
            f"[Hotel Images] File not found: "
            f"{HOTEL_IMAGE_FILE}"
        )
        return {}

    try:
        with open(HOTEL_IMAGE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        image_map: Dict[str, str] = {}

        # Format 1:
        # [
        #   {"hotel_name": "Pullman Hanoi", "image_url": "https://..."}
        # ]
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue

                hotel_name = item.get("hotel_name", "")
                image_url = item.get("image_url", "")

                if (
                    hotel_name
                    and isinstance(image_url, str)
                    and image_url.strip()
                ):
                    key = normalize_hotel_image_name(hotel_name)
                    image_map[key] = image_url.strip()

        # Format 2:
        # {
        #   "Pullman Hanoi": "https://...",
        #   "Melia Hanoi": "https://..."
        # }
        elif isinstance(data, dict):
            for hotel_name, image_url in data.items():
                if (
                    isinstance(image_url, str)
                    and image_url.strip()
                ):
                    key = normalize_hotel_image_name(hotel_name)
                    image_map[key] = image_url.strip()

        print(
            f"[Hotel Images] Loaded {len(image_map)} hotel images."
        )
        return image_map

    except (OSError, ValueError) as error:
        print(f"[Hotel Images] Failed to load JSON: {error}")
        return {}


# Load image mappings once when the application starts
HOTEL_IMAGE_MAP = load_hotel_image_map()


def get_hotel_image_url(
    h_name: str,
    location: str = "",
    addr: str = ""
) -> Optional[str]:
    """
    Return the image URL matched by hotel name in hotel_image.json.
    Return None if no matching image exists.
    """
    key = normalize_hotel_image_name(h_name)

    image_url = HOTEL_IMAGE_MAP.get(key)

    if image_url:
        return image_url

    return None



def calculate_hotel_aspect_scores(reviews: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Calculate aspect-level average ratings from reviews that mention each aspect.

    Each aspect is scored only from the hotel's own reviews containing its
    keywords. The UI can then rank the aspects with the strongest review scores.
    """
    result: Dict[str, Dict[str, float]] = {}
    for aspect, keywords in ASPECT_KEYWORDS.items():
        normalized_keywords = [normalize_text(k) for k in keywords if normalize_text(k)]
        matching_scores: List[float] = []
        for review in reviews:
            review_text = normalize_text(review.get('text', ''))
            if not review_text or not any(keyword in review_text for keyword in normalized_keywords):
                continue
            try:
                score = float(review.get('score', 0))
            except (TypeError, ValueError):
                continue
            if 1.0 <= score <= 5.0:
                matching_scores.append(score)
        if matching_scores:
            average_score = sum(matching_scores) / len(matching_scores)
            result[aspect] = {
                'average_score': round(average_score, 3),
                'review_count': len(matching_scores),
                'positive_rate': sum(1 for score in matching_scores if score >= 4.0) / len(matching_scores)
            }
    return result


def load_hotel_database(parquet_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    global HOTEL_DATABASE, ALL_HOTEL_NAMES
    import pandas as pd

    if parquet_path is None:
        parquet_path = os.path.join(PROJECT_ROOT, 'data', 'df', 'hotel_reviews.parquet')
    elif not os.path.isabs(parquet_path) and not os.path.exists(parquet_path):
        project_path = os.path.join(PROJECT_ROOT, parquet_path)
        if os.path.exists(project_path):
            parquet_path = project_path

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
            loc = clean_location(str(row.get('location', '')).strip())
            addr = clean_address(str(row.get('hotel_address', 'Vietnam')).strip())
            hotels_dict[norm_key] = {
                'raw_name': raw_name,
                'hotel_name': clean_name,
                'norm_key': norm_key,
                'star': star_label,
                'score': float(row.get('score', 4.0)),
                'hotel_address': addr,
                'location': loc,
                'photo_url': get_hotel_image_url(clean_name, loc, addr),
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

    # Precompute static display attributes and normalized fields once at load time
    for norm_key, h in hotels_dict.items():
        revs = h.get('reviews', [])
        rev_count = len(revs)
        score = float(h.get('score', 4.0))
        h['review_count'] = rev_count
        h['pop_score'] = score * math.log1p(rev_count)
        snippet = ""
        if revs:
            first_text = revs[0].get('text', '').strip()
            snippet = (first_text[:110] + '...') if len(first_text) > 110 else first_text
        h['sample_snippet'] = snippet
        h['aspect_scores'] = calculate_hotel_aspect_scores(revs)
        h_name = h.get('hotel_name', '')
        h_loc = h.get('location', '')
        h_addr = h.get('hotel_address', '')
        h['maps_search_url'] = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(h_name + ' ' + (h_addr or h_loc or 'Vietnam'))}"
        h['loc_norm'] = clean_vietnamese_text(h_loc).lower()
        h['addr_norm'] = clean_vietnamese_text(h_addr).lower()
        h['name_norm'] = clean_vietnamese_text(h_name).lower()
        h['search_blob'] = f"{h['name_norm']} {h['loc_norm']} {h['addr_norm']}"

    global HOTEL_DATABASE, ALL_HOTEL_NAMES, PROVINCES_METADATA
    HOTEL_DATABASE = hotels_dict
    ALL_HOTEL_NAMES = [h['hotel_name'] for h in hotels_dict.values()]
    all_provinces_counter = Counter(h.get('location', '').strip() for h in hotels_dict.values() if h.get('location', '').strip())
    PROVINCES_METADATA = [
        {'name': loc, 'count': cnt}
        for loc, cnt in sorted(all_provinces_counter.items(), key=lambda x: (-x[1], x[0]))
    ]
    print(f"Loaded {len(HOTEL_DATABASE)} unique hotel properties into knowledge base ({len(PROVINCES_METADATA)} provinces).")
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

    def retrieve(self, hotel: Dict[str, Any], aspect: str, query_terms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        reviews = hotel.get('reviews', [])
        if not reviews:
            return []

        max_m = hotel.get('max_m', 2020 * 12)
        keywords = ASPECT_KEYWORDS.get(aspect, [])
        q_terms = [t.lower() for t in (query_terms or []) if len(t) >= 2]

        scored_reviews = []
        for r in reviews:
            text = r.get('text', '')
            text_lower = text.lower()

            # Feature 10: Exponential Time Decay w = exp(-lambda * delta_m)
            delta_m = max(0, max_m - r.get('m', max_m))
            time_weight = math.exp(-self.lambda_decay * delta_m)

            # Check query-specific terms
            q_matches = sum(1 for kw in q_terms if kw in text_lower) if q_terms else 0
            asp_matches = sum(1 for kw in keywords if kw in text_lower)

            if q_terms:
                if q_matches > 0:
                    relevance = 8.0 + (q_matches * 4.0) + (asp_matches * 0.5)
                else:
                    relevance = 0.2 + (asp_matches * 0.1)
            else:
                relevance = 1.0 + (asp_matches * 0.8)

            combined_score = time_weight * relevance

            # Sentence extraction for grounded evidence (preserve exact punctuation/quotes for span highlighting)
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if len(s.strip()) > 8]
            matched_sents = []
            if q_terms:
                # Strictly extract sentences matching query terms to prevent cross-aspect leakage
                matched_sents = [s for s in sents if any(kw in s.lower() for kw in q_terms)]
            else:
                matched_sents = [s for s in sents if any(kw in s.lower() for kw in keywords)]
                if not matched_sents and sents:
                    matched_sents = [sents[0]]

            scored_reviews.append({
                'text': text,
                'score': r.get('score', 4.0),
                'date': r.get('date', 'Recent'),
                'recency_weight': round(time_weight, 3),
                'combined_score': combined_score,
                'q_matches': q_matches,
                'matched_sentences': matched_sents
            })

        # Sort descending by combined recency-relevance score
        scored_reviews.sort(key=lambda x: x['combined_score'], reverse=True)

        # If query terms were provided and matching reviews exist, strictly return only reviews with matches
        if q_terms:
            q_matching = [r for r in scored_reviews if r['q_matches'] > 0]
            if q_matching:
                return q_matching[:self.top_k]

        return scored_reviews[:self.top_k]

    def retrieve_all_for_aspect(self, hotel: Dict[str, Any], aspect: str, query_terms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve ALL original reviews for the hotel that touch upon the queried aspect,
        ranked by Feature 10 recency weight and query term relevance. For use in UI 'View original reviews' pagination.
        """
        reviews = hotel.get('reviews', [])
        if not reviews:
            return []

        max_m = hotel.get('max_m', 2020 * 12)
        keywords = ASPECT_KEYWORDS.get(aspect, [])
        q_terms = [t.lower() for t in (query_terms or []) if len(t) >= 2]

        matched = []
        for r in reviews:
            text = r.get('text', '')
            text_lower = text.lower()
            q_matches = sum(1 for kw in q_terms if kw in text_lower) if q_terms else 0
            asp_matches = sum(1 for kw in keywords if kw in text_lower)

            # Relevance filter: must match query terms (if given) or aspect keywords / Experience
            if q_terms:
                if q_matches == 0:
                    continue
            elif aspect != 'Experience' and asp_matches == 0:
                continue

            delta_m = max(0, max_m - r.get('m', max_m))
            time_weight = math.exp(-self.lambda_decay * delta_m)

            if q_terms:
                combined_score = time_weight * (8.0 + q_matches * 4.0 + asp_matches * 0.5)
            else:
                combined_score = time_weight * (1.0 + asp_matches * 0.8)

            score_val = r.get('score', 4.0)
            sent = 'Positive' if score_val >= 4.0 else ('Negative' if score_val <= 2.5 else 'Neutral')

            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if len(s.strip()) > 8]
            matched_sents = []
            if q_terms:
                matched_sents = [s for s in sents if any(kw in s.lower() for kw in q_terms)]
            else:
                matched_sents = [s for s in sents if any(kw in s.lower() for kw in keywords)]

            matched.append({
                'review_id': r.get('review_id', 0),
                'text': text,
                'score': score_val,
                'date': r.get('date', 'Recent'),
                'sentiment': sent,
                'aspect_spans': matched_sents,
                'recency_weight': round(time_weight, 3),
                'combined_score': combined_score
            })

        if not matched and reviews:
            # Clean fallback to general reviews if no specific matches found
            for r in reviews:
                delta_m = max(0, max_m - r.get('m', max_m))
                time_weight = math.exp(-self.lambda_decay * delta_m)
                score_val = r.get('score', 4.0)
                matched.append({
                    'review_id': r.get('review_id', 0),
                    'text': r.get('text', ''),
                    'score': score_val,
                    'date': r.get('date', 'Recent'),
                    'sentiment': 'Positive' if score_val >= 4.0 else ('Negative' if score_val <= 2.5 else 'Neutral'),
                    'aspect_spans': [],
                    'recency_weight': round(time_weight, 3),
                    'combined_score': time_weight
                })

        matched.sort(key=lambda x: x['combined_score'], reverse=True)
        return matched

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

    def forward(self, input_ids, attention_mask=None, dense_features=None, labels=None, decoder_input_ids=None, aspect_id=None):
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

        # Aspect-Conditioned Rationale Injection
        if aspect_id is not None:
            asp_idx = aspect_id.view(-1, 1, 1).expand(-1, fused_seq.size(1), 1)
            asp_mask = masks.gather(-1, asp_idx)
            evidence_seq = fused_seq * (1.0 + asp_mask)
        else:
            evidence_seq = fused_seq

        encoder_container = BaseModelOutput(last_hidden_state=evidence_seq)
        seq2seq_outputs = self.seq2seq(
            encoder_outputs=encoder_container,
            attention_mask=attention_mask,
            labels=labels,
            decoder_input_ids=decoder_input_ids
        )
        return {
            'gen_loss': seq2seq_outputs.loss if labels is not None else None,
            'gen_logits': seq2seq_outputs.logits,
            'aspect_logits': aspect_logits,
            'sentiment_logits': sentiment_logits,
            'rating_logits': rating_logits,
            'masks': masks
        }

    def generate_answer(self, tokenizer, prompt_text: str, dense_features=None, aspect_id=None, max_new_tokens: int = 150, device=None) -> str:
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
                fused_cls = seq_rep[:, 0, :] + feat_emb
            else:
                fused_seq = seq_rep
                fused_cls = seq_rep[:, 0, :]

            # Predict aspect if not supplied
            if aspect_id is None:
                aspect_logits = self.aspect_classifier(fused_cls)
                aspect_id = torch.argmax(aspect_logits, dim=-1)
            elif not isinstance(aspect_id, torch.Tensor):
                aspect_id = torch.tensor([aspect_id], device=dev)

            # PLMR rationale mask injection to steer cross-attention to relevant review spans
            masks = self.rationale_generator(fused_seq) * enc['attention_mask'].unsqueeze(-1).float()
            asp_idx = aspect_id.view(-1, 1, 1).expand(-1, fused_seq.size(1), 1)
            asp_mask = masks.gather(-1, asp_idx)
            evidence_seq = fused_seq * (1.0 + asp_mask)

            encoder_container = BaseModelOutput(last_hidden_state=evidence_seq)
            gen_ids = self.seq2seq.generate(
                encoder_outputs=encoder_container,
                attention_mask=enc['attention_mask'],
                max_new_tokens=max_new_tokens,
                num_beams=4,
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
        if clean_k.startswith('bart.'):
            clean_k = clean_k[5:]
        # Only strip 'model.' wrapper if it's wrapping bert or seq2seq, but preserve native BART weights
        if clean_k.startswith('model.') and not (
            clean_k.startswith('model.encoder.') or
            clean_k.startswith('model.decoder.') or
            clean_k.startswith('model.shared.')
        ):
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
        self.active_model_name = 'model_v3'
        self.inference_lock = threading.Lock()
        self.initialization_lock = threading.Lock()
        self.initialization_attempted = False
        self.checkpoint_path = checkpoint_path

    def _initialize(self, checkpoint_path: str):
        print(f"Loading Generative Model on {self.device}...")

        # Priority 1: Dynamically scan for any model_v* versions (model_v4, model_v5, v6...) sorted descending
        versioned_candidates = []
        for sdir in [BASE_DIR, os.path.join(BASE_DIR, 'model')]:
            if os.path.exists(sdir):
                for item in os.listdir(sdir):
                    full_p = os.path.join(sdir, item)
                    m_dir = re.match(r'^model_v(\d+)$', item)
                    if m_dir and os.path.isdir(full_p):
                        versioned_candidates.append((int(m_dir.group(1)), full_p))
                    m_f = re.match(r'^model_v(\d+)\.(pt|bin)$', item)
                    if m_f and os.path.isfile(full_p):
                        versioned_candidates.append((int(m_f.group(1)), full_p))
        versioned_candidates.sort(key=lambda x: x[0], reverse=True)
        dynamic_paths = [p for _, p in versioned_candidates]

        cand_candidates = dynamic_paths + [
            os.path.join(MODEL_STORAGE_DIR, 'model.pt'),
            os.path.join(BASE_DIR, 'hotel_aspect_qa_bart_engine'),
            os.path.join(BASE_DIR, 'model', 'hotel_aspect_qa_bart_engine'),
            os.path.join(BASE_DIR, 'model', 'best_model.pt'),
            os.path.join(BASE_DIR, 'best_model.pt'),
            os.path.join(BASE_DIR, checkpoint_path),
            checkpoint_path
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
                    try:
                        self.tokenizer = AutoTokenizer.from_pretrained(custom_model_path)
                    except Exception as tok_err:
                        print(f"Notice: Loading local tokenizer failed ({tok_err}), using facebook/bart-base")
                        self.tokenizer = AutoTokenizer.from_pretrained('facebook/bart-base')
                    self.model = AutoModelForSeq2SeqLM.from_pretrained(custom_model_path).to(self.device)
                    self.model_type = 'seq2seq'
                    if getattr(self.model.config, 'is_encoder_decoder', False):
                        dec_start = getattr(self.model.config, 'decoder_start_token_id', None) or getattr(self.tokenizer, 'cls_token_id', None) or 101
                        pad_id = getattr(self.model.config, 'pad_token_id', None) or getattr(self.tokenizer, 'pad_token_id', 0)
                        eos_id = getattr(self.model.config, 'eos_token_id', None) or getattr(self.tokenizer, 'sep_token_id', None) or 102
                        self.model.config.decoder_start_token_id = dec_start
                        self.model.config.pad_token_id = pad_id
                        self.model.config.eos_token_id = eos_id
                        if hasattr(self.model, 'generation_config') and self.model.generation_config is not None:
                            self.model.generation_config.decoder_start_token_id = dec_start
                            self.model.generation_config.pad_token_id = pad_id
                            self.model.generation_config.eos_token_id = eos_id
                    self.model.eval()
                    self.loaded_successfully = True
                    self.active_model_name = os.path.basename(custom_model_path)
                    print(f"Successfully reloaded model directory from {custom_model_path} (decoder_start_token_id={getattr(self.model.generation_config, 'decoder_start_token_id', None)}).")
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

    def generate(self, prompt_text: str, max_new_tokens: int = 180, context_text: Optional[str] = None, dense_features=None, aspect_id=None) -> str:
        if not self.loaded_successfully and not self.initialization_attempted:
            with self.initialization_lock:
                if not self.loaded_successfully and not self.initialization_attempted:
                    self._initialize(self.checkpoint_path)
                    self.initialization_attempted = True

        if not self.loaded_successfully or self.model is None or self.tokenizer is None:
            return ""

        try:
            with self.inference_lock:
                if self.model_type == 'generative_bert':
                    if hasattr(self.model, 'generate_answer'):
                        ans = self.model.generate_answer(self.tokenizer, prompt_text, dense_features=dense_features, aspect_id=aspect_id, max_new_tokens=max_new_tokens, device=self.device)
                    else:
                        enc = self.tokenizer(prompt_text, max_length=512, truncation=True, return_tensors='pt').to(self.device)
                        with torch.no_grad():
                            outputs = self.model.seq2seq.generate(
                                input_ids=enc['input_ids'],
                                attention_mask=enc['attention_mask'],
                                max_new_tokens=max_new_tokens,
                                num_beams=4,
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
                    extra_gen_args = {}
                    if getattr(self.model.config, 'is_encoder_decoder', False):
                        dec_start = getattr(self.model.generation_config, 'decoder_start_token_id', None) or getattr(self.model.config, 'decoder_start_token_id', None) or getattr(self.tokenizer, 'cls_token_id', 101)
                        eos_id = getattr(self.model.generation_config, 'eos_token_id', None) or getattr(self.model.config, 'eos_token_id', None) or getattr(self.tokenizer, 'sep_token_id', 102)
                        extra_gen_args['decoder_start_token_id'] = dec_start
                        extra_gen_args['eos_token_id'] = eos_id
                    with torch.no_grad():
                        outputs = self.model.generate(
                            input_ids=enc['input_ids'],
                            attention_mask=enc['attention_mask'],
                            max_new_tokens=max_new_tokens,
                            num_beams=4,
                            no_repeat_ngram_size=3,
                            repetition_penalty=1.15,
                            early_stopping=True,
                            **extra_gen_args
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
                            do_sample=True,
                            **extra_gen_args
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

    def detect_intent_and_aspect(self, query: str) -> Tuple[str, str, Optional[Dict[str, Any]]]:
        q_raw = query.lower()
        q_clean = clean_vietnamese_text(query).lower()

        is_loc = any(k in q_raw or k in q_clean for k in [
            'where', 'address', 'location', 'map', 'situated', 'directions',
            'o dau', 'dia chi', 'vi tri', 'cho nao', 'nam o dau'
        ])
        is_star = any(k in q_raw or k in q_clean for k in [
            'how many stars', 'star rating', 'star level', 'classification', 'how many star',
            'may sao', 'hang sao', 'hang may sao', 'tieu chuan may sao'
        ])
        is_count = any(k in q_raw or k in q_clean for k in [
            'how many reviews', 'review count', 'total reviews', 'number of reviews',
            'bao nhieu danh gia', 'so luong danh gia', 'tong danh gia'
        ])

        if is_loc:
            return 'location', 'Facility', QUERY_KEYWORD_MAP.get('location')
        if is_star:
            return 'star', 'Branding', QUERY_KEYWORD_MAP.get('star')
        if is_count:
            return 'review_count', 'Experience', None

        # Check specific sub-aspect keywords first (e.g., pool, breakfast, wifi, gym, staff, etc.)
        matched_sub = None
        best_term_len = 0
        for sub_k, sub_info in QUERY_KEYWORD_MAP.items():
            for t in sub_info['terms']:
                t_len = len(t)
                if t_len <= best_term_len:
                    continue
                pattern = r'\b' + re.escape(t) + r'\b'
                if re.search(pattern, q_raw) or re.search(pattern, q_clean):
                    matched_sub = sub_info
                    best_term_len = t_len

        if matched_sub:
            return 'aspect_qa', matched_sub['aspect'], matched_sub

        # Fallback to general aspect keywords
        matched_aspect = None
        best_kw_len = 0
        for asp, kws in ASPECT_KEYWORDS.items():
            for kw in kws:
                kw_len = len(kw)
                if kw_len <= best_kw_len:
                    continue
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, q_raw) or re.search(pattern, q_clean):
                    matched_aspect = asp
                    best_kw_len = kw_len
        if matched_aspect:
            return 'aspect_qa', matched_aspect, None
        return 'aspect_qa', 'Experience', None

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

        for sub_info in QUERY_KEYWORD_MAP.values():
            for t in sub_info['terms']:
                if t in clean_q:
                    aspect_kws.append(t)

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

    def answer_query(self, session_id: str, user_query: str, selected_hotel: Optional[str] = None, action: Optional[str] = None) -> Dict[str, Any]:
        state = self.sessions.get_session(session_id)
        with state.lock:
            clean_q = clean_vietnamese_text(user_query).strip() or user_query.strip()
            intent, aspect, sub_aspect_info = self.detect_intent_and_aspect(user_query)
            query_terms = sub_aspect_info['terms'] if sub_aspect_info else []

            # Hotel Resolution
            matched_hotel = None
            was_coref = False

            if selected_hotel is not None:
                if not selected_hotel or str(selected_hotel).strip() == "":
                    state.current_hotel = None
                else:
                    clean_sel = clean_vietnamese_text(str(selected_hotel)).lower().strip()
                    for h_k, h_val in self.database.items():
                        if h_k == clean_sel or clean_vietnamese_text(h_val.get('hotel_name', '')).lower().strip() == clean_sel:
                            matched_hotel = h_val
                            break
                    if not matched_hotel:
                        matched_hotel = self.matcher.match(str(selected_hotel))
                    if matched_hotel:
                        state.current_hotel = matched_hotel

            if not matched_hotel and intent != 'recommendation':
                matched_hotel = self.matcher.match(user_query)
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

                # Check if this inquiry is an explicit greeting or welcome request
                is_greeting = (action == 'greeting') or any(clean_q.lower().strip().startswith(g) for g in ['hello', 'hi', 'xin chao', 'xin chào', 'welcome', 'introduce'])

                # Retrieve Multi-Review Evidence with Feature 10 Decay and Query Keyword Alignment
                cand_reviews = self.retriever.retrieve(matched_hotel, aspect, query_terms=query_terms)
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
                        "embed_url": f"https://maps.google.com/maps?q={encoded_loc}&t=&z=15&ie=UTF8&iwloc=&output=embed&hl=en"
                    }

                # Extract grounded evidence sentences from candidate reviews
                clean_evidence_list = []
                for r in cand_reviews:
                    for s in r.get('matched_sentences', []):
                        s_clean = s.strip()
                        if len(s_clean) >= 10 and s_clean not in clean_evidence_list:
                            clean_evidence_list.append(s_clean[:140])
                            if len(clean_evidence_list) >= 3:
                                break
                    if len(clean_evidence_list) >= 3:
                        break

                if not clean_evidence_list and cand_reviews:
                    for r in cand_reviews:
                        txt = r.get('text', '')
                        if txt:
                            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', txt.strip()) if len(s.strip()) > 12]
                            if sents and sents[0] not in clean_evidence_list:
                                clean_evidence_list.append(sents[0][:140])
                                if len(clean_evidence_list) >= 2:
                                    break

                evidence_str = " | ".join(clean_evidence_list) if clean_evidence_list else f"Dependable {star_label} hospitality standard"

                # Conditioned Prompt matching model_v3 training architecture exactly
                if is_greeting:
                    clean_prompt_q = f"Hello, can you introduce {h_name}?"
                    ctx = f"Hotel: {h_name} ({star_label}, {loc}) | Welcome Greeting"
                    prompt = f"User Inquiry: {clean_prompt_q} | Target Aspect: Experience | Verified Context: {ctx}"
                else:
                    ctx = f"Hotel: {h_name} ({star_label}) | Aspect: {aspect} | Avg Score: {avg_score:.1f}/5.0 | Evidence: {evidence_str}"
                    prompt = f"User Inquiry: {clean_q} | Target Aspect: {aspect} | Verified Context: {ctx}"

                asp_id = ASPECTS.index(aspect) if aspect in ASPECTS else None
                neural_ans = self.pipeline.generate(clean_q if self.pipeline.model_type == 'extractive_bert' else prompt, context_text=ctx, aspect_id=asp_id)

                # Pure 100% natural neural generation - zero template overrides
                is_fallback = not bool(neural_ans)
                if not neural_ans:
                    neural_ans = f"Regarding {aspect.lower()} at {h_name}, verified guest reviews report an average rating of {avg_score:.1f}/5.0 stars."

                # Retrieve ALL original reviews matching this exact aspect for full UI pagination ("View original reviews")
                all_aspect_reviews = self.retriever.retrieve_all_for_aspect(matched_hotel, aspect, query_terms=query_terms)
                original_reviews_data = []
                for r in all_aspect_reviews:
                    original_reviews_data.append({
                        "date": r.get('date', 'Recent'),
                        "score": r.get('score', 4.0),
                        "sentiment": r.get('sentiment', 'Positive'),
                        "recency_weight": round(r.get('recency_weight', 1.0), 3),
                        "text": r.get('text', ''),
                        "aspect_spans": r.get('aspect_spans', [])
                    })

                aspect_title = sub_aspect_info['display'].title() if sub_aspect_info else ASPECT_DISPLAY.get(aspect, aspect)

                response_payload = {
                    "answer": neural_ans,
                    "reply": neural_ans,
                    "hotel_name": h_name,
                    "star": star_label,
                    "score": round(avg_score, 1),
                    "total_reviews": tot_revs,
                    "aspect": aspect,
                    "aspect_title": aspect_title,
                    "sentiment": consensus.capitalize(),
                    "confidence": 0.95,
                    "maps_card": maps_card,
                    "photo_url": matched_hotel.get('photo_url') or get_hotel_image_url(h_name, matched_hotel.get('location', ''), addr),
                    "original_reviews": original_reviews_data,
                    "citations": original_reviews_data,
                    "context_applied": was_coref,
                    "model_name": getattr(self.pipeline, 'active_model_name', 'model_v4'),
                    "model_type": getattr(self.pipeline, 'model_type', 'seq2seq'),
                    "inference_mode": "fallback_template" if is_fallback else "neural_generation",
                    "prompt_used": prompt
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
                        f"[{i}] {h['hotel_name']} ({h['star']}, Score: {h['score']}/5.0, {h['location']}): \"{clean_quote(rev_quote, 100)}\""
                    )
                    orig_revs.append({
                        "date": "Recent",
                        "score": h['score'],
                        "recency_weight": 1.0,
                        "text": f"{h['hotel_name']} ({h['location']}): {rev_quote}"
                    })
                ctx = " | ".join(hotel_lines)
                prompt = f"User Inquiry: {clean_q} | Target Aspect: Experience | Verified Context: Recommended hotel properties: {ctx}"

                neural_ans = self.pipeline.generate(clean_q if self.pipeline.model_type == 'extractive_bert' else prompt, context_text=ctx)
                is_fallback = not bool(neural_ans)
                if not neural_ans:
                    neural_ans = f"Based on verified guest reviews, recommended accommodations include {top_h.get('hotel_name')} ({top_h.get('star', 'Standard')}) in {top_h.get('location', 'Vietnam')}, rated {top_h.get('score', 4.0):.1f}/5.0 stars."

                response_payload = {
                    "answer": neural_ans,
                    "reply": neural_ans,
                    "hotel_name": top_h.get('hotel_name'),
                    "star": top_h.get('star'),
                    "score": round(top_h.get('score', 4.0), 1),
                    "total_reviews": len(top_h.get('reviews', [])),
                    "aspect": aspect,
                    "aspect_title": "Recommendations",
                    "sentiment": "Positive",
                    "confidence": 0.90,
                    "maps_card": None,
                    "photo_url": top_h.get('photo_url') or get_hotel_image_url(top_h.get('hotel_name', ''), top_h.get('location', ''), top_h.get('hotel_address', '')),
                    "original_reviews": orig_revs,
                    "citations": orig_revs,
                    "context_applied": False,
                    "model_name": getattr(self.pipeline, 'active_model_name', 'model_v4'),
                    "model_type": getattr(self.pipeline, 'model_type', 'seq2seq'),
                    "inference_mode": "fallback_template" if is_fallback else "neural_generation",
                    "prompt_used": prompt
                }
                state.history.append({"user": user_query, "bot": neural_ans})
                return response_payload

            # ------------------------------------------------------------------
            # Scenario C: General Inquiry or Greeting -> Conversational Generation
            # ------------------------------------------------------------------
            prompt = f"User Inquiry: {clean_q} | Target Aspect: Experience | Verified Context: AI Concierge Assistant for Vietnam Hotels and Accommodations"
            neural_ans = self.pipeline.generate(prompt)
            is_fallback = not bool(neural_ans)
            if not neural_ans:
                neural_ans = "Hello, I am your AI assistant specializing in hotel reviews, service quality, and accommodations across Vietnam. How can I help you today?"

            response_payload = {
                "answer": neural_ans,
                "reply": neural_ans,
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
                "citations": [],
                "context_applied": False,
                "model_name": getattr(self.pipeline, 'active_model_name', 'model_v4'),
                "model_type": getattr(self.pipeline, 'model_type', 'seq2seq'),
                "inference_mode": "fallback_template" if is_fallback else "neural_generation",
                "prompt_used": prompt
            }
            state.history.append({"user": user_query, "bot": neural_ans})
            return response_payload

# Global Bot Instance
BOT: Optional[ConversationalQABot] = None

# ---------------------------------------------------------------------------
# Static Directory & Multipart File Parser
# ---------------------------------------------------------------------------
BASE_DIR = PROJECT_ROOT
MODEL_STORAGE_DIR = os.path.abspath(os.environ.get('HOTEL_QA_USER_DATA_DIR', BASE_DIR))
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(APP_DIR, 'index.html')):
    WEBAPP_DIR = APP_DIR
elif os.path.exists(os.path.join(BASE_DIR, 'desktop', 'index.html')):
    WEBAPP_DIR = os.path.join(BASE_DIR, 'desktop')
elif os.path.exists(os.path.join(BASE_DIR, 'webapp', 'index.html')):
    WEBAPP_DIR = os.path.join(BASE_DIR, 'webapp')
elif os.path.exists(os.path.join(BASE_DIR, 'index.html')):
    WEBAPP_DIR = BASE_DIR
else:
    WEBAPP_DIR = APP_DIR

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
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def do_HEAD(self):
        self.do_GET(head_only=True)

    def do_GET(self, head_only: bool = False):
        global HOTEL_DATABASE
        parsed = urllib.parse.urlparse(self.path)
        req_path = parsed.path.lstrip('/')
        if not req_path or req_path == 'index.html':
            req_path = 'index.html'

        if parsed.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            active_m = getattr(BOT.pipeline, 'active_model_name', 'model_v3') if BOT and BOT.pipeline else 'Seq2Seq Engine'
            if not head_only:
                self.wfile.write(json.dumps({
                    'status': 'ok',
                    'hotels_loaded': len(HOTEL_DATABASE),
                    'model_loaded': BOT.pipeline.loaded_successfully if BOT and BOT.pipeline else False,
                    'active_model': active_m
                }).encode('utf-8'))
            return

        if parsed.path == '/api/session-debug':
            query_params = urllib.parse.parse_qs(parsed.query)
            s_id = query_params.get('session_id', [''])[0].strip()
            session_data = {}
            if BOT and hasattr(BOT, 'sessions') and s_id:
                st = BOT.sessions.get_session(s_id)
                if st:
                    with st.lock:
                        session_data = {
                            'session_id': s_id,
                            'current_hotel': st.current_hotel.get('hotel_name') if st.current_hotel else None,
                            'last_aspect': st.last_aspect,
                            'history_turns': len(st.history),
                            'history': list(st.history)
                        }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            if not head_only:
                self.wfile.write(json.dumps({
                    'status': 'ok',
                    'session': session_data,
                    'active_model': getattr(BOT.pipeline, 'active_model_name', None) if BOT and BOT.pipeline else None,
                    'model_type': getattr(BOT.pipeline, 'model_type', None) if BOT and BOT.pipeline else None,
                    'database_size': len(HOTEL_DATABASE)
                }, ensure_ascii=False).encode('utf-8'))
            return

        if parsed.path == '/api/models':
            models = []
            active_m = getattr(BOT.pipeline, 'active_model_name', '') if BOT and BOT.pipeline else ''

            def calc_size_mb(p: str) -> float:
                if os.path.isdir(p):
                    total_bytes = sum(os.path.getsize(os.path.join(r, f)) for r, d, fs in os.walk(p) for f in fs if not f.startswith('.'))
                    return round(total_bytes / (1024 * 1024), 1)
                elif os.path.isfile(p):
                    return round(os.path.getsize(p) / (1024 * 1024), 1)
                return 0.0

            # 1. Check root model directories (model_v3, hotel_aspect_qa_bart_engine)
            root_candidates = ['model_v3', 'hotel_aspect_qa_bart_engine']
            for rname in root_candidates:
                rpath = os.path.join(BASE_DIR, rname)
                if os.path.isdir(rpath) and not any(m['name'] == rname for m in models):
                    is_active = (rname == active_m)
                    models.append({
                        'name': rname,
                        'path': rname,
                        'size_mb': calc_size_mb(rpath),
                        'active': is_active,
                        'is_active': is_active
                    })

            # 2. Scan model/ directory for checkpoint files (.pt, .bin, .safetensors) and subdirectories
            model_dir = os.path.join(BASE_DIR, 'model')
            if os.path.exists(model_dir):
                for fname in sorted(os.listdir(model_dir), reverse=True):
                    if fname.startswith('.'):
                        continue
                    fpath = os.path.join(model_dir, fname)
                    if fname.endswith(('.pt', '.bin', '.safetensors')):
                        is_active = (fname == active_m)
                        models.append({
                            'name': fname,
                            'path': f"model/{fname}",
                            'size_mb': calc_size_mb(fpath),
                            'active': is_active,
                            'is_active': is_active
                        })
                    elif os.path.isdir(fpath) and not any(m['name'] == fname for m in models):
                        is_active = (fname == active_m)
                        models.append({
                            'name': fname,
                            'path': f"model/{fname}",
                            'size_mb': calc_size_mb(fpath),
                            'active': is_active,
                            'is_active': is_active
                        })

            # 3. Check root model.pt if exists
            root_model = os.path.join(BASE_DIR, 'model.pt')
            if os.path.isfile(root_model) and not any(m['name'] == 'model.pt' for m in models):
                models.append({
                    'name': 'model.pt',
                    'path': 'model.pt',
                    'size_mb': calc_size_mb(root_model),
                    'active': (active_m == 'model.pt'),
                    'is_active': (active_m == 'model.pt')
                })

            user_model = os.path.join(MODEL_STORAGE_DIR, 'model.pt')
            if os.path.isfile(user_model) and not any(m['name'] == 'model.pt' for m in models):
                models.append({
                    'name': 'model.pt',
                    'path': 'model.pt',
                    'size_mb': calc_size_mb(user_model),
                    'active': (active_m == 'model.pt'),
                    'is_active': (active_m == 'model.pt')
                })

            if not any(m['active'] for m in models) and models:
                match = next((m for m in models if m['name'] == active_m), None)
                if match:
                    match['active'] = True
                    match['is_active'] = True
                else:
                    models[0]['active'] = True
                    models[0]['is_active'] = True
                    active_m = models[0]['name']

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            if not head_only:
                self.wfile.write(json.dumps({
                    'models': models,
                    'active_model': active_m or (models[0]['name'] if models else 'Default')
                }).encode('utf-8'))
            return

        if parsed.path.rstrip('/') == '/api/hotels':
            if not HOTEL_DATABASE:
                load_hotel_database()

            query_params = urllib.parse.parse_qs(parsed.query)
            raw_city = query_params.get('city', [''])[0].strip() or query_params.get('province', ['all'])[0].strip()
            if not raw_city:
                raw_city = 'all'
            city_filter = clean_vietnamese_text(raw_city).lower()
            raw_search = query_params.get('search', [''])[0].strip()
            search_filter = clean_vietnamese_text(raw_search).lower()
            sort_mode = query_params.get('sort', ['recommended'])[0].strip().lower()

            try:
                min_rating = float(query_params.get('min_rating', ['0'])[0])
            except (ValueError, TypeError):
                min_rating = 0.0

            try:
                min_reviews = max(int(query_params.get('min_reviews', ['0'])[0]), 0)
            except (ValueError, TypeError):
                min_reviews = 0
            try:
                limit = min(max(int(query_params.get('limit', [9])[0]), 1), 100)
            except (ValueError, TypeError):
                limit = 9

            try:
                offset = max(int(query_params.get('offset', [0])[0]), 0)
            except (ValueError, TypeError):
                offset = 0

            city_aliases = CITY_ALIASES.get(city_filter, [city_filter]) if (city_filter and city_filter != 'all') else []

            results = []
            for norm_key, h in HOTEL_DATABASE.items():
                # Province / City filter
                if city_aliases:
                    if not any(a in h.get('loc_norm', '') for a in city_aliases):
                        continue

                # Search query filter (matches hotel name, location, address)
                if search_filter:
                    if search_filter not in h.get('search_blob', ''):
                        continue

                results.append({
                    'hotel_name': h.get('hotel_name', ''),
                    'norm_key': norm_key,
                    'star': h.get('star', 'Standard'),
                    'score': round(float(h.get('score', 4.0)), 1),
                    'location': h.get('location') or 'Vietnam',
                    'address': h.get('hotel_address') or 'Vietnam',
                    'review_count': h.get('review_count', 0),
                    'sample_snippet': h.get('sample_snippet', ''),
                    'pop_score': h.get('pop_score', 0.0),
                    'photo_url': h.get('photo_url'),
                    'aspect_scores': h.get('aspect_scores', {}),
                    'maps_search_url': h.get('maps_search_url', '')
                })

            # Apply rating and review-count filters
            results = [
                h for h in results
                if float(h.get('score') or 0) >= min_rating
                and int(h.get('review_count') or 0) >= min_reviews
            ]

            # Sort hotels according to the selected mode
            if sort_mode == 'top_rated':
                results.sort(
                    key=lambda h: (
                        float(h.get('score') or 0),
                        int(h.get('review_count') or 0),
                        float(h.get('pop_score') or 0)
                    ),
                    reverse=True
                )

            elif sort_mode == 'most_reviewed':
                results.sort(
                    key=lambda h: (
                        int(h.get('review_count') or 0),
                        float(h.get('score') or 0),
                        float(h.get('pop_score') or 0)
                    ),
                    reverse=True
                )

            else:
                # Recommended: sort by the existing popularity score
                results.sort(
                    key=lambda h: float(h.get('pop_score') or 0),
                    reverse=True
                )

            total_count = len(results)
            paginated_hotels = results[offset: offset + limit]
            has_more = (offset + limit) < total_count

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()

            if not head_only:
                self.wfile.write(json.dumps({
                    'total': total_count,
                    'offset': offset,
                    'limit': limit,
                    'has_more': has_more,
                    'returned': len(paginated_hotels),
                    'hotels': paginated_hotels,
                    'provinces': PROVINCES_METADATA if offset == 0 else []
                }).encode('utf-8'))

            return

        # Serve static file from WEBAPP_DIR
        file_path = os.path.normpath(os.path.join(WEBAPP_DIR, req_path))
        if not (file_path == WEBAPP_DIR or file_path.startswith(WEBAPP_DIR + os.sep)) or not os.path.isfile(file_path):
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            if not head_only:
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
            self._send_cors_headers()
            self.end_headers()
            if not head_only:
                self.wfile.write(content)
        except Exception as e:
            self.send_response(500)
            self._send_cors_headers()
            self.end_headers()
            if not head_only:
                self.wfile.write(str(e).encode('utf-8'))

    def do_POST(self):
        global BOT
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/chat':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
            except (ValueError, TypeError):
                self.send_response(400)
                self._send_cors_headers()
                self.end_headers()
                return

            if content_len > 65536:
                self.send_response(413)
                self._send_cors_headers()
                self.end_headers()
                return

            body = self.rfile.read(content_len).decode('utf-8')
            try:
                data = json.loads(body)
            except Exception:
                self.send_response(400)
                self._send_cors_headers()
                self.end_headers()
                return

            if not isinstance(data, dict):
                self.send_response(400)
                self._send_cors_headers()
                self.end_headers()
                return

            session_id = data.get('session_id', 'default_session')
            query = data.get('query', '').strip()
            selected_hotel = data.get('selected_hotel')

            if BOT is None:
                with BOT_INIT_LOCK:
                    if BOT is None:
                        BOT = ConversationalQABot(HOTEL_DATABASE)

            action = data.get('action')
            result = BOT.answer_query(session_id, query, selected_hotel=selected_hotel, action=action)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))

        elif parsed.path == '/api/upload-model':
            try:
                content_len = int(self.headers.get('Content-Length', 0))
            except (ValueError, TypeError):
                self.send_response(400)
                self._send_cors_headers()
                self.end_headers()
                return

            if content_len <= 0:
                self.send_response(400)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Empty upload payload'}).encode('utf-8'))
                return

            # Max 2GB limit for checkpoint upload
            if content_len > 2 * 1024 * 1024 * 1024:
                self.send_response(413)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Model file exceeds 2GB maximum limit'}).encode('utf-8'))
                return

            try:
                filename, file_data = parse_multipart_file(self.headers, self.rfile, content_len)
                if not file_data or len(file_data) == 0:
                    self.send_response(400)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Failed to parse model file payload'}).encode('utf-8'))
                    return

                target_filename = 'model.pt'
                os.makedirs(MODEL_STORAGE_DIR, exist_ok=True)
                save_path = os.path.join(MODEL_STORAGE_DIR, target_filename)
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
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(response_payload).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self._send_cors_headers()
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
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Missing model_name parameter'}).encode('utf-8'))
                    return

                # Strict sanitization against path traversal: only basename
                clean_name = os.path.basename(model_name)
                candidate_paths = [
                    os.path.join(BASE_DIR, 'model', clean_name),
                    os.path.join(BASE_DIR, clean_name),
                    os.path.join(MODEL_STORAGE_DIR, clean_name)
                ]
                target_path = None
                for p in candidate_paths:
                    if os.path.exists(p) and (p.endswith(('.pt', '.bin', '.safetensors')) or os.path.isdir(p)):
                        target_path = p
                        break

                if not target_path:
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self._send_cors_headers()
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
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'status': 'success',
                        'active_model': selected_name,
                        'message': f'Model {selected_name} loaded successfully'
                    }).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': f'Failed to reload model weights from {selected_name}'}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

def main():
    parser = argparse.ArgumentParser(description="Hotel AI Conversational QA Server")
    parser.add_argument('--port', type=int, default=8000, help="Port to listen on (default 8000)")
    parser.add_argument('--host', type=str, default='0.0.0.0', help="Host interface (default 0.0.0.0)")
    args = parser.parse_args()

    # Load Knowledge Base
    load_hotel_database()

    port = args.port
    max_retries = 10
    httpd = None
    for attempt in range(max_retries):
        try:
            server_address = (args.host, port)
            httpd = ThreadedHTTPServer(server_address, QAChatHandler)
            break
        except OSError as e:
            # Address already in use: macOS (48), Linux (98), Windows WSAEADDRINUSE (10048)
            if e.errno in (48, 98, 10048):
                print(f"Notice: Port {port} is occupied. Trying port {port + 1}...")
                port += 1
                if attempt == max_retries - 1:
                    print(f"Error: Could not bind to any port in range {args.port} - {port - 1}.")
                    raise
            else:
                raise

    ready_url = f"http://127.0.0.1:{httpd.server_address[1]}"
    print(f"HOTEL_QA_SERVER_READY={ready_url}", flush=True)
    print(f"Server successfully started at {ready_url}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == '__main__':
    main()


