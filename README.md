# Phát hiện đặc trưng ảnh đa tỷ lệ bằng đạo hàm Gaussian

Lõi tự cài bằng NumPy, tham chiếu FeatureJ/Fiji, đánh giá Edge/Ridge/Blob trên 25 ảnh có ground truth. Các phần Gaussian, scale-space, đạo hàm bậc 1/2, gradient, Hessian và Structure Tensor nằm trong `src/core`.

**Bắt đầu tại [README_DUC_10_11.md](README_DUC_10_11.md)** để xem kết quả, cách mở file và luồng chạy đã chuẩn hóa.

| Phần phụ trách | Thành viên | Sản phẩm |
| --- | --- | --- |
| Lý thuyết và báo cáo | Nguyễn Tiến Hưng | `docs/report_template`, tài liệu tham khảo và PDF cuối cần hoàn thiện |
| Python và tối ưu | Nguyễn Đức Mạnh | `src/core`, kiểm thử, benchmark tối ưu |
| Fiji/FeatureJ | Phạm Bảo Lộc | `src/fiji`, `docs/fiji`, TIFF/manifest và hồ sơ đo |
| Dữ liệu và thực nghiệm | Bùi Trung Đức | `data`, metric, biểu đồ, phân tích và ZIP ảnh |

## Nguồn bàn giao hiện hành

| Nội dung | Vị trí |
| --- | --- |
| Metric và provenance | [outputs/metrics/duc_10_11](outputs/metrics/duc_10_11/KET_QUA_METRIC.md) |
| Biểu đồ, timing, nhận xét | [outputs/analysis/duc_task5_10_11](outputs/analysis/duc_task5_10_11/index.html) |
| Tóm tắt sửa lỗi và số liệu cho nhóm | [docs/10_11/sau_sua_loi](docs/10_11/sau_sua_loi/BAN_GIAO_SAU_SUA.md) |
| Quy ước chạy/chấm | [outputs/metrics/PROTOCOL.md](outputs/metrics/PROTOCOL.md) |
| TIFF Python bàn giao | [3 ZIP, tổng 415 TIFF](outputs/archives/duc_08_11/README_BAN_GIAO.md) |
| Ground truth gửi Hưng | [docs/09_11/GUI_HUNG_GROUND_TRUTH_09_11.md](docs/09_11/GUI_HUNG_GROUND_TRUTH_09_11.md) |
| Slide | [PPTX 10 slide](docs/slides/BTL_XLA_Nhom_BaoCao.pptx), [HTML offline](bai_trinh_trinh_xla.html) |

Các bộ `duc_08_11`, `duc_task5_08_11`, `outputs/metrics/history/pre_fix_10_11` và ZIP `outputs/archives/maintenance_10_11` là **lịch sử**. Không lấy điểm của chúng thay vào bảng hiện hành. Tên ZIP TIFF cũ được giữ vì nội dung ảnh vẫn được đối chiếu với bộ hiện có.

## Cài đặt và chạy

Python 3.11; cài `python -m pip install -r requirements.txt`. Lõi tính toán chỉ dùng NumPy; SciPy ndimage phục vụ kiểm thử độc lập/benchmark, không dùng trong pipeline chấm chính.

1. **CHAY_METRIC_DUC.cmd** — sinh Python TIFF và chấm cả hai nguồn.
2. **CHAY_CONG_VIEC_5_DUC.cmd** — timing/biểu đồ, đồng bộ bảng trong LaTeX và dựng slide.
3. **MO_BIEU_DO_DUC.cmd** — mở gallery.

Tương đương trong terminal:

```powershell
python -m src.eval.run_metrics
python -m src.eval.analyze_task5
python tools/sync_delivery_documents.py
python docs/slides/build_slides.py
python demo.py bsds --no-show
python demo.py drive --no-show
```

Timing cần JDK `javac`, ImageJ/ImageScience JAR. Đường dẫn mặc định `../ij153-win-java8/ImageJ`; dùng `--imagej-dir` nếu khác. Khi mã tính toán/config/raw hoặc máy đo thay đổi, dùng `--remeasure-runtime`. Demo tính metric riêng cho ảnh vừa chạy, không in cứng macro F1 toàn bộ dataset.

`src/eval/benchmark_tier2.py` chỉ là lối gọi tương thích sang pipeline trên; không còn bộ chấm blob/DRIVE độc lập. Các script vẽ/so sánh lịch sử không nằm trong luồng bàn giao hiện hành.

## Kiểm thử

```powershell
python -m unittest discover -s tests -v
python run_tests.py
python src/eval/validate_fiji_outputs.py
python src/eval/smoke_test_analytical.py
python tools/verify_delivery_10_11.py
```

## Điều kiện và giới hạn kết luận

- Tier 1: 220 cặp, 35 đạt ngưỡng gốc; 185 chưa đạt ngưỡng gốc. Có thể trình bày RELAXED theo ngưỡng mở rộng của nhóm, không gọi 220 cặp đều STRICT.
- BSDS cùng Canny và ngưỡng đóng băng; FeatureJ Edges dùng Canny/NMS nội suy, là nhánh tham chiếu riêng.
- DRIVE: giao FOV hợp lệ qua scale; blob: một–một và ignore, cùng 7 sigma.
- Timing Java đo API headless, không gồm GUI/I/O; không suy ra ưu thế phổ quát.
- Đánh giá nội bộ trên tập dùng chọn ngưỡng; chưa có thực nghiệm biến thể nhiễu/kích thước.
- PDF báo cáo ~30 trang, ảnh chụp giao diện bổ sung cho [hồ sơ hiệu chuẩn định lượng của Lộc](docs/fiji/calibration/CALIBRATION_RESULTS.md), câu hỏi bảo vệ và quyền link LMS vẫn cần cả nhóm chốt. Hạn chính thức theo đề **19/11**, mục tiêu nội bộ nộp trước 18/11.
