# Nguồn và đặc điểm dataset đầu vào — 02/11/2026

## BSDS500 — 10 ảnh tự nhiên

Nguồn: [UC Berkeley — BSDS500](https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/resources.html).
Archive nguồn: [BSR_bsds500.tgz](https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/BSR/BSR_bsds500.tgz),
lưu tại `sources/bsds500/archives/BSR_bsds500.tgz`.

SHA-256 archive: `97e49d31764f3912f0c4122707d53062ac9e783ba0f095e447a4d53c1a41af8e`.

Chọn 10 file JPG có tên đầu tiên theo thứ tự từ điển ở `images/train`:
100075, 100080, 100098, 103041, 104022, 105019, 105053, 106020, 106025, 108041.
Chỉ lấy RGB gốc ra `sources/bsds500/images/train`; không giải nén hay xử lý nhãn.
Nguồn gốc là JPEG của dataset; các **ảnh đầu vào bàn giao** là PNG lossless sau
khi chuyển xám BT.601 một lần, không tái mã hóa JPEG hay resize.

Đặc điểm: cảnh tự nhiên có cạnh vật thể và texture, mức tương phản khác nhau.
Giữ split train và ID gốc trong manifest để truy vết.

Tài liệu tham khảo do nguồn đề nghị: P. Arbelaez, M. Maire, C. Fowlkes and
J. Malik, “Contour Detection and Hierarchical Image Segmentation,” IEEE TPAMI,
vol. 33, no. 5, pp. 898–916, 2011.

## DRIVE — 10 ảnh võng mạc

Ảnh gốc đã được sao chép vào `sources/drive/images`, ID 21–30, gồm
`21_training.tif` đến `30_training.tif`. Từng bản sao đã được đối chiếu SHA-256
với ảnh có sẵn trong `trainingR03/training/images` trên máy tại lúc chuẩn bị.
Các thư mục `trainingR03`, `testR03` bên ngoài có sẵn từ trước; không phải sản
phẩm của công việc này. Dataset bàn giao sử dụng các bản sao trong dự án,
không cần đường dẫn tới hai thư mục bên ngoài để chạy lại.

Đặc điểm: mạch máu tối trên nền sáng, có phân nhánh và nhiều bề rộng.
Đầu vào chuẩn là kênh Green của ảnh RGB gốc, giữ nguyên kích thước.
Trong nhiệm vụ 02/11 chưa tạo bản sao nhãn hoặc mặt nạ FOV.

## Blob — 4 ảnh tổng hợp + 1 ảnh sinh học

`blob_01`/`blob_02`: disk sáng/tối, bán kính 3, 5, 7, 8 pixel.
`blob_03`/`blob_04`: Gaussian sáng/tối, độ lệch chuẩn 2, 2.8, 4, 5.7 pixel.
Đều là ảnh 256×256 tự tạo bằng NumPy, mã ở
[src/eval/prepare_data.py](../src/eval/prepare_data.py).
Thông số hình học ở đây mô tả cách tạo dataset, chưa xuất thành ground truth.

`blob_05`: ảnh tế bào người `human_mitosis`, xám uint8 512×512. Theo
[tài liệu scikit-image](https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.human_mitosis),
ảnh do David Root cung cấp, giấy phép CC0. Có các cấu trúc tế bào/nhân sáng trên
nền tối; dùng để khảo sát blob sinh học ngoài mô hình disk/Gaussian lý tưởng.

Tệp tải từ [kho dữ liệu chính thức scikit-image, commit cố định](https://gitlab.com/scikit-image/data/-/raw/2cdc5ce89b334d28f06a58c9f0ca21aa6992a5ba/AS_09125_050116030001_D03f00d0.tif).
Lưu tại `sources/biological/mitosis.tif`, không resize hay đổi dải cường độ.
SHA-256: `2751ba667c4067c5d30817cff004aa06f6f6287f1cdbb5b8c9c6a500308cb456`,
đã đối chiếu [registry chính thức](https://github.com/scikit-image/scikit-image/blob/v0.25.2/skimage/data/_registry.py).

## Kiểm kê bàn giao

25 ảnh grayscale uint8 lossless tại `raw`; tên, đặc điểm và nguồn trong
`manifest.json`; kích thước và checksum trong `metadata/dataset_inventory.csv`.
5 ảnh hiệu chuẩn ở `calib` là ảnh đầu vào bổ sung theo bước chuẩn bị ngày 1–2,
không tính vào 25 ảnh dataset. Chưa chạy thuật toán hay tạo số liệu thực nghiệm.

Các đường dẫn ở tài liệu này tính từ thư mục `data`, trừ liên kết được ghi rõ.
Ảnh gốc có thể là RGB JPEG/TIFF theo định dạng nguồn; tất cả **input chạy thuật
toán** trong `raw` đều là grayscale uint8 PNG lossless theo INSTRUCTIONS.
Mở [bàn giao ngày 02/11](../README_DUC_02_11.md) để xem rõ hai công việc.

## Bổ sung nhãn ngày 05/11

Nhãn mạch máu/FOV gốc DRIVE đã được sao chép thêm vào `sources/drive/1st_manual`
và `sources/drive/mask`, đúng 10 ID đang dùng, kiểm tra SHA-256 với nguồn có sẵn.
Ground truth BSDS được trích đúng các ID trên từ archive, giữ mọi annotator.
Đầu ra GT và trạng thái riêng xem [bàn giao ngày 05/11](../README_DUC_05_11.md).
