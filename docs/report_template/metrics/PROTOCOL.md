# Protocol hiện hành: duc_10_11_v1

Nguồn chính: **`outputs/metrics/duc_10_11`**. Pipeline duy nhất: `python -m src.eval.run_metrics`; `benchmark_tier2.py` chuyển tiếp sang cùng pipeline. Các CSV cũ ở `history/pre_fix_10_11` và bộ `duc_08_11` là lịch sử, khác protocol.

## Cấu hình và normalization

Thông số FeatureJ/scale lấy từ `config.yaml`, thiếu/null phải dừng. Tính float64, ghi TIFF float32 không nén. Trục x=cột, y=hàng.

Tầng 1 giữ đáp ứng thô. Tầng 2 dùng một hàm `normalize_scale`: với gamma=1, bậc n nhân sigma^n. Nguồn Python luôn nhân; nguồn Fiji chỉ bỏ nhân khi `featurej_normalized.<lệnh>` là true. Không nhầm bậc 2 với gamma=2.

## BSDS

- Đĩa Euclidean 2px; precision so với ít nhất một annotator, recall trung bình annotator.
- Ngưỡng phân vị trên NMS khác 0; ảnh NMS rỗng vẫn được tính với P/R/F1=0.
- Grid thô p_low=5..85 bước5, p_high=50..95 bước5; tinh ±2 bước1 quanh cặp tốt nhất. Chọn trên Python, tie-break F1/precision/ngưỡng cao hơn, đóng băng cho Fiji.
- Native FeatureJ Edges dùng grid tuyệt đối riêng trong `src/eval/metrics_protocol.yaml`; không trộn với cặp fair Canny. FeatureJ Edges là Canny, không phải zero-crossing Laplacian.

## DRIVE

- Frangi dark; beta=.5, c=.5*max(S), Hessian đã chuẩn hóa.
- Mỗi scale loại vùng ngoài FOV xói mòn theo support; vùng chấm cuối là giao vùng hợp lệ của tất cả scale, hiện bán kính 32px. Không gõ cứng k hoặc sigma=2.
- Quét các ngưỡng tuyệt đối đã công bố `[.05,.1,.2,.3,.5]` trên Python; áp nguyên ngưỡng và vùng chấm cho Fiji.
- Khác protocol cũ dùng p85/FOV8px; không so trực tiếp điểm giữa hai protocol như cùng phép đo.

## Blob

- Cùng 7 sigma config; không thêm 11.3 riêng cho Python trong cặp so sánh.
- LoG chuẩn hóa; cực tính theo GT; threshold grid `[.5,1,2,5]`, chọn Python rồi đóng băng.
- Matching một–một maximum cardinality, tâm ≤2px và sai số bán kính ≤20%.
- Áp vùng ignore trước khi đếm FP/GT; lưu cặp khớp và chỉ số bị loại trong `blob_matching_audit.json`.
- Báo cáo cả macro và micro F1. `blob_05` là nhãn nhóm đã rà soát, không phải nhãn chuyên gia độc lập.

## Đối chuẩn và timing

- STRICT: relative max error <1e-4 và Pearson>0.9999 sau crop. Ref=0 hoặc Pearson không xác định không tự PASS. PSNR MAX=255 chỉ cho Gaussian.
- 35 STRICT/185 chưa đạt ngưỡng gốc; nếu dùng RELAXED1e-2 phải ghi là mở rộng, không sửa chuẩn gốc ngầm.
- Pipeline chấm/morphology dùng NumPy, không SciPy ndimage. SciPy ndimage chỉ ở test độc lập/benchmark thời gian.
- Timing mới: 357 case/nguồn, 1 warm-up+5 lần đo; Java API headless, không GUI/I/O. Fingerprint và mẫu thô ở `outputs/analysis/duc_task5_10_11/runtime`.
- Ngưỡng chọn trên tập nội bộ; chưa có điểm test độc lập hoặc kết quả nhiễu/đổi kích thước.
