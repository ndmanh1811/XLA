# Kết quả công việc 4 — Đức — phiên chuẩn hóa 10/11/2026

Đã tính lại từ raw/config và nhãn READY hiện tại; xem run_manifest.json để xác minh phiên chạy.

## Fiji so với Python

220 bản đồ Tầng 1: {'PASS': 35, 'FAIL': 185}. Chấm đúng ngưỡng gốc: relative error < 1e-4 **và** Pearson r > 0.9999.
FAIL là kết quả số học không đạt ngưỡng, không phải lỗi chạy chương trình. Không tự nới ngưỡng.
PSNR dùng MAX=255 chỉ cho Gaussian; ô PSNR của toán tử khác để trống có chủ đích.

| Smoke test σ=2 | Relative error | Pearson r | Trạng thái |
| --- | ---: | ---: | --- |
| lx | 0.000364441208 | 1 | FAIL |
| ly | 0.000364467449 | 1 | FAIL |
| lxx | 0.00404238322 | 0.9999955971 | FAIL |

## Precision/Recall/F1 so với ground truth

| Nguồn | Bài toán | Sigma | Macro Precision | Macro Recall | Macro F1 | Micro F1 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| python | edge_bsds | 1.0 | 0.431752 | 0.535166 | 0.455418 | — |
| python | edge_bsds | 2.0 | 0.490923 | 0.513399 | 0.477886 | — |
| python | edge_bsds | 4.0 | 0.476781 | 0.458608 | 0.441491 | — |
| python | edge_bsds | 8.0 | 0.387978 | 0.339731 | 0.343340 | — |
| python | ridge_drive | multiscale | 0.811157 | 0.352088 | 0.477382 | 0.486776 |
| python | blob_log | multiscale | 0.895563 | 0.901449 | 0.898418 | 0.519135 |
| fiji | edge_bsds | 1.0 | 0.431834 | 0.535166 | 0.455478 | — |
| fiji | edge_bsds | 2.0 | 0.490923 | 0.513399 | 0.477886 | — |
| fiji | edge_bsds | 4.0 | 0.476781 | 0.458608 | 0.441491 | — |
| fiji | edge_bsds | 8.0 | 0.387978 | 0.339731 | 0.343340 | — |
| fiji | ridge_drive | multiscale | 0.814269 | 0.347986 | 0.473863 | 0.483343 |
| fiji | blob_log | multiscale | 0.894237 | 0.900725 | 0.897373 | 0.514096 |

## Phạm vi và giới hạn

- Ngưỡng chọn trên tập Python nội bộ và áp nguyên vẹn cho Fiji. Đây là kết quả trên tập thực nghiệm đã dùng chọn ngưỡng, không phải điểm test độc lập chính thức BSDS/DRIVE.
- Edge: dung sai Euclidean ≤2 px; precision so với ít nhất một annotator, recall trung bình annotator. TP/FP/FN chung không áp dụng cho cách gộp đa annotator này.
- DRIVE: đánh giá trong giao các vùng FOV hợp lệ qua mọi scale, xói mòn theo support từ config; dùng cùng vùng cho hai nguồn.
- Blob: ghép một-một, tâm ≤2 px, bán kính sai ≤20%; bỏ dự đoán có tâm trong vùng ignore. Nhãn tế bào là nhãn nhóm đã được Đức rà soát, không phải nhãn chính thức do nhà cung cấp xác nhận.
- Detector blob hiện tại bỏ hai đầu lưới scale; giữ đúng 7 sigma đã chốt. Đối tượng ngoài dải kích thước vẫn thuộc GT và có thể làm giảm recall.
- Native FeatureJ Edges là bảng tham chiếu riêng; không trộn với so sánh hai nguồn cùng Canny.
- Bộ này chưa chạy biến thể nhiễu/crop hoặc vẽ biểu đồ/thời gian. Các CSV runtime cũ không được dùng làm bằng chứng đo lặp mới.
- Nguồn bàn giao duy nhất: outputs/metrics/duc_10_11. Các phiên duc_08_11 và pre_fix_10_11 là lịch sử, khác protocol; không trộn số liệu.
