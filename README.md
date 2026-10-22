# 🏨 Hotel Review AI Chatbot & Aspect-Based Sentiment Rationalization

> **Dự án DAP391m** — Lớp AI2002 — Nhóm 5  
> Hệ thống Trợ lý Ảo Thông minh (AI Chatbot) & Phân tích Đánh giá Khách sạn đa khía cạnh (Aspect-Based Sentiment Analysis & Rationalization) dựa trên tập dữ liệu TripAdvisor (9,990 reviews, 54,326 annotations).

---

## 📌 Tổng quan dự án

Dự án phát triển một hệ thống toàn diện từ nghiên cứu dữ liệu, huấn luyện mô hình học sâu (Seq2Seq / BART) đến triển khai ứng dụng Native Desktop App:

1. **Aspect-Based Sentiment Analysis & Rationalization**: Trích xuất và phân tích 6 khía cạnh chuẩn:
   - **Service**: Dịch vụ, thái độ nhân viên, lễ tân, buồng phòng.
   - **Facility**: Cơ sở vật chất, phòng ốc, giường, vệ sinh, cách âm, thang máy.
   - **Experience**: Trải nghiệm tổng thể, cảm nhận của khách hàng.
   - **Amenity**: Tiện ích đi kèm (hồ bơi, gym, bữa sáng, buffet, spa, wifi, bãi đỗ xe).
   - **Loyalty**: Mức độ trung thành, dự định quay lại, giới thiệu người thân.
   - **Branding**: Danh tiếng, đẳng cấp và giá trị thương hiệu.
2. **Generative Neural Engine**: Mô hình sinh câu trả lời đàm thoại (BART Seq2Seq) kết hợp đặc trưng khía cạnh, trích xuất căn cứ (rationale span) minh bạch.
3. **Knowledge Base Engine**: Cơ sở tri thức Parquet Snappy tốc độ cao (`hotel_reviews.parquet`) và SQLite Relational Database (`chatbot.db`) hỗ trợ truy vấn thông tin khách sạn tức thì.
4. **Native Desktop Application**: Ứng dụng Desktop native khép kín (Electron shell tích hợp giao diện người dùng hiện đại, dark/light mode và backend Python nội bộ).

---

## 📂 Cấu trúc thư mục dự án

Toàn bộ ứng dụng Desktop và giao diện người dùng được đóng gói khép kín trong thư mục `desktop/`, giữ cho thư mục gốc của dự án luôn sạch sẽ, gọn gàng và chuẩn cấu trúc Khoa học Dữ liệu / Học máy:

```text
Hotel-Review-AI-Chatbot/
├── data/                                 # Dữ liệu phục vụ nghiên cứu & ứng dụng
│   ├── chart_img/                        # 12 biểu đồ trực quan hóa dữ liệu EDA
│   ├── dataset/                          # Bộ dữ liệu gốc & nhãn QA kiểm thử
│   │   ├── TripAdvisor_EN.json           # Dữ liệu đánh giá khách sạn tiếng Anh (44MB)
│   │   ├── qa_verified.json              # Tập câu hỏi - trả lời đã kiểm định
│   │   ├── qa_unverified.json            # Tập câu hỏi - trả lời thô
│   │   └── sample_qa.json                # Template hướng dẫn xây dựng nhãn QA
│   ├── df/                               # Dữ liệu có cấu trúc phục vụ truy vấn
│   │   ├── hotel_reviews.parquet         # Tệp Parquet Snappy thống nhất (6.3MB)
│   │   └── chatbot.db                    # CSDL SQLite (bảng reviews, annotations, features)
│   └── feature/
│       └── TripAdvisor_Feature.json      # Dữ liệu kèm vector đặc trưng 6 khía cạnh (75MB)
│
├── desktop/                              # Ứng dụng Native Desktop (khép kín toàn bộ Electron & UI)
│   ├── main.cjs                          # Tiến trình chính điều phối Electron & backend Python
│   ├── app.py                            # Python Backend Server & Neural Inference Engine
│   ├── app.js                            # Logic tương tác phía Client (Chat, Filter, Charts)
│   ├── index.html                        # Giao diện người dùng Desktop App
│   ├── style.css                         # Bộ phong cách thiết kế UI/UX hiện đại
│   ├── package.json                      # Cấu hình Electron dependencies & build scripts
│   ├── package-lock.json                 # Lockfile quản lý phiên bản Node packages
│   └── node_modules/                     # Thư viện Electron (đã được gitignore)
│
├── docs/                                 # Tài liệu kỹ thuật, nghiên cứu & hướng dẫn
│   ├── DESIGN.md                         # Tài liệu thiết kế kiến trúc hệ thống chi tiết
│   ├── Research_Plan.md                  # Đề cương & kế hoạch nghiên cứu DAP391m
│   ├── DESKTOP.md                        # Hướng dẫn chi tiết build & đóng gói Desktop App
│   └── paper/                            # Tài liệu mẫu bài báo nghiên cứu khoa học
│       └── IEEE_Conference_Template.zip  # Template định dạng chuẩn IEEE Conference
│
├── model/                                # Trọng số các phiên bản mô hình học sâu
│   ├── model_v1.pt                       # Checkpoint phiên bản v1 (Extractive Multi-Task BERT)
│   ├── model_v2.pt                       # Checkpoint phiên bản v2 (BART Seq2Seq)
│   └── model_v3/                         # Checkpoint phiên bản v3 (Full Engine & HuggingFace)
│       ├── config.json                   # Cấu hình kiến trúc mô hình
│       ├── model.safetensors             # Trọng số định dạng SafeTensors
│       ├── pytorch_model.bin             # Trọng số định dạng PyTorch
│       ├── tokenizer.json                # Bộ mã hóa từ vựng (BPE Tokenizer)
│       └── model_metadata.json           # Lịch sử huấn luyện & tham số kỹ thuật
│
├── Project.ipynb                         # Notebook phân tích khám phá (EDA) & xuất dữ liệu
├── Training_Kaggle.ipynb                 # Notebook huấn luyện mô hình Seq2Seq trên Kaggle GPU
├── requirements.txt                      # Danh sách các thư viện Python cần thiết
└── README.md                             # Hướng dẫn tổng quan dự án
```

---

## 🚀 Hướng dẫn cài đặt & Khởi chạy

### 1. Yêu cầu hệ thống
- **Python**: Phiên bản 3.10 đến 3.12.
- **Node.js**: Phiên bản 20 trở lên.

### 2. Cài đặt môi trường Python
```bash
# Khởi tạo môi trường ảo
python3 -m venv .venv

# Kích hoạt môi trường ảo
# Trên macOS / Linux:
source .venv/bin/activate
# Trên Windows:
# .venv\Scripts\activate

# Cài đặt toàn bộ thư viện cần thiết
pip install -r requirements.txt
```

### 3. Cài đặt dependencies cho Desktop App
```bash
cd desktop
npm install
```

### 4. Khởi chạy Ứng dụng Native Desktop (Electron)
Bạn có thể khởi chạy ứng dụng bằng 1 trong 2 cách:

- **Cách 1 (Từ thư mục desktop)**:
  ```bash
  cd desktop
  npm start
  ```
- **Cách 2 (Trực tiếp từ thư mục gốc)**:
  ```bash
  npm --prefix desktop run desktop
  ```

Electron sẽ tự động quản lý tiến trình Python backend dưới nền, khởi chạy Neural Inference Engine, tự gán cổng kết nối an toàn và tự động đóng backend khi thoát ứng dụng.

### 5. (Tùy chọn) Chạy backend độc lập qua trình duyệt Web
Nếu muốn chạy trực tiếp máy chủ backend để kiểm thử qua trình duyệt:
```bash
python desktop/app.py
```
Mở trình duyệt tại: 👉 `http://127.0.0.1:8000`.

### 6. Đóng gói bộ cài đặt Native Desktop (Build Installers)
- **macOS (DMG & ZIP)**:
  ```bash
  cd desktop && npm run dist:mac
  ```
- **Windows (NSIS Installer)**:
  ```bash
  cd desktop && npm run dist:win
  ```
Tệp cài đặt sau khi đóng gói sẽ được tạo trong thư mục `release/` ở thư mục gốc.

---

## 📊 Notebooks nghiên cứu

- **[Project.ipynb](file:///Users/trietnguyen/Documents/DAP-Hotel/Project.ipynb)**: Thực hiện đầy đủ 5 giai đoạn:
  1. Nạp và kiểm định chất lượng dữ liệu thô (Data Ingestion & Integrity Audit).
  2. Xây dựng lược đồ cơ sở dữ liệu quan hệ SQLite (`chatbot.db`) và giải quyết các Research Questions (RQs).
  3. Làm sạch dữ liệu, xử lý nhiễu, chuẩn hóa nhãn đa khía cạnh (Multi-Aspect Cleaning).
  4. Trực quan hóa dữ liệu EDA chuyên sâu (12 biểu đồ khoa học lưu tại `data/chart_img/`).
  5. Trích xuất đặc trưng dense feature và xuất dữ liệu ra định dạng Parquet Snappy thống nhất.
- **[Training_Kaggle.ipynb](file:///Users/trietnguyen/Documents/DAP-Hotel/Training_Kaggle.ipynb)**: Huấn luyện mô hình học máy sinh văn bản (BART Seq2Seq) tối ưu hóa hàm mất mát đa nhiệm, đánh giá trên tập Test set với các chỉ số Perplexity, Token F1, ROUGE-L và xuất mô hình chuẩn hóa về thư mục `model/model_v3`.

---

## 📖 Tài liệu kỹ thuật chi tiết

Các tài liệu nghiên cứu và thiết kế chuyên sâu được lưu trữ tập trung tại thư mục [`docs/`](file:///Users/trietnguyen/Documents/DAP-Hotel/docs/):
- **[docs/DESIGN.md](file:///Users/trietnguyen/Documents/DAP-Hotel/docs/DESIGN.md)**: Chi tiết kiến trúc hệ thống, luồng dữ liệu, giao thức API, bộ lọc khía cạnh và quản lý bộ nhớ.
- **[docs/Research_Plan.md](file:///Users/trietnguyen/Documents/DAP-Hotel/docs/Research_Plan.md)**: Mục tiêu nghiên cứu, giả thuyết khoa học, các bài toán rò rỉ khía cạnh (Cross-Aspect Leakage) và benchmark.
- **[docs/DESKTOP.md](file:///Users/trietnguyen/Documents/DAP-Hotel/docs/DESKTOP.md)**: Chi tiết quy trình đóng gói phần mềm Desktop, xử lý tài nguyên tĩnh và cấu hình môi trường thực thi.
- **[docs/paper/](file:///Users/trietnguyen/Documents/DAP-Hotel/docs/paper/)**: Mẫu bản thảo bài báo chuẩn IEEE Conference.
