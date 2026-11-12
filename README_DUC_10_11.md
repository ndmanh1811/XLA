# Đức — Bàn giao metric và phân tích sau sửa lỗi

**Đọc file này trước.** Đây là luồng hiện hành của công việc 4–5, chuẩn hóa ngày 10/11/2026. Dữ liệu/GT ngày 02/11 và 05/11 được giữ nguyên.

**Cập nhật 12/11:** đã chạy lại metric và timing với config sau hiệu chuẩn, sửa bảng đối chiếu thư viện của Mạnh và kiểm tra 58/58 test. Xem [bàn giao Đức + Mạnh](docs/12_11/sau_hoan_thien_duc_manh/KET_QUA_HOAN_THIEN_DUC_MANH.md) và [checklist 29 công việc mới nhất](docs/12_11/sau_hoan_thien_duc_manh/CHECKLIST_29_CONG_VIEC.csv). Bản kiểm tra đầu ngày 12/11 là bằng chứng trước khi xử lý hai vấn đề này.

## Mở file nào?

| Cần xem | File | Cách mở |
| --- | --- | --- |
| Kết quả metric, tiêu chuẩn và giới hạn | [KET_QUA_METRIC.md](outputs/metrics/duc_10_11/KET_QUA_METRIC.md) | VS Code → Ctrl+Shift+V |
| P/R/F1 từng ảnh, hai nguồn | [tier2_results_both.csv](outputs/metrics/duc_10_11/tier2_results_both.csv) | Excel → Data/From Text CSV → UTF-8, dấu phẩy |
| Macro/micro P/R/F1 | [tier2_summary.csv](outputs/metrics/duc_10_11/tier2_summary.csv) | Excel/VS Code |
| 220 cặp MSE/RMSE/relative error/Pearson | [tier1_report.csv](outputs/metrics/duc_10_11/tier1_report.csv) | Excel/VS Code |
| Kiểm tra blob khớp ai, loại đối tượng nào | [blob_matching_audit.json](outputs/metrics/duc_10_11/blob_matching_audit.json) | VS Code |
| Gallery 10 biểu đồ | [index.html](outputs/analysis/duc_task5_10_11/index.html) | Trình duyệt; hoặc MO_BIEU_DO_DUC.cmd |
| Nhận xét thực nghiệm | [PHAN_TICH_KET_QUA.md](outputs/analysis/duc_task5_10_11/PHAN_TICH_KET_QUA.md) | Markdown Preview |
| Đã sửa gì, số liệu bàn giao, việc nhóm còn lại | [BAN_GIAO_SAU_SUA.md](docs/10_11/sau_sua_loi/BAN_GIAO_SAU_SUA.md) | Markdown Preview |
| Trạng thái 29 đầu việc hiện hành | [CHECKLIST_29_CONG_VIEC.csv](docs/12_11/sau_hoan_thien_duc_manh/CHECKLIST_29_CONG_VIEC.csv) | Excel/VS Code |
| Bằng chứng kiểm tra bàn giao | [KIEM_TRA_SAU_SUA.json](docs/10_11/sau_sua_loi/KIEM_TRA_SAU_SUA.json) | VS Code; status phải PASS |
| Slide | [BTL_XLA_Nhom_BaoCao.pptx](docs/slides/BTL_XLA_Nhom_BaoCao.pptx) | PowerPoint; HTML offline ở bai_trinh_trinh_xla.html |

## Chạy theo thứ tự

1. Cài môi trường nếu máy mới: `python -m pip install -r requirements.txt`.
2. Chạy **CHAY_METRIC_DUC.cmd**: sinh lại Python TIFF, kiểm tra raw/GT/config, chấm cả hai nguồn và ghi manifest COMPLETE.
3. Chạy **CHAY_CONG_VIEC_5_DUC.cmd**: kiểm tra metric, đo timing nếu chưa có, vẽ hình, đồng bộ Chương 5–6 và dựng slide. Lần đầu cần JDK cùng `ij.jar`/`imagescience.jar`.
4. Chạy **MO_BIEU_DO_DUC.cmd** để mở gallery.

Tên cũ `CHAY_METRIC_DUC_08_11.cmd` chỉ chuyển tiếp sang lệnh mới; không ghi đè thư mục lịch sử. Khi đổi code/config/raw, phải chạy lại metric; khi đổi mã tính toán hoặc máy đo thì dùng `python -m src.eval.analyze_task5 --remeasure-runtime` rồi chạy lại công việc 5.

Đường dẫn ImageJ mặc định: `../ij153-win-java8/ImageJ`; nếu khác, chạy `python -m src.eval.analyze_task5 --imagej-dir "C:/duong/dan/ImageJ" --remeasure-runtime`. Dùng JDK có `javac`; không yêu cầu mở cửa sổ GUI Fiji.

## Protocol đã chốt

- Tầng 1 giữ giá trị thô, crop theo config; ngưỡng gốc relative error <1e-4 và Pearson >0.9999. Kết quả 35 STRICT, 185 chưa đạt ngưỡng gốc; RELAXED là ngưỡng mở rộng, phải ghi rõ.
- BSDS: đĩa Euclidean 2px; chọn ngưỡng thô/tinh trên Python, áp nguyên cho Fiji; nhánh FeatureJ Edges chỉ tham chiếu riêng.
- DRIVE: giao các FOV hợp lệ qua mọi scale, support suy từ config (hiện 32px); chọn trong lưới ngưỡng đã công bố, dùng chung hai nguồn.
- Blob: cùng 7 sigma; matching một–một, tâm ≤2px, bán kính sai ≤20%; áp 15 vùng ignore trước khi đếm FP.
- Chuẩn hóa chung qua `normalize_scale`; chỉ bỏ nhân thêm cho nguồn Fiji khi cờ `featurej_normalized` của lệnh là true.
- Timing: 357 case/nguồn, 1 warm-up + 5 lượt đo; Java là API headless, không phải GUI/I/O. Không dùng timing một lượt của macro thay cho số đo lặp này.

## Bản lịch sử và phần cần nộp

Nguồn số liệu chính là **duc_10_11**, không dùng bảng cũ chứa DRIVE ~0.681 hoặc blob 0.4651/0.463 để thay vào báo cáo mới. Các bản cũ ở `outputs/metrics/duc_08_11`, `outputs/metrics/history/pre_fix_10_11`, `outputs/analysis/duc_task5_08_11` và ZIP sao lưu `outputs/archives/maintenance_10_11`.

415 TIFF bàn giao vẫn ở [3 ZIP ảnh](outputs/archives/duc_08_11/README_BAN_GIAO.md). Tên ZIP giữ nguyên để tránh đổi gói đã trao đổi; nội dung được kiểm tra với TIFF hiện có. Metric và biểu đồ gửi riêng theo hai thư mục duc_10_11 ở trên.

PDF báo cáo cuối vẫn cần Hưng biên dịch, rà font/số trang và hoàn thiện lý thuyết. Lộc đã bổ sung hồ sơ hiệu chuẩn định lượng tại `docs/fiji/calibration` ngày 11/11; còn ảnh chụp hộp thoại/phiên bản để chốt bằng chứng giao diện. Việc chuẩn bị bảo vệ và kiểm tra link LMS vẫn là phần nhóm tiếp tục hoàn thiện.
