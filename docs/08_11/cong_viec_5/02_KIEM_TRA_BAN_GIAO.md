# Kiểm tra bàn giao công việc 5 của Đức

**STT 24 — Vẽ biểu đồ và phân tích kết quả**, hạn 14/11. Thực hiện ngày
08/11/2026. Điểm mở đầu: [README_DUC_CONG_VIEC_5.md](../../../README_DUC_CONG_VIEC_5.md).

## Sản phẩm theo bảng phân công

| Đầu ra | Sản phẩm |
| --- | --- |
| Biểu đồ theo sigma | F1 cạnh và thời gian theo sigma; PSNR Gaussian theo sigma |
| Biểu đồ theo thời gian chạy | Python và ImageScience cùng case; tỷ số thời gian, phân bố giữa case |
| Precision–Recall | Các điểm vận hành của lưới ngưỡng, đánh dấu cặp đã chọn; không gán AP/AUC |
| Nhận xét ưu/nhược điểm | `PHAN_TICH_KET_QUA.md`: đối chuẩn, biên, cạnh, ridge, blob, macro/micro, thời gian và giới hạn |
| Hình đưa vào báo cáo/slide | 10 hình × PNG 300 DPI, SVG, PDF = 30 file hình |
| Cách mở rõ ràng | HTML offline, CMD mở gallery, CMD tạo lại hình, README và hướng dẫn chi tiết |
| Số liệu có thể truy vết | CSV tổng hợp, CSV mẫu thời gian, môi trường và manifest SHA-256 |

Toàn bộ trong [outputs/analysis/duc_task5_08_11](../../../outputs/analysis/duc_task5_08_11).
Metric công việc 4 vẫn giữ tại `outputs/metrics/duc_08_11/`.

## Kiểm tra đã thực hiện

- Bộ kiểm thử: **45/45 đạt**, gồm 6 kiểm thử mới cho tổng hợp biểu đồ/runtime:
  mean F1 đúng định nghĩa, đủ nhóm đối chuẩn, đủ case hiện tại, loại warm-up,
  median đúng và phát hiện thiếu lần đo/sai cờ warm-up.
- Đọc và đối chiếu checksum toàn bộ đầu ra công việc 4 và các dependency đã
  ghi trong manifest trước/sau phân tích. Raw/GT vẫn nguyên, 25/25 READY.
- Thời gian đo lại trên cùng máy, 357 case × 2 nguồn × 6 lần gọi = 4284 mẫu,
  trong đó 714 warm-up được bỏ, 3570 mẫu dùng tổng hợp.
- Bảng runtime giữ đầy đủ mẫu và median/IQR/min/max từng case. Có kiểm tra
  iteration 0–5, thời gian dương/hữu hạn, ghép nguồn đúng khóa ảnh/lệnh/scale.
- Fingerprint raw/config/code đo và hash CSV ngăn dùng lại thời gian đã lỗi
  thời hoặc bị chỉnh sửa. Java helper biên dịch và chạy headless; không sửa
  plugin/ảnh hoặc macro bên ngoài dự án.
- Đã xem hình xuất ra để kiểm tra chữ tiếng Việt, nhãn trục, chú thích và
  tính phân biệt hai nguồn. Trục F1 chính giữ [0,1], chênh lệch nhỏ có biểu
  đồ riêng; biểu đồ thời gian theo lệnh ghi rõ thang log và ý nghĩa tỷ số.
- Hình biên/lõi dùng symlog có vùng tuyến tính gần 0 để không bỏ các điểm
  bằng 0 hoặc rất nhỏ. Bảng `border_core_comparison.csv` giữ đủ 220 điểm.

`analysis_manifest.json` là bằng chứng trạng thái hoàn tất và hash bộ đầu ra;
chỉ bàn giao khi `status=COMPLETE`. Dữ liệu đọc vào có nguồn tại manifest
công việc 4; số runtime dùng bộ mới trong thư mục analysis, không lấy từ các
CSV cũ sau pull.

## Kết luận được phép trình bày

- Tầng 1 vẫn là **35 PASS, 185 chưa đạt** theo ngưỡng gốc.
- Hai nguồn cùng detector cho F1 gần nhau trên tập nội bộ; điều này không
  chứng minh tất cả bản đồ vi phân tương đương số học.
- F1 cạnh cao nhất trong bốn scale khảo sát ở sigma=2. Không suy rộng thành
  sigma tối ưu toàn cục cho mọi dữ liệu.
- Blob tổng hợp đạt F1=1, ảnh tế bào khó hơn; cần cả macro và micro để thấy
  đúng ảnh hưởng của 276 đối tượng trong blob_05.
- Runtime là **lõi ImageJ/ImageScience gọi qua Java headless**, không phải
  thời gian GUI/macro hoặc toàn pipeline phát hiện/chấm GT. Môi trường đã
  ghi ImageJ 1.53k, ImageScience 3.0.0 và JVM thực sự dùng trong log.

Các diễn giải về kernel/texture/mạch mảnh được ghi là giả thuyết hoặc khả
năng cần kiểm chứng thêm. Chưa có thí nghiệm noise/crop/tập test độc lập mới;
không thêm kết luận về các phần đó. Công việc 5 hoàn tất cho kịch bản cơ sở
đã có metric; hợp nhất vào báo cáo/slide chung vẫn theo vai trò của nhóm.
