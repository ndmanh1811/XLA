# Bàn giao sửa web/app — 13/11/2026

**Đã sửa các lỗi W01–W09 của bản kiểm tra trước.** Web so đúng đại lượng, không lấy TIFF khác loại khi thiếu tham chiếu; giao diện chỉ nhận kết quả mới nhất. Các số P/R/F1 chính thức, GT và TIFF bàn giao không thay đổi.

## 1. Các phần đã chỉnh

| Phần | Hành vi sau sửa |
| --- | --- |
| Canny / gradient | Dựng độ lớn Fiji từ Lx/Ly tương ứng; không dùng native Edges thế chỗ. `bsds_03`, σ=2: MAE từ 13,360923 về khoảng **0,005510705**, Pearson từ 0,483984 về gần 1. Đây là sửa sai bản đồ tham chiếu, không chỉnh lõi để ép sai số. |
| Hướng gradient | So atan2 với atan2; báo sai lệch góc tuần hoàn theo độ, loại vùng gradient bằng 0. Không dùng Pearson tuyến tính cho góc. |
| Blob / Frangi thiếu thành phần | Thiếu scale hoặc cặp Hessian trả N/A và nêu file thiếu, không tự lấy một Laplacian/Hessian đơn để thay thế stack hay vesselness. |
| Toàn vẹn tham chiếu | TIFF phải cùng shape, float32 không nén, hữu hạn, khớp checksum; config phải khớp phiên bản đồ đã ghi nhận. Không làm tròn scale tùy ý thành một scale Fiji khác. |
| Bấm preset / đổi lựa chọn nhanh | Mỗi preset gửi một request. AbortController kết hợp sequence và kiểm tra context chặn phản hồi cũ; lỗi của request cũ không xóa kết quả mới. |
| Các nút xem | Mode binary/response và trạng thái active được đồng bộ với ảnh; không giữ nút nhị phân trong khi hiện response. Thiếu tham chiếu ở ảnh mẫu được ghi đúng nguyên nhân. |
| Ignore và polarity | Checkbox đổi thành **Hiện vùng ignore**; ignore luôn được áp khi chấm. Mặc định polarity theo nhãn: `blob_02`, `blob_04` dark; các ảnh còn lại bright. |
| Chuẩn hóa / tham số | Dùng `normalize_scale`, đọc border/eigen order/scale/support từ config; ngưỡng preset từ CSV đã đóng băng. FOV không còn gõ cứng hệ số 4; có slider σ khi Frangi tắt đa tỷ lệ. |
| Chỉ số số học | MSE/MAE/RMSE/Pearson tính từ mảng số thực trước PNG; mảng hằng có Pearson N/A. Ghi rõ **live toàn ảnh**, không gọi là số STRICT đã crop lõi. |
| Thang hiển thị | Python và Fiji dùng cùng vmin/vmax, bản đồ có dấu đối xứng quanh 0; ảnh raw giữ 0–255. Biểu đồ thu nhỏ giữ toàn bộ khung thay vì cắt trục/chú thích. |
| Timing | Đo riêng đoạn đạo hàm/trị riêng và detector Frangi, bỏ phép chia 70/30. Tooltip ghi rõ một request live, không thay cho benchmark median đã đo. |
| Validation | Tham số số hữu hạn, boolean đúng kiểu, thuật toán/display hợp lệ, 0≤Low≤High≤100; file ảnh hỏng trả HTTP400 JSON. Upload dùng UUID tránh ghi đè khi hai lần tải gần nhau. |
| Benchmark / gallery | Headline tính từ CSV, có gate manifest/checksum và nhãn nguồn; dữ liệu chưa hợp lệ trả 503/N/A. Bỏ badge “63/63 tests” gõ cứng. Phân biệt 35 STRICT, 185 chưa đạt STRICT, trong đó 185 thuộc ngưỡng mở rộng RELAXED <1e-2. |

Danh mục `figure_catalog.csv` đã khác checksum cũ trước khi sửa. Đã sao lưu rồi chạy `python -m src.eval.analyze_task5` để dựng lại 10 biểu đồ/catalog/manifest từ metric hiện có, **tái sử dụng timing đã kiểm chứng**. Không sửa tay hash để bỏ qua gate; không đo lại timing hoặc đổi kết quả P/R/F1.

## 2. Kiểm tra và bằng chứng

- [WEB_CHECK_SUMMARY.json](WEB_CHECK_SUMMARY.json): tổng hợp kết quả và checksum source đúng phiên đã kiểm tra.
- [API_REGRESSION.json](API_REGRESSION.json): **25/25 ảnh** dùng mặc định đúng của app khớp P/R/F1 CSV đến 4 chữ số; Canny/angle/thiếu stack được kiểm tra riêng. Các file config/metric so với trước sửa không thay đổi.
- [BROWSER_REGRESSION.json](BROWSER_REGRESSION.json): **11 luồng PASS trên Edge headless thật**, gồm preset, dark blob, ignore, góc, trạng thái nút, đảo thứ tự response, validation, benchmark và xem/phóng to 10 biểu đồ; không có JavaScript exception.
- [KIEM_TRA_SAU_SUA.json](../../10_11/sau_sua_loi/KIEM_TRA_SAU_SUA.json): kiểm tra toàn bộ bàn giao và unittest hiện có. **77/77 test PASS**, gồm 19 test hồi quy web mới; 415 TIFF trong ZIP tiếp tục khớp nguồn.
- [Ảnh Studio](WEB_STUDIO_SAU_SUA.png) và [ảnh benchmark](WEB_BENCHMARK_SAU_SUA.png): giao diện thực sau sửa, không phải mockup.

Trong phép thử race, trình duyệt cố ý cho fetch trả sai thứ tự bằng hai response kiểm soát được; các F1 0,1111/0,2222 chỉ là token test, không ghi vào metric hoặc các ảnh chụp kết quả thực.

## 3. Mở và chạy

Tại thư mục gốc dự án:

```powershell
.\.venv\Scripts\python.exe -m src.web.app --port 5000
```

Nếu app cũ đang mở, dừng server cũ bằng Ctrl+C, chạy lại lệnh trên và tải lại trang. Source mới không được nạp vào một server đã chạy trước khi sửa. Ứng dụng tự mở trình duyệt tại cổng đang dùng; nếu 5000 bận sẽ chọn cổng kế tiếp.

Chạy kiểm tra khi thay code:

```powershell
python -m unittest discover -s tests -v
python tools/verify_web_13_11.py
node tools/test_web_browser_13_11.cjs
```

Kiểm thử browser dùng Node 24, Edge cài sẵn và `.venv`, chỉ tạo server/profile/cổng tạm; tự dừng đúng các tiến trình test. `tools/verify_duc_manh_12_11.py` đã được đổi sang đếm toàn bộ test hiện có thay vì bắt buộc đúng 58 test cũ.

## 4. Phạm vi nghiệm thu

Sửa này hoàn thiện lớp web và cách công bố chỉ số; **không biến 185 cặp chưa đạt STRICT thành đạt**, không biến F1 nội bộ thành điểm test độc lập, không thay thế PDF báo cáo hoặc ảnh hiệu chuẩn Lộc cần bổ sung. Python F1 một ảnh và macro/micro cả tập được hiển thị tách bạch.

Đã giữ bản sao trước sửa:

- `outputs/archives/maintenance_13_11/web_truoc_sua.zip`.
- `outputs/archives/maintenance_13_11/analysis_truoc_dong_bo_web.zip`.

Không thay code lõi, config, raw, GT, ba ZIP TIFF hoặc phần nội dung LaTeX/slide của các thành viên khác.
