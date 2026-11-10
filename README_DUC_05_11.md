# Bàn giao công việc của Đức — 05/11/2026

**STT 21 — Xây dựng ground truth** cho bộ 25 ảnh bàn giao ngày 02/11.
Yêu cầu: nhãn chuẩn tương ứng từng ảnh edge/ridge/blob, lưu trong `data/gt`
theo [INSTRUCTIONS.md](docs/references/INSTRUCTIONS.md).

## Đọc và mở file theo thứ tự

1. [01 — Bộ ground truth và cách mở từng định dạng](docs/05_11/01_GROUND_TRUTH.md).
2. [02 — Cách gán nhãn/chỉnh sửa ảnh tế bào](docs/05_11/02_GAN_NHAN_TE_BAO.md).
3. [Bảng kiểm kê trạng thái](data/metadata/ground_truth_inventory.csv): mở bằng
   Excel hoặc VS Code để xem ảnh nào có nhãn `READY`, ảnh nào đang chờ.
4. [Ảnh chồng nhãn](data/gt/previews): mở PNG bằng Photos để kiểm tra bằng mắt;
   tên preview khớp tên ảnh gốc trong `data/raw`.
5. [03 — Kiểm tra và danh sách bàn giao](docs/05_11/03_KIEM_TRA_BAN_GIAO.md).

## Trạng thái sau rà soát ngày 05/11

| Nhóm | Đã có nhãn | Nội dung |
| --- | ---: | --- |
| BSDS500 | 10/10 ảnh | `.mat` gốc với đủ người gán nhãn; xuất riêng biên và phân vùng từng người |
| DRIVE | 10/10 ảnh | Mặt nạ mạch máu và FOV đúng ID 21–30, giữ kích thước gốc |
| Blob tổng hợp | 4/4 ảnh | Tọa độ tâm, bán kính và cực tính từ công thức tạo ảnh |
| Tế bào `blob_05` | 1/1 ảnh | Duc đã xác nhận rà soát toàn ảnh: 276 đối tượng, 15 vùng bỏ qua, 0 gợi ý chưa duyệt |

**25/25 ảnh có nhãn READY.** Đã chạy lại công cụ chuẩn bị ground truth và nhận
mã thoát 0; CSV, manifest và ảnh chồng nhãn đã được cập nhật từ file nhãn mới nhất.
Ảnh tế bào sử dụng nhãn của nhóm, có gợi ý hỗ trợ rồi được Duc rà soát, không
phải nhãn chuẩn gốc của nhà cung cấp dataset.

Nếu cần chỉnh sửa thêm, mở `MO_GAN_NHAN_TE_BAO_05_11.cmd` theo hướng dẫn 02.
Công cụ đọc lại nhãn đã lưu, giữ lịch sử khi lưu thay đổi,
và chỉ ghi `READY` khi người gán nhãn xác nhận đã rà soát.
Đã bổ sung nút **Tao goi y** để tạo khung đề xuất, màu tím, cần người dùng kiểm
tra và duyệt. Có duyệt nhanh bằng Enter hoặc duyệt phần ảnh đang xem sau khi
sửa; nhãn đã vẽ được giữ lại. Xem mục **Làm nhanh bằng gợi ý** trong hướng dẫn 02.
Đây là nhãn thủ công của nhóm, cần được kiểm tra chất lượng; trạng thái `READY`
kiểm tra quy cách và xác nhận rà soát, không chứng minh độc lập độ chính xác
của mọi đối tượng.

## Cấu trúc file mới

```text
README_DUC_05_11.md
MO_GAN_NHAN_TE_BAO_05_11.cmd            ← nhấp đúp để mở công cụ tế bào
docs/05_11/
  01_GROUND_TRUTH.md                    ← cách mở/đọc bộ nhãn
  02_GAN_NHAN_TE_BAO.md                  ← thao tác khoanh và rà soát
  03_KIEM_TRA_BAN_GIAO.md                ← trạng thái cuối và file cần gửi
data/gt/
  README.md                            ← quy ước dữ liệu nhãn
  manifest.json                        ← ánh xạ input ↔ GT, trạng thái, checksum
  bsds/
    bsds_01.mat ... bsds_10.mat          ← nhãn gốc, đủ người gán nhãn
    bsds_01/annotator_01_boundaries.png  ← biên riêng từng người
    bsds_01/annotator_01_segments.tif    ← mã phân vùng uint16
    ...
  drive/drive_01_vessels.png             ← nhãn mạch máu
        drive_01_fov.png                 ← vùng quan sát
        ...
  blob/blob_01.json ... blob_05.json     ← tâm/bán kính; cả 5 ảnh đã READY
  previews/*_overlay.png                 ← ảnh chồng nhãn để xem, không phải mask
data/metadata/ground_truth_inventory.csv
data/sources/drive/1st_manual/*.gif       ← bản gốc nhãn DRIVE
data/sources/drive/mask/*.gif             ← bản gốc FOV DRIVE
src/eval/prepare_ground_truth.py         ← tạo/kiểm tra bộ nhãn và bảng kiểm kê
src/eval/annotate_cells.py               ← công cụ desktop gán nhãn thủ công
src/eval/cell_proposals.py               ← gợi ý khung, chờ người dùng duyệt
requirements-ground-truth.txt
tests/test_ground_truth.py               ← kiểm tra tính toàn vẹn/quy cách nhãn
tests/test_cell_proposals.py             ← kiểm tra bảo toàn nhãn và cờ duyệt
```

Mọi file cần cho phần này đã nằm trong dự án. Đường dẫn trong manifest GT và
CSV tính từ gốc dự án; `data/manifest.json` của ngày 02/11 vẫn mô tả input.

## Chạy và cập nhật

Từ PowerShell tại **gốc dự án**:

```powershell
.\.venv\Scripts\python.exe -m src.eval.prepare_ground_truth
```

Lệnh kiểm tra ảnh input với kiểm kê ngày 02/11, đọc nhãn gốc, tạo GT và preview,
cập nhật trạng thái. Không ghi đè nhãn khác dữ liệu hiện có. Nhãn thủ công đã
lưu được đọc lại và kiểm tra; không bị thay bằng JSON trống.

Mã thoát: `0` khi đủ 25 ảnh READY; `1` khi còn nhãn tế bào chờ/nháp;
`2` khi nguồn thiếu, sai kích thước, input thay đổi hoặc nhãn không hợp lệ.
Bộ nhãn sau khi Duc rà soát trả mã 0, đủ 25/25 READY.

Máy mới cần tạo `.venv`, sau đó cài:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ground-truth.txt
```

SciPy chỉ dùng `scipy.io` để đọc nhãn MATLAB. Không dùng `scipy.ndimage`,
gợi ý ngưỡng/liên thông chỉ hỗ trợ người dùng, phải rà soát trước khi thành
nhãn chuẩn. Chưa chạy Smoke Test, tính metric hoặc
vẽ biểu đồ thực nghiệm trong phần công việc này.

Kiểm tra các quy tắc nhãn:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_ground_truth.py -v
```

Quay lại [bàn giao ngày 02/11](README_DUC_02_11.md) để xem dataset đầu vào.
