# Kiểm tra bàn giao toàn nhóm — 09/11/2026

> **Bản kiểm tra lịch sử.** Đã có lần kiểm tra lại ngày 10/11 với code và sản phẩm mới: [KIEM_TRA_TOAN_BO_NHOM.md](../../10_11/kiem_tra_toan_bo_nhom/KIEM_TRA_TOAN_BO_NHOM.md). Một số lỗi bên dưới đã được sửa; dùng bản 10/11 để xác định việc còn lại.

**Kết luận: chưa đủ điều kiện chốt hoàn thiện toàn bộ dự án.** Đã có phần lớn mã nguồn, dữ liệu và sản phẩm thực nghiệm. Tuy nhiên, bản tích hợp hiện tại có lỗi kiểm thử, số liệu tổng hợp không khớp dữ liệu chi tiết và chưa đạt tiêu chuẩn đối chuẩn số học ban đầu. Báo cáo cuối, slide và các bước nộp bài cũng chưa có đủ bằng chứng trong thư mục này.

Đánh giá này đối chiếu **29 đầu việc** trong `Phân công XLA (1).xlsx` với `INSTRUCTIONS.md`, `quyuoc.md`, `debai.md`, `yeucau.md` và các sản phẩm thực tế. Đây là kiểm tra bản trên máy, không xác nhận trạng thái GitHub, Overleaf hoặc tài liệu riêng của thành viên. Các ô người nhận để trống trong Excel vẫn được giữ nguyên; cách gọi Hưng/Mạnh/Lộc/Đức bên dưới dựa trên nhóm vai trò đã trao đổi, không tự sửa phân công.

Hôm nay là 09/11: một số việc có hạn 10–18/11 **chưa đến hạn**. “Chưa hoàn thiện” không đồng nghĩa với “trễ hạn”. Kết quả kiểm tra mới này thay thế các nhận định cũ rằng toàn bộ dự án đã đạt 100%.

## 1. Bằng chứng chạy kiểm tra

| Hạng mục | Kết quả hiện tại | Ý nghĩa |
| --- | --- | --- |
| Bộ unittest trong `tests/` | **43/45 PASS, 2 FAIL** | Có lỗi tích hợp ở đánh giá BSDS; chưa thể bàn giao pipeline như bản đã kiểm thử đầy đủ |
| `run_tests.py` | **5/5 PASS** | Các kiểm thử lõi qua; không thay thế bộ unittest hoặc nghiệm thu Python–Fiji |
| `validate_fiji_outputs.py` | **435/435 PASS** | Đủ bộ TIFF kỳ vọng, manifest, runtime và định dạng float32 |
| Kiểm tra đầu vào/GT | **25/25 READY** | Bộ dữ liệu và nhãn hiện tại hợp lệ theo trình kiểm tra |
| TIFF Python trong 3 ZIP | **415/415**, trùng byte với `outputs/python` | Gói ảnh bàn giao đầy đủ, tên phẳng, không có file phụ |
| Tầng 1 theo chuẩn gốc | **35 PASS / 185 FAIL trên 220 cặp** | Chưa đạt nghiệm thu đồng thời relative error < 1e-4 và Pearson r > 0.9999 |
| Toàn vẹn bàn giao công việc 23 | **FAIL** | 5 file đầu ra và 1 file code khác checksum đã ghi nhận |
| Fingerprint bộ runtime công việc 24 | **PASS** | Dữ liệu đo thời gian vẫn khớp bộ mã/config/ảnh mà trình kiểm tra theo dõi |
| Benchmark tối ưu của Mạnh | **36 trường hợp có dữ liệu** | max abs diff 1.279e-12; speedup lưu trong CSV khoảng 1.76–29.85 lần; còn vấn đề số lần lặp |
| Báo cáo LaTeX | Có bản nháp 6 chương | Không thấy PDF báo cáo hoàn chỉnh; máy không có bộ biên dịch LaTeX để xác nhận số trang/font/bố cục |
| Slide | Không tìm thấy `.pptx`, `.ppt`, `.odp` trong `docs`/`outputs` | Chưa có sản phẩm slide để kiểm tra ở đây; không loại trừ tài liệu online bên ngoài |

Nhật ký: [UNITTEST_LOG.txt](UNITTEST_LOG.txt), [CORE_TEST_LOG.txt](CORE_TEST_LOG.txt). Số liệu cấu trúc, nhãn, tài liệu và ZIP: [AUDIT_FACTS.json](AUDIT_FACTS.json). Lượt kiểm tra Fiji chạy trực tiếp trả về `PASS: 435/435 file đúng bộ kỳ vọng, manifest, runtime và định dạng`.

## 2. Những lỗi cần xử lý trước khi chốt

### A. Bản tích hợp đã đổi hành vi đánh giá BSDS

`src/eval/bsds_threshold_grid.py` hiện dùng `STRUCT_2PX = np.ones((5, 5))`, tức vùng vuông 5×5. Điểm lệch `(2,2)` được chấp nhận dù khoảng cách Euclidean lớn hơn 2 px. Điều này khác protocol Euclidean 2 px trong công việc thực nghiệm đã đóng gói. File này còn loại ảnh có NMS rỗng khỏi mẫu số trung bình, làm trung bình có thể cao hơn khi ảnh thất bại bị bỏ qua.

Hai kiểm thử thất bại xác nhận trực tiếp:

- `test_euclidean_two_pixel_tolerance`: mong F1 = 0, thực tế gần 1.
- `test_empty_nms_still_counts_in_grid_mean`: mong đếm 2 ảnh, thực tế chỉ đếm 1.

Đây là module được `metrics_tier2.py` sử dụng, không chỉ là script cũ không được gọi. Module cũng đang nhập `scipy.ndimage` trong luồng đánh giá, khác giới hạn của INSTRUCTIONS chỉ cho dùng thư viện này trong kiểm thử độc lập/benchmark thời gian. Cần khôi phục hành vi đúng protocol, giữ ảnh không có dự đoán trong phép tính trung bình và kiểm tra lại các test liên quan. Không sửa kỳ vọng test chỉ để có PASS.

### B. Bảng tổng hợp metric không còn khớp file kết quả chi tiết

Trong chính `outputs/metrics/duc_08_11`, giá trị `macro_f1` của `tier2_summary.csv` khác trung bình cột `f1` từ `tier2_results_both.csv` ở **12 nhóm**:

| Nguồn / bài toán | Trung bình tính lại từ kết quả từng ảnh | Bảng tổng hợp hiện tại |
| --- | ---: | ---: |
| Python — BSDS, sigma 2 | 0.472945 | 0.516600 |
| Fiji — BSDS, sigma 2 | 0.472930 | 0.516600 |
| Python — DRIVE | 0.477382 | 0.680633 |
| Fiji — DRIVE | 0.473863 | 0.681651 |
| Python — blob, macro | 0.898418 | 0.893023 |
| Fiji — blob, macro | 0.897373 | 0.891901 |

Chi tiết cả 12 nhóm: [SUMMARY_VS_RAW.json](SUMMARY_VS_RAW.json). Đây là khác biệt nội dung, không thể giải thích chỉ bằng BOM hoặc CRLF/LF. Những số tính lại ở cột giữa chỉ mô tả **lần chạy cũ đang lưu**, không chứng minh chạy lại bằng code hiện tại sẽ ra cùng số.

So với `run_manifest.json`, các file đã khác là:

- `blob_threshold_grid.csv`
- `bsds_selected_thresholds.csv`
- `KET_QUA_METRIC.md`
- `ridge_threshold_grid.csv`
- `tier2_summary.csv`
- code `src/eval/bsds_threshold_grid.py`

100/106 mục checksum đang khớp; 6 mục trên không khớp kể cả khi thử chuẩn hóa BOM/xuống dòng. Xem [MANIFEST_INTEGRITY.csv](MANIFEST_INTEGRITY.csv). Không xác định người hoặc thao tác gây thay đổi từ checksum này.

Cần thống nhất **một protocol chính thức**, sửa pipeline, chạy lại metric rồi sinh bảng, biểu đồ, nhận xét và manifest từ cùng lần chạy. Không ghép điểm F1 của protocol khác vào bảng cũ và không chỉ cập nhật checksum để bỏ qua sai lệch.

### C. Đối chuẩn số học chưa đạt điều kiện gốc

35/220 cặp đạt chuẩn gốc; 185/220 không đạt vì sai khác biên độ vượt ngưỡng dù Pearson cao. Báo cáo hiện gọi nhóm này là RELAXED với ngưỡng 1e-2. Đó là tiêu chí khác, chưa thay thế điều kiện 1e-4 trong tài liệu gốc.

Mạnh và Lộc cần đối chiếu kernel, moment, bán kính cắt, phép đo hiệu chuẩn và quy ước plugin; Đức giữ nguyên báo cáo sai số thực đo. Nếu nhóm chấp nhận ngưỡng khác thì phải có quyết định và lý do được ghi rõ. Chưa đủ bằng chứng để khẳng định chắc chắn mọi sai lệch đều “hoàn toàn không phải lỗi giải thuật”.

## 3. Kiểm tra theo từng thành viên

| Phần phụ trách | Đã có trong thư mục | Việc còn lại trước khi chốt |
| --- | --- | --- |
| **Hưng — STT 1–7, lý thuyết** | Công thức/nội dung rải trong `main.tex`, có thảo luận chuẩn hóa, Hessian, detector, Structure Tensor; 8 tài liệu tham khảo và 8 khóa trích dẫn | Hoàn thiện chương lý thuyết, dẫn giải và ý nghĩa hình học; đồng bộ công thức với code; rà nguồn/định dạng tài liệu tham khảo. Không đánh dấu “chưa có gì”, nhưng chưa đủ cơ sở chốt cả 7 đầu việc |
| **Mạnh — STT 8–14, Python** | Kernel, convolution, derivatives, gradient, Hessian, Structure Tensor, Canny/Frangi/LoG; test lõi; bộ so sánh thư viện; benchmark tối ưu 36 trường hợp | Cùng xử lý lỗi tích hợp BSDS và đối chuẩn 185 cặp; sửa đường dẫn smoke test; loại fallback/gõ cứng khỏi luồng sản xuất; làm rõ số lần lặp benchmark và lưu bằng chứng so sánh |
| **Lộc — STT 15–19, Fiji** | Macro, code Java; 435 TIFF hợp lệ; 2 workflow DOCX cập nhật 09/11, mỗi file 6 ảnh nhúng; 3 screenshot Chương 3 | Bổ sung hồ sơ đo/truy vết tham số hiệu chuẩn theo từng lệnh để giải thích config; phối hợp đối chuẩn biên độ. Không còn thiếu workflow/screenshot như một số nhận xét cũ |
| **Đức — STT 20–24, thực nghiệm** | 25 ảnh, GT READY, thiết kế; bộ metric 19 file; phân tích/biểu đồ và runtime; 3 ZIP 415 TIFF; gói GT gửi Hưng | Sản phẩm đã có, nhưng công việc 23–24 cần nghiệm thu lại sau khi sửa tích hợp/số liệu. Đã thiết kế kịch bản nhiễu/kích thước nhưng bộ kết quả hiện tại chỉ gồm 25 ảnh gốc, chưa có kết quả các biến thể này |

### Chi tiết cần lưu ý ở phần Python

- `src/eval/smoke_test_analytical.py` tìm `data/calib/parabol.tif`, trong khi ảnh đang có là `parabola.tif`. Script riêng này chưa chạy được nguyên trạng theo đường dẫn đó; việc `run_tests.py` PASS không phủ lỗi đường dẫn này.
- `src/config.py` đặt mặc định `strict=False` và có fallback khi thiếu tham số. Cần đảm bảo mọi entrypoint sản xuất dừng khi config thiếu/null, theo INSTRUCTIONS. Config hiện đủ không xóa được rủi ro từ nhánh fallback.
- `verify_tier1.py`, `benchmark_tier2.py` vẫn chứa quy tắc cũ khác pipeline thực nghiệm mới. Cần chỉ rõ entrypoint chính thức và đánh dấu lịch sử để tránh chạy nhầm hoặc lấy số từ hai bộ.
- `benchmark_optimization.py:measure` ghi “lặp ít nhất reps lần”, mặc định reps=5, nhưng có thể dừng ngay sau 3 lần nếu tổng thời gian đủ 0.2 s. CSV không lưu số lần lặp thực tế. Cần sửa điều kiện hoặc mô tả, rồi đo lại nếu cần; không suy ra các dòng hiện có đều đo đúng 5 lần.
- Bộ so sánh SciPy/OpenCV đã có script và ảnh. Cần lưu bảng sai số/thiết lập tái lập rõ ràng; khác biệt kernel/threshold của hai phương pháp không tự chứng minh phương pháp nào chính xác hơn.

### Chi tiết cần lưu ý ở phần lý thuyết/báo cáo

- `docs/report_template/main.tex` có 514 dòng, đủ 6 chương. Chương 2 hiện chỉ khoảng 277 token phân cách bằng khoảng trắng, bao gồm lệnh LaTeX; dấu hiệu nội dung còn ngắn, không phải phép đếm trang đã biên dịch.
- Có 6 hình được gọi và đủ 6 đường dẫn; các môi trường LaTeX cân bằng; không phát hiện khóa citation hoặc `ref` bị thiếu. `ch4_content.tex` không được `input`, nhưng nội dung Chương 4 đã có trực tiếp trong `main.tex`, nên không kết luận mất Chương 4.
- Báo cáo ghi NMS “8 hướng” trong khi thuật toán lượng tử hóa 4 sector. Cần sửa mô tả cho khớp code.
- Các điểm BSDS 0.5166, DRIVE khoảng 0.681 và blob khoảng 0.893 trong báo cáo không phải cùng bộ tổng hợp từ dữ liệu chi tiết của lần chạy Đức đang lưu. Cần ghi protocol cụ thể và đồng bộ toàn văn/hình/bảng sau khi thống nhất.
- Chưa thấy PDF báo cáo cuối. Máy không có `pdflatex`, `xelatex`, `lualatex`, `latexmk`; chưa kiểm chứng được khả năng biên dịch, font tiếng Việt, số trang ~30 và bố cục hình/bảng. Không coi kiểm tra tĩnh là biên dịch thành công.

## 4. Phần của Đức vẫn còn đầy đủ những gì?

- **Dữ liệu/GT:** 10 BSDS với 56 bộ nhãn từ 5–7 người/ảnh trong tập đã chọn; 10 DRIVE có vessel mask và FOV mask; 4 ảnh blob tổng hợp với 16 đối tượng; `blob_05` có 276 đối tượng dương tính và 15 vùng loại trừ hình chữ nhật. Nhãn tế bào do Đức rà soát, không gọi là hội đồng chuyên gia độc lập. Vùng loại trừ JSON không đồng nghĩa đã có file mask PNG riêng.
- **Công việc 4:** mã metric, báo cáo tầng 1/2, kết quả từng ảnh và dữ liệu đối chiếu vẫn có. Nhưng tính toàn vẹn bộ bàn giao hiện không PASS; cần xử lý mục 2A–B.
- **Công việc 5:** có biểu đồ theo sigma/PR/F1, phân tích sai số, thời gian và gallery; 10 hình ở các định dạng PNG/SVG/PDF. Bộ timing có 357 trường hợp, 2 nguồn, 6 lượt/nguồn: 4.284 mẫu gồm 714 warm-up và 3.570 mẫu đo. Java đo engine headless, không phải thời gian thao tác GUI Fiji hay toàn bộ I/O macro.
- **ZIP:** 3 phần ở `outputs/archives/duc_08_11` chứa lần lượt 266 + 94 + 55 TIFF. Giải nén cả 3 vào `outputs/python`. Không cần tạo lại ZIP chỉ vì lỗi tổng hợp metric.
- **Gói gửi Hưng:** `docs/09_11/GUI_HUNG_GROUND_TRUTH_09_11.md/.docx`, có overlay và mô tả nhãn. Có file không có nghĩa là đã gửi cho Hưng.

Sau khi đổi protocol hoặc kết quả metric, các biểu đồ cần được sinh lại dù dữ liệu runtime riêng vẫn hợp lệ. `analysis_manifest.json` cũng còn liệt kê file `.class` được tạo cục bộ; cần thống nhất cách build lại hoặc đóng gói để máy khác kiểm tra không thiếu file.

## 5. Việc chung STT 25–29

| STT | Trạng thái tại thư mục này | Hạn trong bảng |
| --- | --- | --- |
| 25 — khung báo cáo | Có khung và bản nháp; cần thống nhất ký hiệu/công thức | 31/10 |
| 26 — gộp, rà lỗi, báo cáo ~30 trang | Chưa chốt do số liệu xung đột, chưa có PDF biên dịch để nghiệm thu | 14/11 |
| 27 — slide ~10 trang | Chưa có file hoặc bản xuất để kiểm tra | 17/11 |
| 28 — chuẩn bị bảo vệ | Chưa thấy bộ câu hỏi/tài liệu ôn chung; hoạt động ôn trực tiếp không thể xác nhận từ file | 18/11 |
| 29 — nộp LMS và quyền truy cập | Chưa có bằng chứng link nộp/quyền truy cập; chưa xác minh hệ thống LMS | 18/11 |

## 6. Thứ tự xử lý đề nghị

1. **Mạnh + Đức:** thống nhất và sửa module BSDS; đạt lại 45/45 unittest, đảm bảo luồng chính không dùng SciPy ndimage ngoài phạm vi được phép.
2. **Đức:** sau khi pipeline ổn định, chạy lại công việc 23 và 24 theo một protocol; kiểm tra bảng tổng hợp tính được từ từng ảnh, manifest PASS; tránh sửa CSV/báo cáo bằng tay để khớp điểm mong muốn.
3. **Mạnh + Lộc:** đối chiếu hiệu chuẩn và 185 cặp chưa đạt; ghi quyết định nghiệm thu theo đúng điều kiện gốc hoặc đề xuất thay đổi có lý do, không gọi tiêu chí relaxed là đã đạt chuẩn gốc.
4. **Mỗi thành viên:** hoàn thiện các điểm riêng ở mục 3; Đức quyết định phạm vi thực nghiệm nhiễu/kích thước với nhóm và ghi rõ nếu chỉ bàn giao baseline.
5. **Hưng + nhóm:** gộp số liệu đã chốt vào báo cáo, hoàn thiện lý thuyết/trích dẫn, biên dịch PDF kiểm tra ~30 trang; bổ sung slide, câu hỏi bảo vệ và thực hiện kiểm tra nộp bài đúng hạn.

Danh sách từng đầu việc: [CHECKLIST_29_CONG_VIEC.csv](CHECKLIST_29_CONG_VIEC.csv). File gốc trích từ Excel: [TASKS_FROM_WORKBOOK.csv](TASKS_FROM_WORKBOOK.csv).

Lần kiểm tra này chỉ tạo công cụ kiểm tra và bằng chứng trong thư mục kiểm tra; **không sửa thuật toán, GT, config, metric hoặc biểu đồ gốc; không commit/push/gửi tài liệu cho thành viên**.
