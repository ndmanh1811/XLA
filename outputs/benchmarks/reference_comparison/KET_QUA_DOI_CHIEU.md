# Đối chiếu thư viện — số đo thực tế

Bảng đo trên ảnh/scale của phiên chạy; không tự kết luận 100% PASS hoặc bộ lọc nào ưu việt.

| Toán tử | Tham chiếu | Sigma | Max error | RMSE | Pearson |
| --- | --- | ---: | ---: | ---: | ---: |
| Gaussian | SciPy | 1 | 1.13687e-13 | 2.05296e-14 | 1.00000000 |
| Gaussian | OpenCV | 1 | 1.42109e-13 | 2.62756e-14 | 1.00000000 |
| Gaussian | SciPy | 2 | 1.42109e-13 | 2.7428e-14 | 1.00000000 |
| Gaussian | OpenCV | 2 | 1.7053e-13 | 4.71062e-14 | 1.00000000 |
| Gaussian | SciPy | 4 | 1.13687e-13 | 1.87235e-14 | 1.00000000 |
| Gaussian | OpenCV | 4 | 1.98952e-13 | 4.46318e-14 | 1.00000000 |
| Gaussian | SciPy | 8 | 1.42109e-13 | 2.53117e-14 | 1.00000000 |
| Gaussian | OpenCV | 8 | 1.98952e-13 | 2.92659e-14 | 1.00000000 |
| Lx_NumPy vs SciPy (order=1) | SciPy | 2 | 0.025334 | 0.00331593 | 0.99999963 |
| Ly_NumPy vs SciPy (order=1) | SciPy | 2 | 0.0348183 | 0.00347335 | 0.99999976 |
| Grad Mag_NumPy vs SciPy | SciPy | 2 | 0.0386986 | 0.00429078 | 0.99999965 |
| Grad Mag_NumPy vs OpenCV (Sobel) | OpenCV | 2 | 1.47373 | 0.193723 | 0.99888419 |
| Lxx_NumPy vs SciPy (order=2) | SciPy | 2 | 0.0353991 | 0.00929129 | 0.99999598 |
| Lyy_NumPy vs SciPy (order=2) | SciPy | 2 | 0.0461287 | 0.0096664 | 0.99999759 |
| Lxy_NumPy vs SciPy (order=2) | SciPy | 2 | 0.00396991 | 0.000407258 | 1.00000000 |
| Laplacian_NumPy vs SciPy (Laplace) | SciPy | 2 | 0.0694563 | 0.0182614 | 0.99999544 |

## Phạm vi diễn giải

- Pearson được tính từ mảng. Mảng hằng có Pearson không xác định, không gán r=1.
- Đạo hàm SciPy có thể khác support trục làm mịn và chuẩn hóa moment; Sobel là toán tử khác.
- IoU/Dice của Canny là độ giao giữa hai thuật toán, không phải điểm GT. Phép ánh xạ ngưỡng minh họa cũ được ghi rõ trong CSV.
- Thành phần liên thông đã loại nhãn nền. Ít thành phần hơn không tự chứng minh phát hiện biên tốt hơn.
- Thời gian Gaussian trong console chỉ là thăm dò trung bình 3 lượt; timing bàn giao vẫn dùng bộ 357 case, warm-up và median riêng.
- Kết quả chính thức so với GT nằm trong outputs/metrics/duc_10_11; không trộn với bảng thư viện này.
