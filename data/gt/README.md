# Ground truth — công việc 21, hạn 05/11/2026

Hướng dẫn mở file và trạng thái: [README_DUC_05_11.md](../../README_DUC_05_11.md).

Cập nhật sau rà soát ngày 05/11: **25/25 ảnh READY**. `blob_05` đã được Duc xác
nhận rà soát toàn ảnh, có 276 đối tượng và 15 vùng bỏ qua, không còn gợi ý chờ
duyệt. Manifest, CSV và preview đã cập nhật; xem
[danh sách bàn giao](../../docs/05_11/03_KIEM_TRA_BAN_GIAO.md).

- `manifest.json`: 25 bản ghi, tương ứng tên ảnh trong `data/raw`.
  Đường dẫn file trong manifest tính từ gốc dự án, có SHA-256 input và nhãn.
- `bsds/`: giữ `.mat` gốc với đủ người gán nhãn. Trong từng thư mục ảnh,
  `annotator_NN_boundaries.png` là mask uint8 0/255;
  `annotator_NN_segments.tif` là nhãn vùng uint16.
- `drive/`: `*_vessels.png` và `*_fov.png` cùng kích thước input, uint8 0/255.
  FOV là bản gốc, chưa xói mòn.
- `blob/`: JSON tâm x/cột, y/hàng, bán kính pixel và cực tính.
  Gaussian tổng hợp dùng bán kính `sqrt(2)*sigma`; sinh học dùng bán kính
  ellipse tương đương `sqrt(bbox_width*bbox_height)/2`.
- `previews/`: ảnh chồng nhãn để xem; preview BSDS dùng annotator 01.

Trạng thái `READY` áp dụng cho nhãn gốc/giải tích đã kiểm tra quy cách hoặc
nhãn thủ công được người dùng xác nhận đã rà soát. `PENDING_ANNOTATION`, `DRAFT`
không được dùng làm ground truth cho đánh giá. `blob_05` ban đầu chờ gán nhãn;
file JSON rỗng không phải một ảnh được xác nhận không có đối tượng.
Gợi ý tự động từ công cụ gán nhãn mang `annotation_method` và
`proposal_reviewed=false`; chỉ sau khi người dùng rà soát mới chuyển cờ thành
true. Không thể đánh dấu ảnh READY nếu còn gợi ý chưa duyệt. Vòng tím trong
preview là gợi ý chờ duyệt, khác vòng xanh đã gán/duyệt.

Không sử dụng preview màu như mask và không gộp các annotator BSDS để thay cho
nhãn riêng. Dùng lại `prepare_ground_truth` để cập nhật manifest sau khi chỉnh
nhãn tế bào. Lịch sử chỉnh nhãn, nếu có, nằm trong `blob/history`.
