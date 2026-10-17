"""
Data preprocessing and pipeline for Aspect-Based Sentiment Analysis (ABSA)
Extracts fine-grained aspect and sentiment annotations from TripAdvisor_EN.json,
aligns entity spans, and performs stratified splitting (80/10/10) for Train/Val/Test.
"""

import os
import json
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np

ASPECTS = ['Service', 'Facility', 'Experience', 'Amenity', 'Loyalty', 'Branding']
# Aligned with Training_Kaggle.ipynb CFG['sentiments']:
SENTIMENTS = ['Negative', 'Positive', 'Neutral']

ASPECT_MAP = {
    'Service': 'Service',
    'Facility': 'Facility',
    'Experience': 'Experience',
    'Amenity': 'Amenity',
    'Amentity': 'Amenity',  # Handle typo in Label Studio annotations
    'Loyalty': 'Loyalty',
    'Branding': 'Branding'
}

def aggregate_sentiment(sentiments, score=None):
    """
    Aggregate multiple sentiment annotations for a single aspect within a review.
    Uses majority voting with fallback to overall score on ties.
    """
    if not sentiments:
        if score is not None:
            if score <= 2.0:
                return 'Negative'
            elif score == 3.0:
                return 'Neutral'
        return 'Positive'

    counts = Counter(sentiments)
    most_common = counts.most_common()

    if len(most_common) == 1 or most_common[0][1] > most_common[1][1]:
        return most_common[0][0]

    # Handle tie between Positive and Negative
    if 'Negative' in counts and 'Positive' in counts:
        if score is not None and score <= 3.0:
            return 'Negative'
        return 'Positive'

    return most_common[0][0]

def parse_raw_json(json_path, aspects=ASPECTS, sentiments=SENTIMENTS):
    """
    Parse raw Label Studio annotated JSON file into structured ABSA records.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        raw_items = json.load(f)

    aspect2id = {a: i for i, a in enumerate(aspects)}
    sentiment2id = {s: i for i, s in enumerate(sentiments)}

    records = []
    for idx, item in enumerate(raw_items, 1):
        data_block = item.get('data', {})
        text = data_block.get('text', '')
        meta = data_block.get('meta_info', {})
        score = float(meta.get('score', 0.0))
        ref_id = meta.get('ref_id', f'TripAdivisor_En_{idx}')
        hotel_name = meta.get('hotel name', meta.get('normalized_title', '')).strip()
        star = meta.get('star', '').strip()

        entities = {}
        entity_sents = {}

        for ann in item.get('annotations', []):
            for res in ann.get('result', []):
                rid = res.get('id')
                fn = res.get('from_name')
                val = res.get('value', {})
                labels = val.get('labels', [])

                if fn == 'entities' and labels:
                    normalized_aspect = ASPECT_MAP.get(labels[0])
                    if normalized_aspect and normalized_aspect in aspect2id:
                        entities[rid] = {
                            'aspect': normalized_aspect,
                            'start': val.get('start', 0),
                            'end': val.get('end', 0),
                            'text': val.get('text', '')
                        }
                elif fn == 'entity_sentiment' and labels:
                    if labels[0] in sentiment2id:
                        entity_sents[rid] = labels[0]

        aspect_spans = defaultdict(list)
        aspect_s_list = defaultdict(list)

        for rid, ent in entities.items():
            asp = ent['aspect']
            snt = entity_sents.get(rid, 'Positive')
            aspect_spans[asp].append({
                'start': ent['start'],
                'end': ent['end'],
                'text': ent['text'],
                'sentiment': snt
            })
            aspect_s_list[asp].append(snt)

        aspect_labels = [0] * len(aspects)
        sentiment_labels = [-1] * len(aspects)

        for i, asp in enumerate(aspects):
            if asp in aspect_spans and len(aspect_spans[asp]) > 0:
                aspect_labels[i] = 1
                agg_s = aggregate_sentiment(aspect_s_list[asp], score)
                sentiment_labels[i] = sentiment2id[agg_s]

        records.append({
            'review_id': idx,
            'ref_id': ref_id,
            'text': text,
            'char_length': len(text),
            'score': score,
            'star': star,
            'hotel_name': hotel_name,
            'aspect_labels': aspect_labels,
            'sentiment_labels': sentiment_labels,
            'spans': dict(aspect_spans)
        })

    return records

def split_dataset(records, seed=42):
    """
    Perform stratified train/val/test split (80/10/10) preserving
    rating distribution and multi-label aspect co-occurrence patterns.
    """
    rng = np.random.RandomState(seed)
    strata = defaultdict(list)

    for rec in records:
        if rec['score'] <= 2.0:
            rate_bin = 'low'
        elif rec['score'] == 3.0:
            rate_bin = 'mid'
        elif rec['score'] == 4.0:
            rate_bin = 'high'
        else:
            rate_bin = 'top'

        aspect_code = ''.join(str(x) for x in rec['aspect_labels'])
        strata[f'{rate_bin}_{aspect_code}'].append(rec)

    train_data, val_data, test_data = [], [], []

    for key, group in strata.items():
        idx = np.arange(len(group))
        rng.shuffle(idx)
        n_total = len(idx)

        n_test = max(1, int(round(n_total * 0.1))) if n_total >= 10 else (1 if n_total >= 5 else 0)
        n_val = max(1, int(round(n_total * 0.1))) if n_total >= 10 else (1 if n_total >= 3 else 0)

        if n_test + n_val >= n_total:
            n_test, n_val = 0, 0

        for i in idx[:n_test]:
            test_data.append(group[i])
        for i in idx[n_test:n_test + n_val]:
            val_data.append(group[i])
        for i in idx[n_test + n_val:]:
            train_data.append(group[i])

    rng.shuffle(train_data)
    rng.shuffle(val_data)
    rng.shuffle(test_data)

    return train_data, val_data, test_data

def compute_statistics(data, aspects=ASPECTS, sentiments=SENTIMENTS):
    """
    Compute total review count, aspect distribution, and sentiment distribution for a split.
    """
    aspect_dist = {asp: 0 for asp in aspects}
    sentiment_dist = {snt: 0 for snt in sentiments}

    for rec in data:
        for i, asp in enumerate(aspects):
            if rec['aspect_labels'][i] == 1:
                aspect_dist[asp] += 1
                s_id = rec['sentiment_labels'][i]
                if s_id >= 0:
                    sentiment_dist[sentiments[s_id]] += 1

    return {
        'total_reviews': len(data),
        'aspect_distribution': aspect_dist,
        'sentiment_distribution': sentiment_dist
    }

def run_pipeline(json_path='data/dataset/TripAdvisor_EN.json', output_dir='data/train', seed=42):
    """
    Execute end-to-end preprocessing pipeline:
    1. Parse raw Label Studio JSON
    2. Stratified split into train (80%), val (10%), test (10%)
    3. Compute verification statistics
    4. Save train.json, val.json, test.json, label_maps.json, stats.json
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Parsing raw dataset from {json_path}...")
    records = parse_raw_json(json_path, aspects=ASPECTS, sentiments=SENTIMENTS)
    print(f"Successfully parsed {len(records):,} review records.")

    print(f"Splitting dataset into Train/Val/Test (seed={seed})...")
    train_data, val_data, test_data = split_dataset(records, seed=seed)
    print(f"Dataset split complete: Train={len(train_data):,} | Val={len(val_data):,} | Test={len(test_data):,}")

    label_maps = {
        'aspects': ASPECTS,
        'sentiments': SENTIMENTS,
        'aspect2id': {a: i for i, a in enumerate(ASPECTS)},
        'sentiment2id': {s: i for i, s in enumerate(SENTIMENTS)}
    }

    stats = {
        'train': compute_statistics(train_data, ASPECTS, SENTIMENTS),
        'val': compute_statistics(val_data, ASPECTS, SENTIMENTS),
        'test': compute_statistics(test_data, ASPECTS, SENTIMENTS)
    }

    print(f"Exporting processed files to {output_path}...")
    with open(output_path / 'train.json', 'w', encoding='utf-8') as f:
        json.dump(train_data, f, indent=2, ensure_ascii=False)

    with open(output_path / 'val.json', 'w', encoding='utf-8') as f:
        json.dump(val_data, f, indent=2, ensure_ascii=False)

    with open(output_path / 'test.json', 'w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)

    with open(output_path / 'label_maps.json', 'w', encoding='utf-8') as f:
        json.dump(label_maps, f, indent=2, ensure_ascii=False)

    with open(output_path / 'stats.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print("All files exported successfully.")
    return train_data, val_data, test_data, label_maps, stats

if __name__ == '__main__':
    run_pipeline()
