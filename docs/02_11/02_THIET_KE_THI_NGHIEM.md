# Thiết kế thí nghiệm và tham số — Đức — 02/11/2026

Sản phẩm của STT 22 trong bảng phân công, áp dụng theo
[INSTRUCTIONS.md](../references/INSTRUCTIONS.md). Đây là thiết kế để nhóm dùng chung;
chưa thực thi thí nghiệm, chọn ngưỡng tối ưu từ kết quả hay tính metric.

## Mục tiêu và dữ liệu cố định

So sánh kết quả Python và FeatureJ trên cùng input; khảo sát tác động của sigma,
ngưỡng, nhiễu và kích thước ảnh tới việc phát hiện cạnh, đường/gờ và blob.

| Nhóm | Tên nội bộ | Số lượng | Đặc điểm khảo sát |
| --- | --- | ---: | --- |
| Cạnh | bsds_01–bsds_10 | 10 | Ảnh tự nhiên, cạnh vật thể và texture |
| Đường/gờ | drive_01–drive_10 | 10 | Mạch máu tối, phân nhánh, nhiều bề rộng |
| Blob | blob_01–blob_04 | 4 | Disk/Gaussian sáng và tối, nhiều kích thước |
| Blob sinh học | blob_05 | 1 | Tế bào sáng trên nền tối, độ tương phản không đều |

Danh mục ảnh và nguồn được cố định trong
[data/manifest.json](../../data/manifest.json). BSDS dùng split
train và DRIVE dùng training; nếu về sau chọn ngưỡng trên các ảnh này, kết quả
phải mô tả là thực nghiệm nội bộ, không coi là điểm trên tập test chính thức.

Năm ảnh đại diện đã quy định trong config: `bsds_01`, `bsds_02`, `drive_01`,
`blob_01`, `blob_02`. Chưa chạy đối chuẩn trên các ảnh này trong phạm vi 02/11.

## Danh sách sigma và quy ước dùng chung

| Tham số thiết kế | Giá trị |
| --- | --- |
| Sigma chuẩn, đơn vị pixel | 1.0, 2.0, 4.0, 8.0 |
| Sigma dày cho Laplacian/blob | 1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0 |
| Structure Tensor: (sigma_d, sigma_i) | (1.0, 3.0), (2.0, 6.0) |
| Đầu vào chung | Grayscale uint8 lossless, dải 0–255 |
| Dữ liệu tính toán Python | float64, không chia 255 |
| Đầu ra vi phân dự kiến | TIFF float32 không nén |
| Quy ước trục | img[y,x]; x=cột, y=hàng |

Danh sách tỷ lệ ở trên lấy từ [config.yaml](../../config.yaml) hiện có. Tham số đo FeatureJ vẫn
phải lấy từ file config khi triển khai; không tự điền giá trị thay cho phép đo.
Không sửa hay đo mới config trong nhiệm vụ này.
Nếu thông số đo cần dùng còn `null`, bước tính toán tương ứng phải báo lỗi và
dừng theo INSTRUCTIONS; bản thiết kế không cung cấp giá trị thay thế.

Config hiện ghi k theo bậc = (3,4,4), biên `mirror`, thứ tự trị riêng `absolute`,
các cờ chuẩn hóa FeatureJ = false. Đây là **tham chiếu cấu hình sẵn có**, không
phải kết quả đo do Đức thực hiện. Cần nhóm phụ trách Fiji xác nhận bằng chứng đo.
Comment config nói `floor(k*sigma)+1`, trong khi tài liệu yêu cầu `ceil(k*sigma)`;
khác biệt này còn cần xác minh, không coi là đã chốt tương đương số học.

## Lưới ngưỡng và quy tắc lựa chọn đã định trước

Các giá trị dưới đây là lưới khảo sát được thiết kế ngày 02/11, không phải
ngưỡng tối ưu đã đo. Lựa chọn tối ưu chỉ thực hiện ở nhiệm vụ đánh giá sau này.

| Bộ phát hiện | Tham số cố định hoặc lưới khảo sát |
| --- | --- |
| Edge/Canny | p_low ∈ {40,50,60,70}; p_high ∈ {80,90,95}; chỉ cặp p_low < p_high |
| Ridge/Frangi | beta=0.5; c=0.5×max(sqrt(lambda1²+lambda2²)); ngưỡng vesselness ∈ {0.05,0.10,0.20,0.30,0.50} |
| Blob/LoG | Ngưỡng độ lớn đáp ứng chuẩn hóa sigma²×Laplacian ∈ {0.5,1.0,2.0,5.0}, cùng đơn vị cường độ input 0–255 |

- Phân vị Canny tính trên độ lớn gradient của ảnh, không diễn giải là ngưỡng
  cường độ tuyệt đối. Một cặp ngưỡng dùng giống nhau cho Python và Fiji tại
  cùng sigma; FeatureJ Edges nguyên bản là nhánh tham khảo với đơn vị riêng.
- Quy tắc dự kiến: chọn bộ ngưỡng cho từng sigma bằng F1 trung bình trên nhánh
  Python của tập thực nghiệm nội bộ, rồi áp cùng bộ ngưỡng cho nhánh Fiji.
  Nếu hòa điểm, dùng thứ tự lưới ở trên để chọn cặp xuất hiện trước. Không chọn
  bộ ngưỡng riêng cho mỗi nguồn rồi coi đó là so sánh cùng điều kiện.
- DRIVE có cực tính `dark`; sắp trị riêng theo độ lớn bên trong detector;
  lấy max qua sigma trên bản đồ đã chuẩn hóa sigma².
- Blob có cực tính theo manifest; sáng tìm cực tiểu, tối tìm cực đại.
  Kích thước blob tổng hợp được chọn để cực trị tỷ lệ nằm bên trong lưới sigma,
  tránh phải chấp nhận cực trị ở hai đầu lưới. Blob sinh học có thể chứa đối tượng
  ngoài dải kích thước này; đây là điều kiện cần ghi nhận khi đánh giá sau này.
- Tầng đối chuẩn số học dự kiến giữ nguyên bản đồ thô. Chuẩn hóa theo sigma
  chỉ thực hiện ở tầng phát hiện đặc trưng, có xét cờ từng lệnh Fiji để tránh
  nhân hai lần. Chưa viết hàm chuẩn hóa hay chạy các bộ phát hiện ở nhiệm vụ này.

## Kịch bản nhiễu và kích thước

| Kịch bản | Thiết kế |
| --- | --- |
| Cơ sở | Toàn bộ 25 ảnh, giữ nguyên kích thước và cường độ |
| Nhiễu Gaussian | std ∈ {0,5,10,20} trên dải 0–255; mean=0; seed=42 |
| Khảo sát kích thước | Giữ ảnh gốc; dùng thêm crop giữa 256×256 trên 5 ảnh đại diện, cùng tọa độ cho hai nhánh |
| Thời gian chạy | Đo riêng phép toán, tách I/O; 1 lần làm nóng, 5 lần đo; cùng ảnh và sigma; lưu môi trường chạy |

Công thức nhiễu dự kiến: `I_noise = clip(round(I + n), 0, 255).astype(uint8)`.
Mỗi ảnh nhiễu sẽ được tạo một lần, hai nhánh đọc cùng file. Kịch bản cơ sở giữ
nguyên ảnh ở `data/raw`; biến thể chỉ tạo khi tới lịch chạy thực nghiệm.
Crop 256×256 không resize và không thay đổi đơn vị sigma; crop nào trùng ảnh
gốc 256×256 thì không đếm như một mẫu độc lập mới.
Nếu có GT ở giai đoạn sau, phải biến đổi/crop nhãn theo đúng ảnh tương ứng.

Chưa tạo ảnh nhiễu, crop, ground truth, file runtime, metric hay biểu đồ trong
ngày 02/11. Các quy tắc trên là sản phẩm thiết kế của STT 22.

Sản phẩm dataset của STT 20 nằm tại
[01 — Chuẩn bị dataset](01_CHUAN_BI_DATASET.md). Mọi đường dẫn inline trong
bản thiết kế được tính từ gốc dự án. Quay lại
[bàn giao hai công việc ngày 02/11](../../README_DUC_02_11.md).
