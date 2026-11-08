# Thư mục Công cụ Bổ trợ & Trực quan hóa (Tools & Visualization)

Thư mục này chứa các công cụ độc lập phục vụ việc kiểm thử trực quan, xuất kết quả nghiệm thu và tạo các đồ thị chất lượng cao (300 DPI) cho Báo cáo IEEE LaTeX.

## Danh sách công cụ

1. **`export_final_results.py`**:
   - Xuất các ảnh kết quả dò biên Canny (BSDS) và dò mạch máu Frangi (DRIVE) nhị phân vào thư mục `outputs/final_results/`.
   - Chạy: `python tools/export_final_results.py`

2. **`generate_all_in_one_comparison.py`**:
   - Sinh ảnh so sánh toàn diện 5 cột: `[Ảnh gốc] vs [Ground Truth] vs [Code NumPy] vs [Thư viện OpenCV] vs [Ảnh chồng màu]`.
   - Kết quả xuất ra: `outputs/master_side_by_side_comparison.png`.
   - Chạy: `python tools/generate_all_in_one_comparison.py`

3. **`create_5_comparisons.py`**:
   - Tạo ảnh so sánh đối chiếu 5 ảnh đại diện Tầng 1 kèm đáp án chuyên gia: `outputs/comparison_5_images_with_groundtruth.png`.
   - Chạy: `python tools/create_5_comparisons.py`

4. **`demo_visual.py`**:
   - Trực quan hóa lưới các đặc trưng vi phân bậc 1, bậc 2, Hessian và Laplacian.
   - Kết quả: `outputs/demo_features.png`.
   - Chạy: `python tools/demo_visual.py`

5. **`test_bsds02_scales.py`**:
   - So sánh đa tỷ lệ ($\sigma \in \{1.0, 2.0, 4.0, 8.0\}$) cho ảnh `bsds_02`.
   - Kết quả: `outputs/bsds02_multiscale_comparison.png`.
   - Chạy: `python tools/test_bsds02_scales.py`

6. **`visualize_comparison.py`**:
   - So sánh trực quan chi tiết giữa bộ cài đặt From Scratch (NumPy) và thư viện chuẩn (SciPy / OpenCV).
   - Kết quả: `outputs/comparison_custom_vs_libs.png`.
   - Chạy: `python tools/visualize_comparison.py`

7. **`view_image.py`**:
   - Tiện ích mở và kiểm tra nhanh giá trị pixel của tệp ảnh TIFF 32-bit float hoặc PNG trong terminal.
   - Chạy: `python tools/view_image.py <path_to_image>`
