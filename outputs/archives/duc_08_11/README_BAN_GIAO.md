# Bàn giao ảnh TIFF Python

Đủ **415 ảnh TIFF**, chia thành 3 ZIP.

Mỗi ZIP chỉ chứa các file `.tif` ngay khi mở: không thư mục lồng, không file phụ.

| ZIP | Số TIFF | Dung lượng |
| --- | ---: | ---: |
| [python_maps_duc_08_11_part01.zip](python_maps_duc_08_11_part01.zip) | 266 | 89.78 MiB |
| [python_maps_duc_08_11_part02.zip](python_maps_duc_08_11_part02.zip) | 94 | 89.05 MiB |
| [python_maps_duc_08_11_part03.zip](python_maps_duc_08_11_part03.zip) | 55 | 64.36 MiB |

**Bàn giao cả ba ZIP.** Giải nén đủ các ZIP vào **cùng thư mục `outputs/python/`** nếu dùng với code dự án. Có thể giải nén vào thư mục trống khác để mở xem bằng Fiji/ImageJ.

Đã kiểm tra CRC và SHA-256 từng ảnh trong ZIP; giữ nguyên toàn bộ ảnh gốc. Đây là bản đồ đầu ra Python, không phải ground truth.

Sau khi sửa pipeline ngày 10/11, đã kiểm tra lại đủ 415 TIFF trong ZIP với ảnh hiện có: vẫn trùng byte, nên giữ nguyên tên và ba ZIP đã bàn giao. Metric/biểu đồ hiện hành nằm ở `outputs/metrics/duc_10_11` và `outputs/analysis/duc_task5_10_11`.
