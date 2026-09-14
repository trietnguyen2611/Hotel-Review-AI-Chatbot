# Tổng Hợp Nghiên Cứu & Baseline Models Phân Tích Đánh Giá Khách Sạn

Tài liệu này hệ thống hóa phương pháp luận, mô hình baseline và kết quả phân tích định lượng từ các nghiên cứu trích xuất dữ liệu đánh giá khách sạn (Booking.com & TripAdvisor).

---

## 1. Nghiên Cứu 1: Khung Phân Tích Hybrid BERTopic – VADER – WMLR

* **Nguồn tham khảo:** [ScienceDirect (PII: S0278431926000216)](https://www.sciencedirect.com/science/article/abs/pii/S0278431926000216)
* **Khung lý thuyết:** **S-O-R (Stimulus - Organism - Response)**

### 1.1. Kiến Trúc Pipeline & Mô Hình
* **BERTopic (Topic Modeling):** 
  * Trích xuất **9 topics** chi tiết từ văn bản đánh giá.
  * Gom cụm và chuẩn hóa thành **5 danh mục/khía cạnh (5 aspects)** chính.
* **VADER (Sentiment Analysis):** 
  * Gán nhãn cảm xúc theo 3 mức: *Positive*, *Negative*, *Neutral*.
* **Aspect-Based Sentiment Regression / WMLR (Weighted Multiple Linear Regression):** 
  * Mô hình hồi quy liên kết điểm phân cực cảm xúc (sentiment polarity) của từng khía cạnh với điểm xếp hạng (rating) tổng thể.
* **Manual Validation:** Xác thực thủ công để đảm bảo độ chính xác của nhãn chủ đề và cảm xúc.

### 1.2. Phát Hiện Chính (Key Insights)
* **Phân bố cảm xúc:** Cảm xúc tích cực (*Positive sentiment*) chiếm ưu thế tuyệt đối trên cả 5 khía cạnh.
* **Khía cạnh thảo luận nhiều nhất:** Tiện nghi (*Amenity*) và Dịch vụ (*Service*).
* **Mối quan hệ điều tiết (Mediation Effect):**
  * Giá trị trải nghiệm (*Experience value*) và Lòng trung thành (*Customer loyalty*) đóng vai trò trung gian giữa trải nghiệm thực tế và điểm số đánh giá.
  * Lòng trung thành (*Customer loyalty*) có tương quan mạnh nhất với mức điểm rating cao và đóng vai trò trung gian giữa chất lượng dịch vụ (*Service*) và tài sản thương hiệu (*Brand equity*).
* **Tác động không đồng nhất (Heterogeneous Effects):** Mức độ phân cực cảm xúc mang lại tác động khác nhau tùy thuộc vào từng khía cạnh cụ thể.

---

## 2. Nghiên Cứu 2: Khung Phân Tích TextBlob – LDA (Booking.com vs. TripAdvisor)

Nghiên cứu xây dựng bộ dữ liệu quy mô lớn cho thị trường mới nổi gồm:
* **Booking.com:** 607,451 reviews
* **TripAdvisor:** 782,584 reviews

### 2.1. Phân Tích Cảm Xúc Bằng TextBlob (Sentiment & Subjectivity)

| Chỉ Số | Thang Đo | Booking.com | TripAdvisor | Nhận Xét Chung |
| :--- | :---: | :---: | :---: | :--- |
| **Polarity (Độ phân cực)** | $[-1.0, 1.0]$ | $0.25 \to 0.50$ | $0.25 \to 0.35$ | Đa số đánh giá mang tính chất tích cực (*reasonably positive*). |
| **Subjectivity (Tính chủ quan)** | $[0.0, 1.0]$ | $0.50 \to 1.00$ | $0.40 \to 0.60$ | Khách hàng thiên về bày tỏ cảm nhận cá nhân hơn là nhận xét khách quan thuần túy. |

---

### 2.2. Khai Phá Chủ Đề Bằng LDA (Topic Modeling)
* **Các chủ đề cốt lõi xuất hiện:** `Staff` (nhân viên), `Room` (phòng ốc), `Location` (vị trí), `Cleanliness` (vệ sinh), `Breakfast` (bữa sáng).
* **Trọng tâm theo nền tảng:**
  * **Booking.com:** Tập trung mạnh vào `Room`, `Cleanliness`, và `Service`.
  * **TripAdvisor:** Phổ biến hơn các yếu tố trải nghiệm nghỉ dưỡng gồm `Services`, `Location`, `Amenities` (hồ bơi, nhà hàng).

---

### 2.3. Ma Trận Tương Quan (Correlation Matrix With Overall Score)

#### A. Booking.com
* **Mức độ tương quan cao nhất với Overall Score:**
  * `Comfortable` (0.91)
  * `Value` (0.91)
  * `Cleanliness` (0.90)
  * `Facility` (0.90)
  * `Staff` (0.89)
* **Tương quan trung bình/thấp:**
  * `Location` (0.78)
  * `Free-WiFi` (**0.43** – thấp nhất)

#### B. TripAdvisor
* **Mức độ tương quan với Overall Score:**
  * `Service` (**0.82** – cao nhất)
  * `Value` (0.75)
  * `Cleanliness` (0.75)
  * `Location` (0.61)

---

### 2.4. Thống Kê Điểm Đánh Giá (Statistical Ratings)

| Tiêu Chí | Booking.com (Thang 10) | TripAdvisor (Thang 5) |
| :--- | :---: | :---: |
| **Điểm trung bình (Mean $\pm$ Std)** | $8.596 \pm 1.928$ | $4.485 \pm 0.954$ |
| **Điểm đánh giá tiếng Anh (English Reviews)** | $8.715$ | $4.493$ |
| **Tỷ lệ điểm tối đa ở nhóm khách sạn 0 sao** | $50.9\%$ đạt điểm $10/10$ | $70.0\%$ đạt điểm $5/5$ |

---

## 3. Tổng Kết Động Lực Đánh Giá & Gợi Ý Baseline Cho Nghiên Cứu Tiếp Theo

1. **Hiệu ứng thiên lệch tích cực (Positive Bias):** Cả hai nền tảng đều ghi nhận phân phối điểm lệch dương rõ rệt. Đánh giá bằng tiếng Anh thường có mức điểm trung bình cao hơn.
2. **Yếu tố then chốt quyết định điểm số:**
   * Tiện nghi, độ thoải mái (`Comfort`) và mức độ hài lòng về giá trị (`Value`) chi phối mạnh mẽ nhất đến tổng điểm trên Booking.
   * Chất lượng dịch vụ (`Service`) và sự hỗ trợ của nhân viên là động lực chính trên TripAdvisor.
   * `Free-WiFi` chỉ đóng vai trò là tiện ích cơ bản (hygiene factor), ít tạo ra sự khác biệt lớn về điểm số tổng thể.
3. **Mô hình hóa đề xuất:** Có thể kết hợp khung **S-O-R** sử dụng **BERTopic** để trích xuất đặc trưng đa chiều (multi-aspect) và **WMLR/VADER/TextBlob** để dự đoán tương quan mức độ hài lòng khách hàng.