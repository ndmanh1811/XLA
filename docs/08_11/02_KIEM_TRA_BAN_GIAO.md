# Kiểm tra bàn giao — Công việc 4 của Đức

Ngày hoàn thành tính toán: **08/11/2026**. Nhiệm vụ: **STT 23 — Tính metric
định lượng**, hạn 12/11 trong bảng phân công. Điểm vào:
[README_DUC_08_11.md](../../README_DUC_08_11.md).

## Đầu ra đã thực hiện

| Yêu cầu trong phân công/tài liệu | Bằng chứng bàn giao |
| --- | --- |
| Fiji vs Python: MSE và tương quan | [tier1_report.csv](../../outputs/metrics/duc_08_11/tier1_report.csv), 220 dòng, đầy đủ MSE/MAE/RMSE/Max/Relative Error/Pearson |
| PSNR theo phạm vi hợp lệ | Cùng bảng, 20 ô PSNR cho 5 ảnh × 4 sigma Gaussian, MAX=255; toán tử khác để trống theo tài liệu |
| Sai số biên riêng | [tier1_border_report.csv](../../outputs/metrics/duc_08_11/tier1_border_report.csv), 220 dòng |
| Smoke test thật | [smoke_test_report.csv](../../outputs/metrics/duc_08_11/smoke_test_report.csv), 3 cặp từ raw hiện tại |
| Precision/Recall/F1 với GT | [tier2_results_both.csv](../../outputs/metrics/duc_08_11/tier2_results_both.csv), 110 dòng, đủ 25 ảnh mỗi nguồn |
| Cùng điều kiện giữa hai nguồn | [tier2_comparison.csv](../../outputs/metrics/duc_08_11/tier2_comparison.csv), 55 cặp cùng ảnh/bài toán/sigma |
| Tổng hợp đúng macro/micro | [tier2_summary.csv](../../outputs/metrics/duc_08_11/tier2_summary.csv), 12 dòng |
| Tham số có thể kiểm tra lại | YAML protocol, CSV quét/chọn ngưỡng và hồ sơ code/config SHA-256 |
| Nguồn dữ liệu và khả năng truy vết | [run_manifest.json](../../outputs/metrics/duc_08_11/run_manifest.json), input/map manifest, audit ghép blob |

110 dòng không phải 110 ảnh: mỗi nguồn có 40 dòng BSDS (10 ảnh × 4 sigma),
10 DRIVE đa tỷ lệ, 5 blob đa tỷ lệ = 55 dòng cho 25 ảnh. Có bảng tách riêng
cho Python/Fiji và bảng tham chiếu FeatureJ Edges nguyên bản.

## Kiểm tra đã chạy

- `python -m unittest discover -s tests -v`: **39/39 đạt**, gồm 17 kiểm thử
  metric mới; kiểm tra công thức, trường hợp suy biến, config thiếu/null,
  dung sai Euclidean, connected components/hysteresis, ghép một-một và ignore.
- `python run_tests.py`: **5/5 kiểm thử lõi đạt**.
- Chạy `python -m src.eval.run_metrics`: hoàn tất đầy đủ, manifest `COMPLETE`.
- Sinh 415 TIFF Python bằng code nhóm; kiểm tra **383 bản đồ Python cần dùng**
  và **423 bản đồ Fiji cần dùng**, tổng 806. Phần còn lại của bộ Python là
  gradient bổ sung do batch xuất; 12 TIFF edge Fiji legacy không dùng trong
  pipeline mới. Các TIFF cần dùng đều đủ, float32 không nén, đúng shape,
  hữu hạn và được ghi SHA-256.
- Kiểm tra độc lập sau chạy: đủ số dòng, `MSE = RMSE²`, PASS đúng cả hai
  ngưỡng, P/R/F1 trong [0,1], TP/FP/FN nhất quán, không tái sử dụng cặp blob,
  cùng ngưỡng cho Python/Fiji, đúng phạm vi PSNR và hash toàn bộ đầu ra.
- Raw/GT vẫn nguyên checksum, 25/25 READY. Không sửa các nhãn đã duyệt.
- Pipeline mới không import `scipy.ndimage`; morphology và connected
  components là NumPy/Python, đối chiếu SciPy chỉ trong kiểm thử độc lập.

## Kết quả nghiệm thu số học cần giữ nguyên khi nộp

**35/220 PASS, 185/220 FAIL** theo ngưỡng gốc, không có file thiếu/không hợp
lệ trong bộ đã chạy. Ba phép smoke sigma=2 đều FAIL do sai số tương đối vượt
1e-4 dù Pearson cao. Đây là kết quả thực nghiệm cần trao đổi với Mạnh/nhóm;
không diễn giải thành 220 bản đồ đạt chuẩn gốc, không tự đổi sang RELAXED.

Việc **tính metric STT 23 đã được thực hiện**; việc lõi thuật toán đạt toàn
bộ tiêu chuẩn đối chuẩn là một kết luận khác. Không sửa `src/core`, raw,
ground truth hoặc config đo để làm kết quả đẹp hơn.

## Giới hạn và phạm vi tiếp theo

Kết quả là kịch bản cơ sở trên 25 ảnh gốc. Ngưỡng được chọn và chấm trên tập
nội bộ nên không phải điểm test độc lập. Dung sai biên Euclidean, FOV DRIVE
32 px cho gộp đa tỷ lệ và ngưỡng theo thiết kế 02/11 khác một số lựa chọn của
CSV pull về; vì vậy số liệu hai bộ không được so sánh như cùng protocol.

Vùng ignore làm 36 dự đoán Python và 37 dự đoán Fiji của blob_05 bị loại khỏi
chấm ở ngưỡng đã chọn. Nhãn 276 tế bào của Đức được giữ nguyên. Macro và micro
F1 blob khác nhau do số đối tượng giữa các ảnh chênh lệch; bảng ghi cả hai.

Chưa làm STT 24 (biểu đồ/phân tích tổng hợp), chưa tạo biến thể nhiễu/crop
và chưa đo lại runtime Fiji nhiều lần. Phiên bản FeatureJ của bộ xuất được
ghi là chưa xác minh độc lập trong lần chạy này, không suy đoán từ tên file.
Nếu cần tuyên bố độ trung thực số học đạt toàn bộ hoặc kết quả trên các kịch
bản bổ sung, phải có kiểm chứng tương ứng trước khi đưa vào báo cáo.
