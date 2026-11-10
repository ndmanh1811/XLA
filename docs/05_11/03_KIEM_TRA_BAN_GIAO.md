# Kiểm tra và bàn giao ground truth — 05/11/2026

Đức đã xác nhận rà soát toàn ảnh tế bào. File lưu ghi reviewer `Duc`,
status `READY`, reviewed `true`. Đã cập nhật toàn bộ manifest, bảng kiểm kê
và ảnh chồng nhãn bằng `python -m src.eval.prepare_ground_truth`.
Kết quả chuẩn bị: **25/25 READY**, mã thoát 0.

| Nhóm | Số ảnh | Nhãn bàn giao |
| --- | ---: | --- |
| BSDS500 | 10 | Giữ đủ 56 bộ nhãn của người gán nhãn, `.mat` gốc và các mặt nạ/phân vùng xuất riêng |
| DRIVE | 10 | 10 mask mạch máu + 10 FOV, kích thước gốc, chưa xói mòn |
| Blob tổng hợp | 4 | 16 đối tượng giải tích, tâm và bán kính theo mô hình |
| Tế bào sinh học | 1 | 276 đối tượng, 15 vùng bỏ qua, 0 gợi ý chưa duyệt; người rà soát: Duc |

READY xác nhận file hợp lệ và trạng thái rà soát đã khai báo. Nhãn tế bào là
nhãn gán bởi nhóm với hỗ trợ gợi ý ngưỡng/liên thông, cần mô tả đúng nguồn này
trong báo cáo sau này. Các vùng bỏ qua phải áp dụng giống nhau cho hai nhánh
Python/Fiji khi đánh giá; không tính các vùng đó như nền âm đã xác nhận.

## Mở để kiểm tra lần cuối

- [Bảng kiểm kê Excel/CSV](../../data/metadata/ground_truth_inventory.csv): tất cả
  25 hàng phải có status READY; hàng blob_05 có objects=276.
- [Ảnh tế bào chồng nhãn](../../data/gt/previews/blob_05_overlay.png): xanh là
  đối tượng đã gán/duyệt; cam là vùng bỏ qua. Preview dùng để xem trực quan.
- [Nhãn tế bào JSON](../../data/gt/blob/blob_05.json): tâm, bán kính, khung bao,
  vùng bỏ qua, thông tin gợi ý và người rà soát.
- [Manifest GT](../../data/gt/manifest.json): liên kết ảnh với file nhãn và
  checksum. Mọi đường dẫn tính từ gốc dự án.

## File gửi bàn giao công việc 21

1. Thư mục `data/gt/`, gồm nhãn và manifest. `blob/history` lưu lịch sử để truy
   vết; không đưa các JSON lịch sử vào tập nhãn dùng để đánh giá.
2. `data/metadata/ground_truth_inventory.csv`.
3. `README_DUC_05_11.md` và `docs/05_11/` để người nhận biết cách mở, cách đọc
   và các quy ước nhãn/vùng bỏ qua.
4. Người nhận cần cùng bộ `data/raw/` đã bàn giao ngày 02/11. Nếu gửi cho người
   chưa có dataset, gửi kèm thư mục đó.

Để chạy lại chuẩn bị/kiểm tra nhãn, gửi thêm script `src/eval`, các nguồn nhãn
BSDS/DRIVE trong `data/sources`, `data/manifest.json`, bảng kiểm kê dataset và
`requirements-ground-truth.txt`, hoặc chuyển nguyên thư mục dự án.

Nhiệm vụ 21 có đủ sản phẩm bàn giao. Smoke Test, metric và biểu đồ là các bước
khác; bản kiểm tra này không báo điểm chính xác của thuật toán phát hiện.

Nếu sửa nhãn sau lần bàn giao này: lưu nháp, rà soát lại và cập nhật bảng kiểm
kê bằng script trước khi gửi phiên bản mới. Quay lại
[README ngày 05/11](../../README_DUC_05_11.md).
