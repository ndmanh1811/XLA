# Web Demo — BTL Xử Lý Ảnh Số

Demo tương tác so sánh Python Core (NumPy) với các bản đồ Fiji/FeatureJ.

**Giao diện cập nhật 14/11:** chữ lớn, ô nhập số cạnh slider, ảnh có nút phóng to, bố cục cuộn và dùng được trên màn hình nhỏ. Xem [hướng dẫn giao diện](../../docs/14_11/giao_dien_web/README.md). Kiểm tra bằng `node tools/test_web_browser_13_11.cjs --ui-review`.

## Chạy

Từ thư mục gốc dự án:

```bash
pip install -r requirements.txt
python -m src.web.app --port 5000
```

Mở `http://127.0.0.1:5000`.

## Nguồn dữ liệu

- Ảnh mẫu: `data/raw` (10 BSDS + 10 DRIVE + 5 blob).
- Ground truth: `data/gt`.
- Bản đồ Fiji: `outputs/fiji`.
- Metric canonical: `outputs/metrics/duc_10_11` (protocol `duc_10_11_v1`).
- 10 figure phân tích: `outputs/analysis/duc_task5_10_11/figures`.

## Quy ước xử lý và so sánh

- `/api/settings` cung cấp scale, border, eigen order và ngưỡng đã chọn từ config/CSV. Polarity blob mặc định theo nhãn: `blob_02` và `blob_04` là dark, các ảnh còn lại bright.
- Canny `bsds_01` dùng σ=2, Low=67/High=91 trong phiên hiện hành. Đổi σ bằng nút hoặc slider sẽ đồng bộ ngưỡng nếu scale đó có cặp đã đóng băng. Low phải ≤High.
- Frangi `drive_08` mặc định dùng ngưỡng 0.05 và dãy scale từ config; khi tắt đa tỷ lệ có slider chọn σ. FOV suy ra từ support trong config.
- Blob `blob_05` mặc định threshold=5.0, đủ 7 scale. Checkbox **Hiện vùng ignore** chỉ đổi overlay; các vùng ignore luôn được áp dụng khi chấm theo protocol.
- Chuẩn hóa dùng `normalize_scale`, xét cờ `featurej_normalized` để không nhân hai lần. Biên và thứ tự trị riêng đọc từ config.
- Panel Fiji của Canny là **gradient dựng từ Lx/Ly**, không dùng native Edges thay thế khi thiếu file. Góc gradient được dựng bằng atan2; báo sai lệch góc tuần hoàn trên vùng gradient hợp lệ.
- Panel Fiji của Frangi là **Hessian Fiji → Frangi Python (hybrid)**. Panel Blob là **max |σ²LoG|**, không phải vòng tròn detection. Thiếu thành phần/scale hoặc checksum không hợp lệ sẽ báo N/A, không nạp một TIFF khác loại để thay thế.
- Python/Fiji dùng chung giới hạn thang màu; bản đồ có dấu có miền đối xứng quanh 0. Ảnh gốc giữ dải 0–255. Hình biểu đồ thu nhỏ giữ toàn bộ khung, bấm vào để phóng to.
- MAE/MSE/RMSE/Pearson live tính **toàn ảnh**, trước khi chuyển sang PNG; không phải chỉ số STRICT đã crop lõi. Pearson của mảng hằng là N/A. Với góc, dùng Δθ tuần hoàn thay cho Pearson.
- HUD F1 là **Python trên ảnh đang mở**. Tab đối chuẩn hiển thị macro/micro của cả tập; các số này không có cùng đơn vị tổng hợp với F1 một ảnh.
- Timing live là một lần đo phần filter/detector Python, không bao gồm đọc Fiji/GT hoặc render và không thay cho benchmark warm-up + median.

## Nguồn số liệu và nghiệm thu

Headline/bảng đọc từ CSV đã xác minh manifest; gallery kiểm tra phiên analysis và checksum. Nếu nguồn lỗi, hiển thị N/A/503 và lý do, không công bố số gõ cứng.

Phiên hiện hành: **35/220 đạt STRICT, 185/220 chưa đạt STRICT**. Trong 185 cặp đó, tất cả đạt ngưỡng mở rộng RELAXED `<1e-2`; RELAXED không có nghĩa đạt chuẩn gốc `<1e-4`. Vì vậy không gọi toàn bộ 220 cặp là đạt.

Sau khi pull source hoặc thay GT, khởi động lại app và tải lại trang để nạp dữ liệu mới. Khi chủ động đổi code tính toán/config/raw, chạy lại metric/phân tích theo README_DUC_10_11.md trước khi dùng tab kết quả chuẩn.

## Kiểm tra sau sửa ngày 13/11

```powershell
python -m unittest discover -s tests -v
python tools/verify_web_13_11.py
node tools/test_web_browser_13_11.cjs
```

Lệnh trình duyệt dùng Node 24 và Microsoft Edge headless sẵn trên máy Windows, tự chạy Flask trên cổng tạm và dừng các tiến trình test. Không cần npm package. Kết quả API, browser và ảnh chụp nằm trong `docs/13_11/sau_sua_web_app/`.
