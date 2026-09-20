# Copy code dưới đây vào 1.1 trong Notebook

from google.colab import drive
import os

# Mount Google Drive
drive.mount('/content/drive')

# Đường dẫn thư mục chứa dataset trên Drive của bạn (vui lòng cập nhật nếu cần)
drive_path = '/content/drive/MyDrive/Study/FPTU/FU_4_FA26/DAP391m/DAP391m_AI2002_Group 7/2 - Dataset'
dataset_name = 'tripadvisor_review_hotel_dataset.csv'

# Tạo thư mục local lưu trữ dataset (Data/dts_raw)
raw_dir = os.path.join('Data', 'dts_raw')
os.makedirs(raw_dir, exist_ok=True)

# Kiểm tra và tạo liên kết (symlink) hoặc copy file vào thư mục Data/dts_raw local
if os.path.exists(os.path.join(drive_path, dataset_name)):
    local_file = os.path.join(raw_dir, dataset_name)
    if not os.path.exists(local_file):
        # Sử dụng symlink để tiết kiệm dung lượng và thời gian
        os.symlink(os.path.join(drive_path, dataset_name), local_file)
        print(f"Đã liên kết thành công dataset từ Google Drive vào {local_file}")
    else:
        print(f"Tệp dataset đã sẵn sàng tại {local_file}")
else:
    print(f"CẢNH BÁO: Không tìm thấy tệp {dataset_name} tại {drive_path}. Vui lòng kiểm tra lại đường dẫn.")

