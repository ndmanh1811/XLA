# Hồ sơ hiệu chuẩn FeatureJ — Phạm Bảo Lộc

> **Trạng thái 11/11/2026:** phần định lượng đã chạy và được phân tích: 40
> TIFF, 40 dòng đo ROI và 2.682 điểm profile. Xem
> [CALIBRATION_RESULTS.md](CALIBRATION_RESULTS.md). Cấu hình hiện hành được xác
> nhận; còn bổ sung screenshot hộp thoại/phiên bản trước khi chốt bàn giao.

Thư mục này lưu bằng chứng thực nghiệm cho các giá trị FeatureJ đang dùng trong
`config.yaml`. Hồ sơ chỉ được xem là hoàn tất sau khi `reproduce.ijm` đã chạy
trên đúng máy Fiji dùng để bàn giao và các số đo đã được rà soát.

## Phạm vi cần xác nhận

| Nội dung | Giá trị đang dùng | Bằng chứng cần có |
| --- | --- | --- |
| Kernel bậc 0 | `kernel_k.gauss = 3.0` | Profile đáp ứng Dirac tại sigma 1, 2, 4 |
| Kernel bậc 1 | `kernel_k.lx = 4.0` | Profile Lx theo trục đạo hàm và trục làm mịn |
| Kernel bậc 2 | `kernel_k.lxx = 4.0` | Profile Lxx theo hai trục |
| Xử lý biên | `border_mode = mirror` | Profile sát biên của `bright_border.tif` |
| Scale normalization | Các cờ hiện là `false` | ROI trên ramp/parabola/saddle theo từng lệnh |
| Thứ tự trị riêng | `eigen_order = algebraic` | Hessian signed trên `saddle.tif`, tắt Absolute |

Các giá trị trên là cấu hình hiện hành, không phải kết luận mới của hồ sơ này.
Không chép chúng vào cột kết luận nếu số đo chưa chứng minh được.

## Cách chạy

1. Mở Fiji có FeatureJ và ImageScience đúng phiên bản dùng cho dự án.
2. Chọn **Plugins → Macros → Run...** và mở `reproduce.ijm`.
3. Khi được hỏi, chọn thư mục gốc dự án `XLA` — thư mục chứa `config.yaml`.
4. Không mở/chuyển ảnh calibration sang 8-bit. Macro đọc trực tiếp TIFF float32,
   đặt đơn vị pixel ngay sau mỗi `open()` và dùng ROI giữa ảnh.
5. Sau khi macro hoàn tất, kiểm tra:
   - `measurement_results.csv` có các dòng Derivatives, Laplacian, Hessian,
     Edges và Structure;
   - `kernel_profiles.csv` có profile Dirac và profile sát biên;
   - `outputs/` chứa TIFF float32 tương ứng;
   - `environment.csv` có phiên bản ImageJ và thông tin môi trường.
6. Chụp màn hình **Help → About ImageJ/Fiji**, phiên bản FeatureJ/ImageScience,
   hộp thoại tùy chọn Hessian/Edges/Structure và một ROI kết quả; lưu vào
   `screenshots/`.

Macro tạo mới các CSV sinh tự động trong mỗi lần chạy. Nếu đã thêm nhận xét thủ
công, hãy commit hoặc sao lưu trước khi chạy lại.

## Quy tắc đọc kết quả

- `ramp.tif`, Lx/gradient: gần 1 ở mọi sigma nghĩa là đầu ra thô; gần sigma
  nghĩa là đã chuẩn hóa bậc 1.
- `parabola.tif`, Lxx/Laplacian: gần 1 ở mọi sigma nghĩa là đầu ra thô; gần
  sigma bình phương nghĩa là đã chuẩn hóa bậc 2.
- `saddle.tif`, Hessian khi tắt Absolute: kỳ vọng thô xấp xỉ `(1, -2)`.
- `ramp.tif`, Structure: trị riêng vùng lõi dự kiến gần `(1, 0)` nếu gradient
  thô và quy ước đầu ra đúng như giả thiết.
- Profile Dirac phải được xem theo cả trục đạo hàm và trục làm mịn. Không suy
  biên độ kernel 2D chỉ từ một hàng mà bỏ qua hệ số của trục còn lại.
- Profile biên phải được đối chiếu với đúng định nghĩa `reflect`/`mirror` trong
  `quyuoc.md`; không kết luận chỉ bằng tên tùy chọn của thư viện.

## File bàn giao

| File/thư mục | Nội dung |
| --- | --- |
| `measurement_results.csv` | Mean/Min/Max/StdDev/Sum tại ROI, tùy chọn và kỳ vọng thô |
| `kernel_profiles.csv` | Profile đáp ứng xung và các giá trị sát biên |
| `command_mapping.csv` | Ánh xạ mã dự án sang lệnh FeatureJ thực tế |
| `environment.csv` | Phiên bản và thời điểm chạy; phiên bản plugin cần bổ sung thủ công |
| `output_manifest.csv` | SHA-256, kích thước, dtype và miền giá trị của 40 TIFF |
| `reproduce.ijm` | Macro tái hiện phép đo |
| `outputs/` | TIFF float32 của phép hiệu chuẩn |
| `screenshots/` | Ảnh hộp thoại, phiên bản và ROI đo |

## Chốt kết luận

Sau khi chạy, Lộc điền cột `conclusion` dựa trên **giá trị thực đo**, ghi phiên
bản FeatureJ/ImageScience vào `environment.csv`, rồi phối hợp:

1. Mạnh đối chiếu số đo với `config.yaml` và code Python.
2. Hưng chỉ đưa vào báo cáo các kết luận có thể truy ngược về CSV/TIFF/ảnh chụp.
3. Nếu số đo khác config, cả nhóm thống nhất thay đổi trước khi Đức chạy lại
   metric/timing. Không nới ngưỡng hoặc sửa số để biến RELAXED thành STRICT.

