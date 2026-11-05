# THƯ MỤC KIỂM THỬ ĐỐI CHUẨN THAM CHIẾU NGOÀI (REFERENCE ORACLE TESTING)

> **MỤC ĐÍCH KỸ THUẬT & LIÊM CHÍNH HỌC THUẬT:**
> 1. Thư mục này được tạo ra nhằm mục đích **đối chuẩn thẩm định chéo (cross-validation)** giữa thuật toán tự cài đặt thuần NumPy (`src/core/`) với các thư viện xử lý ảnh công nghiệp hàng đầu thế giới (**SciPy ndimage** và **OpenCV cv2**).
> 2. Thư mục này **HOÀN TOÀN TÁCH BIỆT** khỏi mã nguồn cốt lõi (`src/core/`). Mã nguồn trong `src/core/` vẫn đảm bảo 100% tự viết from scratch, không sử dụng OpenCV hay SciPy theo đúng quy định BTL.
> 3. Được thiết kế như một công cụ "Oracle Baseline" để chứng minh độ chính xác toán học của nhóm đạt chuẩn công nghiệp quốc tế khi bảo vệ đồ án trước Hội đồng chấm thi.

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
