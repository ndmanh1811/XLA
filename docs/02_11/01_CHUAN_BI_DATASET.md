# Công việc 20 — Chuẩn bị dataset — Đức — 02/11/2026

Đầu ra theo bảng phân công: bộ ảnh có cạnh, đường/gờ và blob, kèm mô tả nguồn
và đặc điểm. Quy mô và định dạng áp dụng theo
[INSTRUCTIONS.md](../references/INSTRUCTIONS.md), mục vai trò Dữ liệu & Đánh giá.

## Bộ dữ liệu bàn giao

| Nhóm ảnh | Tên trong data/raw | Số lượng | Chuẩn bị đầu vào |
| --- | --- | ---: | --- |
| BSDS500 | bsds_01.png–bsds_10.png | 10 | RGB gốc → grayscale BT.601 một lần |
| DRIVE | drive_01.png–drive_10.png | 10 | Lấy đúng kênh Green của RGB gốc |
| Blob tổng hợp | blob_01.png–blob_04.png | 4 | NumPy tạo disk/Gaussian sáng và tối |
| Blob sinh học | blob_05.png | 1 | Giữ nguyên grayscale uint8 của ảnh tế bào |

25 ảnh PNG lossless, một kênh uint8, kích thước tối thiểu 256×256, giữ kích
thước gốc. Dùng chính các file này cho cả Python và Fiji. Python đọc sang
float64 khi tính toán; không chuẩn hóa riêng input của từng nhánh.

Phép BT.601 là `round(0.299R + 0.587G + 0.114B)`. Script tính tử số nguyên
`299R + 587G + 114B`, chia 1000, làm tròn gần nhất với trường hợp hòa .5 về
số chẵn để tránh sai khác do thứ tự cộng số thực. DRIVE không chuyển xám RGB
bằng công thức này, chỉ lấy kênh Green.

Chi tiết ID gốc, cách chọn ảnh, đặc điểm và nguồn tham khảo:
[data/SOURCES.md](../../data/SOURCES.md).

## Vị trí các file

- [data/raw](../../data/raw): 25 ảnh đầu vào đã chuẩn hóa.
- [data/sources](../../data/sources): ảnh gốc chia theo `bsds500`, `drive`,
  `biological`. Archive BSDS ở `bsds500/archives`, RGB chọn từ archive ở
  `bsds500/images/train`. 10 RGB DRIVE đã được sao chép vào `drive/images` và
  đối chiếu checksum với nguồn trên máy.
- [manifest.json](../../data/manifest.json): danh mục 25 ảnh, nguồn, đặc điểm,
  phép tạo và cực tính blob. Đường dẫn `source` tính từ thư mục `data`, đều
  nằm trong dự án.
- [dataset_inventory.csv](../../data/metadata/dataset_inventory.csv): tên,
  nguồn, kích thước, dtype, min/max, cách chuyển đổi và SHA-256. Các đường dẫn
  file trong bảng tính từ gốc dự án. Đây là bảng kiểm kê, không phải metric.
- [prepare_data.py](../../src/eval/prepare_data.py): script chuẩn bị theo vị trí
  yêu cầu của INSTRUCTIONS; [common.py](../../src/eval/common.py) hỗ trợ I/O.

## Ảnh đầu vào hiệu chuẩn ngày 1–2

Theo checklist chuẩn bị của INSTRUCTIONS, `data/calib` có:

| File | Nội dung | Kích thước |
| --- | --- | --- |
| ramp.tif | I=x | 256×256 |
| parabola.tif | I=x²/2 | 256×256 |
| saddle.tif | I=x²/2−y² | 256×256 |
| dirac.tif | Xung đơn vị ở tâm | 101×101 |
| bright_border.tif | Viền sáng | 256×256 |

Đều là TIFF float32 không nén; ảnh đa thức dùng tọa độ gốc ở tâm. 5 ảnh này
là input bổ sung, không tính vào 25 ảnh. Bước này chuẩn bị file cho người làm
Fiji; chưa thực hiện phép đo FeatureJ.

## Chạy lại chuẩn bị dữ liệu

Các lệnh chạy từ **gốc dự án**, không chạy từ thư mục tài liệu.

Trên máy hiện tại:

```powershell
.\.venv\Scripts\python.exe -m src.eval.prepare_data --manifest data/manifest.json
```

Trên máy mới:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-data.txt
.\.venv\Scripts\python.exe -m src.eval.prepare_data --manifest data/manifest.json
```

Script đọc ảnh nguồn đã nằm trong `data/sources`, tạo hoặc dùng lại ảnh giống
hệt dữ liệu hiện có, rồi cập nhật bảng kiểm kê. Nếu ảnh hiện có khác nội dung
cần tạo, script từ chối ghi đè. Mã thoát 0 khi đủ 25 ảnh, 1 nếu thiếu/sai ảnh.
Để chỉ chuẩn bị ảnh hiệu chuẩn, dùng `--calib-only`.

## Giới hạn nhiệm vụ

Ground truth có lịch riêng sau ngày 02/11 theo bảng phân công. Vì vậy lần
bàn giao này chỉ có input và metadata; script không đọc/xuất nhãn hay FOV.
Smoke Test, benchmark, metric và biểu đồ cũng chưa triển khai. Công việc 22
được bàn giao riêng tại [02 — Thiết kế thí nghiệm](02_THIET_KE_THI_NGHIEM.md).
