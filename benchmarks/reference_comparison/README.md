# THƯ MỤC KIỂM THỬ ĐỐI CHUẨN THAM CHIẾU NGOÀI (REFERENCE ORACLE TESTING)

> **MỤC ĐÍCH KỸ THUẬT & LIÊM CHÍNH HỌC THUẬT:**
> 1. Thư mục này so sánh đáp ứng thực đo giữa thuật toán tự cài đặt thuần NumPy (`src/core/`) và **SciPy ndimage/OpenCV** trên ảnh, scale và cấu hình được ghi rõ.
> 2. Thư mục này **HOÀN TOÀN TÁCH BIỆT** khỏi mã nguồn cốt lõi (`src/core/`). Mã nguồn trong `src/core/` vẫn đảm bảo 100% tự viết from scratch, không sử dụng OpenCV hay SciPy theo đúng quy định BTL.
> 3. Đây là bằng chứng so sánh thư viện độc lập. Không tự gán “100% PASS”, không dùng Pearson cao hoặc ít thành phần liên thông để kết luận một thuật toán ưu việt; việc đánh giá GT và nghiệm thu Fiji dùng pipeline riêng.

---

## Cấu trúc thư mục

* `compare_gaussian.py`: So sánh phép lọc Gaussian đa tỷ lệ giữa NumPy thuần vs `scipy.ndimage.gaussian_filter` vs `cv2.GaussianBlur`.
* `compare_derivatives.py`: So sánh toàn bộ các đạo hàm vi phân bậc 1 ($L_x, L_y, |\nabla L|$) và bậc 2 ($L_{xx}, L_{yy}, L_{xy}, \nabla^2 L$) với SciPy & OpenCV.
* `compare_canny.py`: So sánh thuật toán phát hiện biên Canny (dựa trên đạo hàm Gaussian liên tục & loang BFS) với `cv2.Canny` (Sobel 3x3 rời rạc).
* `run_all_comparisons.py`: Script tổng hợp chạy toàn bộ quá trình đối chuẩn chỉ bằng **1 dòng lệnh duy nhất**, xuất bảng báo cáo định lượng và ảnh đối chiếu trực quan 300 DPI ra `outputs/comparison_custom_vs_libs.png`.

---

## Cách chạy nhanh

Từ thư mục gốc của dự án, mở Terminal (PowerShell) và chạy:

```powershell
python benchmarks/reference_comparison/run_all_comparisons.py
```
Hoặc chạy riêng từng bài kiểm tra:
```powershell
python benchmarks/reference_comparison/compare_gaussian.py
python benchmarks/reference_comparison/compare_derivatives.py
python benchmarks/reference_comparison/compare_canny.py
```

## Bản sửa ngày 12/11 — số đo thay cho kết luận gõ cứng

- Pearson, Max Error, MAE, RMSE và Relative Error được tính từ mảng; ảnh hằng có Pearson `N/A`, không bị gán r=1.
- Số thành phần liên thông loại nhãn nền; IoU/Dice Canny chỉ là độ giao hai thuật toán, không phải F1 so với chuyên gia.
- Gaussian dùng scale/k/border từ config. Derivatives có thể khác support/moment giữa các thư viện; Sobel là toán tử khác.
- Giữ phép ánh xạ ngưỡng Canny minh họa của bản cũ và ghi rõ ngưỡng thực tế, không gọi là cùng ngưỡng vật lý.
- Không thay các module thuật toán lõi hoặc thay đổi công thức để ép sai số.

Sau khi chạy lệnh tổng hợp, mở:

| File | Nội dung |
| --- | --- |
| [continuous_comparison.csv](../../outputs/benchmarks/reference_comparison/continuous_comparison.csv) | 16 cặp so sánh liên tục ở cấu hình mặc định |
| [canny_mask_agreement.csv](../../outputs/benchmarks/reference_comparison/canny_mask_agreement.csv) | IoU/Dice, số pixel, ngưỡng OpenCV của 2 cấu hình minh họa |
| [KET_QUA_DOI_CHIEU.md](../../outputs/benchmarks/reference_comparison/KET_QUA_DOI_CHIEU.md) | Bảng số đo và giới hạn diễn giải |
| [comparison_manifest.json](../../outputs/benchmarks/reference_comparison/comparison_manifest.json) | Tham số, phiên bản thư viện, SHA-256 source/config/input/output |
| [comparison_custom_vs_libs.png](../../outputs/comparison_custom_vs_libs.png) | Ảnh tổng hợp giữ bố cục cũ, số đo được tính lại |

Có thể thay ảnh/sigma/percentile bằng `--image`, `--sigma`, `--p-low`, `--p-high`. Gaussian vẫn quét dãy scale trong config; derivative/Canny dùng sigma truyền vào. `COMPLETE` chỉ nói phiên chạy hoàn tất, không phải mọi bộ lọc đã đạt một ngưỡng nghiệm thu chung.

Thời gian thăm dò Gaussian trong console dùng trung bình 3 lượt. Không trộn nó với bộ timing bàn giao 357 case/nguồn, warm-up + 5 lượt và median ở `outputs/analysis/duc_task5_10_11/runtime`.
