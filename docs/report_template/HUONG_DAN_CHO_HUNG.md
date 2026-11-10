# Hưng — hoàn thiện báo cáo từ phiên thực nghiệm đã sửa

Đọc [bàn giao sau sửa](../10_11/sau_sua_loi/BAN_GIAO_SAU_SUA.md) và [README hiện hành](../../README_DUC_10_11.md). Số liệu chính chỉ lấy từ `outputs/metrics/duc_10_11`; biểu đồ/timing từ `outputs/analysis/duc_task5_10_11`.

## Nội dung đã đồng bộ

- Chương 5–6 có bảng BSDS theo sigma, P/R/F1 ridge/blob, tế bào và giới hạn nghiên cứu từ CSV hiện hành.
- 35 cặp đạt STRICT và 185 chưa đạt ngưỡng gốc; RELAXED là ngưỡng mở rộng, không phải 220 STRICT.
- Blob matching một–một và ignore; DRIVE dùng giao FOV qua scale; cùng 7 sigma cho hai nguồn.
- FeatureJ Edges là Canny; gamma=1 cho cả hai bậc; bậc 2 nhân sigma². Checksum toàn vẹn không chứng minh hai engine giống hệt byte.

Hai vùng `% BEGIN AUTO_CH5`…`% END AUTO_CH5` và `AUTO_CH6` được sinh lại từ `tools/sync_delivery_documents.py`. Muốn thêm phần bàn luận thủ công, đặt **ngoài các vùng AUTO**; nội dung đó được giữ khi đồng bộ lại. Nếu cần đổi câu trong vùng AUTO, sửa template của công cụ rồi chạy lại.

## Hưng còn hoàn thiện

1. Mở rộng Chương 2 theo bảng phân công: Gaussian/scale-space, đạo hàm, gradient, Hessian, scale normalization, mô hình Edge/Ridge/Blob, Structure Tensor/coherence/hướng; bổ sung diễn giải và trích dẫn có nguồn.
2. Phối hợp Lộc đưa hồ sơ đo k/border/normalization và ảnh workflow vào Chương 3; không coi vài ghi chú config là đủ hồ sơ đo.
3. Rà trích dẫn, ý nghĩa bảng/hình và kết luận. Không dùng lại DRIVE ~0.681 hoặc blob 0.4651/0.463 từ protocol cũ để thay vào bảng mới.
4. Đánh giá phạm vi: bộ hiện có chỉ là baseline nội bộ 25 ảnh, không phải test độc lập hay thực nghiệm nhiễu/kích thước mới.

## Biên dịch và nghiệm thu PDF

- Upload đủ `main.tex`, `references.bib` và thư mục `figures` lên Overleaf; không chỉ upload hai file TEX/BIB.
- Chọn compiler **XeLaTeX**. Preamble đã có font Unicode TeX Gyre; nhánh pdfLaTeX dùng T5/Vietnamese nếu môi trường có đủ gói.
- Biên dịch lại cho đến khi citation/ref ổn định, kiểm tra dấu tiếng Việt, bảng tràn cột, vị trí hình và khoảng 30 trang theo yêu cầu.
- Chưa có compiler LaTeX trên máy thực nghiệm: việc kiểm tra file/hình/ref ở đây không thay thế nghiệm thu PDF đã biên dịch.
- Xuất PDF cuối và rà slide PowerPoint 10 trang. Hạn chính thức trong đề là 19/11; nhóm hướng tới nộp trước 18/11.
