# Bảo Lộc — Bổ sung hồ sơ đo hiệu chuẩn FeatureJ

> **Cập nhật 11/11/2026:** phép đo định lượng đã hoàn tất tại
> `docs/fiji/calibration/`: 40 TIFF, 40 dòng ROI, 2.682 điểm profile và manifest
> SHA-256. Kết quả xác nhận config hiện hành; xem `CALIBRATION_RESULTS.md`.
> Phần screenshot hộp thoại/phiên bản đã hoàn tất ngày 12/11/2026; xem
> `calibration/screenshots/README.md` để truy vết từng PNG tới lệnh và TIFF.

## Mục đích

Lưu bằng chứng cho các thông số đang dùng trong `config.yaml`: bán kính cắt kernel theo bậc, cách xử lý biên, cờ chuẩn hóa theo sigma và thứ tự trị riêng.

Các TIFF và workflow đã có chứng minh nhóm đã chạy/xuất kết quả. Hồ sơ hiệu chuẩn giúp giải thích **vì sao chọn các thông số đó**, để Mạnh kiểm tra code và Hưng trình bày trong báo cáo.

Nếu đã đo và lưu bằng chứng từ trước, chỉ cần gom lại. Nếu còn thiếu bằng chứng thì chạy lại các phép đo dưới đây. Không cần chạy lại toàn bộ 435 TIFF chỉ để lập hồ sơ hiệu chuẩn.

Các đường dẫn bên dưới tính từ thư mục dự án `XLA-dev-NguyenDucManh`.

## 1. Dùng các ảnh hiệu chuẩn đã có

Mở bằng Fiji các file trong `data/calib/`:

| File | Nội dung | Dùng kiểm tra |
| --- | --- | --- |
| `ramp.tif` | I(x,y) = x | Dấu Lx, gradient, cờ chuẩn hóa bậc 1 |
| `parabola.tif` | I(x,y) = x²/2 | Lxx, Laplacian và cờ chuẩn hóa bậc 2 |
| `saddle.tif` | I(x,y) = x²/2 − y² | Dấu/thứ tự trị riêng Hessian |
| `dirac.tif` | Xung tâm bằng 1, kích thước 101×101 | Đáp ứng kernel và bán kính cắt |
| `bright_border.tif` | Ảnh có viền sáng | Xử lý biên reflect/mirror |

Giữ ảnh float32, không chuyển sang ảnh 8-bit để đo. Ngay sau mỗi lần mở ảnh, đặt đơn vị pixel bằng **Analyze → Set Scale**, tương đương lệnh:

```ijm
run("Set Scale...", "distance=0 known=0 pixel=1 unit=pixel");
```

Ghi phiên bản ImageJ/Fiji, FeatureJ và ImageScience thực tế trên máy đo; chụp hộp thoại các tùy chọn đã dùng.

## 2. Đo cờ chuẩn hóa riêng cho từng lệnh

Chọn ROI ở giữa ảnh, cách biên đủ xa theo support của phép lọc. Ghi tọa độ/kích thước ROI, Mean và nếu có thì thêm Min/Max/StdDev. Không đo trung bình toàn ảnh vì vùng biên có thể khác vùng lõi.

### Derivatives

- Trên `ramp.tif`, lấy Lx tại sigma = **1, 2, 4**.
- Nếu các giá trị đều gần **1**: đầu ra chưa nhân sigma.
- Nếu lần lượt gần **1, 2, 4**: đầu ra đã nhân sigma.
- Kiểm tra dấu Lx phải dương trên ảnh I=x.
- Trên `parabola.tif`, lấy Lxx: đối chiếu giá trị gần **1** với giá trị gần **sigma²** để kiểm tra bậc 2.

### Laplacian

Chạy trên `parabola.tif`, bật tính ảnh Laplacian và tắt tìm zero-crossings. Đối chiếu giá trị gần **1** với **sigma²** tại sigma = 1, 2, 4.

### Hessian

Chạy trên `saddle.tif` tại sigma = 1, 2, 4, xuất Largest và Smallest.

- Kỳ vọng lý thuyết của Hessian thô, có dấu: khoảng **(1, −2)**.
- Nếu đã chuẩn hóa bậc 2: khoảng **sigma² × (1, −2)**.
- Chụp rõ trạng thái **Absolute eigenvalue comparison**. Khi bật, FeatureJ sắp xếp và xuất độ lớn trị riêng, làm mất dấu; muốn kiểm tra cặp có dấu thì phải tắt tùy chọn này.
- Ghi tên từng ảnh đầu ra cùng số đo tương ứng; không chỉ ghi hai số mà bỏ mất tùy chọn/dấu.

Tham khảo: [FeatureJ Hessian — tài liệu chính thức](https://imagescience.org/meijering/software/featurej/hessian/).

### Edges

Chạy trên `ramp.tif`: bật tính gradient magnitude, **tắt NMS**, để trống hai ngưỡng. Đối chiếu giá trị gần **1** với **sigma**. Đây là đo đáp ứng gradient thô, không phải đo ảnh biên nhị phân.

### Structure

Chạy trên `ramp.tif` với hai cặp scale đang dùng **(sigma_d, sigma_i) = (1,3), (2,6)**. Xuất hai trị riêng, ghi số đo và tùy chọn. Với gradient thô gần (1,0), kỳ vọng tensor ở vùng lõi có trị riêng gần **(1,0)**; đối chiếu sự thay đổi theo scale để kết luận normalization.

**Lưu giá trị thực đo, không làm tròn thành giá trị lý thuyết để ép khớp.** Chẳng hạn đo được 0.9996 thì ghi 0.9996 và nhận xét gần 1.

## 3. Đo kernel và bán kính cắt k

Dùng `dirac.tif`, chạy Derivatives tại sigma = **1, 2, 4**, lần lượt:

- Gaussian: x-order=0, y-order=0.
- Lx: x-order=1, y-order=0.
- Lxx: x-order=2, y-order=0.

Lưu TIFF đáp ứng xung, trích profile/số liệu để xác định vùng hỗ trợ, tổng trọng số và so với đáp ứng Gaussian/đạo hàm giải tích tương ứng. Ghi bán kính theo từng trục; với đạo hàm theo x, cần phân biệt support trục đạo hàm và support trục làm mịn.

Từ bán kính r đo được và sigma, đối chiếu **r = ceil(k × sigma)** để suy ra k riêng cho Gaussian, bậc 1 và bậc 2. Không tự điền lại k=3/4 chỉ vì config hiện đang ghi như vậy. Profile ở một hàng của kernel 2D còn có hệ số của kernel theo trục còn lại; khi so biên độ phải dùng đúng đáp ứng 2D hoặc phép trích kernel phù hợp.

Nếu đáp ứng khác giả định, trọng số không như kỳ vọng hoặc không xác định rõ bán kính cắt, ghi lại và trao đổi với Mạnh thay vì tự sửa kết quả.

## 4. Đo kiểu biên và ghi lệnh tái hiện

- Dùng `bright_border.tif`, lưu profile/các giá trị sát biên để đối chiếu reflect và mirror theo định nghĩa của dự án.
- Ghi kết luận `border_mode` kèm số liệu/ảnh, không chỉ chép tên trong tài liệu plugin.
- Mở **Plugins → Macros → Record**, ghi lại các lệnh và tùy chọn thật đã chạy.
- Lập bảng ánh xạ mã `gauss`, `lx`, `lxy`, `lap`, `grad`, `hess-l1/l2`, `st-l1/l2` sang lệnh FeatureJ/tùy chọn tương ứng. Ghi rõ gradient lấy bằng Edges khi tắt NMS/ngưỡng nếu dùng cách đó.

## 5. Hồ sơ cần bàn giao

Bộ khung tái hiện đã được tạo tại `docs/fiji/calibration/` trong dự án. Các CSV
ban đầu chỉ có schema/trạng thái `NOT_RUN`; chúng chưa phải bằng chứng thực đo
cho đến khi Lộc chạy `reproduce.ijm` trên Fiji và bổ sung ảnh chụp/phiên bản:

```text
calibration/
├── README.md                 # Phiên bản, cách chạy, kết luận và giới hạn
├── measurement_results.csv   # Số đo theo ảnh/lệnh/sigma/ROI/tùy chọn
├── kernel_profiles.csv       # Profile/giá trị đáp ứng xung và phép đo biên
├── command_mapping.csv       # Ánh xạ mã thuật toán sang lệnh FeatureJ
├── reproduce.ijm             # Macro Recorder/script tái hiện phép đo
├── screenshots/              # Hộp thoại, phiên bản và kết quả đo
└── outputs/                  # TIFF float32 của phép hiệu chuẩn
```

Các file khung đã có không có nghĩa phép đo đã hoàn tất. Chỉ kết luận sau khi
CSV có giá trị thực, TIFF calibration tồn tại và tùy chọn/phiên bản được ghi lại.

CSV số đo nên có các cột:

```text
image,command,sigma,sigma_i,options,roi_x,roi_y,roi_width,roi_height,
output_name,expected_raw,measured_mean,measured_min,measured_max,conclusion
```

Mỗi kết luận cần truy được về file TIFF, số đo và tùy chọn tương ứng. Bảng tổng kết nên trả lời đủ: k theo từng bậc; kiểu biên; normalization từng lệnh; dấu và thứ tự trị riêng; các điểm còn chưa xác minh.

## 6. Phối hợp chốt với nhóm

1. **Lộc** bàn giao bằng chứng đo và kết luận.
2. **Mạnh** đối chiếu code, quy ước và `config.yaml`; **Hưng** đưa mô tả và bằng chứng phù hợp vào báo cáo.
3. Nếu kết luận đo khác cấu hình hiện tại, nhóm thống nhất thay đổi trước; khi đổi config/code thì **Đức chạy lại metric và timing theo hướng dẫn hiện hành**.

Mục đích là kiểm chứng và giải thích các thông số/sai số, không phải bảo đảm sau khi bổ sung hồ sơ thì 185 cặp RELAXED sẽ tự trở thành STRICT. Không nới ngưỡng hoặc sửa kernel chỉ để có kết quả PASS.
