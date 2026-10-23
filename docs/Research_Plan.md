# **Cross-Aspect Leakage in Ordinal Rationalization of Hotel Reviews** 

Nhóm 5, lớp AI2002, môn DAP391m Người hướng dẫn: Thầy Hường, Cô Thư 

Ngày: 28/09/2026 

## **Hướng khả thi** 

Bài toán được thu gọn như sau: đọc một review khách sạn, dự đoán điểm từ 1 tới 5 cho ba khía cạnh Location, Service và Cleanliness, đồng thời chỉ ra đoạn văn làm căn cứ cho từng điểm. Dòng nghiên cứu tương ứng là selective rationalization. Mô hình tự chọn một phần văn bản (rationale) rồi chỉ dựa vào phần đó để dự đoán, nên lời giải thích trung thực với dự đoán ngay từ thiết kế. 

Hướng này khả thi với nhóm vì ba lý do: Thứ nhất, đã có benchmark chuẩn là HotelReview, dùng review TripAdvisor, có đúng ba khía cạnh trên và có tập review được người đánh dấu rationale để chấm, nên nhóm không phải gán nhãn tay. Thứ hai, các công trình mạnh gần đây ở KDD 2025, ICLR 2025 và NeurIPS 2024 đều dùng benchmark này, phần lớn có code công khai và chạy được trên một GPU. Thứ ba, kết quả nhìn thấy được từ rất sớm: sau hai tuần đầu, nhóm đã có review được tô sáng theo từng khía cạnh kèm điểm dự đoán. 

## **Dữ liệu** 

_Bảng 1. Dữ liệu được chốt, quy mô, nguồn công bố và vai trò trong thí nghiệm_ 

|**STT**|**Bộ dữ liệu**|**Quy mô và nhãn**|**Nguồn công bố**|**Vai trò**|
|---|---|---|---|---|
|1|**HotelReview**|Ba khía cạnh Location,<br>Service, Cleanliness. Tập<br>train khoảng 7 nghìn tới 75<br>nghìn review tùy khía<br>cạnh, tập dev và test<br>khoảng 900 tới 9 nghìn<br>review. Nhãn trong các bài<br>rationalization đã gộp về<br>hai lớp và cân bằng|Bao và cộng sự,<br>EMNLP 2018,<br>code R2A trên<br>GitHub|Benchmark<br>chính, dùng lại<br>chia tập để so<br>với các bài đã<br>công bố|
|2|Tập có rationale<br>của người|Khoảng 100 review mỗi<br>khía cạnh được đánh dấu<br>từ làm bằng chứng|Cùng nguồn với<br>bộ 1|Chấm chất lượng<br>rationale bằng<br>token F1|
|3|TripAdvisor gốc<br>của Wang và<br>cộng sự|Review có điểm tổng và<br>điểm theo từng khía cạnh<br>trên thang 1 tới 5|KDD 2010|**Lấy lại nhãn 5**<br>**mức**cho các<br>review của bộ 1|



Khoảng trống của bài nằm ở dòng 3, mọi bài rationalization trên HotelReview đều gộp điểm 1 tới 5 thành tích cực và tiêu cực, rồi cân bằng dữ liệu. Cách làm này bỏ qua hai khó 

khăn của bài toán thật: phân biệt các mức gần nhau (4 sao khác 5 sao ở chỗ nào) và dữ liệu lệch mạnh về phía 5 sao. Đưa rationalization về đúng thang 5 mức là đóng góp chính, và phần này chỉ cần ghép lại nhãn gốc chứ không cần gán thêm. 

## **Năm mô hình được chọn** 

Bảng 2 chốt năm mô hình, trải từ mô hình gốc của dòng nghiên cứu tới công trình mới nhất. Tiêu chí chọn gồm ba điều: công bố ở hội nghị hàng đầu, đã báo kết quả trên HotelReview, và có code công khai. Năm mô hình dùng chung chia tập, chung nhãn 5 mức và chung bộ chỉ số, nên mọi chênh lệch đều quy được về phương pháp. 

_Bảng 2. Năm mô hình được chốt, nơi công bố, backbone và vai trò trong bài_ 

|**STT**|**Mô hình**|**Nơi công bố**|**Backbone**|**Vai trò**|
|---|---|---|---|---|
|1|RNP|EMNLP 2016|GRU|Mô hình gốc của dòng nghiên<br>cứu, chạy nhanh, dùng để<br>kiểm tra pipeline và làm mốc<br>thấp|
|2|MGR|ACL 2023|GRU|Mốc quen thuộc, bài gốc có<br>token F1 56.2, 45.7 và 40.7<br>cho Location, Service,<br>Cleanliness|
|3|MRD|NeurIPS 2024|GRU, cần<br>kiểm tra bản<br>BERT|Thay tiêu chí MMI bằng độ<br>chênh phần còn lại, nhắm vào<br>đặc trưng giả tương quan, gần<br>với hiện tượng lẫn khía cạnh|
|4|Rationalization<br>dựa trên chuẩn<br>biểu diễn|ICLR 2025|GRU, BERT|Công trình mới, bài gốc báo<br>kết quả ngang Llama-3.1-8B.<br>Cần kiểm tra code trước khi<br>chốt, nếu không có thì thay<br>bằng Adversarial Cooperative<br>Rationalization (ICML 2025)|
|5|**PLMR**|KDD 2025|BERT,<br>RoBERTa,<br>ELECTRA|**Nền của phương pháp đề**<br>**xuất**, có code, bài gốc báo F1<br>rationale khoảng 49.2% trên<br>HotelReview|



## **Ba câu hỏi nghiên cứu** 
RQ1 (Thách thức bài toán thực tế - Thang điểm 5 sao vs. 2 lớp nhị phân):
"Khi chuyển từ bài toán phân loại nhị phân 2 lớp (Tốt/Xấu) sang thang điểm 5 mức sao thực tế, độ chính xác khi tìm đoạn bằng chứng (rationale) và đánh giá cảm xúc theo từng khía cạnh giảm bao nhiêu, và sự sụt giảm này có tập trung chủ yếu ở các mức đánh giá trung gian (2 đến 4 sao) hay không?"
• Giải thích dễ hiểu: Đa số các bài báo trước đây thường gộp điểm đánh giá thành 2 nhóm đơn giản: "Khen" và "Chê". Thực tế, khách sạn chấm điểm từ 1 đến 5 sao (rất khó phân biệt giữa 3 sao và 4 sao). RQ1 chứng minh rằng bài toán 5 sao thực tế khó hơn rất nhiều so với bài toán nhị phân, đặc biệt ở các review có mức điểm trung bình.
• Thước đo định lượng: Điểm Token-F1 của đoạn bằng chứng, Macro-F1 của phân loại cảm xúc tách biệt theo từng mức từ 1 đến 5 sao.

RQ2 (Đóng góp của mô hình đề xuất CRAM-ABSA - Chống lẫn lộn bằng chứng):
"Cơ chế phạt chồng lấn phân đoạn (ℒ_{overlap}) kết hợp hàm mất mát thứ bậc (CORN Loss) trong mô hình CRAM-ABSA có giúp loại bỏ hiện tượng 'lẫn bằng chứng' giữa các khía cạnh và giảm sai lệch dự đoán điểm sao mà không làm suy giảm chất lượng trích xuất câu văn hay không?"
• Giải thích dễ hiểu: Trong một bài đánh giá, khách thường viết: "Phòng rất sạch nhưng nhân viên phục vụ chậm chạp". Mô hình thông thường hay bị "lẫn", lấy câu khen phòng sạch để làm căn cứ chấm điểm cho dịch vụ nhân viên.
• Thước đo định lượng: Tỷ lệ chồng lấn/lẫn token giữa các khía cạnh (Leakage Rate), sai số tuyệt đối trung bình theo thứ tự (Macro-MAE), và Token-F1 qua thí nghiệm bóc tách thành phần (Ablation Study).

RQ3 (Hiệu quả ứng dụng thực tiễn - Chatbot Hỏi Đáp & Trọng số thời gian):
"Việc tích hợp bằng chứng khía cạnh từ CRAM-ABSA cùng cơ chế ưu tiên đánh giá mới theo thời gian (Time-weighting) giúp Chatbot cải thiện độ chính xác và tính thuyết phục của câu trả lời như thế nào so với các mô hình hỏi đáp truyền thống trên bộ benchmark thực tế?"
• Giải thích dễ hiểu: Người dùng hỏi Chatbot: "Dạo này bữa sáng khách sạn thế nào?". Chatbot cần ưu tiên các review gần đây (vì chất lượng năm 2026 có thể đã khác năm 2019) và phải trích dẫn đúng đoạn nhận xét về bữa sáng để trả lời. RQ3 đánh giá xem chatbot được xây dựng có trả lời đúng trọng tâm và đáng tin cậy hơn chatbot thông thường trên bộ 60 câu hỏi thử nghiệm hay không.
• Thước đo định lượng: Điểm ROUGE-L / Token-F1 của câu trả lời sinh ra, tỷ lệ câu trả lời truy xuất đúng bằng chứng khía cạnh (Aspect Retrieval Accuracy) trên bộ QA Benchmark qa_verified.json.

## **Lộ trình** 

Bảng 5 sắp công việc sao cho mỗi mốc đều có kết quả nhìn thấy được. Mốc 1 quan trọng nhất: nếu không ghép được nhãn 5 mức cho phần lớn review, nhóm cần báo lại ngay để điều chỉnh. 

_Bảng 5. Lộ trình mười tuần với kết quả nhìn thấy được và điểm quyết định ở mỗi mốc_ 

|**STT**|**Tuần**|**Công việc**|**Kết quả và điểm quyết định**|
|---|---|---|---|
|1|1,2,3|Tải HotelReview và dữ liệu gốc của<br>Wang và cộng sự, ghép nhãn 5 mức,<br>chạy RNP để kiểm tra pipeline|Phân bố 5 mức theo khía cạnh, tỉ<br>lệ ghép thành công, vài review tô<br>sáng đầu tiên|
|2|4|Tái lập MGR, MRD và PLMR ở<br>thiết lập 2 lớp, kiểm tra code của mô<br>hình ICLR 2025|Số khớp với bài gốc. Không khớp<br>thì dừng lại kiểm tra trước khi đi<br>tiếp|
|3|4|Chạy năm mô hình ở thiết lập 5<br>mức, tính mức lẫn khía cạnh|Bảng RQ1, ma trận lẫn cho RQ2|
|4|5|Thêm mất mát thứ tự và phạt chồng<br>lấn vào PLMR, chạy ablation|Bảng RQ3, so sánh tô sáng trước<br>và sau|



|**STT**|**Tuần**|**Công việc**|**Kết quả và điểm quyết định**|
|---|---|---|---|
|5|5|Phân tích lỗi, chọn ví dụ minh hoạ,<br>viết bài|Bản thảo đầy đủ|



Ngoài tên đề tài ở đầu văn bản, có thể cân nhắc hai phương án khác: "Ordinal Multi-Aspect Rationalization for Five-Level Hotel Review Ratings" nếu kết quả RQ3 nổi bật hơn RQ2, và "Rationales That Stay on Their Aspect in Five-Level Hotel Review Rating" nếu phạt chồng lấn cho kết quả rõ. 

