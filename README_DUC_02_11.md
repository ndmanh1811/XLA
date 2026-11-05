# Bàn giao hai công việc của Đức — 02/11/2026

Đề tài: Phát hiện đặc trưng ảnh đa tỷ lệ bằng đạo hàm Gaussian — FeatureJ.
Vai trò: Dữ liệu & Đánh giá thực nghiệm.

| Công việc trong bảng phân công | Sản phẩm bàn giao | Hướng dẫn |
| --- | --- | --- |
| STT 20 — Chuẩn bị dataset | 25 ảnh đầu vào chuẩn, nguồn ảnh, mô tả và kiểm kê; 5 ảnh hiệu chuẩn theo giai đoạn chuẩn bị ngày 1–2 | [01 — Chuẩn bị dataset](docs/02_11/01_CHUAN_BI_DATASET.md) |
| STT 22 — Thiết kế thí nghiệm và chốt tham số | Danh sách sigma, lưới ngưỡng khảo sát, kịch bản nhiễu/kích thước và quy tắc dùng chung | [02 — Thiết kế thí nghiệm](docs/02_11/02_THIET_KE_THI_NGHIEM.md) |

## Cấu trúc bàn giao

```text
README_DUC_02_11.md                  ← đọc từ đây
docs/
  02_11/
    01_CHUAN_BI_DATASET.md            ← công việc 20
    02_THIET_KE_THI_NGHIEM.md         ← công việc 22
  references/
    INSTRUCTIONS.md                  ← bản sao nguyên văn tài liệu đã gửi
    yeucau.md
data/
  raw/                              ← 25 PNG grayscale uint8 cho Python và Fiji
  calib/                            ← 5 TIFF float32 không nén để hiệu chuẩn
  sources/                          ← ảnh gốc theo từng bộ dữ liệu
    bsds500/
      archives/BSR_bsds500.tgz       ← archive nguồn của công việc 20
      images/train/                 ← 10 RGB gốc đã chọn
    drive/images/                   ← 10 RGB gốc, ID 21–30
    biological/mitosis.tif           ← ảnh tế bào gốc
  metadata/dataset_inventory.csv     ← kiểm kê file, kích thước và checksum
  manifest.json                     ← danh mục 25 ảnh và đường dẫn nguồn
  SOURCES.md                        ← nguồn và đặc điểm các nhóm ảnh
src/eval/
  prepare_data.py                    ← chuẩn bị dataset đúng vị trí INSTRUCTIONS
  common.py                         ← đọc/ghi và checksum phục vụ chuẩn bị dữ liệu
requirements-data.txt                ← thư viện cho công việc 20
config.yaml                          ← cấu hình chung hiện có của nhóm
```

Giữ `data/raw`, `data/calib` và `src/eval/prepare_data.py` đúng vị trí theo
[INSTRUCTIONS.md](docs/references/INSTRUCTIONS.md). Hai công việc được phân biệt
bằng tài liệu bàn giao; không nhân đôi dataset vào hai thư mục công việc.

## Trạng thái và phạm vi

- Đã chuẩn bị đủ 25 ảnh: 10 BSDS500 + 10 DRIVE + 4 blob tổng hợp + 1 ảnh tế bào.
  Nguồn và đặc điểm ở [data/SOURCES.md](data/SOURCES.md); bảng file ở
  [dataset_inventory.csv](data/metadata/dataset_inventory.csv).
- Tất cả ảnh nguồn cần để chạy lại chuẩn bị dataset đã ở trong dự án. Manifest
  dùng đường dẫn tương đối tính từ `data`; đường dẫn source/output trong bảng
  kiểm kê tính từ gốc dự án. Chuyển nguyên thư mục dự án sẽ giữ được các đường dẫn.
- Công việc 22 bàn giao **thiết kế**: lưới khảo sát được ghi trước; chưa có ngưỡng
  tối ưu đã đo. Thông số FeatureJ tham chiếu `config.yaml`, cần bằng chứng hiệu
  chuẩn từ người phụ trách Fiji; chưa coi bản thiết kế là chứng nhận phép đo.
- Theo yêu cầu của Đức, chỉ triển khai hai việc hạn 02/11. Ground truth, Smoke
  Test, chạy detector, metric và biểu đồ thuộc các mốc sau, chưa triển khai.
  Code lõi trong `src/core` là phần hiện có của thành viên khác.
- Chưa nhận được `debai.md`, `quyuoc.md`. Căn cứ hiện có là hai tài liệu nguyên
  văn trong `docs/references`, đề bài Đức gửi trong chat và bảng phân công.

## Chạy lại công việc 20

Mở PowerShell tại gốc dự án:

```powershell
.\.venv\Scripts\python.exe -m src.eval.prepare_data --manifest data/manifest.json
```

Trên máy khác, cài môi trường theo hướng dẫn trong tài liệu công việc 20.
Thư mục `.venv` là môi trường của máy hiện tại, cần tạo lại khi chuyển máy.

## Công việc tiếp theo ngày 05/11

Tài liệu này giữ phạm vi bàn giao ngày 02/11. Phần ground truth (công việc 21)
được triển khai riêng tại [README_DUC_05_11.md](README_DUC_05_11.md).
