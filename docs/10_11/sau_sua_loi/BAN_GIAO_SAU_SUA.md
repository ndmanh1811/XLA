# Bàn giao sau sửa lỗi — phiên 10/11/2026

## Nguồn số liệu chính

- Metric: `outputs/metrics/duc_10_11`; manifest phải là COMPLETE và checksum phải hợp lệ.
- Biểu đồ, nhận xét, timing: `outputs/analysis/duc_task5_10_11`.
- Các bộ duc_08_11/pre_fix_10_11 là lịch sử. Không trộn ngưỡng/FOV/sigma giữa các phiên.

## Đã xử lý

- Chỉ một pipeline thực hiện chấm điểm; benchmark_tier2.py là lối gọi tương thích, không còn bộ chấm độc lập.
- Blob khớp một–một theo maximum cardinality, loại ignore trước khi đếm FP; có test ở đúng hàm chấm hai nguồn.
- DRIVE dùng giao FOV hợp lệ theo support lớn nhất suy ra từ config; hình thái học NumPy.
- Chuẩn hóa qua một hàm, xét featurej_normalized cho Fiji; hai nguồn dùng cùng 7 sigma blob.
- BSDS đĩa Euclidean 2px; tìm ngưỡng thô/tinh trên Python, đóng băng cho Fiji.
- Đã sinh lại metric, biểu đồ và timing. Launcher công việc 5 đọc phiên hiện hành.
- Slide dùng gamma=1 cho cả hai bậc, mô tả đúng FeatureJ Edges/Canny; checksum chỉ nói toàn vẹn dữ liệu.
- Demo tính P/R/F1 thật cho một ảnh; số trong slide/báo cáo lấy từ cùng CSV.

## Kết quả

Tầng 1 theo ngưỡng gốc: {'PASS': 35, 'FAIL': 185}. 185 cặp vẫn không đạt ngưỡng gốc; có thể ghi RELAXED theo ngưỡng mở rộng của nhóm, không gọi đạt STRICT.

| Nguồn | Bài toán | Sigma | Macro P | Macro R | Macro F1 | Micro F1 |
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

### Ảnh tế bào

| Nguồn | TP | Dự đoán sau ignore | GT | Bỏ qua | F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| python | 140 | 293 | 276 | 36 | 0.492091 |
| fiji | 139 | 295 | 276 | 37 | 0.486865 |

Điểm DRIVE khác số ~0.681 của phiên cũ vì vùng FOV và cách chọn ngưỡng đã đổi. Điểm blob khác vì matching/ignore/ngưỡng đã được chốt lại; đây không phải các phép đo có thể trộn với phiên cũ.
Phép thử giữ ngưỡng cũ 7.65 cho blob_05 từng cho F1 0.493827/0.488576. Phiên bàn giao chọn ngưỡng trong lưới đã công bố, nên không thay F1 hiện tại bằng các số kiểm chứng đó.

## Còn cần nhóm hoàn thiện

- Hưng mở rộng lý thuyết, rà nguồn/trích dẫn, biên dịch và nghiệm thu PDF ~30 trang. Mã LaTeX cập nhật chưa đồng nghĩa đã có PDF cuối.
- Lộc bổ sung hồ sơ đo k/border/normalization theo từng lệnh để bảo vệ giải thích sai số tầng 1.
- Cả nhóm kiểm tra trình chiếu, chuẩn bị câu hỏi bảo vệ và xác minh quyền link LMS trước nộp.
- Baseline 25 ảnh; chưa kết luận về nhiễu/đổi kích thước khi chưa có thí nghiệm bổ sung.
