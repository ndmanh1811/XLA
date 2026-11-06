# CẨM NANG HƯỚNG DẪN VIẾT BÁO CÁO KHOA HỌC ~30 TRANG IEEE
**Đề tài:** Phát hiện đặc trưng ảnh đa tỷ lệ bằng đạo hàm Gaussian (FeatureJ vs Pure Python)  
**Tác giả biên soạn kỹ thuật:** Nguyễn Đức Mạnh (Trưởng nhóm / Role 2 - Lead Developer)  
**Người nhận tài liệu:** Thành viên phụ trách Báo cáo & Cơ sở Lý thuyết (Hưng / Role 4)  

---

## 1. Nền tảng soạn thảo & Biên dịch LaTeX chuẩn IEEE

### A. Nền tảng số 1 (Khuyên dùng hàng đầu): [Overleaf.com](https://www.overleaf.com/)
* **Tại sao nên dùng:** 
  * Hoàn toàn miễn phí, chạy trên trình duyệt web, biên dịch PDF trực tiếp trong 2 giây.
  * Không cần cài đặt cồng kềnh (TeXLive/MiKTeX nặng ~5GB dễ lỗi font/package trên máy tính).
  * **Hỗ trợ cộng tác thời gian thực:** Hưng có thể bật tính năng chia sẻ link (*Share*) để Mạnh, Đức, Lộc vào đọc, soát lỗi ngữ pháp, công thức và hình ảnh trực tiếp.
* **Cách khởi tạo trong 1 phút:**
  1. Đăng ký/Đăng nhập tài khoản tại [Overleaf.com](https://www.overleaf.com/).
  2. Tạo dự án mới: `New Project` $\rightarrow$ `Upload Project` (hoặc tạo Blank Project).
  3. Tải lên 2 file đã dựng sẵn trong thư mục `docs/report_template/`:
     * `main.tex`: Khung sườn 6 chương chuẩn IEEE Transactions 2 cột.
     * `references.bib`: Toàn bộ trích dẫn BibTeX bài báo kinh điển.
  4. Nhấn **Recompile** là có ngay bản PDF chuẩn đẹp!

### B. Nền tảng số 2: VS Code + Extension LaTeX Workshop (Nếu muốn gõ Offline)
* Cài đặt bộ phần mềm **TeXLive** (hoặc **MiKTeX**) trên máy tính.
* Cài extension **LaTeX Workshop** trên Visual Studio Code.
* **Tính năng SyncTeX:** Giữ `Ctrl` + Click chuột vào vị trí bất kỳ trên file PDF sẽ tự động nhảy con trỏ về đúng dòng mã nguồn trong `main.tex`.

---

## 2. Bản đồ nội dung và phân bổ dung lượng 6 Chương (~30 trang)

| Chương | Tiêu đề chương | Số trang đề xuất | Nội dung kỹ thuật cần viết | Tài nguyên có sẵn để lấy số liệu & hình ảnh |
| :--- | :--- | :---: | :--- | :--- |
| **Chương 1** | **Giới thiệu & Tổng quan** | ~2 – 3 trang | Bối cảnh xử lý ảnh đa tỷ lệ, tầm quan trọng của đạo hàm Gaussian, mục tiêu nghiên cứu và cấu trúc báo cáo. | Đọc tổng quan trong `debai.md` và `quyuoc.md`. |
| **Chương 2** | **Cơ sở lý thuyết & Mô hình toán** | ~7 – 8 trang | Không gian tỷ lệ (Scale-space), tiên đề Lindeberg, tích chập tách rời 2D, đạo hàm riêng bậc 1, bậc 2, chuẩn hóa $\gamma$-normalized, ma trận Hessian, Structure Tensor, tiêu chuẩn cực trị Canny, Frangi Vesselness, LoG Blob. | Đã gõ sẵn toàn bộ công thức toán LaTeX đẹp trong `docs/report_template/main.tex`. |
| **Chương 3** | **Khảo sát FeatureJ & Workflow Fiji** | ~5 – 6 trang | Phân tích plugin FeatureJ (tác giả Erik Meijering), dịch ngược mã nguồn Java (`Differentiator.class`), giải thích vì sao FeatureJ chỉ chuẩn hóa bậc 0 mà không chuẩn hóa moment Taylor bậc 1/2, workflow đồ họa và ImageJ Macro. | Tham khảo file Java `src/fiji/BatchTier1Fiji.java` và Macro `src/fiji/batch_process.ijm`. |
| **Chương 4** | **Thiết kế & Cài đặt hệ thống (Python)** | ~6 – 7 trang | Kiến trúc mã nguồn thuần NumPy from scratch (0% OpenCV trong lõi), thuật toán tích chập tách rời $O(2K)$ thay vì $O(K^2)$, xử lý biên `mirror`/`reflect`, thuật toán loang BFS Canny, tìm cực trị 3D scale-space LoG. | Đọc docstring và code trong `src/core/*.py` (`kernel.py`, `derivatives.py`, `hessian.py`, `detectors.py`). |
| **Chương 5** | **Thực nghiệm, Đối chuẩn & Phân tích** | ~8 – 9 trang | **Tầng 1:** Đối chuẩn bản đồ vi phân Python Core với FeatureJ ($r > 0.9999$ cho làm mịn và đạo hàm bậc 1; sai số tương đối tăng theo bậc đạo hàm). **Đối chuẩn ngoại:** Khớp SciPy/OpenCV ($r=1.00000000$). **Tầng 2:** Đánh giá trên Ground Truth 25 ảnh (10 BSDS500 + 10 DRIVE + 5 Blob; BSDS500 F1=0.494, DRIVE F1=0.679/IoU=0.516, Blob F1=1.000 cho blob_01–04, F1=0.463 cho blob_05). | Lấy dữ liệu từ mục 3 và mục 4 bên dưới. |
| **Chương 6** | **Kết luận & Hướng mở rộng** | ~2 trang | Đánh giá mức độ hoàn thành chỉ tiêu, đóng góp khoa học, bài học kinh nghiệm và hướng phát triển (GPU CUDA, 3D volumn). | Tóm tắt từ kết quả thực nghiệm vượt chuẩn. |

---

## 3. Bảng số liệu thực nghiệm & Cách chuyển đổi sang LaTeX

### A. Bảng đối chuẩn Tầng 1 (220 bản đồ vi phân Python vs FeatureJ)
* **Nguồn dữ liệu:** File CSV [outputs/tier1_verification_summary.csv](file:///c:/Users/ROG%20M16/OneDrive/Desktop/XLA/outputs/tier1_verification_summary.csv).
* **Kết quả chính:** Dữ liệu Tầng 1 cần tái lập đầy đủ 220 bản đồ. Dữ liệu lịch sử: 35/220 đạt chuẩn STRICT (rel < 1e-4 AND r > 0.9999), 220/220 đạt chuẩn RELAXED (rel < 1e-2 AND r > 0.9999). Pearson trung bình toàn hệ thống từ dữ liệu lịch sử: $r = 0.99999734$.
* **Bảng thời gian chạy:** File [outputs/metrics/fiji_runtime.csv](file:///c:/Users/ROG%20M16/OneDrive/Desktop/XLA/outputs/metrics/fiji_runtime.csv).

### B. Bảng đánh giá Tầng 2 (So với Ground Truth 25 ảnh chuẩn của Đức)
* **Nguồn dữ liệu:** Xuất từ script [src/eval/benchmark_tier2.py](file:///c:/Users/ROG%20M16/OneDrive/Desktop/XLA/src/eval/benchmark_tier2.py).
* **Số liệu chính thức đưa vào báo cáo:**
  1. **Bài toán dò biên (BSDS500 - Canny):**
     * Đánh giá dung sai $\pm 2$ pixel so với tập nhãn đa annotator con người vẽ tay của Berkeley.
     * F1-Score trung bình (10 ảnh): **0.494** ($\sigma=2.0$, phân vị 60/85).
  2. **Bài toán dò mạch máu võng mạc (DRIVE - Frangi Vesselness):**
     * Đánh giá trong vùng quan sát xói mòn (Eroded FOV $17\times 17 \approx$ 8px) so với nét vẽ bác sĩ nhãn khoa.
     * F1-Score trung bình (10 ảnh): **0.679**, IoU trung bình: **0.516**.
  3. **Bài toán dò đốm đa tỷ lệ (Blob Detection - LoG 3D Scale-Space):**
     * Ảnh toán học giải tích (`blob_01` đến `blob_04`): **Đạt F1 = 1.000 tuyệt đối (Khớp 100% cả tâm và bán kính)**.
     * Ảnh kính hiển vi tế bào sinh học (`blob_05` - Mitosis): Detector khớp **140 / 276 đối tượng** $\rightarrow$ **F1 = 0.463**. Tổng thể F1 (5 ảnh): **0.490** (hạn chế của detector trên domain tế bào thật, không phải kết luận nhãn Ground Truth sai).

### C. Công cụ biến CSV thành bảng LaTeX trong 3 giây
* Truy cập trang web miễn phí: **[TablesGenerator.com](https://www.tablesgenerator.com/)**.
* Chọn thẻ **LaTeX**, click vào `File` $\rightarrow$ `Paste table data`, dán nội dung từ file CSV vào.
* Bấm **Generate** $\rightarrow$ Copy đoạn mã `\begin{table} ... \end{table}` dán thẳng vào `main.tex`.

---

## 4. Kho hình ảnh chất lượng cao 300 DPI (Chèn vào Chương 4 & 5)

Tất cả các hình ảnh sau đều được xuất ở độ phân giải in ấn chuẩn khoa học **300 DPI**, tỷ lệ khung hình được tính toán vừa khít khổ 2 cột của IEEE:

| Tên file hình ảnh trong thư mục `outputs/` | Vị trí chèn đề xuất | Ý nghĩa khoa học & Chú thích (Caption) |
| :--- | :--- | :--- |
| `master_side_by_side_comparison.png` | **Chương 5 (Hình lớn 2 cột)** | Bảng đối chứng 5 cột toàn diện: *Ảnh gốc $\rightarrow$ Ground Truth $\rightarrow$ Thuật toán tự viết thuần NumPy $\rightarrow$ OpenCV C++ tham chiếu $\rightarrow$ Bản đồ chồng màu phát hiện (True Positives, False Positives)*. |
| `comparison_custom_vs_libs.png` | **Chương 4 hoặc 5** | Đối chuẩn trực quan tính đẳng hướng và độ mượt mà giữa NumPy Core vs OpenCV Sobel/Canny và SciPy. |
| `bsds09_albatross_groundtruth_comparison.png` | **Chương 5** | Phân tích chi tiết bài toán dò biên Canny trên ảnh chim hải âu (BSDS 108041) đối sánh với 8 bản đồ vẽ tay của 8 annotator con người. |
| `showcase_detector_overlays.png` | **Chương 5** | Minh họa kết quả 3 bộ dò đặc trưng phủ màu trực tiếp lên ảnh thực tế: Canny biên (xanh lá), Frangi mạch (xanh lơ), LoG đốm (vòng tròn vàng). |
| `showcase_scientific_diverging_maps.png` | **Chương 4** | Bản đồ vi phân nhiệt phân kỳ đối xứng nóng - lạnh (`seismic` colormap) minh họa các cực trị đạo hàm bậc 1 ($L_x, L_y$) và bậc 2 ($L_{xx}, L_{yy}, L_{xy}$). |
| `showcase_multiscale_frangi.png` | **Chương 2 hoặc 4** | Sự biến thiên của phản hồi cấu trúc dạng mạch (Vesselness response) qua các tỷ lệ $\sigma \in \{1.0, 2.0, 3.0, 4.0\}$. |

*Mẹo LaTeX để ảnh chiếm trọn 2 cột:* Dùng môi trường `\begin{figure*} ... \end{figure*}` (có dấu sao `*`). Để ảnh nằm gọn trong 1 cột: Dùng `\begin{figure} ... \end{figure}` với `width=\columnwidth`.

---

## 5. Vẽ sơ đồ kiến trúc hệ thống (Vector Graphics)

* **Công cụ khuyên dùng:** **[Draw.io](https://app.diagrams.net/)**.
* **Các khối cần vẽ trong sơ đồ Pipeline:**
  $$\text{Ảnh xám đầu vào} \longrightarrow \text{Tích chập Gaussian tách trục 1D } (O(2K)) \longrightarrow \begin{cases} \text{Đạo hàm bậc 1 } (L_x, L_y) \rightarrow \text{Canny NMS / Hysteresis} \\ \text{Đạo hàm bậc 2 } (L_{xx}, L_{yy}, L_{xy}) \rightarrow \text{Hessian Trị riêng } (\lambda_1, \lambda_2) \rightarrow \text{Frangi} \\ \text{Toán tử Laplacian } (\nabla^2 L) \rightarrow \text{3D Scale-Space Extrema} \rightarrow \text{Blob} \\ \text{Structure Tensor } (S_0, S_1) \rightarrow \text{Coherence / Orientation} \end{cases}$$
* **Xuất file:** Chọn `File` $\rightarrow$ `Export as` $\rightarrow$ **PDF** (chọn `Crop to content`). File PDF này là đồ họa vector (Vector Graphics), khi phóng to trong báo cáo không bao giờ bị mờ hay vỡ nét!

---

## 6. Quản lý trích dẫn tài liệu tham khảo (BibTeX)

* Sử dụng phần mềm **[Zotero](https://www.zotero.org/)** kết hợp plugin **Zotero Connector** để lưu bài báo từ Google Scholar / IEEE Xplore.
* Danh mục trích dẫn đã có sẵn trong `references.bib`:
  * Trích dẫn bài báo của Tony Lindeberg: `\cite{lindeberg1998principles}` hoặc `\cite{lindeberg1994scale}`.
  * Trích dẫn bài báo Canny: `\cite{canny1986computational}`.
  * Trích dẫn bài báo Frangi: `\cite{frangi1998multiscale}`.
  * Trích dẫn bài báo FeatureJ: `\cite{meijering2004design}`.
  * Trích dẫn bộ dữ liệu BSDS500: `\cite{arbelaez2011contour}`.

---

## 7. Checklist nghiệm thu Báo cáo trước khi nộp giảng viên

- [ ] **Độ dài trang:** Đạt từ 28 – 32 trang (chuẩn yêu cầu khoảng 30 trang IEEE).
- [ ] **Bố cục:** Đầy đủ 6 chương mục lục, có phần Tóm tắt (Abstract) và Từ khóa (Index Terms).
- [ ] **Công thức toán:** Viết bằng môi trường LaTeX `\begin{equation} ... \end{equation}`, đánh số công thức tự động, các biến ký hiệu in nghiêng ($x, y, \sigma$).
- [ ] **Bảng và Hình:** Tất cả đều có tiêu đề (Caption), được viện dẫn rõ ràng trong nội dung văn bản (ví dụ: *"như trình bày trong Bảng~\ref{tab:tier1} và Hình~\ref{fig:master}"*).
- [ ] **Không còn lỗi trích dẫn:** Không xuất hiện dấu chấm hỏi đỏ `[?]` do thiếu citation key.
- [ ] **Liêm chính học thuật:** Nhấn mạnh đóng góp cốt lõi của nhóm: Toàn bộ thuật toán Python được lập trình thuần NumPy từ công thức toán học giải tích (from scratch), không sử dụng hàm tích chập có sẵn của OpenCV hay SciPy.
