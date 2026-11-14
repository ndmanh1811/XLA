# Giao diện demo dễ đọc — 14/11/2026

Đã chỉnh giao diện theo hướng chữ lớn, thao tác rõ và ưu tiên ảnh. Các hàm xử lý ảnh, cách chấm điểm, config và dữ liệu metric được giữ nguyên.

## Cách sử dụng

1. Mở web đang chạy ở `http://127.0.0.1:5000`; nhấn **Ctrl+F5** nếu còn thấy giao diện cũ.
2. Chọn nhanh **Canny / Frangi / Blob**, hoặc chọn ảnh và thuật toán ở cột bên trái.
3. Kéo slider hoặc **nhập số trực tiếp** vào ô bên cạnh. Giá trị và nút scale được đồng bộ; ô nhập sai miền/bước hoặc để trống sẽ được nhắc trước khi gửi.
4. Bấm **Chạy tính toán**. Nếu cần, cuộn trong cột điều chỉnh để xem các tùy chọn nâng cao. Nút Chạy được giữ trong vùng nhìn thấy trên desktop.
5. Khu kết quả tách rõ **ảnh gốc, Python, tham chiếu Fiji và Ground Truth**. Mỗi khung có tiêu đề, mô tả và màu viền nhận biết.
6. Bấm **Phóng to ảnh** hoặc bấm trực tiếp ảnh. Có thể dùng Enter/Space khi focus vào ảnh, và **Escape** để đóng ảnh lớn.

Trang cho phép cuộn, không còn ép mọi nội dung trong 100vh. Trên điện thoại, phần điều khiển và kết quả xếp thành một cột; có liên kết **Đi tới ảnh kết quả**.

## Những thay đổi chính

- Chữ nền 17 px, nhãn điều khiển 16 px, tiêu đề ảnh 19 px; tăng kích thước nút, checkbox và tay kéo slider.
- Preset thu gọn thành ba nút; cột điều chỉnh rộng 320 px trên desktop.
- Chỉ số đặt cùng khu kết quả, có khoảng cách và phân cấp rõ.
- Khung ảnh lớn, giữ tỷ lệ và không cắt nội dung; phóng to dùng chung modal với biểu đồ.
- Giao diện có focus bàn phím rõ; ô nhập số được gắn nhãn hỗ trợ truy cập.
- CSS giao diện nằm riêng trong `src/web/static/studio.css`; phần tính toán backend không đổi.

## Kiểm tra

```powershell
node tools/test_web_browser_13_11.cjs --ui-review
```

Đã chạy **15 luồng PASS trên Edge headless thật**, gồm kiểm tra mới về chữ lớn, đồng bộ slider/number, ô trống, phóng to ảnh/Escape, nút Chạy trong viewport và bố cục **1440 / 1024 / 390 px** không tràn ngang. Các luồng cũ về request mới nhất, preset, F1, ignore, góc và gallery vẫn hoạt động.

- [BROWSER_REGRESSION.json](BROWSER_REGRESSION.json): kết quả và checksum source đã kiểm tra.
- [UI_FULL_PAGE.png](UI_FULL_PAGE.png): toàn bộ bố cục desktop.
- [UI_1440.png](UI_1440.png): desktop; [UI_1024.png](UI_1024.png): tablet; [UI_390.png](UI_390.png): điện thoại.
- [UI_CHANGE_SUMMARY.json](UI_CHANGE_SUMMARY.json): đối chiếu backend và dữ liệu với phiên trước.

Bản sao trước sửa: `outputs/archives/maintenance_14_11/web_giao_dien_truoc_sua.zip`.
