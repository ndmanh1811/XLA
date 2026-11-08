# Đức — Công việc 4: Tính metric định lượng

> Công việc 5 đã được tách riêng tại
> [README_DUC_CONG_VIEC_5.md](README_DUC_CONG_VIEC_5.md). Các file bên dưới
> vẫn là bộ metric công việc 4, không bị thay thế bởi bộ biểu đồ.

**STT 23 trong bảng phân công, hạn 12/11.** Bộ này thực hiện hai đầu ra:

1. **Fiji vs Python:** MSE, MAE, RMSE, sai số lớn nhất/tương đối, tương quan
   Pearson; PSNR cho Gaussian smoothing theo phạm vi đã chốt trong tài liệu.
2. **So với ground truth:** Precision, Recall, F1 cho Edge/BSDS, Ridge/DRIVE,
   Blob/LoG, chạy cùng detector và bộ tham số cho hai nguồn.

## Mở những file nào trước?

| Cần xem | File | Cách mở |
| --- | --- | --- |
| Kết quả ngắn gọn, PASS/FAIL và P/R/F1 | [KET_QUA_METRIC.md](outputs/metrics/duc_08_11/KET_QUA_METRIC.md) | VS Code, nhấn Ctrl+Shift+V để xem Markdown |
| Bảng metric 220 cặp TIFF | [tier1_report.csv](outputs/metrics/duc_08_11/tier1_report.csv) | Excel hoặc VS Code |
| Sai số riêng vùng biên | [tier1_border_report.csv](outputs/metrics/duc_08_11/tier1_border_report.csv) | Excel hoặc VS Code |
| Precision/Recall/F1 của 25 ảnh, hai nguồn | [tier2_results_both.csv](outputs/metrics/duc_08_11/tier2_results_both.csv) | Excel, lọc `source`, `task`, `image`, `sigma` |
| Đối sánh Python/Fiji cùng ảnh và sigma | [tier2_comparison.csv](outputs/metrics/duc_08_11/tier2_comparison.csv) | Excel |
| Tổng hợp P/R/F1 theo bài toán và sigma | [tier2_summary.csv](outputs/metrics/duc_08_11/tier2_summary.csv) | Excel |
| Phiên chạy đã hoàn tất hay chưa | [run_manifest.json](outputs/metrics/duc_08_11/run_manifest.json) | VS Code; `status` phải là `COMPLETE` |
| Hướng dẫn chạy và đọc từng cột | [01_HUONG_DAN_METRIC.md](docs/08_11/01_HUONG_DAN_METRIC.md) | VS Code Markdown Preview |

Các CSV dùng UTF-8 có BOM. Nếu Excel mở dồn vào một cột: **Data → From
Text/CSV → UTF-8 → delimiter Comma**. Nhập qua menu này cũng giúp giữ đúng dấu
thập phân `.` khi thiết lập vùng của Windows dùng dấu phẩy.

## Chạy lại

Nháy đúp [CHAY_METRIC_DUC_08_11.cmd](CHAY_METRIC_DUC_08_11.cmd), hoặc mở terminal
ở gốc dự án và chạy:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -u -m src.eval.run_metrics
```

Lệnh sẽ kiểm tra raw/GT/config, tạo lại đầu ra Python từ lõi nhóm đã bàn giao,
chấm Tầng 1 và Tầng 2 rồi cập nhật bộ kết quả ở `outputs/metrics/duc_08_11/`.
Lệnh không sửa raw, ground truth, cấu hình đo hoặc lõi thuật toán.

Không cần chạy Fiji lại nếu vẫn dùng bộ TIFF đã pull và config hiện tại.
Nếu thay input/config/phiên bản FeatureJ, phải tái xuất bản đồ Fiji tương ứng;
checksum giúp nhận biết dữ liệu đã đổi nhưng không chứng minh một TIFF thực
sự được tạo bằng cấu hình mới.

## Lưu ý khi bàn giao

- **Hoàn tất tính metric không đồng nghĩa mọi bản đồ đạt nghiệm thu số học.**
  `PASS` Tầng 1 yêu cầu đồng thời `relative_error < 1e-4` và `pearson_r > 0.9999`.
  `FAIL` được giữ nguyên; bộ này không tự chuyển sang ngưỡng RELAXED.
- PSNR/MAX=255 chỉ dùng cho Gaussian. Những ô PSNR còn lại để trống có chủ
  đích, theo INSTRUCTIONS/quyuoc hiện tại. MSE và các sai số vẫn có cho mọi toán tử.
- Ngưỡng chọn trên Python của tập thực nghiệm nội bộ rồi đóng băng cho Fiji.
  Đây không phải điểm đánh giá trên một tập test độc lập chưa dùng chọn ngưỡng.
- Bảng `featurej_edge_reference.csv` là tham khảo FeatureJ Edges nguyên bản,
  tách khỏi nhánh so sánh hai nguồn cùng Canny.
- Kết quả cũ trực tiếp trong `outputs/metrics/`, `outputs/tier1_verification_summary.csv`
  và `outputs/smoke_test_tier1/` được giữ làm lịch sử; không trộn với bộ bàn giao này.
- Đầu ra giao diện theo tài liệu `outputs/metrics/tier1_report.csv` là bản sao
  của báo cáo Tầng 1 trong bộ này, cập nhật sau khi phiên chạy hoàn tất.

Không tạo biểu đồ hay làm STT 24 trong bộ công việc này. Hồ sơ kiểm tra trước
khi triển khai được giữ tại [00_KIEM_TRA_DIEU_KIEN_METRIC.md](docs/08_11/00_KIEM_TRA_DIEU_KIEN_METRIC.md).
