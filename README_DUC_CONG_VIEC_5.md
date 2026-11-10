# Đức — Công việc 5: biểu đồ và phân tích

Phiên hiện hành nằm ở **outputs/analysis/duc_task5_10_11**, đọc metric **outputs/metrics/duc_10_11**. Bộ `duc_task5_08_11` giữ làm lịch sử.

1. Chạy `CHAY_METRIC_DUC.cmd` nếu chưa có metric COMPLETE phù hợp code/config/raw.
2. Chạy `CHAY_CONG_VIEC_5_DUC.cmd`: kiểm tra nguồn metric, đo timing khi cần, vẽ 10 hình PNG/SVG/PDF, đồng bộ Chương 5–6 và slide.
3. Mở `MO_BIEU_DO_DUC.cmd` hoặc [gallery](outputs/analysis/duc_task5_10_11/index.html).
4. Đọc [PHAN_TICH_KET_QUA.md](outputs/analysis/duc_task5_10_11/PHAN_TICH_KET_QUA.md) và [bàn giao sau sửa](docs/10_11/sau_sua_loi/BAN_GIAO_SAU_SUA.md).

Khi đổi mã tính toán/config/raw hoặc máy đo: `python -m src.eval.analyze_task5 --remeasure-runtime`, sau đó chạy lại công việc 5 để đồng bộ tài liệu/slide. Có thể truyền `--remeasure-runtime` trực tiếp cho CMD.

Runtime cần JDK, ImageJ và ImageScience JAR, lưu đủ 1 warm-up + 5 lượt/case. Java đo API headless, không phải GUI hoặc đọc/ghi TIFF. Không bỏ kiểm tra checksum/fingerprint để sử dụng dữ liệu cũ với source mới.

Hướng dẫn đầy đủ: [README_DUC_10_11.md](README_DUC_10_11.md).
