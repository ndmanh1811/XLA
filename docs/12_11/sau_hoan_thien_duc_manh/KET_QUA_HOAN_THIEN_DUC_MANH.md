# Hoàn thiện phần Đức + Mạnh — 12/11/2026

**Hai vấn đề còn tồn tại của Đức + Mạnh trong bản kiểm tra đầu ngày đã xử lý xong:** hồ sơ metric/timing khớp config hiện tại và công cụ so sánh thư viện xuất số đo thực tế. Kiểm tra bàn giao đạt PASS, 58/58 unittest. Đây chưa phải nghiệm thu toàn bộ dự án: 185/220 cặp tầng 1 vẫn chưa đạt ngưỡng STRICT gốc; báo cáo cuối và các việc chung còn phải hoàn thiện.

## 1. Phần Đức: chạy lại và xác minh phiên kết quả

- Chạy lại `python -m src.eval.run_metrics`: sinh lại Python TIFF và chấm cả Python/Fiji trên raw, GT, config hiện tại; `run_manifest.json` là `COMPLETE`, checksum hợp lệ.
- Chạy lại `python -m src.eval.analyze_task5 --remeasure-runtime`: 357 case/nguồn, mỗi case có 1 warm-up + 5 lượt đo; tổng 4.284 mẫu gồm warm-up. Phiên đo bàn giao được chạy riêng, không chạy song song phép đối chiếu thư viện.
- Sinh lại 10 biểu đồ ở PNG/SVG/PDF, gallery, phân tích và 10 slide bằng builder hiện có. Tên thư mục `duc_10_11` được giữ để các link/launcher tiếp tục hoạt động.
- Hai CSV metric tầng 2 trước/sau giống byte: thay đổi checksum config không làm thay điểm P/R/F1. Đã chạy lại thực tế, không sửa tay manifest để bỏ qua kiểm tra.
- Cập nhật hash phiên trong `SO_LIEU_BAN_GIAO.json` sau khi xác nhận bảng số liệu không đổi.

## 2. Phần Mạnh: đối chiếu thư viện bằng số đo

- Pearson, MAE, RMSE, relative max error được tính từ mảng. Pearson của mảng hằng là không xác định (`N/A` trong bảng, `null` trong JSON), không gán bằng 1.
- Bỏ kết luận “100% PASS” và nhận xét ưu việt gõ cứng. Số thành phần liên thông không tính nhãn nền; có IoU/Dice thực tế cho hai mặt nạ Canny.
- Xuất 16 cặp so sánh liên tục và 2 cấu hình Canny trên `bsds_01`, cấu hình mặc định. Có tham số, phiên bản thư viện và checksum source/config/input/output để truy vết.
- Ví dụ: Gradient NumPy so với Sobel có Pearson khoảng **0,99888419**, không được làm tròn thành khẳng định tất cả >0,999. Canny minh họa dùng toán tử và ánh xạ ngưỡng khác nhau; IoU/Dice này không phải điểm so với chuyên gia.
- Giữ bố cục ảnh so sánh; thêm 6 test cho cách tính và trình bày số đo. Thư viện SciPy/OpenCV chỉ nằm trong phép đối chiếu độc lập, không đưa vào luồng chấm chính.

## 3. Mở file bàn giao

| Cần xem | File | Cách mở |
| --- | --- | --- |
| Bằng chứng kiểm tra sau hoàn thiện | [KIEM_TRA_HOAN_THIEN.json](KIEM_TRA_HOAN_THIEN.json) | VS Code; status phải PASS |
| Checklist 29 công việc hiện hành | [CHECKLIST_29_CONG_VIEC.csv](CHECKLIST_29_CONG_VIEC.csv) | Excel nhập UTF-8 hoặc VS Code |
| Metric Fiji/Python và so với GT | [KET_QUA_METRIC.md](../../../outputs/metrics/duc_10_11/KET_QUA_METRIC.md) | Markdown Preview |
| 10 biểu đồ và timing hiện hành | [index.html](../../../outputs/analysis/duc_task5_10_11/index.html) | Trình duyệt hoặc `MO_BIEU_DO_DUC.cmd` |
| Bảng đối chiếu SciPy/OpenCV | [KET_QUA_DOI_CHIEU.md](../../../outputs/benchmarks/reference_comparison/KET_QUA_DOI_CHIEU.md) | Markdown Preview; CSV/manifest cùng thư mục |
| Ảnh so sánh tổng hợp | [comparison_custom_vs_libs.png](../../../outputs/comparison_custom_vs_libs.png) | Trình xem ảnh |
| Các test và ZIP TIFF | [KIEM_TRA_SAU_SUA.json](../../10_11/sau_sua_loi/KIEM_TRA_SAU_SUA.json) | Log test cùng thư mục; 415 TIFF trong 3 ZIP đã kiểm tra |
| Slide đã cập nhật timing | [BTL_XLA_Nhom_BaoCao.pptx](../../slides/BTL_XLA_Nhom_BaoCao.pptx) | PowerPoint; cần nhóm rà khi trình chiếu |

Chạy lại đối chiếu thư viện từ gốc dự án:

```powershell
python benchmarks/reference_comparison/run_all_comparisons.py
```

Kiểm tra lại bàn giao và bằng chứng trước/sau:

```powershell
python tools/verify_delivery_10_11.py --run-tests
python tools/verify_duc_manh_12_11.py
```

Nếu chỉ xem kết quả thì mở các file ở bảng trên; không cần chạy lại. Launcher công việc 5 vẫn có bước đồng bộ Chương 5–6, nên khi Hưng đã sửa nội dung LaTeX cần thống nhất trước khi chạy bước đồng bộ đó. Lần hoàn thiện này chạy riêng metric, analysis và builder slide; nội dung LaTeX được giữ nguyên.

## 4. Những phần Lộc và nhóm còn làm

**Lộc:** bổ sung ảnh chụp vào `docs/fiji/calibration/screenshots`, theo [danh sách đã có](../../fiji/calibration/screenshots/README.md): phiên bản Fiji/ImageJ/FeatureJ/ImageScience; hộp thoại Derivatives, Laplacian, Hessian, Edges, Structure; profile Dirac và sát biên. Ảnh phải khớp lệnh, sigma và TIFF của phiên đo, ghi rõ filename tham chiếu. Nếu chụp ở môi trường/phiên mới, ghi rõ môi trường và liên hệ với lần đo cũ. CSV và 40 TIFF định lượng hiện có đã được kiểm chứng, không cần làm lại toàn bộ chỉ để thêm minh chứng giao diện.

**Hưng/nhóm:** hoàn thiện lý thuyết, rà nguồn và xuất PDF cuối; đưa biểu đồ timing mới từ thư mục analysis vào bản báo cáo cuối, rà slide, chuẩn bị bảo vệ và quyền truy cập link LMS. Không kết luận “220/220 đạt STRICT”: hiện **35 đạt, 185 chưa đạt ngưỡng gốc**; báo cáo phải giải thích sai khác có đo hiệu chuẩn. Nếu nhóm muốn đáp ứng đủ ngưỡng STRICT ban đầu thì vẫn cần một đợt cải tiến/kiểm chứng riêng, không thay ngưỡng để gọi là đạt.

Nội dung `main.tex`, `references.bib`, `config.yaml` và toàn bộ hồ sơ hiệu chuẩn của Lộc được kiểm tra bằng SHA-256 trước/sau, không thay đổi trong đợt này. Bản sao trước sửa: `outputs/archives/maintenance_12_11/truoc_hoan_thien_duc_manh.zip`.
