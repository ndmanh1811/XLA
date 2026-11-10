# Kiểm tra toàn bộ dự án — 10/11/2026

> **Trạng thái trước sửa.** Pipeline và tài liệu đã được chỉnh sau lần kiểm tra này. Xem [bàn giao sau sửa](../sau_sua_loi/BAN_GIAO_SAU_SUA.md) và [README hiện hành](../../../README_DUC_10_11.md) để biết kết quả mới và phần còn lại của nhóm. Giữ các bằng chứng dưới đây làm lịch sử.

**Kết luận: dự án đi đúng chủ đề và đã có phần lớn sản phẩm của cả 4 người, nhưng chưa đủ điều kiện chốt bàn giao toàn bộ.** Các vấn đề chính hiện nằm ở quy trình chấm blob/DRIVE, sự thống nhất giữa hai pipeline thực nghiệm, diễn giải khoa học trên slide và bản báo cáo cuối. Không còn đúng nếu nói bản hiện tại thiếu slide hoặc còn hai lỗi BSDS như ngày 09/11.

Phạm vi: đối chiếu 29 đầu việc trong `Phân công XLA (1).xlsx`, bốn tài liệu gốc `debai.md`, `yeucau.md`, `quyuoc.md`, `INSTRUCTIONS.md`; đọc mã lõi, đánh giá, Fiji, tài liệu và sản phẩm trên đĩa; chạy kiểm thử và một số phép kiểm chứng độc lập. Không xác minh GitHub/Overleaf/LMS hoặc tài liệu ở ngoài thư mục. Hạn chính thức theo yêu cầu là **19/11**; nhóm đặt mục tiêu nộp LMS trước 18/11. Nhiều việc trong bảng có hạn 12–18/11, chưa đến hạn tại thời điểm kiểm tra.

## 1. Những điểm đã tốt hơn so với bản 09/11

| Hạng mục | Kết quả kiểm tra mới |
| --- | --- |
| Toàn bộ unittest | **47/47 PASS**, đã chạy lại; không còn kết quả 43/45 của bản cũ |
| Kiểm thử lõi `run_tests.py` | **5/5 PASS** |
| Smoke test giải tích riêng | **PASS**; tên `parabola.tif` đã được sửa đúng |
| Module BSDS | Đã dùng đĩa Euclidean 2 px bằng NumPy; ảnh NMS rỗng vẫn được tính vào trung bình |
| F1 BSDS chính thức tại sigma 2 | Chạy kiểm chứng lại 10 ảnh/nguồn với p_low=67 và p_high=91: Python **0.4778861641842619**, Fiji **0.4778861641842619**; khớp số công bố đến 6 chữ số |
| Config cho k/border/eigen/normalization | Mặc định strict đã chuyển thành True; kernel/convolution/Hessian cũng gọi strict |
| Benchmark tối ưu | Đã sửa việc dừng sớm; 36 dòng CSV đều ghi **reps=5**, max abs diff 1.279e-12; speedup trong CSV khoảng **1.38–31.39 lần** |
| Bảng tổng hợp Đức cũ | Đã khớp dữ liệu từng ảnh: **0 sai lệch** ở ngưỡng kiểm tra 1e-8; không còn 12 nhóm F1 lệch như trước |
| Phân biệt nguồn metric | `outputs/metrics/PROTOCOL.md` đã chọn nguồn chính; bộ `duc_08_11` được đánh dấu `ARCHIVED_HISTORICAL` |
| Slide | Đã có PowerPoint **12 slide** và HTML **11 slide**; PPTX đọc được và kiểm tra ZIP không hỏng |

Nhật ký: [UNITTEST_LOG.txt](UNITTEST_LOG.txt), [CORE_TEST_LOG.txt](CORE_TEST_LOG.txt), [ANALYTICAL_SMOKE_LOG.txt](ANALYTICAL_SMOKE_LOG.txt), [FIJI_VALIDATION_LOG.txt](FIJI_VALIDATION_LOG.txt). Các phép kiểm chứng cụ thể: [EVALUATION_PROBES.json](EVALUATION_PROBES.json).

## 2. Đối chiếu với chủ đề ban đầu

| Nội dung trong đề | Hiện thực/sản phẩm đã có | Đánh giá phạm vi |
| --- | --- | --- |
| Gaussian smoothing | `src/core/kernel.py`, `derivatives.py`, TIFF gauss | Đúng chủ đề |
| Scale-space | Các danh sách sigma và batch nhiều tỷ lệ; lý thuyết trong báo cáo | Có triển khai; diễn giải lý thuyết còn ngắn |
| First derivative | Lx/Ly, kiểm tra dấu và đa thức | Có, test PASS |
| Second derivative | Lxx/Lyy/Lxy/Laplacian | Có, test PASS |
| Gradient | Độ lớn gradient, hướng dùng trong Canny | Có |
| Hessian matrix | Đạo hàm bậc 2 và nghiệm đóng trị riêng | Có |
| Edge detection | Canny NMS + hysteresis; đối chiếu FeatureJ | Có |
| Ridge detection | Frangi đa tỷ lệ từ Hessian trên DRIVE | Có; protocol đánh giá cần rà lại |
| Blob/structure analysis | LoG cực trị không gian–tỷ lệ; Structure Tensor và coherence | Có; chấm blob còn sai hợp đồng nhãn |

**Không phát hiện việc đổi sang một đề tài khác.** Canny/Frangi/LoG đều là cách triển khai các nội dung Edge/Ridge/Blob của đề. Sai sót cần sửa nằm ở đánh giá, diễn giải và hoàn thiện sản phẩm; không phải thiếu toàn bộ 9 nội dung chuyên môn. Một vài khẳng định trên slide lại mô tả sai chính lý thuyết của đề, xem mục 4.

## 3. Các vấn đề ảnh hưởng trực tiếp đến tính đúng của kết quả

### 3.1. Pipeline chính thức vẫn cho phép một dự đoán blob khớp nhiều nhãn

Nguồn chính hiện được README/PROTOCOL chọn là `src/eval/benchmark_tier2.py`, xuất vào `outputs/metrics/`. Trong `evaluate_blobs`, vòng lặp đi qua từng GT rồi tìm bất kỳ detection phù hợp, nhưng không đánh dấu detection đã được sử dụng.

Đã chạy phép thử trên **chính hàm này**, chỉ giả lập dữ liệu đầu vào: 2 GT gần nhau, 1 detection ở giữa. Kết quả trả về **matched_count=2, detected_count=1, Precision=2.0, F1=1.3333**. Đây là lỗi logic đã được chứng minh, dù 47 unittest hiện tại đều PASS; các test đó chưa bao phủ hợp đồng của pipeline đang được chọn làm chính thức.

Cần khớp **một–một** với cả hai điều kiện tâm ≤2 px và sai số bán kính ≤20%. `src/eval/metric_utils.py:match_blobs` đã có cơ chế này, nhưng pipeline chính chưa dùng nó. Không suy ra rằng số TP trên mọi ảnh hiện tại đều bị tăng; phép thử chứng minh hàm không bảo đảm tính đúng trong trường hợp tổng quát.

### 3.2. Pipeline chính thức bỏ qua 15 vùng loại trừ của blob_05

`evaluate_blobs` đọc `objects` và `polarity` nhưng không đọc `ignore_regions`. Vì vậy các dự đoán nằm trong vùng mà Đức đã đánh dấu loại trừ vẫn bị tính vào mẫu số precision.

Đã giữ nguyên ảnh, detector, ngưỡng 0.03×255, 7 sigma config và kiểm chứng lại:

| Nguồn | Dự đoán ban đầu | TP cũ | Dự đoán nằm trong ignore | F1 theo cách chấm hiện tại | F1 sau khớp một–một và dùng ignore |
| --- | ---: | ---: | ---: | ---: | ---: |
| Python | 326 | 140 | 35 | **0.465116** | **0.493827** |
| Fiji | 329 | 139 | 36 | **0.459504** | **0.488576** |

Đây là **kết quả kiểm tra tác động của cách chấm**, không phải bộ metric chính thức mới và không thay thế CSV đang bàn giao. Cần sửa pipeline rồi sinh lại đầy đủ macro/micro P/R/F1, bảng so sánh, biểu đồ và báo cáo. Không chỉ sửa hai con số trên slide.

### 3.3. Ràng buộc không dùng SciPy ndimage trong luồng chính vẫn chưa được tuân thủ hết

BSDS đã sửa sang NumPy, nhưng `benchmark_tier2.py` vẫn nhập `scipy.ndimage` và dùng `binary_erosion` khi chấm DRIVE. `demo.py` cũng dùng nó. Điều này khác giới hạn trong **INSTRUCTIONS mục 2.1** và **PROTOCOL mục 7**, vốn chỉ cho phép SciPy ndimage ở kiểm thử độc lập/benchmark thời gian.

Tên file chứa chữ “benchmark” không biến luồng chấm GT thành benchmark thời gian. Cần dùng các hàm hình thái học NumPy đã có hoặc cập nhật quy ước chung nếu nhóm chủ động thay đổi ràng buộc; hiện tài liệu đang mâu thuẫn với code. Lõi `src/core` vẫn tự cài bằng NumPy, không kết luận toàn bộ nhân lõi đã dùng SciPy.

### 3.4. DRIVE, normalization và danh sách sigma chưa thống nhất hoàn toàn

- `benchmark_tier2.py` gõ cứng k=4.0; vùng chấm FOV cuối gõ cứng sigma=2 nên xói mòn **8 px**, trong khi stack dùng sigma 1/2/4/8 với hỗ trợ đến 32 px. Từng scale có mask riêng, nhưng vùng đánh giá cuối không được suy ra từ cấu hình/stack. Cách này khác pipeline Đức trước đó dùng giao vùng hợp lệ của các scale (32 px). Cần mô tả rõ và thống nhất cách tính, không so các điểm DRIVE từ hai vùng đánh giá như cùng một phép đo.
- Pipeline chính nhân sigma/sigma² trực tiếp ở nhiều nhánh, chưa đi qua một hàm chuẩn hóa duy nhất có xét `featurej_normalized` như yêu cầu. Cờ hiện đều false nên chưa chứng minh đã nhân đôi ở lần chạy hiện có; đây là thiếu bảo đảm khi cấu hình thay đổi.
- Nhánh Python mặc định thêm sigma=11.3 cho blob, trong khi Fiji chỉ có 7 sigma config. Lệnh `--source both --blob-sigmas config` cho so sánh cùng 7 sigma; phải dùng chính cặp đó khi kết luận Python–Fiji. README đã giải thích 7/8 sigma, nhưng báo cáo/slide vẫn trộn số `blob_05` 0.4651, 0.463 và macro của các nhánh.
- Các hàm `get_sigmas/get_blob_sigmas/get_structure_pairs/get_tier1_images` còn fallback khi **thiếu khóa**. Việc đã sửa strict cho k/border/eigen là tiến bộ, nhưng chưa bảo đảm mọi entrypoint dừng khi thiếu mọi cấu hình bắt buộc. Config hiện tại đã đủ giá trị.

### 3.5. Công việc 5 và các lệnh chạy cũ chưa được chuyển sang nguồn số liệu chính

`CHAY_CONG_VIEC_5_DUC.cmd` vẫn gọi `src.eval.analyze_task5`, hàm này yêu cầu `duc_08_11/run_manifest.json` có status `COMPLETE`. Status hiện là `ARCHIVED_HISTORICAL`, nên hàm kiểm tra dừng với **“Task 23 must be COMPLETE before plotting”**. Đã kiểm tra trực tiếp điều kiện này; không chạy lại toàn pipeline để ghi đè sản phẩm.

Các bảng/biểu đồ ở `outputs/analysis/duc_task5_08_11` vẫn dùng bộ cũ, ví dụ BSDS sigma2=0.472945, trong khi nguồn chính mới=0.477886. Fingerprint runtime công việc 5 cũng **không khớp code hiện tại**, yêu cầu đo lại hoặc quản lý như một phiên lịch sử có ghi rõ mã phiên. Đây là trạng thái dữ liệu cũ, không tự chứng minh mọi giá trị thời gian cũ sai.

Cần chọn rõ: giữ bộ phân tích này như lịch sử và cập nhật launcher/tài liệu sang bộ mới; hoặc chuyển pipeline phân tích sang nguồn chính và sinh lại. Không đổi ngược status archive thành COMPLETE chỉ để bỏ qua kiểm tra. `CHAY_METRIC_DUC_08_11.cmd` cũng vẫn ghi vào thư mục đã được đánh dấu lịch sử, cần tránh hướng dẫn người khác chạy nhầm rồi ghi đè bản lưu trữ.

## 4. Sai sót chuyên môn và diễn giải trên báo cáo/slide

1. **Slide 3 PowerPoint nhầm gamma với bậc đạo hàm:** ghi gamma=1 cho Gradient nhưng gamma=2 cho Hessian/Ridge/Blob. Theo quy ước đang dùng, **gamma=1 cho cả hai**; bậc n nhân sigma^(n·gamma), nên bậc 1 nhân sigma và bậc 2 nhân sigma². Công thức triển khai đúng không làm cho lời giải thích sai trở thành đúng.
2. **Slide 7 mô tả FeatureJ Edges là zero-crossing đạo hàm bậc 2:** sai với mô tả chính thức. FeatureJ Edges dùng Canny: gradient magnitude, NMS theo hướng gradient và threshold/hysteresis; NMS dùng nội suy tuyến tính. Xem [tài liệu chính thức FeatureJ Edges](https://imagescience.org/meijering/software/featurej/edges/). Không nhầm nó với tìm zero-crossing Laplacian.
3. **Slide 6 ghi “220/220 khớp SHA-256 / 100% bản đồ trùng khớp”:** kiểm tra ZIP Java so với TIFF Python hiện có cho **0/220 file có cùng SHA-256**. Nếu ý định là xác minh 220 TIFF Fiji khớp *manifest của chính Fiji*, phải ghi đúng như vậy; checksum toàn vẹn không chứng minh hai engine cho kết quả giống hệt nhau.
4. **Slide 4 gọi k=3,4 là “bậc xấp xỉ Taylor”:** k là hệ số bán kính cắt r=ceil(k·sigma), không phải bậc đạo hàm hay bậc Taylor.
5. **`main.tex` còn gọi NMS là “8 hướng”** trong đoạn mô tả lượng tử hóa 4 sector. Cần phân biệt 4 sector so sánh cực đại với 8 lân cận liên thông hysteresis.
6. **`main.tex` gọi 5 ảnh tầng 1 là “5 ảnh hiệu chuẩn”:** thực tế là 2 BSDS + 1 DRIVE + 2 blob đại diện. Bộ đa thức/Dirac trong `data/calib` phục vụ kiểm tra giải tích và đo tham số, là bộ khác.
7. **Không suy ra “không có lỗi logic” từ Pearson cao**, hoặc “vượt trội” từ hai bộ lọc có kernel/ngưỡng khác nhau mà chưa có đánh giá phù hợp. Bộ đối chiếu thư viện còn câu `VERDICT: 100% PASS` gõ cứng trong mã tạo ảnh; nên xuất kết luận từ tiêu chí đo thực tế.
8. **Demo không tính F1 tại thời điểm chạy:** `demo.py` in cứng 0.477886, đồng thời chạy 1 ảnh tại 1 sigma và gọi là đa tỷ lệ. Cần ghi rõ đó là số tổng hợp tham khảo trên 10 ảnh, không phải metric vừa đo cho ảnh demo hoặc minh chứng chạy toàn scale-space.
9. **Mốc thời gian/test trên slide chưa thống nhất:** PPT ghi mốc 13/11 nhưng yêu cầu chính thức 19/11; nếu là mốc nội bộ cần ghi rõ. HTML còn ghi 20/20 test, trong khi bộ toàn dự án đang là 47 test. 12 slide PPT và 11 slide HTML đều gần yêu cầu “~10 slide”, không coi số lượng này tự thân là lỗi thiếu bài.

Văn bản trích xuất từ PPTX: [SLIDE_TEXT.json](SLIDE_TEXT.json). PPTX đã đọc cấu trúc và kiểm tra ZIP; chưa kiểm tra trực quan trên màn hình trình chiếu/khả năng tràn chữ.

## 5. Kết quả tầng 1 và dữ liệu bàn giao

Đã **tính lại trực tiếp 220 cặp TIFF** bằng `benchmark_tier1.py`, ghi riêng vào [tier1_recheck/tier1_report.csv](tier1_recheck/tier1_report.csv): **35 PASS theo chuẩn gốc, 185 chưa đạt chuẩn gốc**. Không ghi đè CSV bàn giao. Kết quả phù hợp lần chạy đã lưu.

Tài liệu mới đã ghi ngưỡng **RELAXED** 1e-2 và lý do khác biệt rời rạc hóa. INSTRUCTIONS cho phép nhóm quyết định nới ngưỡng có lý do khi sai số hệ thống còn lại. Vì vậy cần trình bày đúng **35 STRICT / 185 RELAXED theo ngưỡng mở rộng**, đồng thời giữ rõ rằng 185 cặp không đạt ngưỡng gốc 1e-4. Không bắt buộc ép code đạt STRICT bằng mọi giá; cũng không gọi 220/220 là đạt STRICT. Hồ sơ đo hiệu chuẩn vẫn cần đủ để bảo vệ cách giải thích nguyên nhân.

| Sản phẩm dữ liệu | Kết quả kiểm tra |
| --- | --- |
| Raw | 25/25 ảnh PNG xám uint8; kích thước mỗi chiều tối thiểu 256 |
| Calibration | 5 TIFF float32 không nén, hữu hạn; Dirac 101×101; các ảnh đa thức 256×256; smoke giải tích PASS |
| Ground truth | 25/25 READY; 56 bộ nhãn BSDS trên 10 ảnh; DRIVE có vessel/FOV; blob_05 có 276 đối tượng và 15 vùng ignore |
| Fiji | **435/435** TIFF hợp lệ theo bộ kỳ vọng, manifest và định dạng; runtime macro 369 dòng |
| Python ZIP | **415/415** TIFF trong 3 ZIP, trùng byte nguồn `outputs/python`; 266 + 94 + 55 file, tên phẳng |
| Java Tier 1 | Có ZIP `outputs/fiji_java_tier1.zip`; hiện chưa có thư mục giải nén `outputs/fiji_java`. Đây không phải mất dữ liệu vì ZIP và cơ chế giải nén vẫn có |
| Gói GT cho Hưng | Có MD/DOCX và overlay; không xác nhận đã gửi qua kênh ngoài |

Các CSV/manifest lịch sử vẫn kiểm tra được. [MANIFEST_INTEGRITY.csv](MANIFEST_INTEGRITY.csv) ghi 112 mục khớp và 12 mục khác ở những nhóm đã đối chiếu: 7 phụ thuộc code của phiên metric cũ và 5 nguồn metric mà phiên phân tích cũ đang trỏ tới. Việc code đã sửa và archive đã cập nhật có thể giải thích khác checksum; **không dùng con số 12 này để kết luận 12 kết quả hiện tại sai**. Vấn đề là các sản phẩm cũ chưa đủ căn cứ tự nhận tái lập với code mới.

## 6. Bàn giao theo từng người

| Thành viên / STT trong bảng | Đã có | Còn cần bàn giao hoặc sửa |
| --- | --- | --- |
| **Hưng — 1–7** | Bản nháp 6 chương, 8 tài liệu trích dẫn, có các công thức; đã có slide | Hoàn thiện cơ sở lý thuyết, hướng/ý nghĩa hình học của tensor; sửa các lỗi mục 4; đồng bộ số liệu; có PDF báo cáo cuối và kiểm tra số trang/font/bố cục |
| **Mạnh — 8–14** | Toàn bộ nhóm thuật toán lõi và detector; 47 unittest PASS; bộ đối chiếu thư viện; benchmark tối ưu 36 trường hợp đã ghi reps=5 | Sửa hợp đồng chấm blob của pipeline chính với Đức; bỏ SciPy ndimage khỏi luồng sản xuất theo ràng buộc; tập trung config/normalization; bổ sung kiểm thử cho pipeline thực sự được chọn làm chính thức; sửa demo/slide kỹ thuật |
| **Lộc — 15–19** | Workflow Edge/Ridge và Blob/Structure DOCX, screenshot, macro, Java và 435 TIFF | Chưa thấy hồ sơ đo độc lập đủ truy vết profile Dirac/k/border/normalization theo từng lệnh; cần đưa bảng/ảnh/log đo này vào bàn giao và phối hợp giải thích sai khác tầng 1. Config có giá trị và vài ghi chú chưa thay thế toàn bộ bằng chứng đo |
| **Đức — 20–24** | Dataset/GT/thiết kế, cả hai bộ metric, biểu đồ và ZIP; nhãn vẫn hợp lệ | Cùng Mạnh thống nhất pipeline chấm đúng; chạy lại metric blob/DRIVE sau khi chốt; cập nhật công việc 5, launcher, biểu đồ, nhận xét theo cùng nguồn chính; phân biệt kết quả baseline với kịch bản nhiễu/kích thước mới chỉ thiết kế |

Không quy lỗi tích hợp cho cá nhân chỉ từ vị trí/tên file. Đề xuất người phối hợp ở bảng trên dựa trên chức năng phụ trách, không xác định ai đã gây thay đổi.

## 7. Báo cáo, slide và các việc chung

- **STT 25:** Có khung LaTeX và các chương. Cần chốt ký hiệu, tham số và tên vai trò thống nhất giữa tài liệu.
- **STT 26:** Chưa thấy PDF báo cáo hoàn chỉnh. `main.tex` có 514 dòng, Chương 2 khoảng 277 token phân cách bằng khoảng trắng gồm cả lệnh LaTeX; chính hướng dẫn cho Hưng cũng ghi cần mở rộng. Có 6 đường dẫn hình và đều tồn tại, 8 khóa trích dẫn không bị thiếu, môi trường LaTeX cân bằng. Máy không có compiler LaTeX nên chưa xác nhận được biên dịch/font/số trang ~30. Kiểm tra tĩnh không thay thế PDF cuối.
- **STT 27:** Đã có PPTX 12 slide và HTML 11 slide; cần sửa nội dung mục 4, đồng bộ số blob và kiểm tra trình chiếu. `python-pptx` chưa cài trong venv và chưa khai báo trong requirements, nên script dựng lại PPTX chưa tái lập từ môi trường đã bàn giao. Điều này không ngăn mở file PPTX có sẵn.
- **STT 28:** Có slide Q&A, nhưng chưa thấy bộ câu hỏi/trả lời bảo vệ riêng. Hoạt động ôn trực tiếp không thể xác minh từ file.
- **STT 29:** Chưa có bằng chứng link nộp LMS và kiểm tra quyền truy cập. Chưa đến hạn nộp; không kết luận nhóm đã nộp hoặc chưa làm việc này ngoài thư mục.

HTML dùng Reveal.js/MathJax qua CDN; khi thuyết trình offline nên dùng PPTX hoặc chuẩn bị đủ tài nguyên. Chưa kiểm tra mạng/CDN hay trình chiếu live trong lần rà soát này.

## 8. Thứ tự nên xử lý để chốt dự án

1. **Mạnh + Đức:** sửa matching một–một/ignore của pipeline chính; thống nhất FOV, sigma, normalization và nguồn metric. Bổ sung kiểm thử có ý nghĩa cho đúng entrypoint đó.
2. **Đức:** sinh lại metric và biểu đồ từ cùng phiên chạy; chuyển hoặc thay thế launcher công việc 5; giữ phiên cũ làm lịch sử với mô tả đúng protocol.
3. **Hưng + Mạnh:** sửa gamma, FeatureJ Edges, ý nghĩa SHA-256/k/NMS và các khẳng định quá mức; dùng thống nhất một nhánh 7 sigma khi đối chiếu Python–Fiji.
4. **Lộc + Mạnh:** hoàn thiện hồ sơ đo và giải thích đối chuẩn; ghi rõ nghiệm thu STRICT/RELAXED, không đánh đồng hai chuẩn.
5. **Hưng + cả nhóm:** hoàn thiện và xuất PDF báo cáo; rà slide, chuẩn bị bảo vệ và kiểm tra link/quyền nộp bài đúng hạn.

Danh sách theo từng đầu việc: [CHECKLIST_29_CONG_VIEC.csv](CHECKLIST_29_CONG_VIEC.csv). Bằng chứng tổng hợp: [CURRENT_CHECKS.json](CURRENT_CHECKS.json), [AUDIT_FACTS.json](AUDIT_FACTS.json).

Lần này chỉ tạo tài liệu/công cụ/bằng chứng kiểm tra và tính metric vào thư mục kiểm tra riêng. Không sửa thuật toán, config, nhãn, slide hoặc các CSV bàn giao; không commit/push/gửi tài liệu cho thành viên.
