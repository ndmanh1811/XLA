# Kiểm tra logic và chỉ số web/app — 13/11/2026

> **Bằng chứng trước khi sửa.** Đã xử lý các lỗi trong lượt tiếp theo ngày 13/11; xem [bàn giao sau sửa web](../sau_sua_web_app/BAN_GIAO_SAU_SUA_WEB.md). Các JSON bên dưới được giữ nguyên làm đối chiếu trước/sau.

**Kết luận: có lỗi thực sự ở lớp web, nhất là chọn sai bản đồ Fiji và hiển thị kết quả của yêu cầu cũ. Chưa nên dùng mọi MAE/Pearson trên web để kết luận độ khớp Python–Fiji.** Ngược lại, P/R/F1 của Python trên 25 ảnh với tham số chuẩn khớp CSV hiện hành đến 4 chữ số thập phân; chưa thấy bằng chứng dữ liệu metric chuẩn bị sai hoặc bị sửa.

Phạm vi: đọc toàn bộ `src/web/app.py`, JavaScript trong template và tài liệu web; chạy 53 ca POST `/api/process` gồm ca dữ liệu thật, đầu vào sai và hai ca mô phỏng; thử các endpoint đọc dữ liệu/upload; đối chiếu đủ 25 ảnh với CSV; chạy JavaScript thật trong Node VM với DOM/fetch kiểm soát được. Không kiểm thử bố cục trên trình duyệt thực hoặc triển khai từ xa.

## 1. Lỗi cần ưu tiên sửa

### W01 — P1: fallback chọn sai loại bản đồ Fiji

**Vị trí:** `src/web/app.py:175`, `:625`, `:675`; nhãn giao diện tại `src/web/templates/index.html:1417`.

- **Tái hiện Canny:** chọn `bsds_03`, σ=2, Low=67, High=91. Không có TIFF `grad` của ảnh này, nên nhánh dự kiến bỏ qua. Fallback sau đó nạp `fiji_bsds_03_edge_s2.0.tif`, trong khi bản đồ Python dùng tính MAE/Pearson vẫn là gradient magnitude đã nhân σ. Hai bản đồ khác phép xử lý/chuẩn hóa nhưng giao diện vẫn gọi Fiji là `|∇L|`.
- Web trả **MAE=13,360923, r=0,483984**. Khi dựng đúng gradient Fiji từ Lx/Ly rồi chuẩn hóa giống Python, cùng ảnh này có **MAE≈0,005510705, r≈1**. Chênh lệch trên web không phải bằng chứng lõi NumPy sai ở mức đó.
- **Tái hiện Blob:** chọn `bsds_01` rồi chuyển thuật toán sang Blob. Bộ Fiji không đủ 7 Laplacian của ảnh này; fallback lại nạp một `fiji_bsds_01_lap_s2.0.tif` thô, trong khi Python là max của |σ²LoG| qua 7 scale. Web vẫn báo có tham chiếu và trả **MAE=11,442378, r=−0,081333**.

**Cách xử lý:** mỗi loại kết quả cần một hàm dựng counterpart rõ ràng. Canny có thể dựng gradient từ Fiji Lx/Ly nếu thiếu grad; Blob phải đủ stack hoặc báo không có tham chiếu. Bỏ fallback tổng quát cho các đầu ra khác đại lượng/đơn vị; không tính MAE/r khi counterpart không tương ứng.

### W02 — P1: so góc gradient với độ lớn gradient

**Vị trí:** `src/web/app.py:175` (resolver cho `gradient`), `:350` (tạo góc), `:675` (nạp tham chiếu).

Chọn Gradient → Hướng gradient, `bsds_01`, σ=2. Python trả `atan2(Ly,Lx)` theo radian, resolver Fiji lại trả `grad` vì chỉ phân nhánh Lx/Ly; web so góc với độ lớn và báo **MAE=3,507136, r=−0,001896**.

**Cách xử lý:** dựng góc Fiji từ cặp Lx/Ly cùng scale. Với góc, dùng sai khác góc có quấn chu kỳ 2π và quy định vùng gradient đủ lớn; không dùng trực tiếp Pearson tuyến tính để nghiệm thu hướng. Số đối chiếu tuyến tính bổ trợ trong JSON không thay thế metric góc đúng nghĩa.

### W03 — P1: phản hồi cũ có thể ghi đè lựa chọn mới

**Vị trí:** `src/web/templates/index.html:1342`, `:1394`, `:1427`.

`runAlgorithm()` không có request sequence, AbortController hoặc kiểm tra ảnh/thuật toán đã gửi so với lựa chọn hiện tại. Kết quả được gán thẳng vào `lastData`; nhãn lại dùng `currentAlgo` tại lúc nhận phản hồi.

Phép thử thứ tự phản hồi: gửi Canny/BSDS trước, Frangi/DRIVE sau; cho DRIVE trả trước rồi BSDS trả sau. Giao diện cuối cùng chứa **ảnh/F1 của BSDS** nhưng nhãn **Fiji Hessian → Frangi** và lựa chọn vẫn là `drive_08`. Các token ảnh và F1 minh họa trong JSON frontend là dữ liệu giả kiểm soát thứ tự, không phải số đo của ảnh thật.

Ngoài ra, một lần bấm preset gửi **2 request**: `onAlgoChange()` đã gọi xử lý, rồi `applyPreset()` gọi thêm. Điều này tăng tải và khả năng gặp trạng thái trên.

**Cách xử lý:** chụp snapshot tham số, chỉ render response có sequence mới nhất; hủy request cũ khi có thể; preset dựng xong controls/tham số rồi gọi xử lý đúng một lần. Đính kèm thông tin ảnh/thuật toán vào response để đối chiếu.

## 2. Những lỗi logic/chỉ số khác đã xác minh

| Mã | Mức | Lỗi và bằng chứng | Vị trí | Cách xử lý |
| --- | --- | --- | --- | --- |
| W04 | P2 | Checkbox ghi “Áp dụng 15 vùng Ignore” nhưng chỉ đổi việc vẽ khung; matching luôn nhận ignore. `blob_05` bật/tắt đều F1=0,4921; nếu thực sự bỏ ignore, các detection chuẩn hiện có cho F1≈0,462810. | `app.py:495`, `:526`, `:531`; `index.html:1087` | Đổi nhãn thành “Hiện vùng ignore” để giữ nguyên protocol chuẩn, hoặc làm chế độ thăm dò riêng có chỉ rõ protocol thay đổi. |
| W05 | P2 | Khi mảng hằng, web gán Pearson bằng 1 nếu allclose, bằng 0 nếu không; thử hai mảng toàn 1 nhận r=1 dù Pearson không xác định. Đây là ca mô phỏng, không phải tuyên bố các ảnh raw hiện tại đều hằng. | `app.py:693` | Trả `null`/N/A cùng lý do; frontend kiểm tra số hữu hạn trước khi `.toFixed()`. |
| W06 | P2 | API Frangi chia thời gian đạo hàm/detector theo 70%/30% cố định; cả 10 ảnh đều trả tỷ lệ đó. Tổng thời gian vẫn có đo, nhưng hai thành phần không được đo riêng. | `app.py:462` | Đo trực tiếp từng đoạn hoặc chỉ công bố tổng; không sử dụng hai thành phần này như benchmark thực. UI hiện chỉ dùng tổng. |
| W07 | P2 | Python/Fiji tự min–max từng ảnh khi render. Mảng A và 2A tạo PNG giống hệt nhau; vì vậy màu giống không chứng minh đáp ứng cùng biên độ. | `app.py:87`, các lệnh gọi `array_to_base64_png` | Dùng vmin/vmax chung cho hai counterpart, với thang có tâm 0 cho bản đồ có dấu; thêm chú thích/colorbar. |
| W08 | P2 | Thiếu validation đầu vào: `algorithm=unknown` vẫn HTTP200; `sigma='abc'` HTTP500 HTML; σ=0 HTTP500; Low=95/High=10 vẫn xử lý; file `.png` hỏng HTTP500 HTML. Người dùng có thể kéo Low vượt High ngay trong UI. | `app.py:270`, `:285`, `:326`; `index.html:1032` | Kiểm tra whitelist thuật toán, kiểu số hữu hạn, σ>0, 0≤Low≤High≤100 và file ảnh; trả HTTP400 JSON có thông báo cụ thể. |
| W09 | P2 | Chuyển Canny → Gaussian → Canny giữ `pyView='response'`, nhưng hàm xử lý không đồng bộ trạng thái active của hai nút xem. Có thể thấy nút “nhị phân” vẫn active trong khi ảnh là response. | `index.html:1297`, `:1400` | Đồng bộ mode, trạng thái nút và ảnh qua một hàm duy nhất mỗi khi nhận kết quả mới. |

## 3. Các điểm cần làm rõ, không được gọi nhầm là lỗi số liệu hiện tại

- **P/R/F1 Python trên 25 ảnh: khớp.** 10 BSDS tại σ=2, 10 DRIVE đa tỷ lệ và 5 blob dùng tham số chuẩn đều khớp CSV đến 4 chữ số. Blob dùng lại matching một–một và ignore của pipeline, không quay lại lỗi một detection khớp nhiều GT.
- **Một ảnh khác macro là đúng.** Canny `bsds_01` F1=0,4821 khác macro 10 ảnh=0,4779; Frangi `drive_08` F1=0,6420 khác macro=0,4774; `blob_05` F1=0,4921 khác blob macro=0,8984. Đây là khác đơn vị tổng hợp, không phải bằng chứng web tính sai F1.
- **Nhãn hybrid được ghi đúng.** Frangi ở panel Fiji dùng Hessian Fiji rồi chạy Frangi Python; README và title nói rõ hybrid. Blob panel Fiji là response, không phải vòng tròn detection. Không coi việc hiển thị response khác mặt nạ Python là lỗi tính toán tự thân; phải xét loại mảng thực sự dùng cho metric như W01/W02.
- **Benchmark đọc đúng dữ liệu hiện tại.** `/api/benchmarks` trả đủ 220 dòng tầng 1, bảng tầng 2 đúng CSV; 10 URL biểu đồ hoạt động. Headline 0,4779 / 0,4774 / 0,8984 hiện đúng khi làm tròn, nhưng vẫn gõ cứng trong HTML và không tự cập nhật theo API.
- **“0 FAIL” cần chú thích ngưỡng.** CSV chuẩn là 35 PASS / 185 FAIL theo STRICT. Web đổi cách gọi thành 35 STRICT / 185 RELAXED / 0 FAIL. Có thể trình bày phân hạng mở rộng nếu ghi rõ RELAXED là ngưỡng 1e-2 và 185 cặp vẫn thất bại theo ngưỡng gốc 1e-4; không trình bày như không có trường hợp chưa đạt chuẩn ban đầu. Headline nên tính từ dữ liệu và ngưỡng được công bố.
- **Chưa đi qua gate provenance khi đọc benchmark.** Lần kiểm tra này `verify_metric_delivery()` PASS, nên chưa có lỗi stale CSV hiện tại. Route web vẫn có thể phục vụ bảng cũ khi manifest không hợp lệ vì chỉ đọc CSV, không xác minh trạng thái/checksum hoặc báo nguồn mất đồng bộ.
- **MAE/RMSE live khác protocol lõi.** Web đo toàn ảnh bằng float64 vừa tính; bảng chuẩn đo bản đồ TIFF float32 sau crop. Ví dụ Laplacian `bsds_01`, σ=2: web MAE=0,016528, bảng lõi=0,016475465. Cần ghi rõ phạm vi toàn ảnh và không dùng số live làm kết quả STRICT trực tiếp; sự khác nhau này không tự chứng minh công thức sai.
- **Config bị gõ cứng ở web.** Biên mirror, algebraic, dãy scale, hệ số xói mòn 4 và nhân σ/σ² trực tiếp đang trùng config hiện tại, nên các preset vẫn khớp. Nhưng app không xét cờ `featurej_normalized` và không dùng hàm chuẩn hóa chung; phép thử cô lập khi đổi cờ xác nhận web không đổi cách nhân. Đây là ràng buộc kỹ thuật chưa được tuân thủ, cần sửa để không lệch khi cấu hình/phiên Fiji đổi.
- **Hai chi tiết UI khác:** thiếu TIFF ở ảnh mẫu/scale tự chọn vẫn bị ghi như “ảnh tải lên”; nhãn Hessian “λ2 chính / λ1 phụ” không diễn đạt đúng thứ tự algebraic Largest/Smallest. Ở các chế độ chỉ có MAE, HUD vẫn mang tiêu đề “Ground Truth F1” dù giá trị có tiền tố MAE.
- **Upload RGB thông thường dùng PIL L.** Ảnh green thuần ra pixel150 theo chuyển xám; không lấy riêng green như bước chuẩn bị DRIVE. Đây không phải lỗi với ảnh raw DRIVE đang có; cần công bố nếu muốn so ảnh retina người dùng tải lên với kết quả dataset chuẩn.

## 4. Bằng chứng và cách chạy lại

- [API_NUMERICAL_AUDIT.json](API_NUMERICAL_AUDIT.json): 53 ca xử lý, 25 đối chiếu P/R/F1 và giá trị các lỗi tái hiện.
- [FRONTEND_STATE_AUDIT.json](FRONTEND_STATE_AUDIT.json): phản hồi đảo thứ tự, 2 request/preset và trạng thái nút xem.
- [UNITTEST_LOG.txt](UNITTEST_LOG.txt): 58/58 kiểm thử lõi/metric hiện có PASS. Dòng debug `Tier 1 ... 0 PASS ... 0 FAIL` trong log được in khi test dùng dữ liệu giả; không phải kết quả đối chuẩn trên bộ TIFF thật (vẫn 35 STRICT/185 chưa đạt). Các test cũ không bao phủ các lỗi web nêu trên.

```powershell
python tools/audit_web_13_11.py
node tools/audit_web_frontend_13_11.cjs
python -m unittest discover -s tests -q
```

Đã cài Flask/flask-cors theo `requirements.txt` vào `.venv` để chạy thử. Đợt này chỉ thêm script kiểm tra và hồ sơ kết quả; SHA-256 xác nhận source web, config, các file metric và manifest analysis không bị sửa. Không sinh lại TIFF/metric hoặc thay dữ liệu để làm các phép thử đạt.

Thứ tự sửa đề xuất: **W01/W02 → W03 → W04/W05 → validation/config → timing/thang màu/trạng thái nút**. Sau khi sửa, thêm test hồi quy tại route và kiểm thử UI bằng trình duyệt thực; không dùng việc 25 preset khớp để bỏ qua các nhánh so sánh sai.
