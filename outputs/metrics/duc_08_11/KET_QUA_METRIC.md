# Kết quả công việc 4 — Đức — 08/11/2026

> [!ARCHIVED]
> Bản ghi này là **lịch sử (pre-disk-fix)**: sinh bởi mã cũ trước khi sửa dung sai BSDS từ ô vuông 5×5 thành đĩa Euclidean bán kính 2 px (`src/eval/bsds_threshold_grid.py`). Số BSDS ở đây (ví dụ 0.516600 tại σ=2.0) **không còn canonical**. Dùng `outputs/metrics/` làm nguồn chính (BSDS σ=2.0 = 0.477886). `tier2_summary.csv` đã được tính lại từ `tier2_results_both.csv` để nội bộ nhất quán.

Đã tính lại từ raw/config và nhãn READY hiện tại; xem run_manifest.json để xác minh phiên chạy.

## Fiji so với Python

220 bản đồ Tầng 1: {'STRICT': 35, 'RELAXED': 185, 'FAIL': 0}. Chấm đúng ngưỡng gốc: relative error < 1e-4 **và** Pearson r > 0.9999.
RELAXED là kết quả số học không đạt ngưỡng STRICT (rel < 1e-4) nhưng đạt ngưỡng RELAXED (rel < 1e-2 và r > 0.9999), không phải lỗi chạy chương trình. Không tự nới ngưỡng.
PSNR dùng MAX=255 chỉ cho Gaussian; ô PSNR của toán tử khác để trống có chủ đích.

| Smoke test σ=2 | Relative error | Pearson r | Trạng thái |
| --- | ---: | ---: | --- |
| lx | 0.000364441208 | 1 | FAIL |
| ly | 0.000364467449 | 1 | FAIL |
| lxx | 0.00404238322 | 0.9999955971 | FAIL |

## Precision/Recall/F1 so với ground truth

| Nguồn | Bài toán | Sigma | Macro Precision | Macro Recall | Macro F1 | Micro F1 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| python | edge_bsds | 1.0 | 0.421340 | 0.534874 | 0.490868 | — |
| python | edge_bsds | 2.0 | 0.478408 | 0.518773 | 0.516600 | — |
| python | edge_bsds | 4.0 | 0.477295 | 0.457956 | 0.490542 | — |
| python | edge_bsds | 8.0 | 0.509335 | 0.248494 | 0.395759 | — |
| python | ridge_drive | multiscale | 0.811157 | 0.352088 | 0.680633 | 0.486776 |
| python | blob_log | multiscale | 0.895563 | 0.901449 | 0.893023 | 0.4921 |
| fiji | edge_bsds | 1.0 | 0.421340 | 0.534874 | 0.490868 | — |
| fiji | edge_bsds | 2.0 | 0.478399 | 0.518750 | 0.516600 | — |
| fiji | edge_bsds | 4.0 | 0.477295 | 0.457956 | 0.490542 | — |
| fiji | edge_bsds | 8.0 | 0.509335 | 0.248494 | 0.395759 | — |
| fiji | ridge_drive | multiscale | 0.814269 | 0.347986 | 0.681651 | 0.483343 |
| fiji | blob_log | multiscale | 0.894237 | 0.900725 | 0.891901 | 0.514096 |

## Phạm vi và giới hạn

- Ngưỡng chọn trên tập Python nội bộ và áp nguyên vẹn cho Fiji. Đây là kết quả trên tập thực nghiệm đã dùng chọn ngưỡng, không phải điểm test độc lập chính thức BSDS/DRIVE.
- Edge: dung sai Euclidean ≤2 px; precision so với ít nhất một annotator, recall trung bình annotator. TP/FP/FN chung không áp dụng cho cách gộp đa annotator này.
- DRIVE: đánh giá trong giao các vùng FOV hợp lệ qua mọi scale, xói mòn theo support từ config; dùng cùng vùng cho hai nguồn.
- Blob: ghép một-một, tâm ≤2 px, bán kính sai ≤20%; bỏ dự đoán có tâm trong vùng ignore. Nhãn tế bào là nhãn nhóm đã được Đức rà soát, không phải nhãn chính thức do nhà cung cấp xác nhận.
- Detector blob hiện tại bỏ hai đầu lưới scale; giữ đúng 7 sigma đã chốt. Đối tượng ngoài dải kích thước vẫn thuộc GT và có thể làm giảm recall.
- Native FeatureJ Edges là bảng tham chiếu riêng; không trộn với so sánh hai nguồn cùng Canny.
- Bộ này chưa chạy biến thể nhiễu/crop hoặc vẽ biểu đồ/thời gian. Các CSV runtime cũ không được dùng làm bằng chứng đo lặp mới.
- Các CSV nằm trực tiếp ở outputs/metrics từ lần pull là kết quả lịch sử; bộ bàn giao này ở outputs/metrics/duc_08_11.
