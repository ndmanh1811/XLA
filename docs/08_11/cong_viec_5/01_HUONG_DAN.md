# Hướng dẫn mở, đọc và dùng sản phẩm công việc 5

Quay về [README công việc 5](../../../README_DUC_CONG_VIEC_5.md).
Kết quả nằm gọn trong `outputs/analysis/duc_task5_08_11/`, tách khỏi
`outputs/metrics/duc_08_11/` của công việc 4.

## 1. Thứ tự xem

1. Mở `MO_BIEU_DO_DUC.cmd` ở gốc dự án để xem gallery trên Chrome/Edge.
2. Đọc `PHAN_TICH_KET_QUA.md` bằng Markdown Preview trong VS Code.
3. Chọn hình trong `figures/` để đưa vào báo cáo/slide. Dùng file PNG gốc,
   không chụp màn hình gallery. Mỗi PNG có DPI metadata xấp xỉ 300; SVG/PDF
   giữ đường và chữ dạng vector.
4. Khi cần kiểm tra số liệu, mở CSV trong `tables/` hoặc `runtime/`. CSV dùng
   UTF-8 BOM; nếu Excel dồn một cột, nhập qua Data → From Text/CSV, chọn UTF-8
   và dấu phân cách Comma.

## 2. Mười hình và cách diễn giải

| Hình | Nội dung | Điều cần chú ý khi thuyết trình |
| --- | --- | --- |
| `01_doi_chuan_tang1` | Sai số tương đối theo toán tử/scale và số PASS/FAIL | PASS phải đạt cả relative error và Pearson. ST chỉ có hai cặp scale |
| `02_sai_so_bien_va_loi` | RMSE biên và lõi, cùng chuẩn hóa bằng peak lõi | Symlog tuyến tính gần 0 giữ cả điểm sai số bằng 0; đường chéo nghĩa là RMSE hai vùng bằng nhau |
| `03_psnr_gaussian` | PSNR theo sigma của 5 ảnh | Chỉ Gaussian dùng MAX=255; không diễn giải thành chất lượng phát hiện cạnh |
| `04_f1_theo_sigma` | F1 Canny theo sigma và chênh lệch hai nguồn | Native Edges là đường tham chiếu riêng, có ngưỡng/thuật toán khác |
| `05_precision_recall` | Các điểm P/R của lưới ngưỡng và điểm được chọn | Không phải đường PR liên tục; không có AP/AUC |
| `06_luoi_nguong_canny` | F1 Python của 12 cặp ngưỡng tại mỗi sigma | Ngưỡng được chọn trong lưới đã thiết kế, rồi áp nguyên cho Fiji |
| `07_f1_tung_anh` | DRIVE và blob từng ảnh | So ảnh tổng hợp với tế bào để thấy giới hạn dữ liệu thực |
| `08_blob_macro_micro` | Macro và micro F1 blob | Macro đặt cùng trọng số cho ảnh; micro gộp đối tượng |
| `09_thoi_gian_theo_lenh` | Thời gian và tỷ số Python/engine theo phép toán | Trên trục tỷ số, >1 nghĩa là Python mất nhiều thời gian hơn; IQR là giữa case |
| `10_thoi_gian_theo_sigma` | Runtime tăng theo sigma, giữ cùng 5 ảnh | Mỗi case đã lấy median 5 lần sau warm-up, không thay nhóm ảnh theo sigma |

Nếu chỉ đủ chỗ đưa 4 hình vào slide, có thể chọn 01, 04, 07 và 09. Các hình
còn lại dùng cho báo cáo/phụ lục hoặc khi giải thích câu hỏi. Đây là gợi ý
chọn hình; không tự sửa slide chung của thành viên khác.

## 3. Phép đo thời gian mới

Code Python tự cài đặt được đo cùng các trường hợp với API ImageScience cục
bộ. Bảng case dựng từ config và 25 ảnh, không lấy số thời gian cũ làm dữ liệu
đầu vào. Có 357 case, tương ứng 423 map trong phạm vi macro hợp nhất (Hessian
và ST xuất hai map trong một lần gọi). Bỏ 12 case edge legacy của log cũ.

Mỗi nguồn có 2142 mẫu: một warm-up và năm mẫu đo cho mỗi case. Chỉ 1785 mẫu
mỗi nguồn được tổng hợp; tổng hai nguồn có 4284 mẫu gồm warm-up và 3570 mẫu
giữ lại. Đơn vị là ms. Dùng `perf_counter_ns` cho Python và `System.nanoTime`
cho Java, không gồm đọc ảnh/chuyển kiểu, clone input Java hay lưu TIFF.

CSV từng mẫu có `iteration=0, warmup=true`; năm lần dùng chấm có iteration
1–5. `runtime_case_summary.csv` giữ median, Q25/Q75, min/max từng case.
`runtime_paired.csv` ghép cùng ảnh/lệnh/scale và lấy tỷ số hai median case.
`runtime_by_command.csv` trong tables tổng hợp giữa case, không phải mẫu lặp.

ImageJ/ImageScience đo qua headless API; giao diện macro, đọc/ghi đĩa,
Canny hysteresis, Frangi và chấm GT không nằm trong số này. Không trình bày
thành thời gian toàn pipeline. Python float64 và precision nội tại của engine
được giữ theo cài đặt tương ứng, không dùng kết quả này để tách riêng hiệu
ứng ngôn ngữ lập trình. Môi trường/JAR hash nằm trong `runtime_environment.json`.

## 4. Tạo lại hình hoặc đo lại

```powershell
# Chỉ dùng lại thời gian đã đo nếu fingerprint code/raw/config trùng
.\.venv\Scripts\python.exe -B -X utf8 -u -m src.eval.analyze_task5

# Đo lại cả hai nguồn rồi vẽ
.\.venv\Scripts\python.exe -B -X utf8 -u -m src.eval.analyze_task5 --remeasure-runtime

# Máy khác: trỏ thư mục có ij.jar và plugins/jars/imagescience.jar
.\.venv\Scripts\python.exe -B -X utf8 -u -m src.eval.analyze_task5 --remeasure-runtime --imagej-dir "C:\duong-dan\ImageJ"
```

Để đo mới cần JDK có `javac` trên PATH. Java helper được biên dịch vào
`runtime/classes/` trong dự án; không sửa/cài plugin vào ImageJ bên ngoài.
PNG được đọc bằng Java ImageIO để không khởi tạo menu AWT trong ImageJ cũ.
Mọi tính toán đo vẫn gọi các toán tử thật của `imagescience.jar`.

Nếu metric task 4 bị sửa hoặc dependency của nó đổi, chương trình dừng trước
khi vẽ. Cần chạy lại công việc 4 để tạo bộ metric có provenance mới, không
chỉnh checksum thủ công. Chỉ lấy sản phẩm khi `analysis_manifest.json` có
`status=COMPLETE`; nếu `ERROR/RUNNING`, chưa dùng để bàn giao.

## 5. File cần gửi cho nhóm

- `PHAN_TICH_KET_QUA.md`: phần viết của Đức, có chú thích hình và giới hạn.
- `figures/`: chọn PNG/PDF/SVG tùy khung báo cáo và slide.
- `tables/`: số liệu tổng hợp cho các hình, kèm các CSV metric công việc 4
  nếu người biên tập cần kiểm tra sâu hơn.
- `runtime/`: số liệu đo mới, môi trường và log phiên bản; không lấy lại log
  thời gian cũ thay cho phép đo lặp.
- `index.html`, `figure_catalog.csv`, `analysis_manifest.json`: xem nhanh và
  kiểm tra bộ bàn giao. Giữ nguyên cấu trúc thư mục khi copy.

Không có kết luận mới về noise/crop hoặc tập test độc lập. Phần đối chuẩn
vẫn giữ đúng 35 PASS/185 chưa đạt; mô tả nguyên nhân chưa được hiệu chuẩn
chứng minh phải được ghi như giả thuyết.
