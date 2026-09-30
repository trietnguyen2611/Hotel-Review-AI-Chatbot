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

Mỗi câu hỏi được phát biểu kèm một giả thuyết có thể bác bỏ và một con số cụ thể để kết luận. RQ1 và RQ2 chỉ cần chạy năm mô hình rồi tính toán trên output, nên có kết quả sớm. Chỉ RQ3 cần sửa code. 

_Bảng 3. Ba câu hỏi nghiên cứu, giả thuyết có thể bác bỏ và phép đo quyết định_ 

|**STT**|**Câu hỏi nghiên cứu**|**Giả thuyết**|**Phép đo quyết định**|
|---|---|---|---|
|RQ1|Khi chuyển từ nhãn 2 lớp<br>sang 5 mức, token F1 của<br>rationale giảm bao nhiêu ở<br>từng mô hình, và mức giảm ở<br>review 2 tới 4 sao có lớn hơn<br>ở review 1 và 5 sao không|Mức giảm tập trung ở<br>các mức giữa, vì phân<br>biệt 3 với 4 sao cần bằng<br>chứng tinh hơn phân biệt<br>tốt với xấu|Token F1 của năm mô<br>hình ở hai thiết lập, tách<br>theo mức sao, kèm khoảng<br>tin cậy bootstrap|
|RQ2|**Bao nhiêu phần trăm token**<br>**rationale của mỗi khía cạnh**<br>**rơi vào câu nói về khía cạnh**<br>**khác, và mức lẫn có tăng**<br>**theo độ tương quan điểm**<br>**giữa hai khía cạnh không**|Cặp khía cạnh có điểm<br>tương quan càng cao thì<br>lẫn càng nhiều, và xoá<br>câu của khía cạnh khác<br>làm điểm dự đoán đổi ít<br>nhất một mức ở một tỉ lệ<br>đáng kể review|Ma trận lẫn 3 × 3 cho năm<br>mô hình, tương quan giữa<br>mức lẫn và hệ số tương<br>quan điểm, tỉ lệ review đổi<br>điểm khi xoá câu|
|RQ3|Thêm mất mát thứ tự và phạt<br>chồng lấn vào PLMR có đồng<br>thời giảm mức lẫn và giảm<br>macro-MAE mà không làm<br>giảm token F1 không|Phạt chồng lấn giảm lẫn,<br>mất mát thứ tự giảm<br>macro-MAE, và hai<br>thành phần không triệt<br>tiêu nhau|Ablation bốn cấu hình:<br>PLMR gốc, thêm mất mát<br>thứ tự, thêm phạt chồng<br>lấn, thêm cả hai|



RQ2 cho thấy các khía cạnh trong cùng một review tương quan mạnh, nên mô hình dự đoán Service có thể lấy câu khen phòng sạch làm căn cứ mà vẫn đoán đúng điểm. Hiện tượng này đã được ghi nhận trên bộ BeerAdvocate nhưng chưa được đo có hệ thống trên review khách sạn ở thang 5 mức. Để biết câu nào thuộc khía cạnh nào, nhóm dùng từ khoá của từng khía cạnh cộng một bộ phân loại câu nhỏ, rồi kiểm tay 100 câu để báo độ chính xác của bước gán này. 

## **Phương pháp đề xuất** 

Phương pháp giữ nguyên kiến trúc của PLMR và chỉ thay hàm mất mát. Với mỗi khía cạnh a, bộ sinh tạo mặt nạ m_a trên các token, bộ dự đoán f_a chỉ nhìn phần văn bản được chọn: 

_L = Σ_a ω(y_a) · L_ord( f_a(x ⊙ m_a), y_a ) + λ_1 · Σ_a m_a‖ ‖₁ + λ_2 · Σ_a≠b m_a,⟨ m_b⟩_ 

Thành phần thứ nhất là mất mát thứ tự CORN thay cho cross-entropy, để mô hình hiểu rằng đoán 4 khi đúng là 5 ít sai hơn đoán 1. Trọng số ω(y) tỉ lệ nghịch với tần suất của mức sao để xử lý dữ liệu lệch. Thành phần thứ hai giữ rationale ngắn như các bài gốc. Thành phần thứ ba là điểm mới: phạt khi rationale của hai khía cạnh chọn cùng một đoạn, nhắm thẳng vào hiện tượng lẫn ở RQ2. Mỗi thành phần bật tắt được riêng, nên ablation ở RQ3 rất rõ ràng. 

## **Chỉ số đánh giá** 

Bảng 4 chốt các chỉ số theo bốn nhóm, tương ứng với bốn điều người đọc sẽ hỏi: đoán điểm có đúng không, bằng chứng có giống người chọn không, bằng chứng có thật sự là lý do của dự đoán không, và bằng chứng có lẫn khía cạnh không. 

_Bảng 4. Chỉ số đánh giá được chốt theo bốn nhóm câu hỏi_ 

|**STT**|**Nhóm**|**Chỉ số**|
|---|---|---|
|1|Dự đoán điểm|QWK (chỉ số chính), macro-F1 năm lớp, macro-MAE tính<br>trung bình theo từng mức sao|
|2|Khớp với người|Token precision, recall và F1 so với rationale của người, độ<br>dài rationale|
|3|Độ trung thực|Sufficiency (dự đoán từ riêng rationale) và<br>comprehensiveness (dự đoán khi đã xoá rationale) theo<br>chuẩn ERASER|
|4|Lẫn khía cạnh|Tỉ lệ token rationale rơi vào câu của khía cạnh khác, tỉ lệ<br>review đổi điểm khi xoá câu của khía cạnh khác|



Mọi cấu hình chạy 5 seed, báo trung bình và độ lệch chuẩn. Tập có rationale của người chỉ khoảng 100 review mỗi khía cạnh, nên token F1 phải kèm khoảng tin cậy bootstrap theo review. 

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

