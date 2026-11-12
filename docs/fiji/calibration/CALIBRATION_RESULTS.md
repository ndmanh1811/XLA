# Kết quả hiệu chuẩn FeatureJ — Phạm Bảo Lộc

Phép đo được tạo bởi `reproduce.ijm` trên 5 TIFF float32 trong `data/calib`.
Bộ bằng chứng gồm **40 TIFF**, **40 dòng đo ROI** và **2.682 điểm profile**.
`output_manifest.csv` lưu SHA-256, kích thước, dtype và miền giá trị của từng TIFF.

## Kết luận cấu hình

| Khóa | Kết luận thực đo |
| --- | --- |
| `kernel_k.gauss` | **3.0** |
| `kernel_k.lx` | **4.0** theo trục đạo hàm; trục làm mịn dùng support Gaussian k=3 |
| `kernel_k.lxx` | **4.0** theo trục đạo hàm; trục làm mịn dùng support Gaussian k=3 |
| `border_mode` | **mirror**, không lặp pixel biên |
| `featurej_normalized.derivatives` | **false** |
| `featurej_normalized.laplacian` | **false** |
| `featurej_normalized.hessian` | **false** |
| `featurej_normalized.edges` | **false** |
| `featurej_normalized.structure` | **false** |
| `eigen_order` | **algebraic**, Largest dương và Smallest âm trên saddle |

Các kết luận trên khớp `config.yaml` hiện hành. Không có thay đổi config nào được
thực hiện bởi script phân tích.

## Normalization và dấu

| Lệnh | Mean theo scale | Kết luận |
| --- | --- | --- |
| lx | s=1: 0.999925017; s=2: 0.999635696; s=4: 0.999323964 | RAW_NO_SIGMA; POSITIVE_X_SIGN |
| lxx | s=1: 0.986809949; s=2: 0.981585365; s=4: 0.986985359 | RAW_NO_SIGMA_SQUARED |
| lap | s=1: 0.974480105; s=2: 0.966612538; s=4: 0.9798343 | RAW_NO_SIGMA_SQUARED |
| grad | s=1: 0.999925017; s=2: 0.999635696; s=4: 0.999323964 | RAW_NO_SIGMA; NMS_OFF |
| hess-l1 | s=1: 1.01146964; s=2: 1.01153103; s=4: 1.00128747 | RAW_SIGNED_ALGEBRAIC_LARGEST; NO_SIGMA_SQUARED |
| hess-l2 | s=1: -1.98594998; s=2: -1.97814373; s=4: -1.98112167 | RAW_SIGNED_ALGEBRAIC_SMALLEST; NO_SIGMA_SQUARED |
| st-l1 | s=1: 0.999850035; s=2: 0.999271512 | RAW_STRUCTURE_EIGENVALUE; NO_SCALE_NORMALIZATION |
| st-l2 | s=1: 0; s=2: 0 | RAW_STRUCTURE_EIGENVALUE; NO_SCALE_NORMALIZATION |

Lx và gradient giữ gần 1 ở sigma 1, 2, 4. Các đáp ứng bậc hai/Hessian giữ gần
giá trị thô thay vì tăng theo sigma bình phương. Structure tại cặp (1,3) và
(2,6) cũng giữ trị riêng lớn gần 1 và trị riêng nhỏ bằng 0.

## Support từ Dirac

| Lệnh | Sigma | Bán kính x | Bán kính y | Tổng 2D |
| --- | ---: | ---: | ---: | ---: |
| gauss | 1.0 | 3 | 3 | 0.999999971966 |
| gauss | 2.0 | 6 | 6 | 0.999999987513 |
| gauss | 4.0 | 12 | 12 | 1.00000000445 |
| lx | 1.0 | 4 | 3 | 0 |
| lx | 2.0 | 8 | 6 | 0 |
| lx | 4.0 | 16 | 12 | 0 |
| lxx | 1.0 | 4 | 3 | -7.20183816156e-05 |
| lxx | 2.0 | 8 | 6 | -8.66882696755e-05 |
| lxx | 4.0 | 16 | 12 | -4.00395193338e-05 |

Với Lx/Lxx, x là trục đạo hàm và y là trục làm mịn. Profile y của Lx được lấy
tại cột có đáp ứng đạo hàm cực đại vì cột tâm của kernel lẻ bằng 0.

## Kiểu biên

`bright_border.tif` thực tế là ảnh 256×256 với viền ngoài cùng bằng 1. Tại pixel
biên giữa hàng, cả ba sigma cho sai số so với mô hình mirror nhỏ hơn rõ rệt so
với reflect lặp pixel; chi tiết nằm trong `calibration_summary.csv`.

## Giới hạn và bằng chứng giao diện

- `FeatureJ Edges` được đo ở chế độ gradient magnitude, NMS tắt và ngưỡng trống;
  NMS không thay đổi hệ số chuẩn hóa nên cờ `edges=false` được áp cho nhánh Edge.
- Các toán tử Ly/Lxy/Lyy dùng cùng lệnh Derivatives và cùng quy tắc theo bậc;
  kết luận của chúng được suy từ Lx/Lxx thay vì đo lặp riêng.
- Đã lưu **15 PNG** hộp thoại, phiên bản, ROI và profile trong `screenshots/`; bảng ánh xạ nằm trong `screenshots/README.md`.
- CSV/TIFF là bằng chứng định lượng chính; screenshot không thay thế số đo.
- Hồ sơ này giải thích config; không biến 185 cặp chưa đạt STRICT thành STRICT.
