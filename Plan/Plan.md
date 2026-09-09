# 📄 KẾ HOẠCH THỰC HIỆN STEP-BY-STEP PAPER SỐ 2: CRAM-ABSA[cite: 1]

## ⚠️ Nền tảng & Cảnh báo Quan Trọng
*   **Dữ liệu hiện có**: Gold Set gồm 9.826 reviews của 2.601 khách sạn[cite: 1]. Dữ liệu chia Hotel-Disjoint 70/15/15 với 0% hotel overlap[cite: 1].
*   **Mô hình hiện tại**: CRAM-ABSA sử dụng DeBERTa-v3-base kết hợp Focal Loss, Attention Pooling, Continuous Rating Head và Conflict Attenuation Gating[cite: 1].
*   **Vấn đề cần giải quyết**: Khoảng cách quá lớn giữa Overlap Triplet F1 (78,19%) và Exact Triplet F1 (6,65%)[cite: 1]. Các F1 theo aspect hiện đang khá thấp[cite: 1]. 
*   **Hành động cốt lõi**: Chỉ bước sang viết Results sau khi evaluation script, span matching, label mapping và subset/aspect metrics đã được audit độc lập[cite: 1].

---

## 🎯 1. Mục tiêu, Định vị & Câu chuyện Khoa học
*   **Trọng tâm**: Trả lời câu hỏi kết hợp hiểu biết aspect/opinion với global rating như thế nào[cite: 1], và cách xử lý review chứa nhiều polarity hoặc đánh giá mâu thuẫn[cite: 1].
*   **Tên đề xuất (Đã chốt)**: Joint Fine-Grained Opinion Extraction and Overall Rating Prediction from Real-World Hotel Reviews[cite: 1].

| Research Question (RQ) / Giả thuyết (H) | Bằng chứng cần có |
| :--- | :--- |
| **RQ1**: CRAM-ABSA có cải thiện joint ABSA + rating prediction so với baseline không?[cite: 1] | Main comparison table, 3-5 seeds, significance[cite: 1]. |
| **RQ2**: Continuous Rating Head giúp biểu diễn toàn cục hay chỉ cải thiện rating?[cite: 1] | Ablation -Rating Head; task trade-off analysis[cite: 1]. |
| **RQ3**: Conflict Attenuation Gating có giúp các review mixed/conflicting sentiment?[cite: 1] | Gold-defined conflict subset; Full vs -Gate[cite: 1]. |
| **RQ4**: Tại sao Overlap F1 cao nhưng Exact F1 thấp?[cite: 1] | Metric audit, error decomposition, relaxed IoU curve[cite: 1]. |
| **RQ5**: Hotel-Disjoint evaluation thay đổi hiệu năng ra sao so với random split?[cite: 1] | Leakage/generalization experiment[cite: 1]. |
| **H1**: Full CRAM-ABSA tốt hơn các biến thể bỏ từng thành phần[cite: 1]. | Ablation table[cite: 1]. |
| **H2**: Lợi ích Conflict Gate lớn hơn trên conflict subset so với consistent subset[cite: 1]. | Delta-F1/MAE theo subset[cite: 1]. |
| **H3**: Joint learning không đánh đổi nghiêm trọng extraction lấy rating hoặc ngược lại[cite: 1].| Pareto plot, loss-weight sensitivity[cite: 1]. |

---

## 🚧 2. Các Gate Bắt Buộc Trước Khi Viết Results

| Gate | Tiêu chí đạt | Nếu chưa đạt |
| :--- | :--- | :--- |
| **G0 - Metric integrity**[cite: 1] | Exact/Overlap/aspect/subset metrics audit độc lập; dùng chung 1 script[cite: 1]. | Dừng mọi so sánh SOTA; sửa script và chạy lại[cite: 1]. |
| **G1 - Label integrity**[cite: 1] | Khóa Triplet schema, span boundary, aspect/sentiment, conflict; không data leakage[cite: 1]. | Rà soát annotation guideline và mapping[cite: 1]. |
| **G2 - Fair baselines**[cite: 1] | Chạy 4-6 baseline/variant trên đúng VietHotel-ABSA split, preprocessing, metric[cite: 1]. | Không dùng số literature để claim vượt SOTA[cite: 1]. |
| **G3 - Ablation evidence**[cite: 1] | Bỏ riêng từng module; chạy 3-5 seeds[cite: 1]. | Không claim contribution nếu chưa có ablation[cite: 1]. |
| **G4 - Conflict validity**[cite: 1] | Xác định độc lập conflict subset; đủ sample thống kê[cite: 1]. | Thiết kế lại subset; human check[cite: 1]. |
| **G5 - Statistical reliability**[cite: 1] | Báo cáo mean±std và significance/bootstrap theo hotel[cite: 1]. | Chạy lại seeds/bootstraps trước khi chốt[cite: 1]. |

---

## 🛠️ 3. Kế Hoạch Thực Hiện Step-by-Step

| Bước | Mục tiêu | Đầu ra bắt buộc |
| :--- | :--- | :--- |
| **0. Khóa paper charter**[cite: 1] | Biến hệ thống thành method paper có giả thuyết[cite: 1]. Chốt task chính (ASTE + Rating)[cite: 1]. | Paper charter 1 trang, Traceability matrix[cite: 1]. |
| **1. Audit evaluation script**[cite: 1] | Xử lý triệt để gap giữa Overlap (78,19%) và Exact (6,65%)[cite: 1]. Đóng băng 50-100 review test để đối chiếu[cite: 1]. | evaluation_spec.md, Unit tests, IoU curve, 20 case audit[cite: 1]. |
| **2. Audit nhãn & conflict**[cite: 1] | Kiểm tra mapping[cite: 1]. Định nghĩa subset từ gold labels[cite: 1]. Phân loại lỗi[cite: 1]. | Label table, Confusion matrix, Error taxonomy[cite: 1]. |
| **3. Đóng băng data split**[cite: 1] | Giữ Hotel-Disjoint (0 overlap) làm protocol chính[cite: 1]. Khóa tokenizer/seeds[cite: 1]. | Frozen splits, Preprocessing config, Leakage audit log[cite: 1]. |
| **4. Xây baseline ladder**[cite: 1] | Xây dựng B0 (mean rating) đến B4-B6 (ASTE families chạy lại nội bộ)[cite: 1]. | Baseline matrix, Checkpoint logs, Nháp Main table[cite: 1]. |
| **5. Chạy ablation đầy đủ**[cite: 1] | Bỏ từng phần: Focal Loss, Attention, Rating Head, Conflict Gate (3-5 seeds)[cite: 1]. | Ablation table (mean±std), Per-component delta table[cite: 1]. |
| **6. Kiểm tra MTL objective**[cite: 1] | Đảm bảo kết quả không đến từ task dominance[cite: 1]. Tạo Pareto plot cho loss weights λ[cite: 1]. | Loss formulation, λ sensitivity plot, Task trade-off plot[cite: 1]. |
| **7. Conflict Gate Focus**[cite: 1] | So sánh Full vs -Gate trên conflict/consistent subsets[cite: 1]. Trích xuất case studies[cite: 1]. | Conflict subset table, Gain-by-intensity plot, Qualitative case[cite: 1]. |
| **8. Đánh giá Rating**[cite: 1] | Biến MAE 0,328 / QWK 0,837 thành bằng chứng mạnh[cite: 1]. Thêm per-rating-bin MAE[cite: 1]. | Rating comparison table, Error-by-class figure, Bootstrap CI[cite: 1]. |
| **9. Split Diagnostic**[cite: 1] | So sánh chênh lệch giữa Hotel-Disjoint vs Random Split để chứng minh leakage[cite: 1]. | Split comparison table, Generalization gap figure[cite: 1]. |
| **10. Statistical significance**[cite: 1]| Chạy 3-5 seeds, báo cáo paired bootstrap (resample theo hotel)[cite: 1]. | Seed summary table, Bootstrap CI/significance table[cite: 1]. |
| **11. Error analysis**[cite: 1] | Gán taxonomy 100 lỗi (nhấn mạnh near-miss boundary)[cite: 1]. | Error taxonomy, Near-miss stats, Future hypotheses[cite: 1]. |
| **12. Efficiency & Artifact**[cite: 1] | Đảm bảo khả năng tái tạo từ môi trường sạch[cite: 1]. | Reproducibility checklist, Artifact folder, Efficiency table[cite: 1]. |

---

## 🧪 4. Ma Trận Thực Nghiệm Tối Thiểu

| ID | Thực nghiệm | Model/Variant | Metric Chính |
| :--- | :--- | :--- | :--- |
| **E1**[cite: 1] | Metric audit[cite: 1] | Current CRAM[cite: 1] | Exact/Overlap P-R-F1, IoU curve[cite: 1] |
| **E2**[cite: 1] | Baseline single-task[cite: 1]| Rating-only; Extraction-only[cite: 1]| F1; MAE/QWK[cite: 1] |
| **E3**[cite: 1] | Plain multi-task[cite: 1] | Shared DeBERTa + 2 heads[cite: 1] | F1 + MAE/QWK[cite: 1] |
| **E4**[cite: 1] | Full CRAM[cite: 1] | Full model[cite: 1] | Tất cả metric[cite: 1] |
| **E5**[cite: 1] | Ablation -Gate[cite: 1] | CRAM không Conflict Gate[cite: 1] | Subset F1/MAE[cite: 1] |
| **E6**[cite: 1] | Ablation -Rating Head[cite: 1]| Extraction only / no global head[cite: 1]| F1[cite: 1] |
| **E7**[cite: 1] | Ablation -Focal[cite: 1] | Standard loss[cite: 1] | F1 per aspect[cite: 1] |
| **E8**[cite: 1] | Ablation -Attention[cite: 1]| CLS/mean pooling[cite: 1] | Rating + extraction[cite: 1] |
| **E9**[cite: 1] | Loss-weight sensitivity[cite: 1]| 3-5 λ settings[cite: 1] | Pareto F1 vs MAE[cite: 1] |
| **E10**[cite: 1]| Conflict subset[cite: 1] | Full vs -Gate[cite: 1] | Conflict vs consistent delta[cite: 1]|
| **E11**[cite: 1]| Split diagnostic[cite: 1] | Hotel-disjoint vs random[cite: 1] | Generalization gap[cite: 1] |
| **E12**[cite: 1]| Seeds/bootstrap[cite: 1] | Top 3-4 models[cite: 1] | mean±std, 95% CI[cite: 1] |
| **E13**[cite: 1]| Error analysis[cite: 1] | Full + -Gate[cite: 1] | Error taxonomy[cite: 1] |
| **E14**[cite: 1]| Efficiency[cite: 1] | Top models[cite: 1] | Params/time/latency[cite: 1] |

---

## 📊 5. Blueprint Bảng và Hình cho Manuscript

*   **Bảng chính**: 
    *   Table 1: VietHotel-ABSA stats & split[cite: 1]. 
    *   Table 2: Main comparison[cite: 1]. 
    *   Table 3: Rating comparison[cite: 1]. 
    *   Table 4: Ablation study[cite: 1]. 
    *   Table 5: Conflict vs consistent[cite: 1]. 
    *   Table 6: Per-aspect metrics[cite: 1]. 
    *   Table 7: Error taxonomy[cite: 1].
*   **Hình chính**: 
    *   Fig 1: Architecture[cite: 1]. 
    *   Fig 2: Example hotel review mixed sentiment[cite: 1]. 
    *   Fig 3: IoU threshold vs F1[cite: 1]. 
    *   Fig 4: Conflict intensity vs gain[cite: 1]. 
    *   Fig 5: Pareto plot[cite: 1]. 
    *   Fig 6: Split gap[cite: 1].

---

## 🧭 6. Định hướng Xử lý Tình huống (Decision Rules)

| Tình huống | Phương án hành động |
| :--- | :--- |
| **Exact F1 tăng mạnh sau audit**[cite: 1] | Chạy lại toàn bộ baseline/ablation; dùng exact làm metric chính[cite: 1]. |
| **Exact F1 vẫn ~6-10%, Overlap cao**[cite: 1]| Không claim SOTA ASTE; tập trung cải tiến span decoder/boundary objective hoặc đổi narrative[cite: 1]. |
| **Gate giúp rõ conflict subset**[cite: 1] | Giữ “Conflict-Aware” làm contribution trung tâm[cite: 1]. |
| **Gate không giúp/gây hại**[cite: 1] | Cải tiến gate hoặc hạ contribution; tuyệt đối không cherry-pick[cite: 1]. |
| **Rating MAE tốt nhưng extraction kém**[cite: 1]| Đổi paper sang joint representation/rating focus; điều chỉnh loss/adapters[cite: 1]. |

---

## 📅 7. Lịch Triển Khai 8 Tuần

*   **W1**: STEP 0-2 (Audit metrics, labels, định nghĩa paper charter). Phải khóa metric mới qua W2[cite: 1].
*   **W2**: STEP 3-4 (Đóng băng split, chạy baselines)[cite: 1].
*   **W3**: STEP 5 (Chạy Full CRAM + Ablation chính 1 seed)[cite: 1].
*   **W4**: STEP 6-7 (Tạo Pareto plot, Conflict case analysis)[cite: 1].
*   **W5**: STEP 8-10 (Đánh giá Rating, chạy 3-5 seeds, tính Bootstrap CI)[cite: 1].
*   **W6**: STEP 11-12 (Phân tích lỗi, Reproducibility package)[cite: 1].
*   **W7**: Viết Full draft v1 (Introduction, Method, Results)[cite: 1].
*   **W8**: Chỉnh manuscript, submission-ready v2. Đảm bảo mọi claim đều có evidence[cite: 1].

---

## ✅ 8. Checklist Sẵn Sàng Submission (Definition of Done)
*   **Khoa học**: 1 claim trung tâm rõ ràng (conflict-aware multi-task)[cite: 1].
*   **Đánh giá**: Metric audit hoàn tất; code chung cho mọi model; không trộn protocol[cite: 1].
*   **Thực nghiệm**: Ablation đủ (mean±std)[cite: 1]; Effect size + CI cho conflict subset[cite: 1].
*   **Minh bạch**: Script tính mọi figures/tables tự động; artifact đầy đủ[cite: 1].
*   **Viết lách**: Không dùng từ "SOTA", "conflict-aware" thiếu bằng chứng; mỗi RQ có bảng/hình map trực tiếp[cite: 1].