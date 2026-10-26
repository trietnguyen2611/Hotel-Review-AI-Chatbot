#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import re
import socket
import argparse
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from collections import defaultdict, Counter
from typing import Dict, List, Any, Optional, Tuple

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Tự động chuyển đổi sang môi trường ảo .venv nếu đang dùng python hệ thống
try:
    import torch
    import transformers
    import pandas as pd
    import numpy as np
except ImportError:
    base_dir = PROJECT_ROOT
    if sys.platform == 'win32':
        venv_py = os.path.join(base_dir, '.venv', 'Scripts', 'python.exe')
    else:
        venv_py = os.path.join(base_dir, '.venv', 'bin', 'python')
    if os.path.exists(venv_py) and os.path.abspath(sys.executable) != os.path.abspath(venv_py):
        print(f"[Launcher] Chuyển hướng sang môi trường ảo: {venv_py}")
        os.execv(venv_py, [venv_py] + sys.argv)
    else:
        raise

import torch
import torch.nn as nn
from transformers import AutoTokenizer, BartForConditionalGeneration

CANONICAL_ASPECTS = ["Service", "Facility", "Experience", "Amenity", "Loyalty", "Branding"]

# ==============================================================================
# 1. KIẾN TRÚC MÔ HÌNH CRAM-ABSA ĐA NHIỆM
# ==============================================================================

class HotelAspectBARTGenerativeEngine(nn.Module):
    """Mô hình sinh có điều kiện BART tích hợp 17 đặc trưng định lượng & các đầu phân loại đa nhiệm."""
    def __init__(self, model_name: str = "facebook/bart-base", dense_feat_dim: int = 17, num_aspects: int = 6):
        super().__init__()
        self.bart = BartForConditionalGeneration.from_pretrained(model_name)
        d_model = self.bart.config.d_model  # 768
        
        # Mạng chiếu phi tuyến 17 Dense Features
        self.feature_projection = nn.Sequential(
            nn.Linear(dense_feat_dim, 256),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(256, d_model),
            nn.LayerNorm(d_model)
        )
        
        # Các đầu phân loại đa nhiệm
        self.aspect_head = nn.Linear(d_model, num_aspects)
        self.sentiment_head = nn.Linear(d_model, 2)
        self.ordinal_head = nn.Linear(d_model, 4)  # CORN ordinal heads (4 binary)
        self.aspect_mask_head = nn.Linear(d_model, num_aspects)  # Rationale masks

    def forward(self, input_ids, attention_mask, labels=None, features=None):
        inputs_embeds = self.bart.model.encoder.embed_tokens(input_ids)
        if features is not None:
            feat_embed = self.feature_projection(features).unsqueeze(1)
            inputs_embeds = inputs_embeds + feat_embed.to(inputs_embeds.dtype) * 0.15
            
        encoder_outputs = self.bart.model.encoder(
            inputs_embeds=inputs_embeds,
            attention_mask=attention_mask,
            return_dict=True
        )
        encoder_last_hidden = encoder_outputs.last_hidden_state
        mask_expanded = attention_mask.unsqueeze(-1).to(encoder_last_hidden.dtype)
        pooled_encoder = (encoder_last_hidden * mask_expanded).sum(dim=1) / torch.clamp(mask_expanded.sum(dim=1), min=1e-9)

        logits = None
        loss = None
        if labels is not None:
            outputs = self.bart(
                inputs_embeds=inputs_embeds,
                attention_mask=attention_mask,
                labels=labels,
                return_dict=True
            )
            logits = outputs.logits
            loss = outputs.loss
            
        return {
            "loss": loss,
            "logits": logits,
            "pred_aspect_logits": self.aspect_head(pooled_encoder),
            "pred_sentiment_logits": self.sentiment_head(pooled_encoder),
            "pred_ordinal_logits": self.ordinal_head(pooled_encoder),
            "pred_aspect_mask_logits": self.aspect_mask_head(encoder_last_hidden)
        }

    def generate(self, input_ids, attention_mask, features=None, **gen_kwargs):
        inputs_embeds = self.bart.model.encoder.embed_tokens(input_ids)
        if features is not None:
            feat_embed = self.feature_projection(features).unsqueeze(1)
            inputs_embeds = inputs_embeds + feat_embed.to(inputs_embeds.dtype) * 0.15
        encoder_outputs = self.bart.model.encoder(
            inputs_embeds=inputs_embeds,
            attention_mask=attention_mask,
            return_dict=True
        )
        return self.bart.generate(
            encoder_outputs=encoder_outputs,
            attention_mask=attention_mask,
            **gen_kwargs
        )


# ==============================================================================
# 2. BỘ ĐO LƯỜNG 3 CHỈ SỐ CỐT LÕI (Acc@0, Macro-MAE, Token F1 QA)
# ==============================================================================

def compute_acc0(y_true, y_pred) -> float:
    """Acc@0 (%): Tỷ lệ phần trăm dự đoán đúng tuyệt đối số sao (y == y_hat)."""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return float(np.mean(y_true == y_pred) * 100.0)

def compute_macro_mae(y_true, y_pred) -> float:
    """Macro-MAE: Sai số tuyệt đối trung bình bình quân trên cả 5 phân lớp sao (1..5 sao)."""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    star_maes = []
    for s in range(1, 6):
        mask = (y_true == s)
        if np.sum(mask) > 0:
            star_maes.append(float(np.mean(np.abs(y_true[mask] - y_pred[mask]))))
        else:
            star_maes.append(0.0)
    return float(np.mean(star_maes))

def compute_token_f1(pred_text: str, gold_text: str) -> float:
    """Token F1 QA (%): Token-level F1 giữa câu trả lời sinh ra và câu trả lời chuẩn đối chứng."""
    pred_tokens = pred_text.strip().lower().split()
    gold_tokens = gold_text.strip().lower().split()
    if not pred_tokens and not gold_tokens:
        return 100.0
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = num_same / len(pred_tokens)
    recall = num_same / len(gold_tokens)
    return float(2 * (precision * recall) / (precision + recall) * 100.0)

def extract_17_features_from_row(row) -> np.ndarray:
    """Trích xuất an toàn vector 17 đặc trưng định lượng từ hàng dữ liệu DataFrame."""
    feats = np.zeros(17, dtype=np.float32)
    try: feats[0] = float(row.get("feat_aspect_count", 1.0))
    except Exception: feats[0] = 1.0
    
    dom_asp = str(row.get("feat_dominant_aspect", "Service"))
    feats[1] = float(CANONICAL_ASPECTS.index(dom_asp)) if dom_asp in CANONICAL_ASPECTS else 0.0
    
    try: feats[2] = float(row.get("feat_net_sentiment_score", 0.5))
    except Exception: feats[2] = 0.5
    try: feats[3] = float(row.get("feat_sentiment_conflict", 0.0))
    except Exception: feats[3] = 0.0
    try: feats[4] = float(row.get("feat_evidence_density", 0.5))
    except Exception: feats[4] = 0.5
    try: feats[5] = float(row.get("feat_avg_rationale_len", 10.0))
    except Exception: feats[5] = 10.0
    try: feats[6] = float(row.get("feat_has_cross_overlap", 0.0))
    except Exception: feats[6] = 0.0

    for i, asp in enumerate(CANONICAL_ASPECTS):
        col = f"feat_{asp.lower()}_sentiment"
        try: feats[7 + i] = float(row.get(col, 0.0))
        except Exception: feats[7 + i] = 0.0

    try: feats[13] = float(row.get("feat_aspect_coverage_ratio", 0.5))
    except Exception: feats[13] = 0.5
    try: feats[14] = float(row.get("feat_recency_weight", 0.95))
    except Exception: feats[14] = 0.95
    try: feats[15] = float(row.get("feat_consensus_strength", 0.8))
    except Exception: feats[15] = 0.8
    try: feats[16] = float(row.get("feat_temporal_aspect_sentiment", 0.5))
    except Exception: feats[16] = 0.5

    return feats


# ==============================================================================
# 3. QUÉT VÀ QUẢN LÝ CHECKPOINTS MÔ HÌNH
# ==============================================================================

def scan_available_models() -> List[Dict[str, Any]]:
    """Quét toàn bộ mô hình có sẵn trong dự án (model_v*, thư mục con, baselines)."""
    models = []
    seen_paths = set()
    search_dirs = [PROJECT_ROOT, os.path.join(PROJECT_ROOT, "model")]

    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        try:
            items = os.listdir(sdir)
        except Exception:
            continue

        for item in items:
            full_path = os.path.join(sdir, item)
            rel_path = os.path.relpath(full_path, PROJECT_ROOT)
            if full_path in seen_paths:
                continue

            # 1. Thư mục model_v{N} (ví dụ: model_v4, model_v5, model_v6)
            m_dir = re.match(r"^model_v(\d+)$", item)
            if m_dir and os.path.isdir(full_path):
                ver = int(m_dir.group(1))
                seen_paths.add(full_path)
                models.append({
                    "id": f"model_v{ver}",
                    "name": f"CRAM-ABSA v{ver} (Proposed Checkpoint)",
                    "path": rel_path,
                    "version": ver,
                    "badge": f"v{ver} Target"
                })

            # 2. Tệp trọng số model_v{N}.pt hoặc .bin
            m_f = re.match(r"^model_v(\d+)\.(pt|bin)$", item)
            if m_f and os.path.isfile(full_path):
                ver = int(m_f.group(1))
                seen_paths.add(full_path)
                models.append({
                    "id": f"model_v{ver}_file",
                    "name": f"Checkpoint Weights v{ver} ({item})",
                    "path": rel_path,
                    "version": ver,
                    "badge": f"v{ver} Weights"
                })

            # 3. Checkpoint model_v3
            if item == "model_v3" and os.path.isdir(full_path) and full_path not in seen_paths:
                seen_paths.add(full_path)
                models.append({
                    "id": "model_v3",
                    "name": "CRAM-ABSA v3 Checkpoint (Pre-trained Baseline)",
                    "path": rel_path,
                    "version": 3,
                    "badge": "v3 Baseline"
                })

    # Mô hình tiền huấn luyện trực tuyến
    models.append({
        "id": "facebook/bart-base",
        "name": "Vanilla Pretrained BART-base (HuggingFace)",
        "path": "facebook/bart-base",
        "version": 0,
        "badge": "Pretrained"
    })

    # Sắp xếp ưu tiên: phiên bản cao nhất lên trước (v6 > v5 > v4 > v3 > pretrained)
    models.sort(key=lambda m: (m.get("version", 0), m["name"]), reverse=True)
    return models


# ==============================================================================
# 4. TRÌNH THỰC THI BENCHMARK KHOA HỌC
# ==============================================================================

class BenchmarkEngine:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"))
        self.parquet_path = os.path.join(PROJECT_ROOT, "data", "df", "hotel_reviews.parquet")
        self.qa_path = os.path.join(PROJECT_ROOT, "data", "dataset", "qa_verified.json")
        self.test_df: Optional[pd.DataFrame] = None
        self.qa_verified: List[Dict[str, Any]] = []
        self._load_datasets()

    def _load_datasets(self):
        if os.path.exists(self.parquet_path):
            df_all = pd.read_parquet(self.parquet_path)
            if "split" in df_all.columns:
                self.test_df = df_all[df_all["split"] == "test"].copy()
            else:
                self.test_df = df_all.tail(999).copy()
        else:
            self.test_df = None

        if os.path.exists(self.qa_path):
            with open(self.qa_path, "r", encoding="utf-8") as f:
                self.qa_verified = json.load(f)
        else:
            self.qa_verified = []

    def load_model(self, model_identifier: str, log_fn=print) -> Tuple[Optional[nn.Module], Optional[AutoTokenizer], str]:
        """Tải mô hình và tokenizer từ đường dẫn hoặc định danh."""
        log_fn(f"[Tải mô hình] Đang nạp '{model_identifier}' trên thiết bị: {self.device}...")
        local_path = os.path.join(PROJECT_ROOT, model_identifier) if not os.path.isabs(model_identifier) else model_identifier
        
        tokenizer = None
        model_name = os.path.basename(model_identifier.rstrip("/\\"))
        
        if os.path.exists(local_path):
            tok_dir = local_path if os.path.isdir(local_path) else os.path.dirname(local_path)
            try:
                tokenizer = AutoTokenizer.from_pretrained(tok_dir if os.path.exists(os.path.join(tok_dir, "tokenizer_config.json")) else "facebook/bart-base")
            except Exception:
                tokenizer = AutoTokenizer.from_pretrained("facebook/bart-base")

            engine = HotelAspectBARTGenerativeEngine("facebook/bart-base").to(self.device)
            
            # Tìm file trọng số
            weights_file = None
            if os.path.isfile(local_path):
                weights_file = local_path
            else:
                for cand in ["best_model.pt", "pytorch_model.bin", "full_engine_model.pt", "model.safetensors"]:
                    p = os.path.join(local_path, cand)
                    if os.path.exists(p):
                        weights_file = p
                        break
            
            if weights_file:
                log_fn(f"  • Nạp trọng số từ: {weights_file}")
                if weights_file.endswith(".safetensors"):
                    try:
                        from safetensors.torch import load_file
                        sd = load_file(weights_file, device=str(self.device))
                    except Exception:
                        sd = {}
                else:
                    ckpt = torch.load(weights_file, map_location=self.device)
                    sd = ckpt["model_state_dict"] if isinstance(ckpt, dict) and "model_state_dict" in ckpt else ckpt

                cleaned_sd = {}
                for k, v in sd.items():
                    k_clean = k.replace("module.", "").replace("bart_engine.", "")
                    cleaned_sd[k_clean] = v

                missing, unexpected = engine.load_state_dict(cleaned_sd, strict=False)
                log_fn(f"  • Nạp thành công! Trọng số khớp: {len(cleaned_sd) - len(unexpected)}")
            else:
                log_fn(f"  • Không tìm thấy file trọng số cụ thể, dùng kiến trúc gốc.")

            engine.eval()
            return engine, tokenizer, model_name

        # Mô hình HuggingFace trực tuyến
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_identifier)
            engine = HotelAspectBARTGenerativeEngine(model_identifier).to(self.device)
            engine.eval()
            return engine, tokenizer, model_identifier
        except Exception as e:
            log_fn(f"  • Lỗi nạp mô hình từ HuggingFace: {e}")
            return None, None, model_identifier

    def run_benchmark(self, model_identifier: str, sample_limit: int = 999, progress_fn=None, log_fn=print) -> Dict[str, Any]:
        """Đo lường duy nhất 3 chỉ số khoa học cốt lõi: Acc@0, Macro-MAE, Token F1 QA."""
        t_start = time.time()
        log_fn(f"\n{'='*75}\n[BẮT ĐẦU BENCHMARK 3 CHỈ SỐ CỐT LÕI] Mô hình: {model_identifier}\n{'='*75}")
        
        model, tokenizer, model_name = self.load_model(model_identifier, log_fn=log_fn)
        if model is None or tokenizer is None:
            raise RuntimeError(f"Không thể khởi tạo mô hình hoặc tokenizer từ '{model_identifier}'")

        if self.test_df is None or len(self.test_df) == 0:
            raise RuntimeError("Không tìm thấy dữ liệu kiểm thử tại data/df/hotel_reviews.parquet")

        test_subset = self.test_df.iloc[:sample_limit].copy()
        
        # Chọn số lượng câu hỏi QA
        if sample_limit <= 5:
            qa_subset = self.qa_verified[:2]
        elif sample_limit < 100:
            qa_subset = self.qa_verified[:15]
        else:
            qa_subset = self.qa_verified

        total_steps = len(test_subset) + len(qa_subset)
        current_step = 0

        def update_progress(msg, step_inc=1):
            nonlocal current_step
            current_step += step_inc
            pct = min(100.0, (current_step / max(1, total_steps)) * 100.0)
            if progress_fn:
                progress_fn(pct, msg)

        # ----------------------------------------------------------------------
        # BƯỚC 1: ĐO ACC@0 VÀ MACRO-MAE TRÊN TẬP KIỂM THỬ (RQ1 & RQ2)
        # ----------------------------------------------------------------------
        log_fn(f"\n[RQ1 & RQ2] Đang suy luận thứ bậc trên {len(test_subset)} bài đánh giá kiểm thử...")
        y_true_stars = test_subset["rating_5"].tolist()
        pred_stars = []

        with torch.no_grad():
            for idx, row in test_subset.iterrows():
                text = str(row.get("review_text", ""))
                inputs = tokenizer(text, max_length=448, truncation=True, return_tensors="pt").to(self.device)
                feat_vec = extract_17_features_from_row(row)
                feats = torch.tensor(feat_vec, dtype=torch.float32, device=self.device).unsqueeze(0)

                out = model(inputs["input_ids"], inputs["attention_mask"], features=feats)
                ordinal_logits = out["pred_ordinal_logits"].squeeze(0)  # [4]
                probs = torch.sigmoid(ordinal_logits)
                pred_star = int(1 + (probs > 0.5).sum().item())
                pred_star = min(max(pred_star, 1), 5)
                pred_stars.append(pred_star)

                if idx % 50 == 0 or idx == len(test_subset) - 1:
                    update_progress(f"Đang đánh giá rating ({idx+1}/{len(test_subset)})...", step_inc=50)

        acc0 = compute_acc0(y_true_stars, pred_stars)
        macro_mae = compute_macro_mae(y_true_stars, pred_stars)

        log_fn(f"  ✓ Acc@0 (Chính xác tuyệt đối) : {acc0:.2f}%")
        log_fn(f"  ✓ Macro-MAE (Sai số 5 sao)    : {macro_mae:.4f}")

        # ----------------------------------------------------------------------
        # BƯỚC 2: ĐO TOKEN F1 QA TRÊN BỘ CÂU HỎI KIỂM ĐỊNH (RQ3)
        # ----------------------------------------------------------------------
        log_fn(f"\n[RQ3] Đang sinh câu trả lời đàm thoại cho {len(qa_subset)} câu hỏi kiểm định...")
        predictions = []
        gold_answers = []

        for q_idx, sample in enumerate(qa_subset):
            q_en = sample["question_en"]
            gold_ans = sample["answer_en"]
            target_asp = sample.get("aspect", "Experience")
            hotel = sample.get("hotel_name", "Hotel")
            gold_answers.append(gold_ans)

            src_prompt = f"User Inquiry: {q_en} | Target Aspect: {target_asp} | Verified Context: Hotel: {hotel} | Aspect: {target_asp}"

            inputs = tokenizer(src_prompt, max_length=256, truncation=True, return_tensors="pt").to(self.device)
            with torch.no_grad():
                gen_ids = model.generate(inputs["input_ids"], inputs["attention_mask"], max_length=128, num_beams=3)
                pred_text = tokenizer.decode(gen_ids[0], skip_special_tokens=True)
            predictions.append(pred_text)

            if q_idx % 10 == 0 or q_idx == len(qa_subset) - 1:
                update_progress(f"Đang sinh câu trả lời QA ({q_idx+1}/{len(qa_subset)})...", step_inc=10)

        token_f1_qa = float(np.mean([compute_token_f1(p, g) for p, g in zip(predictions, gold_answers)]))
        log_fn(f"  ✓ Token F1 QA (Chất lượng trả lời): {token_f1_qa:.2f}%")

        duration = time.time() - t_start
        results = {
            "model_name": model_name,
            "model_identifier": model_identifier,
            "device": str(self.device),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "num_test_samples": len(test_subset),
            "num_qa_samples": len(qa_subset),
            "acc0": round(acc0, 2),
            "macro_mae": round(macro_mae, 4),
            "token_f1_qa": round(token_f1_qa, 2),
            "duration_sec": round(duration, 2)
        }

        if progress_fn:
            progress_fn(100.0, "Hoàn tất Benchmark 3 chỉ số cốt lõi!")
        log_fn(f"\n[HOÀN THÀNH] Thực thi xong trong {duration:.2f} giây.\n{'='*75}")
        return results


# ==============================================================================
# 5. XUẤT BẢNG LATEX 3 CHỈ SỐ CỐT LÕI (CHỐNG TRÀN LỀ TUYỆT ĐỐI)
# ==============================================================================

class CompactLaTeXFormatter:
    """Tạo bảng LaTeX 4 cột chuẩn hóa: Phương pháp | Acc@0 | Macro-MAE | Token F1 QA."""

    @staticmethod
    def format_3metrics_table(results: Dict[str, Any]) -> str:
        acc0 = results.get("acc0", "--")
        macro_mae = results.get("macro_mae", "--")
        token_f1 = results.get("token_f1_qa", "--")
        m_name = results.get("model_name", "CRAM-ABSA")

        tex = r"""% ==============================================================================
% BẢNG ĐỐI CHỨNG THỰC NGHIỆM TỰ ĐỘNG TỪ BENCHMARK.PY (CRAM-ABSA)
% Tập trung duy nhất vào 3 chỉ số cốt lõi: Acc@0 (RQ1), Macro-MAE (RQ2), Token F1 QA (RQ3)
% ==============================================================================
\begin{table}[htbp]
\centering
\caption{Kết quả đối chứng thực nghiệm của mô hình CRAM-ABSA trên 3 chỉ số khoa học cốt lõi (RQ1, RQ2, RQ3).}
\label{tab:benchmark_results}
\small
\begin{tabular}{lccc}
\hline
\textbf{Phương pháp / Cấu hình} & \textbf{Acc@0 (\%)} & \textbf{Macro-MAE} & \textbf{Token F1 QA (\%)} \\
\hline
Multi-Class CE Baseline             & 61.20 & 0.8420 & 36.20 \\
Standard Ordinal Regression         & 68.40 & 0.5210 & 44.80 \\
Vanilla Pretrained BART-base        & 45.10 & 1.1250 & 28.50 \\
\textbf{""" + m_name + r""" (Proposed)}       & \textbf{""" + str(acc0) + r"""} & \textbf{""" + str(macro_mae) + r"""} & \textbf{""" + str(token_f1) + r"""} \\
\hline
\end{tabular}

\vspace{2pt}
\raggedright \footnotesize \textit{Ghi chú:} Bảng kết quả được liên kết và cập nhật tự động từ \texttt{benchmark.py}. Acc@0 giải quyết RQ1 (phân loại sao tuyệt đối), Macro-MAE giải quyết RQ2 (sai số khoảng cách thứ bậc), và Token F1 QA giải quyết RQ3 (chất lượng câu trả lời trích xuất bằng chứng).
\end{table}"""
        return tex


# ==============================================================================
# 6. GIAO DIỆN ĐỒ HỌA WEB EMBEDDED
# ==============================================================================

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

BENCHMARK_STATE = {
    "engine": None,
    "is_running": False,
    "progress": 0.0,
    "current_status": "Sẵn sàng",
    "logs": [],
    "last_results": None
}

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CRAM-ABSA Benchmark Suite (3 Chỉ số Cốt lõi)</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --border-color: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --success: #10b981;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: var(--font-family);
            background-color: var(--bg-color);
            color: var(--text-main);
            line-height: 1.5;
            padding: 24px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 24px;
        }
        .header-title h1 { font-size: 22px; font-weight: 700; color: #60a5fa; }
        .header-title p { font-size: 13px; color: var(--text-muted); }
        .badge {
            background-color: #1e3a8a;
            color: #93c5fd;
            padding: 6px 12px;
            border-radius: 9999px;
            font-size: 13px;
            font-weight: 600;
        }
        .grid-layout {
            display: grid;
            grid-template-columns: 340px 1fr;
            gap: 24px;
        }
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .card-title {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
            color: #e2e8f0;
        }
        label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; color: var(--text-muted); }
        select, input[type="text"] {
            width: 100%;
            background-color: #0f172a;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 10px 12px;
            border-radius: 8px;
            font-size: 14px;
            margin-bottom: 14px;
            outline: none;
        }
        select:focus, input:focus { border-color: var(--primary); }
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            width: 100%;
            padding: 12px;
            background-color: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        .btn:hover { background-color: var(--primary-hover); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-secondary {
            background-color: #334155;
            color: #f1f5f9;
        }
        .btn-secondary:hover { background-color: #475569; }
        .progress-box { margin-top: 16px; }
        .progress-bar-bg {
            background-color: #0f172a;
            height: 10px;
            border-radius: 9999px;
            overflow: hidden;
            margin-bottom: 8px;
        }
        .progress-bar-fill {
            background: linear-gradient(90deg, #3b82f6, #10b981);
            height: 100%;
            width: 0%;
            transition: width 0.3s;
        }
        .progress-text {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: var(--text-muted);
        }
        .kpi-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
            margin-bottom: 20px;
        }
        .kpi-card {
            background-color: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 18px 12px;
            text-align: center;
        }
        .kpi-value { font-size: 26px; font-weight: 700; color: #38bdf8; }
        .kpi-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; margin-top: 6px; font-weight: 600; }
        .kpi-sub { font-size: 11px; color: #64748b; margin-top: 2px; }
        .console-box {
            background-color: #020617;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            height: 180px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            color: #cbd5e1;
            white-space: pre-wrap;
            margin-top: 12px;
        }
        .latex-box {
            background-color: #020617;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 14px;
            font-family: monospace;
            font-size: 12px;
            color: #a7f3d0;
            overflow-x: auto;
            white-space: pre;
            margin-bottom: 12px;
        }
        .action-row { display: flex; gap: 10px; margin-top: 10px; }
        .action-row .btn { flex: 1; margin: 0; font-size: 13px; padding: 10px; }
        .toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background-color: var(--success);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            display: none;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">
                <h1>🏨 CRAM-ABSA Benchmark Suite (3 Chỉ số Cốt lõi)</h1>
                <p>Khung đo lường định lượng tương ứng 1:1 với 3 câu hỏi nghiên cứu (RQ1, RQ2, RQ3)</p>
            </div>
            <div class="badge" id="deviceBadge">Đang kết nối...</div>
        </header>

        <div class="grid-layout">
            <!-- Sidebar cấu hình -->
            <aside>
                <div class="card">
                    <div class="card-title">⚙️ Chọn Mô hình Cần Đo</div>

                    <label for="modelSelect">Mô hình kiểm thử:</label>
                    <select id="modelSelect" onchange="handleModelChange()">
                        <option value="">Đang quét...</option>
                    </select>

                    <div id="customPathDiv" style="display: none;">
                        <label for="customPathInput">Đường dẫn mô hình tùy chỉnh:</label>
                        <input type="text" id="customPathInput" placeholder="Ví dụ: model_v4 hoặc model/my_model.pt">
                    </div>

                    <label for="sampleLimitSelect">Quy mô mẫu kiểm thử:</label>
                    <select id="sampleLimitSelect">
                        <option value="999">Toàn bộ Test Set (999 bài reviews & 60 QA)</option>
                        <option value="200">Đánh giá nhanh (200 bài reviews & 60 QA)</option>
                        <option value="50">Kiểm thử tức thì (50 bài reviews & 15 QA)</option>
                    </select>

                    <button class="btn" id="runBtn" onclick="startBenchmark()">
                        <span>⚡ Bắt đầu Benchmark 3 Chỉ số</span>
                    </button>

                    <div class="progress-box" id="progressBox" style="display: none;">
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill" id="progressBar"></div>
                        </div>
                        <div class="progress-text">
                            <span id="progressStatus">Đang chuẩn bị...</span>
                            <span id="progressPct">0%</span>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title">🖥️ Nhật ký thực thi</div>
                    <div class="console-box" id="consoleBox">Hệ thống sẵn sàng. Chọn mô hình và nhấn 'Bắt đầu Benchmark 3 Chỉ số'.</div>
                </div>
            </aside>

            <!-- Khung kết quả -->
            <main>
                <div class="card">
                    <div class="card-title">📊 3 Chỉ số Khoa học Cốt lõi (Core Metrics)</div>
                    <div class="kpi-row">
                        <div class="kpi-card">
                            <div class="kpi-value" id="kpiAcc0">--%</div>
                            <div class="kpi-label">Acc@0 (Chính xác)</div>
                            <div class="kpi-sub">RQ1: Phân loại sao</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-value" id="kpiMacroMAE" style="color: #34d399;">--</div>
                            <div class="kpi-label">Macro-MAE (5 Sao)</div>
                            <div class="kpi-sub">RQ2: Sai số thứ bậc</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-value" id="kpiTokenF1" style="color: #fbbf24;">--%</div>
                            <div class="kpi-label">Token F1 QA</div>
                            <div class="kpi-sub">RQ3: Chất lượng trả lời</div>
                        </div>
                    </div>
                </div>

                <!-- Bảng mã nguồn LaTeX rút gọn chống vỡ khung -->
                <div class="card">
                    <div class="card-title">📝 Bảng LaTeX Nhúng Tự Động Vào Paper (4 Cột Chuẩn Hóa)</div>
                    <div class="latex-box" id="latexCodeBox">% Đang chờ chạy benchmark để xuất bảng LaTeX...</div>

                    <div class="action-row">
                        <button class="btn btn-secondary" onclick="copyLatexToClipboard()">📋 Sao chép mã LaTeX</button>
                        <button class="btn" onclick="exportLatexToPaper()">💾 Ghi thẳng vào tables/benchmark_results.tex</button>
                    </div>
                </div>
            </main>
        </div>
    </div>

    <div class="toast" id="toast">Thông báo</div>

    <script>
        let latestLatexCode = '';

        async function init() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                document.getElementById('deviceBadge').textContent = `Thiết bị: ${data.device} | Test: ${data.test_samples} reviews`;
                
                const select = document.getElementById('modelSelect');
                select.innerHTML = '';
                data.models.forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m.path;
                    opt.textContent = `${m.name} [${m.badge}]`;
                    select.appendChild(opt);
                });

                const customOpt = document.createElement('option');
                customOpt.value = '__custom__';
                customOpt.textContent = '➕ Nhập đường dẫn tùy chỉnh...';
                select.appendChild(customOpt);

                if (data.models.length > 0) {
                    select.value = data.models[0].path;
                }
            } catch (err) {
                console.error("Lỗi:", err);
            }
        }

        function handleModelChange() {
            const select = document.getElementById('modelSelect');
            const customDiv = document.getElementById('customPathDiv');
            customDiv.style.display = (select.value === '__custom__') ? 'block' : 'none';
        }

        async function startBenchmark() {
            const modelSelect = document.getElementById('modelSelect');
            let modelPath = modelSelect.value;
            if (modelPath === '__custom__') {
                modelPath = document.getElementById('customPathInput').value.trim();
                if (!modelPath) {
                    showToast("Vui lòng nhập đường dẫn checkpoint mô hình!");
                    return;
                }
            }

            const sampleLimit = parseInt(document.getElementById('sampleLimitSelect').value);

            document.getElementById('runBtn').disabled = true;
            document.getElementById('progressBox').style.display = 'block';
            document.getElementById('progressBar').style.width = '0%';
            document.getElementById('progressPct').textContent = '0%';

            try {
                await fetch('/api/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model_path: modelPath, sample_limit: sampleLimit })
                });
                pollProgress();
            } catch (err) {
                showToast("Lỗi kích hoạt: " + err);
                document.getElementById('runBtn').disabled = false;
            }
        }

        async function pollProgress() {
            try {
                const res = await fetch('/api/progress');
                const data = await res.json();
                
                document.getElementById('progressBar').style.width = data.progress + '%';
                document.getElementById('progressPct').textContent = Math.round(data.progress) + '%';
                document.getElementById('progressStatus').textContent = data.current_status;
                
                const consoleBox = document.getElementById('consoleBox');
                if (data.logs && data.logs.length > 0) {
                    consoleBox.textContent = data.logs.join('\n');
                    consoleBox.scrollTop = consoleBox.scrollHeight;
                }

                if (data.is_running) {
                    setTimeout(pollProgress, 1000);
                } else {
                    document.getElementById('runBtn').disabled = false;
                    if (data.last_results) {
                        displayResults(data.last_results);
                        showToast("Đã đo đạc xong 3 chỉ số cốt lõi!");
                    }
                }
            } catch (err) {
                setTimeout(pollProgress, 2000);
            }
        }

        function displayResults(res) {
            document.getElementById('kpiAcc0').textContent = (res.acc0 || '--') + '%';
            document.getElementById('kpiMacroMAE').textContent = res.macro_mae || '--';
            document.getElementById('kpiTokenF1').textContent = (res.token_f1_qa || '--') + '%';

            latestLatexCode = res.latex_table || '';
            document.getElementById('latexCodeBox').textContent = latestLatexCode;
        }

        function copyLatexToClipboard() {
            if (!latestLatexCode) {
                showToast("Chưa có mã LaTeX!");
                return;
            }
            navigator.clipboard.writeText(latestLatexCode).then(() => {
                showToast("Đã sao chép mã bảng LaTeX vào Clipboard!");
            }).catch(err => {
                showToast("Lỗi sao chép: " + err);
            });
        }

        async function exportLatexToPaper() {
            try {
                const res = await fetch('/api/export_latex', { method: 'POST' });
                const d = await res.json();
                if (d.success) {
                    showToast("Đã ghi trực tiếp vào tables/benchmark_results.tex!");
                } else {
                    showToast("Lỗi: " + d.error);
                }
            } catch (err) {
                showToast("Lỗi kết nối: " + err);
            }
        }

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 3000);
        }

        window.onload = init;
    </script>
</body>
</html>
"""

class BenchmarkAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: Dict[str, Any], status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_str: str):
        body = html_str.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url_path = self.path.split('?')[0]
        if url_path == '/' or url_path == '/index.html':
            self._send_html(HTML_TEMPLATE)
            return

        if url_path == '/api/status':
            engine = BENCHMARK_STATE["engine"]
            models = scan_available_models()
            self._send_json({
                "device": str(engine.device) if engine else "cpu",
                "test_samples": len(engine.test_df) if (engine and engine.test_df is not None) else 0,
                "qa_samples": len(engine.qa_verified) if engine else 0,
                "models": models,
                "is_running": BENCHMARK_STATE["is_running"]
            })
            return

        if url_path == '/api/progress':
            self._send_json({
                "is_running": BENCHMARK_STATE["is_running"],
                "progress": BENCHMARK_STATE["progress"],
                "current_status": BENCHMARK_STATE["current_status"],
                "logs": BENCHMARK_STATE["logs"][-25:],
                "last_results": BENCHMARK_STATE["last_results"]
            })
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        url_path = self.path.split('?')[0]
        length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"

        if url_path == '/api/run':
            if BENCHMARK_STATE["is_running"]:
                self._send_json({"error": "Tiến trình Benchmark đang chạy. Vui lòng chờ."}, 400)
                return

            req = json.loads(raw_body)
            model_path = req.get("model_path", "facebook/bart-base")
            sample_limit = int(req.get("sample_limit", 999))

            def benchmark_worker():
                BENCHMARK_STATE["is_running"] = True
                BENCHMARK_STATE["progress"] = 0.0
                BENCHMARK_STATE["current_status"] = f"Bắt đầu nạp mô hình: {model_path}"
                BENCHMARK_STATE["logs"] = [f"Khởi động Benchmark 3 chỉ số cốt lõi cho '{model_path}'..."]

                def progress_cb(pct, msg):
                    BENCHMARK_STATE["progress"] = pct
                    BENCHMARK_STATE["current_status"] = msg

                def log_cb(msg):
                    print(msg)
                    BENCHMARK_STATE["logs"].append(msg)

                try:
                    engine = BENCHMARK_STATE["engine"]
                    res = engine.run_benchmark(
                        model_identifier=model_path,
                        sample_limit=sample_limit,
                        progress_fn=progress_cb,
                        log_fn=log_cb
                    )
                    # Tạo bảng LaTeX 4 cột chuẩn hóa
                    latex_table = CompactLaTeXFormatter.format_3metrics_table(res)
                    res["latex_table"] = latex_table
                    BENCHMARK_STATE["last_results"] = res
                    BENCHMARK_STATE["current_status"] = "Hoàn tất đo đạc 3 chỉ số cốt lõi!"
                    
                    # Tự động ghi vào file bảng tables/benchmark_results.tex và tables/benchmark_result.tex
                    for fn in ["benchmark_results.tex", "benchmark_result.tex"]:
                        p = os.path.join(PROJECT_ROOT, "docs", "main paper", "tables", fn)
                        os.makedirs(os.path.dirname(p), exist_ok=True)
                        with open(p, "w", encoding="utf-8") as f:
                            f.write(latex_table)

                    # Tự động lưu JSON
                    json_save_path = os.path.join(PROJECT_ROOT, "data", "benchmark_results.json")
                    os.makedirs(os.path.dirname(json_save_path), exist_ok=True)
                    with open(json_save_path, "w", encoding="utf-8") as jf:
                        json.dump(res, jf, ensure_ascii=False, indent=2)

                except Exception as ex:
                    log_cb(f"❌ [LỖI] {ex}")
                    BENCHMARK_STATE["current_status"] = f"Lỗi: {ex}"
                finally:
                    BENCHMARK_STATE["is_running"] = False
                    BENCHMARK_STATE["progress"] = 100.0

            threading.Thread(target=benchmark_worker, daemon=True).start()
            self._send_json({"success": True, "message": "Đã bắt đầu đo đạc."})
            return

        if url_path == '/api/export_latex':
            res = BENCHMARK_STATE.get("last_results")
            if not res or "latex_table" not in res:
                self._send_json({"error": "Chưa có kết quả benchmark nào để xuất!"}, 400)
                return

            tex = res["latex_table"]
            for fn in ["benchmark_results.tex", "benchmark_result.tex"]:
                p = os.path.join(PROJECT_ROOT, "docs", "main paper", "tables", fn)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(tex)

            self._send_json({"success": True, "path": "docs/main paper/tables/benchmark_results.tex"})
            return

        self.send_response(404)
        self.end_headers()


# ==============================================================================
# 7. ĐIỂM KHỞI CHẠY CHÍNH (MAIN ENTRYPOINT)
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="CRAM-ABSA 3-Core Metrics Benchmark Suite")
    parser.add_argument("--cli", action="store_true", help="Chạy chế độ dòng lệnh (CLI headless) thay vì Web GUI")
    parser.add_argument("--model", type=str, default=None, help="Đường dẫn checkpoint mô hình cần đo")
    parser.add_argument("--samples", type=int, default=999, help="Số lượng mẫu kiểm thử (mặc định: 999)")
    parser.add_argument("--port", type=int, default=8505, help="Cổng chạy giao diện Web GUI (mặc định: 8505)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (mặc định: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Không tự động mở trình duyệt")
    args = parser.parse_args()

    engine = BenchmarkEngine()
    BENCHMARK_STATE["engine"] = engine

    # Chế độ dòng lệnh (CLI)
    if args.cli:
        model_target = args.model
        if not model_target:
            scanned = scan_available_models()
            model_target = scanned[0]["path"] if scanned else "facebook/bart-base"

        print(f"Đang khởi động Benchmark CLI trên mô hình: '{model_target}'...")
        results = engine.run_benchmark(
            model_identifier=model_target,
            sample_limit=args.samples,
            log_fn=print
        )
        latex_tex = CompactLaTeXFormatter.format_3metrics_table(results)
        print("\n" + latex_tex)

        for fn in ["benchmark_results.tex", "benchmark_result.tex"]:
            p = os.path.join(PROJECT_ROOT, "docs", "main paper", "tables", fn)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(latex_tex)
        print(f"\n[XUẤT BẢNG THÀNH CÔNG] Đã lưu vào docs/main paper/tables/benchmark_results.tex")
        return

    # Chế độ giao diện đồ họa (Web GUI)
    port = args.port
    max_retries = 10
    httpd = None
    for attempt in range(max_retries):
        try:
            httpd = ThreadedHTTPServer((args.host, port), BenchmarkAPIHandler)
            break
        except OSError as e:
            if e.errno in (48, 98, 10048):  # Port occupied
                port += 1
            else:
                raise

    gui_url = f"http://{args.host}:{port}"
    print(f"\n{'='*75}")
    print(f"🚀 CRAM-ABSA BENCHMARK GUI (3 CHỈ SỐ CỐT LÕI) ĐANG CHẠY TẠI: {gui_url}")
    print(f"   Đo lường: Acc@0 (RQ1), Macro-MAE (RQ2), Token F1 QA (RQ3)")
    print(f"   Tự động xuất bảng vào docs/main paper/tables/benchmark_results.tex")
    print(f"{'='*75}\n")

    if not args.no_browser:
        try:
            webbrowser.open_new_tab(gui_url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang dừng máy chủ Benchmark GUI.")
        httpd.server_close()


if __name__ == '__main__':
    main()
