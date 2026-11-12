# Kiểm tra toàn bộ dự án sau khi bổ sung hiệu chuẩn — 12/11/2026

> **Bản kiểm tra trước khi sửa trong ngày 12/11.** Hai vấn đề Đức + Mạnh nêu dưới đây đã được xử lý và kiểm tra lại: [kết quả hoàn thiện](../sau_hoan_thien_duc_manh/KET_QUA_HOAN_THIEN_DUC_MANH.md), [checklist cập nhật](../sau_hoan_thien_duc_manh/CHECKLIST_29_CONG_VIEC.csv). Giữ nguyên nội dung dưới đây để đối chiếu trước/sau; không dùng trạng thái gate FAIL cũ làm trạng thái hiện hành.

**Kết luận: phần đo hiệu chuẩn định lượng của Lộc đã được bổ sung và kiểm chứng tốt; code/dữ liệu tiếp tục qua các kiểm thử. Tuy nhiên, chưa đủ điều kiện chốt toàn bộ bộ bàn giao cuối.** Còn thiếu ảnh bằng chứng hiệu chuẩn, hồ sơ phiên metric/timing chưa khớp checksum config mới, PDF báo cáo cuối và các bước chung chuẩn bị bảo vệ/nộp bài.

Đối chiếu 29 đầu việc trích lại từ `Phân công XLA (1).xlsx`, đề tài và các quy ước gốc. Chỉ đánh giá sản phẩm hiện có trong thư mục dự án trên máy; không xác nhận công việc trên Overleaf/GitHub/LMS hoặc tài liệu riêng ngoài thư mục. Hạn chính thức theo đề là 19/11, mục tiêu nội bộ trước 18/11; các đầu việc có hạn 14–18/11 chưa đến hạn tại thời điểm kiểm tra.

## 1. Kết quả kiểm tra mới

| Hạng mục | Kết quả ngày 12/11 | Kết luận |
| --- | --- | --- |
| Unittest toàn bộ | **52/52 PASS** | Không phát hiện hồi quy trong bộ test hiện có |
| Kiểm thử lõi | **5/5 PASS** | Các kiểm thử kernel, convolution, đa thức, tensor và detector đạt |
| Smoke giải tích | **PASS** | Dấu/trị riêng và đáp ứng đa thức được kiểm tra |
| TIFF Fiji | **435/435 PASS** | Bộ kỳ vọng, manifest, định dạng float32 hợp lệ |
| Ground truth | **25/25 READY** | Raw/GT tiếp tục khớp checksum và điều kiện nhãn |
| ZIP Python | **415/415 TIFF**, trùng byte nguồn | Ba ZIP đầy đủ, không mất ảnh bàn giao |
| Hiệu chuẩn mới | **40 TIFF + 40 phép đo + 2.682 điểm profile**, không lỗi đối chiếu | Đã có bằng chứng định lượng thực tế |
| Screenshot hiệu chuẩn | **0 ảnh trong `docs/fiji/calibration/screenshots`** | Mới có README liệt kê ảnh cần bổ sung |
| Kết quả metric từng ảnh/tổng hợp | **110 dòng**, không phát hiện lệch macro hoặc số đếm matching | Nội dung metric vẫn nhất quán |
| Toàn vẹn file kết quả/map đã ghi nhận | Không file nào đổi so với manifest | Chưa có bằng chứng số liệu/ảnh đầu ra bị sửa |
| Kiểm tra phiên metric hiện hành | **Không PASS: `config.yaml` khác checksum** | Luồng kiểm tra/plot/demo bị chặn cho đến khi đồng bộ phiên |
| Kiểm tra phiên runtime | **Không PASS: config hash khác** | Mẫu timing không đổi nhưng fingerprint chưa khớp config hiện tại |
| Slide | **10 slide PPTX**, file không hỏng | Các F1 headline vẫn khớp CSV đang lưu |
| PDF báo cáo cuối | **Chưa thấy trong `docs`** | Chưa nghiệm thu số trang/font/bố cục hoặc độ đầy đủ bản cuối |

Bằng chứng máy đọc được: [AUDIT_FACTS.json](AUDIT_FACTS.json). Nhật ký: [UNITTEST_LOG.txt](UNITTEST_LOG.txt), [CORE_LOG.txt](CORE_LOG.txt), [FIJI_LOG.txt](FIJI_LOG.txt), [ANALYTICAL_LOG.txt](ANALYTICAL_LOG.txt).

## 2. Phần Lộc vừa bổ sung: đã xác minh được gì?

Thư mục `docs/fiji/calibration` đã có macro tái hiện, script phân tích, bảng môi trường, ánh xạ lệnh, manifest TIFF, số đo ROI, profile và báo cáo kết luận. Không còn đúng nếu nói Lộc chưa có hồ sơ đo định lượng.

Đã đọc lại TIFF và kiểm tra độc lập:

- **40/40 TIFF** khớp SHA-256/kích thước/shape trong manifest, là float32 không nén và hữu hạn.
- Mean/Min/Max/Sum tính lại từ ROI khớp CSV trong độ chính xác làm tròn: sai khác Mean lớn nhất khoảng **4.98e-10**. Chênh StdDev tối đa khoảng 3.16e-7 ở mức sai số rất nhỏ của phép tính thống kê.
- **2.682/2.682 giá trị profile** khớp pixel TIFF tại tọa độ đã ghi; sai khác lớn nhất khoảng **4.99e-10**.
- Các hash ảnh hiệu chuẩn đầu vào trong `environment.csv` khớp ảnh hiện có trong `data/calib`.

| Thông số | Bằng chứng kiểm tra lại | Đánh giá |
| --- | --- | --- |
| k Gaussian = 3 | Dirac sigma 1/2/4 có bán kính 3/6/12 | Phù hợp |
| k đạo hàm bậc 1/2 = 4 theo trục đạo hàm | Lx/Lxx có bán kính x=4/8/16, y=3/6/12 | Phù hợp; phân biệt trục đạo hàm và trục làm mịn |
| Trọng số đáp ứng xung | So với mô hình Gaussian/đạo hàm lấy mẫu tương ứng | Relative max error lớn nhất khoảng **7.34e-8**, phù hợp độ chính xác lưu float32 |
| Biên mirror | Sai số mô hình mirror khoảng 5.4e-9–1.34e-8, nhỏ hơn rõ rệt reflect | Dữ liệu ủng hộ mirror không lặp pixel biên |
| Normalization | Đáp ứng khác 0 gần hằng theo scale, phù hợp mô hình thô hơn mô hình nhân sigma/sigma² | Hỗ trợ các cờ false hiện hành |
| Hessian có dấu/algebraic | Largest gần +1, Smallest gần −2 ở các sigma | Phù hợp khi Absolute tắt |
| Structure | Trị riêng lớn gần 1, trị riêng nhỏ bằng 0 | Phù hợp đầu ra thô; trị riêng bằng 0 riêng lẻ không đủ kết luận normalization |

Bộ đo cũng cho thấy Lxx có tổng kernel khác 0 rất nhỏ và đáp ứng parabol không bằng đúng 1. Điều này cung cấp thêm bằng chứng về khác biệt rời rạc hóa/moment; không tự chứng minh mọi sai số trên 220 cặp đều chỉ có một nguyên nhân.

### Đối chiếu môi trường hiệu chuẩn với môi trường timing

Môi trường Lộc ghi Fiji 2.16.0/ImageJ 1.54p, ImageScience 3.0.0, Java 8. Môi trường timing trước đó là ImageJ 1.53k/ImageScience 3.0.0, Java 24. Hai JAR ImageScience có SHA-256 khác nhau.

Để tránh suy luận sai chỉ từ hash, đã dùng thư viện timing hiện có tính lại **cả 40 phép hiệu chuẩn**, ghi riêng vào thư mục kiểm tra: **40/40 mảng kết quả trùng giá trị, max abs error = 0** với TIFF Lộc bàn giao. Khác hash gói JAR không tạo khác kết quả trong các phép đo này; không kết luận hai gói phần mềm đồng nhất trên mọi chức năng.

Xem [CALIBRATION_CHECKS.json](CALIBRATION_CHECKS.json), [TIMING_LIBRARY_CALIBRATION.json](TIMING_LIBRARY_CALIBRATION.json), [bảng 40 phép đối chiếu](TIMING_LIBRARY_CALIBRATION.csv).

### Lộc còn bổ sung gì?

`screenshots/` mới có README, và `environment.csv` tự ghi `SCREENSHOTS_PENDING`. Cần ảnh phiên bản, hộp thoại các lệnh, trạng thái Absolute/NMS/threshold, ROI đo và profile. Ảnh workflow cũ trong DOCX/Chương 3 không tự thay thế bằng chứng của phiên hiệu chuẩn cụ thể này.

Script `analyze_results.py` hiện gán một số nhãn kết luận normalization trực tiếp, thay vì tự kiểm tra điều kiện trước khi ghi. Dữ liệu hiện tại đã được đối chiếu độc lập và ủng hộ kết luận đó; nếu dùng script cho phiên sau cần rà lại kết quả, không coi việc script chạy xong là mọi kết luận tự động đúng.

## 3. Vấn đề tích hợp còn tồn tại: checksum config

`config.yaml` đã được cập nhật các ghi chú liên quan kết quả hiệu chuẩn. Các giá trị đang dùng vẫn phù hợp protocol được tài liệu hóa, nhưng bộ bàn giao cũ khóa theo **hash toàn bộ file**, gồm cả ghi chú.

Kiểm tra trực tiếp hiện trả về:

```text
Task 23 dependency changed: config.yaml; regenerate metrics first
Runtime config/protocol mismatch; use --remeasure-runtime
```

Chỉ `config.yaml` khác trong danh sách phụ thuộc đã ghi nhận. Các file kết quả metric, TIFF nguồn, mẫu runtime và biểu đồ trong manifest đều còn khớp; bảng F1 không có lỗi tổng hợp được phát hiện. **Đây là vấn đề provenance/khả năng chạy lại, chưa phải bằng chứng F1 hiện tại bị tính sai.**

Hệ quả: launcher công việc 5, demo và công cụ đồng bộ tài liệu có kiểm tra đầu vào sẽ bị chặn, dù các file đã sinh trước đó vẫn mở được và 52 unit test PASS.

Trước khi chốt bàn giao, cần đồng bộ lại phiên metric/timing và sau đó chạy công việc 5 để cập nhật manifest, hình, LaTeX và slide. Luồng hiện hỗ trợ là các lệnh trong README. Nếu nhóm muốn xử lý riêng thay đổi thuần ghi chú, phải có bước xác minh ngữ nghĩa và ghi lịch sử cập nhật metadata rõ ràng; không sửa hash hoặc bỏ kiểm tra chỉ để ép PASS.

Lần kiểm tra này **không tự cập nhật manifest, chạy lại metric/timing hay ghi đè số liệu**.

## 4. Đầu ra của từng người

| Thành viên | Đã có và đã kiểm tra | Trạng thái còn lại |
| --- | --- | --- |
| **Mạnh — STT 8–14** | Các module lõi/detector còn đủ; source đã ghi trong manifest không phát hiện thay đổi ngoài config; 52 test PASS; benchmark tối ưu 36 trường hợp, reps=5 | Phối hợp Đức chốt provenance sau cập nhật config; rà kết luận gõ cứng trong bộ đối chiếu thư viện; mô tả trung thực STRICT/RELAXED |
| **Lộc — STT 15–19** | Workflow, macro, 435 TIFF; thêm hồ sơ định lượng 40 TIFF được kiểm chứng | Bổ sung screenshot phiên hiệu chuẩn, cập nhật trạng thái hồ sơ/checklist khi đã đủ. Không còn thiếu toàn bộ phép đo như trước |
| **Đức — STT 20–24** | 25 raw/GT, thiết kế, metric 110 dòng, 10 hình ở 3 định dạng, timing lặp và ZIP 415 TIFF | Nội dung hiện có hợp lệ khi đối chiếu nội bộ, nhưng bộ hiện hành chưa vượt gate checksum config mới; cần đồng bộ phiên trước bàn giao cuối |
| **Hưng — STT 1–7** | Bản nháp 6 chương, 8 mục tài liệu tham khảo, các khóa trích dẫn/ref/hình không bị thiếu trong kiểm tra tĩnh | Hoàn thiện chiều sâu lý thuyết và phân tích; xuất/nghiệm thu PDF cuối. Chương 5–6 vẫn là bản rút gọn sau lần sửa trước, không đồng nghĩa đã hoàn thiện cuốn báo cáo |

Ở phần đối chiếu thư viện STT 13, `benchmarks/reference_comparison/run_all_comparisons.py` còn hai nhãn Pearson `1.00000000` và kết luận `VERDICT: 100% PASS` gõ cứng trong mã dựng ảnh. Đây là công cụ độc lập, không phải pipeline chấm GT chính. Không kết luận các số đo hiện có chắc chắn sai, nhưng nhãn gõ cứng không đủ làm bằng chứng nghiệm thu tự động khi ảnh/tham số đổi; cần tính kết luận từ số đo hoặc ghi rõ chỉ là minh họa.

## 5. Các việc chung và yêu cầu báo cáo

- **STT 25:** Khung báo cáo có; cần thống nhất ký hiệu và tích hợp bằng chứng hiệu chuẩn mới.
- **STT 26:** `main.tex` hiện 472 dòng, Chương 2 khoảng 266 token tách bằng khoảng trắng gồm cả lệnh LaTeX. Đây chỉ là chỉ báo nội dung còn ngắn; chưa có PDF để xác nhận ~30 trang. Máy chưa có `pdflatex/xelatex/lualatex/latexmk`, nên không tuyên bố đã biên dịch hoặc đã rà bố cục.
- **STT 27:** Có PowerPoint 10 slide, HTML và 10 bộ biểu đồ PNG/SVG/PDF. Các điểm F1 chính còn khớp bảng lưu; cần làm mới provenance sau bước metric và rà trình chiếu thực tế.
- **STT 28:** Có trang hỏi đáp/định hướng câu hỏi, chưa thấy bộ hỏi–đáp bảo vệ hoàn chỉnh riêng hoặc bằng chứng ôn tập ngoài thư mục.
- **STT 29:** Chưa xác minh link LMS, mã nhóm và quyền truy cập. Không kết luận việc này đã hoàn thành ở ngoài thư mục.

Đề tài vẫn bám đủ chín nhóm nội dung Gaussian, scale-space, đạo hàm bậc 1/2, gradient, Hessian, edge, ridge và blob/structure. Không phát hiện việc đổi đề tài. Bộ số liệu hiện là baseline nội bộ 25 ảnh; chưa có cơ sở kết luận đã khảo sát độ bền với nhiễu/kích thước mới.

## 6. Điều kiện để chốt bàn giao

1. **Đức + Mạnh:** xử lý checksum/provenance config theo luồng có kiểm chứng; xác nhận metric/analysis/runtime đều qua gate với bản hiện tại.
2. **Lộc:** bổ sung ảnh bằng chứng hiệu chuẩn và chốt trạng thái hồ sơ.
3. **Hưng + nhóm:** hoàn thiện và biên dịch PDF báo cáo; đưa bằng chứng hiệu chuẩn mới vào đúng phần; rà slide.
4. **Cả nhóm:** chuẩn bị bảo vệ và xác minh link/quyền nộp bài theo hạn.

Đối chuẩn vẫn là **35 đạt ngưỡng gốc / 185 chưa đạt ngưỡng gốc**. Nhóm có thể ghi 185 RELAXED theo ngưỡng mở rộng đã thống nhất, nhưng hồ sơ hiệu chuẩn mới không biến chúng thành STRICT.

Checklist từng đầu việc: [CHECKLIST_29_CONG_VIEC.csv](CHECKLIST_29_CONG_VIEC.csv). Nguồn Excel trích mới: [TASKS_FROM_WORKBOOK.csv](TASKS_FROM_WORKBOOK.csv). Kết quả này mô tả trạng thái 12/11; không dùng tệp PASS ngày 10/11 để khẳng định mọi gate hiện tại vẫn PASS.
