# Ground truth ngày 05/11 — vị trí và cách mở

Đây là đầu ra công việc 21 của Đức. Nhãn dùng đúng bộ ảnh trong
[`data/raw`](../../data/raw); không đổi kích thước, cắt ảnh hoặc sửa input.

## Mở nhanh theo nhu cầu

| Muốn xem | Mở file nào | Cách mở |
| --- | --- | --- |
| Trạng thái 25 ảnh | [ground_truth_inventory.csv](../../data/metadata/ground_truth_inventory.csv) | Excel; chọn UTF-8 nếu nhập qua Data → From Text/CSV; hoặc mở VS Code |
| Kiểm tra nhãn chồng ảnh | [data/gt/previews](../../data/gt/previews) | Nhấp đúp PNG bằng Photos, hoặc Fiji → File → Open |
| Mặt nạ biên BSDS | `data/gt/bsds/bsds_01/annotator_01_boundaries.png` | Photos/Fiji; trắng=biên, đen=không phải biên |
| Phân vùng BSDS | `data/gt/bsds/bsds_01/annotator_01_segments.tif` | Fiji → File → Open; mã vùng uint16, có thể đổi LUT để xem |
| Nhãn gốc BSDS | `data/gt/bsds/bsds_01.mat` | MATLAB/Octave `load(...)`, hoặc Python `scipy.io.loadmat` |
| Nhãn DRIVE | `data/gt/drive/drive_01_vessels.png` | Photos/Fiji; trắng=mạch máu |
| FOV DRIVE | `data/gt/drive/drive_01_fov.png` | Photos/Fiji; trắng=vùng quan sát hợp lệ |
| Tâm/bán kính blob | `data/gt/blob/blob_01.json` | VS Code; xem `objects`, `x`, `y`, `radius`, `polarity` |
| Liên kết input ↔ nhãn | [data/gt/manifest.json](../../data/gt/manifest.json) | VS Code; mỗi ảnh có danh sách file, nguồn, vai trò và SHA-256 |

Các đường dẫn inline ở bảng tính từ gốc dự án. PNG chồng nhãn `*_overlay.png`
chỉ để xem: màu cyan là biên/mạch, vòng xanh là blob, vùng cam là vùng bỏ qua.
Khi đánh giá cần đọc file mask/JSON tương ứng, không dùng ảnh màu overlay.

## BSDS500

Mỗi ảnh giữ nguyên `.mat` trích đúng ID từ archive BSDS500 có sẵn. Tất cả
người gán nhãn được xuất riêng trong thư mục cùng tên ảnh, không gộp thành một
mask. File `boundaries.png` là uint8 0/255; `segments.tif` giữ mã vùng uint16.
Script kiểm tra kích thước từng nhãn bằng kích thước input và giữ nguyên chỉ
số hàng/cột; không chuyển vị các mảng MATLAB khi xuất.

Ảnh preview BSDS hiển thị **người gán nhãn số 01**, không phải hợp nhất mọi
người. Số người của từng ảnh nằm trong CSV và manifest; khi đánh giá sau này
phải dùng đủ các nhãn theo quy tắc BSDS trong INSTRUCTIONS.

## DRIVE

10 cặp nhãn gốc ID 21–30 đã được sao chép vào `data/sources/drive/1st_manual`
và `data/sources/drive/mask`, đối chiếu checksum với nguồn có sẵn trên máy.
PNG trong `data/gt/drive` giữ nguyên kích thước và giá trị nhị phân, không resize,
không xói mòn FOV tại bước chuẩn bị GT. Phép xói mòn phụ thuộc sigma sẽ thuộc
bước đánh giá sau này. Giữ nhãn gốc; số pixel mạch ngoài FOV, nếu có, được ghi
trong cột notes để người đánh giá áp vùng quan sát đúng quy tắc.

## Blob tổng hợp

Tọa độ gốc (0,0) ở góc trên trái; **x=cột, y=hàng**, đơn vị pixel.
`blob_01` và `blob_02` dùng bán kính disk 3,5,7,8 px. `blob_03` và `blob_04`
giữ `gaussian_sigma` 2,2.8,4,5.7 px; bán kính quy ước để đối chiếu LoG là
`sqrt(2)*gaussian_sigma`. Hai ảnh Gaussian là mô hình mềm, không có biên cứng.
Mỗi ảnh có 4 đối tượng; tổng 16 đối tượng giải tích.

Trước khi xuất nhãn, script tái tạo ảnh bằng công thức đã có và kiểm tra bằng
ảnh raw từng pixel. Nếu input khác công thức, script dừng; không tự suy ra tâm
bằng bộ dò rồi coi là chuẩn.

## Tế bào sinh học

`blob_05.json` ban đầu mang trạng thái `PENDING_ANNOTATION`; danh sách đối tượng
rỗng không có nghĩa ảnh không có tế bào. Chỉ dùng để đánh giá sau khi đã gán,
rà soát và chuyển thành `READY`. Làm theo
[hướng dẫn gán nhãn](02_GAN_NHAN_TE_BAO.md).

## Định dạng và nguồn

Quy tắc TIFF float32 trong INSTRUCTIONS áp dụng cho kết quả vi phân/gradient/
Hessian. Ở đây GT gồm nhãn phân loại nhị phân hoặc mã vùng: PNG uint8 0/255,
TIFF uint16 giữ số vùng, `.mat` nguyên gốc và JSON tọa độ. Đây là các kiểu dữ
liệu nhãn, không phải bản đồ đạo hàm.

Các file nguồn được truy vết trong manifest; file gốc và nhãn thủ công khác
nội dung hiện có sẽ không bị script chuẩn bị tự ghi đè.

Quay lại [README ngày 05/11](../../README_DUC_05_11.md).
