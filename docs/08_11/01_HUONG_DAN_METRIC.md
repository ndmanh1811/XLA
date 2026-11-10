# Hướng dẫn công việc 4 — Tính metric định lượng

Quay về [README_DUC_08_11.md](../../README_DUC_08_11.md). Quy chuẩn áp dụng:
[INSTRUCTIONS.md](../../INSTRUCTIONS.md), [quyuoc.md](../../quyuoc.md) ở gốc dự
án và STT 23 trong bảng phân công. Không dùng các bản tài liệu cũ để thay
tham số đã cập nhật của nhóm.

## 1. Phạm vi và cách chạy

Chạy tại gốc dự án:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -u -m src.eval.run_metrics
```

Máy khác cần môi trường Python có NumPy, Pillow, tifffile và PyYAML. Có thể
cài các dependency dự án bằng `python -m pip install -r requirements.txt`.
SciPy chỉ được dùng làm oracle kiểm thử, không có trong đường tính metric
chính của bộ bàn giao này.

Pipeline thực hiện:

1. Kiểm tra đủ 25 raw uint8 và 25 GT READY, kiểm tra SHA-256 tất cả input/nhãn.
   Nhãn tế bào chưa duyệt hoặc config thiếu/null sẽ dừng, không tự điền mặc định.
2. Chạy code `src/core/batch_runner.py` đã có của nhóm để tạo TIFF float32
   không nén trong `outputs/python/`, cùng raw và config.
3. Kiểm tra mọi bản đồ cần dùng của hai nguồn: đủ file, kích thước, dtype,
   không nén, hữu hạn. Lưu danh sách và SHA-256 vào `map_manifest.csv`.
4. Chấm Tầng 1; chấm Tầng 2; kiểm tra input/nhãn/config/code/bản đồ không
   thay đổi trong thời gian chạy. Sau đó mới đặt `run_manifest.status=COMPLETE`.

Nếu chạy lỗi, `status=ERROR`; không lấy một bảng đã ghi dở làm kết quả hoàn
chỉnh. Chạy lại lệnh đầy đủ sau khi xử lý nguyên nhân. `--skip-generate` chỉ
dùng lại TIFF Python nếu hồ sơ code/config/raw trùng phiên sinh trước đó;
chạy mặc định luôn sinh lại để tránh dùng nhầm file cũ.

## 2. Tầng 1 — Fiji vs Python

Tham chiếu chính: `outputs/fiji/` do ImageJ macro xuất. Bộ Java trong ZIP vẫn
được giữ nguyên, không trộn hai nguồn tham chiếu trong cùng bảng. Chấm 5 ảnh
trong config × (10 toán tử × 4 sigma + 2 trị riêng ST × 2 cặp scale) = **220 cặp**.

| Cột | Ý nghĩa |
| --- | --- |
| `python_file`, `fiji_file` | Cặp TIFF thực tế được đọc |
| `crop_px`, `region`, `n_pixels` | Support bỏ biên, vùng lõi/biên và số pixel chấm |
| `mse` | Trung bình bình phương `(Python − Fiji)` |
| `mae` | Trung bình trị tuyệt đối sai số |
| `rmse` | Căn bậc hai MSE |
| `max_error` | Sai số tuyệt đối lớn nhất |
| `reference_peak` | `max(abs(Fiji))` trong chính vùng đang chấm |
| `relative_error` | `max_error / reference_peak` |
| `pearson_r` | Hệ số tương quan Pearson |
| `psnr_db` | `20*log10(255/RMSE)` chỉ với Gaussian |
| `status`, `reason` | PASS/FAIL/UNDEFINED hoặc lỗi file, kèm lý do |

Crop theo k từng bậc từ config. Structure cộng **hai ceil riêng** của support
vi phân và tích phân. Tính toán metric bằng float64 từ TIFF float32 thô,
không nhân sigma và không rescale/min-max từng ảnh.

PASS khi **cả hai** `relative_error < 1e-4` và `pearson_r > 0.9999` trên lõi.
Bản đồ hằng có Pearson không xác định; mẫu số tham chiếu bằng 0 cũng không
được tự coi đạt. Lõi rỗng/file hỏng báo INVALID. Báo cáo biên là thông tin
riêng, không dùng thay lõi để chấm nghiệm thu. PSNR Gaussian hoàn hảo là `inf`;
PSNR toán tử khác trống, không phải thiếu phép tính.

Ba cặp `bsds_01`, sigma=2, lx/ly/lxx được trích riêng trong
`smoke_test_report.csv`. Đây là bộ tính lại từ raw hiện tại, không dùng sáu
file smoke cũ. Nếu FAIL, ghi sai số thực và trao đổi Mạnh/nhóm theo quy tắc
không đạt; không đổi nhãn PASS hoặc sửa lõi để ép ngưỡng.

## 3. Tầng 2 — Precision/Recall/F1 với GT

Một hàm `normalize_scale` áp dụng cho cả hai nguồn, nhân sigma cho bậc 1 và
sigma² cho bậc 2. Fiji đã normalized theo cờ lệnh trong config thì không
nhân lần nữa. Các sigma đều đọc nguyên từ config, không tự thêm 11.3.

Lưới ngưỡng được công khai trong
[metrics_protocol.yaml](../../src/eval/metrics_protocol.yaml). Nhánh chính dùng
đúng các lưới đã thiết kế ngày 02/11, khác lưới mở rộng của CSV nhận về:

- Canny: p_low = 40/50/60/70, p_high = 80/90/95; chọn theo mean F1 Python
  **riêng mỗi sigma**, áp cùng cặp cho Fiji. Hòa điểm chọn cặp đầu trong lưới.
- Frangi: ngưỡng 0.05/0.10/0.20/0.30/0.50; chọn theo macro F1 Python trên
  10 DRIVE, áp cùng ngưỡng cho Fiji, không chọn riêng mỗi ảnh/nguồn.
- Blob: ngưỡng 0.5/1.0/2.0/5.0 trên LoG đã chuẩn hóa, theo cùng quy tắc
  macro F1 Python trên 5 ảnh và đóng băng cho Fiji.

Toàn bộ ảnh dùng chọn ngưỡng cũng là tập thực nghiệm đang báo cáo; phải gọi
đúng là đánh giá nội bộ, không diễn giải thành điểm test độc lập.

**Edge/BSDS:** Dung sai Euclidean ≤2 px, không dùng hình vuông 5×5. Precision
đếm một pixel dự đoán là đúng nếu gần biên ít nhất một annotator; Recall là
trung bình recall từng annotator. Không suy ra một TP/FP/FN chung từ công thức
recall đa annotator; các ô đó để trống cho Edge. Hai nguồn đều gọi Canny của
nhóm. Quét lưới dùng connected components NumPy/Python có kiểm thử tương
đương hysteresis của core; đầu ra chấm cuối gọi detector core.

FeatureJ Edges nguyên bản có NMS của plugin: dùng lưới **ngưỡng tuyệt đối**
riêng, ghi `featurej_edge_reference*.csv`. Chỉ là tham chiếu bổ sung, không
trình bày thành kết quả cùng thuật toán với Python.

**Ridge/DRIVE:** Cực tính dark, Frangi beta=.5 và c=.5×max(S) theo từng ảnh/
scale, tự sắp trị riêng theo độ lớn trong detector. Xói mòn FOV từng scale
bằng hình vuông support kernel; khi lấy max qua scale, vùng chấm cuối là
**giao các FOV hợp lệ**, tức support lớn nhất (32 px ở config hiện tại).
Hai nguồn chấm cùng mặt nạ; xuất thêm IoU. Không dùng FOV cố định ở sigma=2
để chấm toàn bộ scale.

**Blob:** Tâm lệch ≤2 px **và** sai số bán kính ≤20%. Dùng matching một-một
có số cặp hợp lệ lớn nhất, không đếm cùng phát hiện nhiều lần. Dự đoán có tâm
trong hình chữ nhật ignore (kể cả biên) được bỏ trước khi ghép/chấm FP; quy
tắc này giống nhau cho hai nguồn. File `blob_matching_audit.json` cho phép
xem lại các phát hiện và chỉ số cặp khớp với `objects` trong GT.

P=TP/(TP+FP), R=TP/(TP+FN), F1=2TP/(2TP+FP+FN). Trường hợp không có dự đoán/
nhãn được quy ước điểm 0 và không bỏ ảnh khỏi trung bình. Macro là trung bình
điểm mỗi ảnh; micro cộng TP/FP/FN trước khi tính. Không trộn macro và micro,
đặc biệt khi blob_05 có nhiều tế bào hơn bốn ảnh tổng hợp.

## 4. Danh mục bàn giao

Tất cả trong `outputs/metrics/duc_08_11/`:

| File | Dùng để bàn giao |
| --- | --- |
| `KET_QUA_METRIC.md` | Bản đọc nhanh, số liệu thật và giới hạn |
| `tier1_report.csv` | 220 cặp metric vùng lõi, gồm MSE/PSNR/Pearson theo phạm vi |
| `tier1_border_report.csv` | 220 dòng vùng biên tương ứng |
| `smoke_test_report.csv` | 3 phép đối chuẩn sigma=2 |
| `tier2_results_both.csv` | 110 dòng = 55 mỗi nguồn, bao phủ 25 ảnh mỗi nguồn |
| `tier2_results_python.csv`, `tier2_results_fiji.csv` | Tách 55 dòng từng nguồn |
| `tier2_comparison.csv` | 55 dòng đối sánh cùng bài toán/ảnh/sigma |
| `tier2_summary.csv` | Tổng hợp P/R/F1; macro và micro đúng phạm vi |
| `bsds_threshold_grid.csv`, `bsds_selected_thresholds.csv` | Lưới và 4 cặp ngưỡng đóng băng theo sigma |
| `ridge_threshold_grid.csv`, `blob_threshold_grid.csv` | Bằng chứng chọn ngưỡng trên Python |
| `featurej_edge_reference.csv`, `featurej_edge_reference_grid.csv` | Nhánh tham chiếu native riêng |
| `blob_matching_audit.json` | Từng phát hiện, vùng bỏ qua và cặp khớp |
| `input_manifest.csv`, `map_manifest.csv`, `run_manifest.json` | Input/map/checksum, code/config, phiên bản thư viện và trạng thái phiên chạy |

Có thêm `outputs/metrics/tier1_report.csv` theo đường dẫn giao diện yêu cầu.
Ảnh tính toán nằm ở `outputs/python/`; không phải thư mục nhãn để sửa thủ công.

Tác vụ này không đo lại runtime Fiji, không tạo noise/crop, không vẽ biểu đồ
STT 24. Không lấy runtime đơn lẻ có sẵn làm số liệu đo lặp mới. Bộ code:
`run_metrics.py` điều phối, `benchmark_tier1.py` chấm TIFF, `metrics_tier2.py`
chấm GT, `metric_utils.py` kiểm tra và công thức dùng chung. Các script
`verify_tier1.py`/`benchmark_tier2.py` cũ được giữ nguyên làm lịch sử, không
phải lệnh chạy bộ bàn giao này.
