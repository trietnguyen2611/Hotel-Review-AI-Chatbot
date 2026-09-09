# DAP391m - AI2002 - Group 5 - Hotel Question Answering Chatbot

> **Đề tài nghiên cứu khoa học:** Joint Fine-Grained Opinion Extraction and Overall Rating Prediction from Real-World Hotel Reviews - Xây dựng hệ thống Chatbot thông minh hỗ trợ trả lời câu hỏi và tư vấn khách sạn dựa trên tập dữ liệu đánh giá thực tế từ TripAdvisor. 
> **Học kỳ:** Fall 2026
> **Môn học:** DAP391m
> **Lớp:** AI2002 
> **Nhóm thực hiện:** Group 5 

---

## Giới thiệu đề tài (Introduction)

Trong thời đại số, đánh giá trực tuyến (online customer reviews) là nguồn dữ liệu vô giá đối với người dùng trước khi quyết định đặt phòng khách sạn. Tuy nhiên, việc phải đọc hàng trăm đến hàng nghìn bài đánh giá dài dòng và phân tán để tìm câu trả lời cho các thắc mắc cụ thể (ví dụ: *"Phòng khách sạn này có cách âm tốt không?"*, *"Bữa sáng tại khách sạn có phong phú không?"*, *"Vị trí có thuận tiện đến trung tâm không?"*) gây tốn nhiều thời gian và công sức.

Dự án được phát triển nhằm giải quyết bài toán trên thông qua việc:
- Tự động hóa quá trình phân tích và khai phá các khía cạnh dịch vụ (*aspect-based opinion mining*) từ tập dữ liệu lớn các đánh giá khách sạn.
- Xây dựng cơ chế truy xuất thông tin ngữ nghĩa và trả lời câu hỏi thông minh (*Question Answering System*), hỗ trợ khách hàng đưa ra quyết định đặt phòng nhanh chóng và chính xác.

---

## Bộ dữ liệu nghiên cứu (Dataset Overview)

Dự án sử dụng bộ dữ liệu đánh giá khách sạn quy mô lớn thu thập từ **TripAdvisor** (`tripadvisor_review_hotel_dataset.csv`) với quy mô **~782,584 bản ghi** và **25 trường thông tin** chi tiết:

| Nhóm thông tin | Các trường dữ liệu chính | Mô tả mục đích |
| :--- | :--- | :--- |
| **Thực thể khách sạn** | `hotel_name`, `hotel_province`, `hotel_address`, `hotel_star` | Định danh khách sạn, khu vực địa lý và phân khúc sao |
| **Điểm số & Khía cạnh** | `normalized_score`, `Value`, `Rooms`, `Location`, `Cleanliness`, `Service`, `Sleep_Quality` | Đánh giá định lượng tổng quan và chi tiết từng khía cạnh dịch vụ |
| **Văn bản đánh giá (NLP)** | `normalized_title`, `normalized_content`, `Word_count`, `language` | Dữ liệu văn bản dùng để trích xuất đặc trưng, huấn luyện mô hình hỏi đáp |
| **Bối cảnh lưu trú** | `trip_type`, `Date`, `month`, `year` | Phân khúc chuyến đi (công tác, cặp đôi, gia đình) và thời gian trải nghiệm |

> *Lưu ý:* Do dung lượng file dataset vượt quá 100 MB, file được lưu trữ cục bộ trong thư mục `Data (Dataset, Data Frame, Chart Images)/` và được cấu hình bỏ qua bởi `.gitignore` theo quy định của GitHub, nếu cần tải về vui lòng liên hệ [EMAIL_ADDRESS].

---

## Bản quyền (License)
Dự án được phát triển phục vụ mục đích nghiên cứu học thuật trong môn học DAP391m của Trường Đại Học FPT TP.HCM.