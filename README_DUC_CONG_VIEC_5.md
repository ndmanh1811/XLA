# Đức — Công việc 5: Vẽ biểu đồ và phân tích kết quả

**STT 24 trong bảng phân công, hạn 14/11.** Thực hiện ngày **08/11/2026**.
Bộ này đọc kết quả công việc 4, tạo hình và phân tích; đo mới thời gian Python
và ImageScience trên cùng máy. Ảnh, nhãn và CSV metric công việc 4 giữ nguyên.

## Mở file nào trước?

| Bạn cần | File | Cách mở |
| --- | --- | --- |
| Xem toàn bộ 10 biểu đồ | [index.html](outputs/analysis/duc_task5_08_11/index.html) | Nháy đúp trong Explorer để mở bằng Chrome/Edge; không cần server |
| Mở nhanh thư viện hình | [MO_BIEU_DO_DUC.cmd](MO_BIEU_DO_DUC.cmd) | Nháy đúp file CMD |
| Đọc phần phân tích để đưa vào báo cáo | [PHAN_TICH_KET_QUA.md](outputs/analysis/duc_task5_08_11/PHAN_TICH_KET_QUA.md) | VS Code, Ctrl+Shift+V |
| Lấy hình chất lượng cao | [Thư mục figures](outputs/analysis/duc_task5_08_11/figures) | PNG 300 DPI cho Word/slide; PDF hoặc SVG cho bản in/vector |
| Xem số liệu đứng sau biểu đồ | [Thư mục tables](outputs/analysis/duc_task5_08_11/tables) | CSV mở bằng Excel/VS Code |
| Xem thời gian từng lần đo | [python_samples.csv](outputs/analysis/duc_task5_08_11/runtime/python_samples.csv), [fiji_engine_samples.csv](outputs/analysis/duc_task5_08_11/runtime/fiji_engine_samples.csv) | Excel, lọc iteration; iteration=0 là warm-up |
| Xem trạng thái hoàn tất | [analysis_manifest.json](outputs/analysis/duc_task5_08_11/analysis_manifest.json) | Phải có `status=COMPLETE` |
| Hướng dẫn đọc biểu đồ và bàn giao | [01_HUONG_DAN.md](docs/08_11/cong_viec_5/01_HUONG_DAN.md) | VS Code Markdown Preview |

Trong VS Code, nhấn vào HTML có thể mở source. Muốn xem dạng trang, dùng
`MO_BIEU_DO_DUC.cmd` hoặc mở file HTML bằng trình duyệt. Thư viện hoạt động
offline, không tải font/script từ Internet. Giữ nguyên các thư mục con khi
copy bộ bàn giao để liên kết ảnh còn hoạt động.

## Các sản phẩm đã tạo

- **10 biểu đồ**, mỗi hình có **PNG 300 DPI, SVG và PDF**: đối chuẩn, sai số
  biên, PSNR Gaussian, F1 theo sigma, Precision–Recall, lưới ngưỡng, F1 từng
  ảnh, macro/micro F1 blob, thời gian theo lệnh và thời gian theo sigma.
- **Phân tích tiếng Việt** theo từng nhóm kết quả, có số liệu, ưu điểm,
  hạn chế, giả thuyết cần kiểm chứng và kết luận phù hợp để dùng trong báo cáo.
- **Đo thời gian mới:** 357 trường hợp cùng ảnh/lệnh/scale cho hai nguồn;
  mỗi trường hợp bỏ 1 warm-up, giữ 5 lần đo. Tổng 4284 mẫu gồm warm-up,
  tương ứng 3570 mẫu được dùng tổng hợp.
- CSV tổng hợp, CSV từng lần đo, môi trường và checksum để đối chiếu lại.

## Chạy lại

Chỉ vẽ/phân tích lại từ metric và thời gian đã đo:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -u -m src.eval.analyze_task5
```

Hoặc nháy đúp [CHAY_CONG_VIEC_5_DUC.cmd](CHAY_CONG_VIEC_5_DUC.cmd). Nếu chưa
có bộ runtime, chương trình tự đo trước khi vẽ. Nếu code/raw/config đã thay
đổi so với bộ runtime, chương trình dừng và yêu cầu đo lại:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -u -m src.eval.analyze_task5 --remeasure-runtime
```

Chạy lại metric công việc 4 nếu dữ liệu/code ảnh hưởng metric đã thay đổi.
Không sửa CSV/nhãn để vượt qua kiểm tra. Trên máy khác, chỉ xem hình/HTML thì
không cần Python hay Java; tái tạo hình cần Matplotlib và dependencies dự án.
Đo lại Java cần JDK (`javac` trên PATH), `ij.jar` và `imagescience.jar`; xem
hướng dẫn chi tiết để chỉ đường dẫn ImageJ.

## Những kết luận phải giữ đúng khi nộp

- **35/220 đạt chuẩn gốc, 185 chưa đạt.** Không đổi thành 220 PASS vì Pearson
  cao hoặc vì hai nguồn có F1 gần nhau.
- F1 cạnh cao nhất **trong bốn sigma đã khảo sát** là sigma=2. Không khẳng
  định đây là scale tốt nhất cho mọi ảnh/tập dữ liệu.
- Blob tổng hợp tốt hơn ảnh tế bào; trình bày cả macro và micro F1.
- Biểu đồ runtime dùng **lõi ImageJ/ImageScience qua Java headless** đo mới,
  không gọi là thời gian GUI/macro Fiji. Không trộn với CSV runtime cũ.
- Không có thí nghiệm noise/crop mới hoặc tập test độc lập; phần phân tích
  không suy ra các kết luận đó.

Quay lại [công việc 4](README_DUC_08_11.md). Bản đọc/phân tích này là sản phẩm
của Đức; việc hợp nhất vào báo cáo/slide chung vẫn thực hiện theo phân công nhóm.
