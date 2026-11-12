# Thuyết trình 14 slide — nền sáng, chữ đen

Mở **BTL_XLA_ThuyetTrinh_14_Slide.pptx** bằng PowerPoint; nhấn F5 để trình chiếu. File tự chứa toàn bộ ảnh, không cần mở Python.

Bản PDF xem nhanh: **BTL_XLA_ThuyetTrinh_14_Slide.pdf**. Ảnh preview từng trang và nhật ký kiểm tra khung chữ nằm trong `thuyet_trinh_14/`.

Tỷ lệ 16:9; nội dung và biểu đồ lấy từ phiên metric/timing hiện hành. Gợi ý thời lượng 12–16 phút. Nội dung nói có sẵn trong Notes dưới từng slide.

Bộ 10 slide cũ và builder `build_slides.py` được giữ nguyên. Khi cần cập nhật bộ 14 slide, từ gốc dự án chạy `python docs/slides/build_presentation_14.py`.

Nếu máy có PowerPoint và cần xuất lại PDF/preview sau khi dựng mới: `cscript //Nologo docs/slides/render_presentation_14.vbs`. Script chỉ đóng bài do nó mở, không đóng các bài đang mở khác.

## Nội dung và gợi ý nói

### Slide 01 — Giới thiệu đề tài

Giới thiệu đề tài và bốn thành viên. Nêu mục tiêu: cùng một nền tảng đạo hàm Gaussian để phân tích cạnh, gờ và đốm ở nhiều kích thước. Python tự cài, FeatureJ là nguồn tham chiếu. Dành khoảng 40 giây.

### Slide 02 — Bài toán và mục tiêu

Mở đầu bằng ba loại đặc trưng. Cạnh là chuyển mức sáng; ridge là cấu trúc dài mảnh; blob là vùng đậm/sáng cục bộ. Mục tiêu thứ nhất là tự cài đúng, thứ hai so bản đồ với FeatureJ, thứ ba chấm phát hiện với GT. Dẫn vào lộ trình lý thuyết → cài đặt → thực nghiệm → kết luận.

### Slide 03 — Gaussian smoothing và scale-space

Giải thích L=Gσ*I và tính tách trục. Ảnh minh họa đọc từ TIFF Python đã tính, cùng bsds_01 ở bốn sigma. Không so sáng từng ảnh bằng chuẩn hóa riêng: dải hiển thị 0–255 được giữ chung. Scale-space là họ ảnh theo sigma, không phải chỉ phóng to/thu nhỏ ảnh. Nguồn lý thuyết: Lindeberg, Scale-Space Theory in Computer Vision (1994).

### Slide 04 — Đạo hàm Gaussian, gradient và chuẩn hóa

Lx, Ly được tạo bằng tích chập với đạo hàm Gaussian; gradient biểu diễn độ biến thiên và hướng. Laplacian là tổng Lxx+Lyy. Phân biệt chuẩn hóa tỷ lệ ở tầng detector và giữ bản đồ thô khi đối chuẩn. Không gọi bậc 2 là gamma=2. Ba ảnh cùng sigma=2, Lxx dùng thang xám có tâm 0; dải hiển thị khác nhau nên không suy biên độ từ độ sáng giữa các panel. Nguồn: Lindeberg (1998), Feature Detection with Automatic Scale Selection.

### Slide 05 — Hessian và Structure Tensor

Hessian dùng đạo hàm bậc hai, trị riêng cho biết độ cong theo các hướng chính. Ridge chọn cấu trúc một hướng cong mạnh; blob có độ cong ở nhiều hướng. Structure Tensor lấy tích các đạo hàm bậc một rồi làm mịn ở scale tích phân; coherence phản ánh tính trội của một hướng. Hessian có dấu; tensor cấu trúc lý tưởng bán xác định dương. Bộ đối chuẩn giữ thứ tự algebraic; Frangi tự xếp trị riêng theo độ lớn. Không đồng nhất hai ma trận này.

### Slide 06 — Từ đạo hàm đến ba bộ phát hiện

Đi lần lượt ba nhánh. Canny từ gradient qua NMS và hysteresis. Python dùng 4 sector NMS và liên thông 8 lân cận; FeatureJ có nội suy riêng nên native Edges chỉ là tham chiếu riêng. Frangi dùng Hessian chuẩn hóa, giữ tín hiệu ridge phù hợp dấu và lấy cực đại các scale. Blob tìm cực trị không gian–tỷ lệ của LoG chuẩn hóa; blob sáng tìm cực tiểu. Bán kính xấp xỉ sqrt(2)*sigma. Tham khảo Canny (1986), Frangi et al. (1998), Lindeberg (1998).

### Slide 07 — Dữ liệu thực nghiệm và Ground Truth

BSDS có 10 ảnh, tổng 56 bộ nhãn ranh giới; DRIVE có 10 ảnh, vessel mask và FOV. Blob gồm 4 ảnh tổng hợp và 1 ảnh tế bào blob_05: 276 đối tượng, 15 vùng ignore. Tất cả raw uint8 xám lossless. BSDS theo BT.601, DRIVE lấy green. Không gọi nhãn blob_05 là nhãn chuyên gia của nhà cung cấp. Nguồn: data/SOURCES.md, data/manifest.json và data/gt.

### Slide 08 — Triển khai hai nguồn trên cùng cấu hình

Giải thích hai nguồn bản đồ: Python tự cài từ kernel đến tích chập, đạo hàm và trị riêng; Fiji xuất từ FeatureJ/ImageScience. Hai nguồn cùng downstream detector. Nội bộ Python float64, lưu TIFF float32 không nén. Config chứa k theo lệnh, mirror, cờ normalization và dãy sigma; không tự đoán fallback. Hiệu chuẩn đã có 40 TIFF và số đo định lượng, còn ảnh giao diện cần Lộc bổ sung. SHA-256 xác minh toàn vẹn file của từng nguồn, không chứng minh Python byte-identical Fiji.

### Slide 09 — Hai tầng đánh giá: độ khớp và độ chính xác

Tầng 1 crop vùng lõi theo support từ config rồi so bản đồ thô: MSE, RMSE, relative max error, Pearson; PSNR MAX255 chỉ cho Gaussian. Tiêu chuẩn gốc đồng thời relative error<1e-4 và r>.9999. Tầng 2 chấm P/R/F1; BSDS dung sai Euclidean2px, precision any annotator, recall mean annotator; DRIVE giao FOV hợp lệ qua mọi scale (32px support hiện tại); blob matching maximum-cardinality một–một, tâm<=2px bán kính<=20%, áp ignore trước FP. Chọn và chấm cùng tập nên không gọi là test độc lập.

### Slide 10 — Đối chuẩn số học: Gaussian khớp tốt nhất

Tầng 1 có 35 PASS STRICT trong 220 cặp; 185 chưa đạt ngưỡng gốc. Gaussian20/20; đạo hàm bậc cao và tensor còn sai số hệ thống. Các cặp này đạt ngưỡng mở rộng 1e-2 theo phân tích cũ nhưng không được gọi đạt STRICT. Đáp ứng xung/hiệu chuẩn giúp kiểm tra cách rời rạc hóa, support và chuẩn hóa; chưa khẳng định nguyên nhân duy nhất. Biểu đồ tính từ tier1_report.csv của phiên hiện hành.

### Slide 11 — Cạnh: tỷ lệ trung gian cho F1 tốt hơn

F1 trung bình Python cao nhất trong lưới là 0.477886 tại sigma=2; Fiji cùng Canny 0.477886. Hai đường gần trùng, marker rỗng giúp phân biệt. Đây là mean trên10ảnh, không phải F1 của một ảnh demo. Khi sigma tăng quá lớn, chi tiết/cạnh yếu có thể mất; đó là diễn giải xu hướng nội bộ. Native FeatureJ Edges không nằm trong hai đường vì NMS/ngưỡng khác. Nguồn edge_by_sigma.csv.

### Slide 12 — Ridge và blob: cần đọc cả macro lẫn micro

DRIVE macro F1 Python/Fiji=0.477382/0.473863. Python precision=0.811157, recall=0.352088: còn bỏ sót. Blob macro/micro như biểu đồ. Bốn ảnh tổng hợp F1=1 nhưng blob_05 chỉ 0.492091/0.486865; micro gộp số đối tượng nên phản ánh ảnh276nhãn nhiều hơn. Matching một–một và15ignore đã được dùng. Nguồn tier2_summary.csv và tier2_results_both.csv.

### Slide 13 — Thời gian chạy và đánh đổi thực thi

357 case mỗi nguồn,1warmup+5lượt giữ lại; dùng median5mẫu mỗi case. Biểu đồ là median giữa các median case theo lệnh, không phải tổng thời gian. Median tỷ số từng case Python/engine=10.668, khác tỷ số hai median. API Java ImageScience headless, loại I/O; đo nguồn Java trước, Python sau. Pythonfloat64 và precision nội tại engine khác nhau. Các lệnhedge chỉ gradient+NMS, không phải toàn bộ pipeline Canny/GT. Độ phức tạp tích chập tách trục giúp giảm chi phí so với2D trực tiếp nhưng không đồng nghĩa Python nhanh hơn engineJava. Nguồn runtime_paired.csv và runtime_environment.json.

### Slide 14 — Kết luận và hướng phát triển

Tổng kết ba đóng góp: lõi tự cài; pipeline hai nguồn, có dữ liệu/GT/manifest; số liệu và biểu đồ có thể tái hiện. Nêu giới hạn thẳng thắn:185cặp chưaSTRICT; nhãn tế bào nội bộ; chọn ngưỡng và chấm cùng tập; chưa thí nghiệm nhiễu/resize. Hướng phát triển: tách tập chọn ngưỡng/đánh giá, mở rộng dải kích thước và ảnh thật, hoàn thiện đối chiếu kernel/hiệu chuẩn. Nguồn nền tảng: Lindeberg1994/1998; Canny1986; Frangi1998; FeatureJ/ImageScience và quy ước dự án. Bộ slide phản ánh kết quả hiện có, không tuyên bố mọi tiêu chí nghiệm thu đã đạt.

## Nguồn số liệu

- `outputs/metrics/duc_10_11/`: MSE/PSNR/Pearson, P/R/F1, matching audit.
- `outputs/analysis/duc_task5_10_11/`: F1 theo sigma, timing và manifest.
- `outputs/python/`: TIFF dùng làm ảnh minh họa scale-space và đạo hàm.
- `data/raw/`, `data/gt/`: ảnh đầu vào và số nhãn.
- Lý thuyết: các mục Lindeberg/Canny/Frangi đã có trong `docs/report_template/references.bib`.

Không diễn giải 35/220 STRICT thành tất cả đều đạt. Không gọi điểm trên tập dùng chọn ngưỡng là điểm test độc lập. Nội dung slide không thay thế việc Lộc bổ sung screenshot hoặc Hưng nghiệm thu PDF báo cáo.
