# Phát Hiện Đặc Trưng Ảnh Đa Tỷ Lệ Bằng Đạo Hàm Gaussian: Cài Đặt Thuần NumPy và Thẩm Định Đối Chuẩn với FeatureJ / Fiji

Dự án Bài tập lớn môn **Xử lý ảnh số (XLA)** — Khóa học 2026.  
Đề tài nghiên cứu, thiết kế, cài đặt và đánh giá toàn diện hệ thống phát hiện đặc trưng ảnh đa tỷ lệ (*Gaussian Scale-Space Feature Detection*) từ đầu (*from scratch*) bằng NumPy thuần, đối chuẩn số học với thư viện quốc tế **FeatureJ / ImageScience (ImageJ/Fiji)** và thẩm định định lượng trên bộ nhãn **Ground Truth (BSDS500, DRIVE, Blobs)**.

---

## 👥 Nhóm Tác Giả & Phân Công Nhiệm Vụ

| STT | Họ và Tên | Vai Trò Dự Án | Nhiệm Vụ Trọng Tâm |
| :---: | :--- | :--- | :--- |
| **37** | **Nguyễn Đức Mạnh** | **Trưởng nhóm / Role 2** *(Lead Developer)* | Lập trình 100% nhân vi phân NumPy thuần (*Zero-Dependencies*), thiết kế kiến trúc hệ thống, bộ sinh đối chuẩn Java Exporter, kịch bản nghiệm thu Tier 1 & Tier 2. |
| — | **Bùi Trung Đức** | **Role 4** *(Data & Ground Truth)* | Xây dựng, chuẩn hóa và kiểm thử bộ nhãn Ground Truth 25 ảnh mẫu (BSDS500, DRIVE, Blobs; rà soát thủ công `blob_05`). |
| — | **Phạm Bảo Lộc** | **Role 3** *(Fiji / FeatureJ Macro)* | Khảo sát nền tảng FeatureJ, biên soạn tài liệu workflow GUI (.docx), xây dựng kịch bản tự động hóa ImageJ Macro (`batch_process.ijm`). |
| — | **Nguyễn Tiến Hưng** | **Role 1** *(Theory & IEEE Report)* | Phụ trách cơ sở lý thuyết toán học không gian tỷ lệ, tổng hợp số liệu và biên tập toàn bộ Báo cáo khoa học chuẩn IEEE LaTeX (`main.tex`). |

---

## 🏗 Cấu Trúc Thư Mục Dự Án

```text
XLA/
├── config.yaml                    # Trung tâm cấu hình tham số toàn cục (sigma, pairs, kernel_k, quy ước)
├── run_tests.py                   # Script khởi chạy bộ 5 unit test kiểm thử thuật toán lõi
├── README.md                      # Tài liệu tổng quan và hướng dẫn vận hành toàn hệ thống
├── data/
│   ├── raw/                       # 25 ảnh đầu vào chuẩn hóa 8-bit xám lossless (PNG)
│   ├── gt/                        # Bộ nhãn Ground Truth (BSDS500 đa annotator, DRIVE FOV, Blob JSON)
│   └── metadata/                  # Bảng kiểm kê trạng thái nhãn (ground_truth_inventory.csv)
├── src/
│   ├── core/                      # NHÂN TOÁN HỌC THUẦN NUMPY (FROM SCRATCH)
│   │   ├── kernel.py              #   Sinh kernel Gaussian 1D bảo toàn moment rời rạc Taylor (bậc 0, 1, 2)
│   │   ├── convolution.py         #   Tích chập tách rời 2D O(2K), đệm biên phản xạ 'reflect' (mirror)
│   │   ├── derivatives.py         #   Giao diện vi phân: L, Lx, Ly, Grad, Lxx, Lyy, Lxy, Laplacian
│   │   ├── hessian.py             #   Ma trận Hessian và nghiệm giải tích trị riêng (thứ tự đại số)
│   │   ├── structure_tensor.py    #   Ten-xơ cấu trúc đa tỷ lệ (sigma_d, sigma_i) và độ định hướng
│   │   └── detectors.py           #   Bộ dò mức cao: Canny (NMS + BFS), Frangi Vesselness, LoG 3D Extrema
│   ├── fiji/                      # TỰ ĐỘNG HÓA FIJI / FEATUREJ
│   │   ├── BatchTier1Fiji.java    #   Java Exporter tự động xuất 220 bản đồ vi phân chuẩn mực
│   │   ├── batch_process.ijm      #   ImageJ Macro xử lý hàng loạt của Lộc
│   │   └── batch_blob_structure.ijm
│   └── eval/                      # KHUNG ĐÁNH GIÁ VÀ NGHIỆM THU ĐỊNH LƯỢNG
│       ├── verify_tier1.py        #   Nghiệm thu Tầng 1 (Python Core vs 220 bản đồ FeatureJ)
│       └── benchmark_tier2.py     #   Đánh giá Tầng 2 (So sánh với Ground Truth 25 ảnh chuẩn)
├── outputs/                       # DỮ LIỆU ĐẦU RA VÀ ĐỐI CHUẨN
│   ├── python/                    #   220 bản đồ vi phân chuẩn xuất từ Python Core (TIFF 32-bit float)
│   ├── fiji/                      #   231 bản đồ vi phân do kịch bản Macro của Lộc xuất
│   ├── fiji_java/                 #   220 bản đồ vi phân do BatchTier1Fiji.java xuất (đối chuẩn Tầng 1)
│   ├── fiji_java_tier1.zip        #   Kho lưu trữ nén 220 TIFF Tier 1 (92.58 MiB)
│   ├── tier1_verification_summary.csv # Kết quả đối chuẩn pixel-to-pixel chi tiết 220 bản đồ
│   └── metrics/                   #   Bảng số liệu thực nghiệm (tier2_results.csv, fiji_runtime_java.csv)
├── docs/                          # TÀI LIỆU VÀ BÁO CÁO KHOA HỌC
│   ├── report_template/           #   Mã nguồn LaTeX báo cáo chuẩn IEEE (main.tex, references.bib, figures/)
│   └── report_overleaf.zip        #   Gói 1-click (gửi kèm, không tracked trên Git)
└── tests/                         # KIỂM THỬ TỰ ĐỘNG
    └── test_ground_truth.py       #   Bộ 10 unit test kiểm tra tính toàn vẹn và hợp thức của Ground Truth
```

---

## ⚙️ Môi Trường Thực Thi & Phiên Bản Cài Đặt

Hệ thống được thiết kế theo triết lý **Zero-External-Dependencies** cho nhân tính toán lõi (toàn bộ các phép vi phân, giải trị riêng, biến đổi hình thái học đều dùng mảng đa chiều thuần NumPy, không dùng hàm có sẵn của OpenCV hay SciPy).

### Phiên bản Python & Thư viện (khuyến nghị `Python >= 3.11`):
* `python == 3.11.8`
* `numpy == 2.3.5` (hoặc `>= 1.26.0`)
* `scipy == 1.17.1` (chỉ dùng ngoài nhân lõi: unit test đối chuẩn, đọc ma trận `.mat` của BSDS500, và morphology trong `src/eval/` — `binary_erosion` cho FOV, `binary_dilation` cho dung sai 2 px)
* `tifffile == 2026.3.3` (đọc và ghi file ảnh TIFF 32-bit float không nén)
* `opencv-python == 5.0.0` (chỉ dùng trong thẩm định chéo ngoại vi, tuyệt đối không dùng trong `src/core/`)
* `matplotlib == 3.10.8` (trực quan hóa bản đồ nhiệt và biểu đồ)
* `PyYAML == 6.0.3` (phân tích file cấu hình `config.yaml`)
* `Pillow == 12.3.0` (đọc ảnh đầu vào PNG)
* **Lưu ý:** Tuyệt đối **không cài đặt và không sử dụng `pandas`** (tuân thủ quy định `quyuoc.md`).

### Cài đặt môi trường nhanh:
```bash
pip install -r requirements.txt
```

### Môi trường Fiji / ImageJ:
* **Fiji win64** (với Java JDK nhúng Zulu OpenJDK 21).
* Đã tích hợp plugin `FeatureJ_.jar` và thư viện `imagescience.jar` trong thư mục `plugins/`.

---

## 🚀 Hướng Dẫn Thực Thi (Lệnh Chạy Dự Án)

### 1. Kiểm thử đơn vị thuật toán cốt lõi (Core Unit Tests)
Kiểm tra bảo toàn moment Gaussian 1D, tích chập tách rời 2D đối chuẩn SciPy ($< 10^{-14}$), giải tích ảnh đa thức, Structure Tensor và smoke test 3 bộ dò:
```bash
python run_tests.py
# Kết quả kỳ vọng: 5/5 bài test đạt chuẩn!
```

### 2. Kiểm thử tính toàn vẹn của bộ nhãn Ground Truth (Ground Truth Tests)
Kiểm tra tính hợp thức của 25 bộ nhãn, cấu trúc thư mục, định dạng mặt nạ nhị phân và trạng thái rà soát:
```bash
python -c "import unittest; suite = unittest.TestLoader().discover('tests', pattern='test_ground_truth.py'); res = unittest.TextTestRunner(verbosity=2).run(suite); assert res.wasSuccessful()"
# Kết quả kỳ vọng: Ran 10 tests ... OK (10/10 PASS)
```

### 3. Nghiệm thu đối chuẩn Tầng 1 (Tier 1 Verification: Python vs FeatureJ)
So sánh đối chuẩn pixel-to-pixel giữa 220 bản đồ của Python Core với 220 bản đồ FeatureJ của ImageScience:
```bash
python src/eval/verify_tier1.py
```
* **Cơ chế tự động giải nén:** Nếu thư mục `outputs/fiji_java/` chưa có đủ 220 file TIFF (ví dụ khi mới clone repo về máy mới), script sẽ **tự động giải nén** từ kho lưu trữ `outputs/fiji_java_tier1.zip` (92.58 MiB). Bảng mã băm SHA256 của 220 file nằm tại `outputs/metrics/fiji_java_manifest.csv` để đối chiếu toàn vẹn thủ công; hàm `ensure_fiji_java_data()` hiện chỉ giải nén, chưa tự động so hash.
* **Kết quả nghiệm thu thực tế:**
  - **Kỳ vọng:** 220 bản đồ vi phân | **Có sẵn:** 220 bản đồ | **Thiếu:** 0 file | **Bỏ qua:** 0 file.
  - **PASS STRICT:** 35 bản đồ ($\text{rel} < 10^{-4} \land r > 0.9999$): 20 bản đồ Gauss (5 ảnh × 4 $\sigma$) + 15 bản đồ đạo hàm bậc 1 tại $\sigma=1.0$ (5 `lx`, 5 `ly`, 5 `grad`).
  - **PASS RELAXED:** 185 bản đồ ($\text{rel} < 10^{-2} \land r > 0.9999$ - đạo hàm bậc 1, bậc 2, Hessian, Structure Tensor).
  - **FAIL:** 0 | **ACCEPTABLE:** 0.
  - **Tương quan Pearson trung bình toàn hệ thống:** $r = 0.99999710$ (thấp nhất $r_{\min} = 0.99996553$).

### 4. Đánh giá thực nghiệm Tầng 2 (Tier 2 Benchmark: Ground Truth Evaluation)
Đánh giá định lượng trên 25 ảnh thực tế với Ground Truth chuyên gia, áp dụng xói mòn FOV thích ứng đa tỷ lệ $r = \lceil 4.0\sigma \rceil$ và hỗ trợ tham số hóa Canny từ dòng lệnh:
```bash
python src/eval/benchmark_tier2.py --p-low 60.0 --p-high 85.0
```
* **Kết quả xuất ra file:** `outputs/metrics/tier2_results.csv` (đầy đủ 25 dòng số liệu chi tiết).
* **Hiệu năng định lượng đạt được:**
  - **Bài toán Biên (BSDS500 - Canny Edge, 10 ảnh):** $F_1 = 0.494$ (dung sai $\pm 2$ px so với nhãn người vẽ tay).
  - **Bài toán Mạch máu (DRIVE - Frangi Vesselness, 10 ảnh):** $F_1 = 0.681$, $\text{IoU} = 0.518$ (trong vùng FOV xói mòn thích ứng).
  - **Bài toán Đốm (Blobs - LoG Scale-Space, 5 ảnh):**
    - `blob_01` đến `blob_04` (đốm giải tích): **$F_1 = 1.000$ tuyệt đối** (khớp 100% tâm và bán kính).
    - `blob_05` (tế bào sinh học tự gán nhãn): **$F_1 = 0.463$** (phát hiện chính xác 140/276 tế bào).
    - Đánh giá tổng hợp tập đốm: Trung bình cộng 5 ảnh đạt **macro-$F_1 = 0.8926$**; tính gộp toàn bộ 292 đối tượng (micro-average) đạt **micro-$F_1 = 0.4898$**.

### 5. Tái sinh toàn bộ 220 bản đồ FeatureJ bằng Java Exporter (Tùy chọn)
Nếu cần tái sinh độc lập 220 bản đồ từ Fiji engine trong môi trường có sẵn JDK của Fiji:
```bash
# Biên dịch
& "C:\Fiji\java\win64\zulu21.42.19-ca-jdk21.0.7-win_x64\bin\javac.exe" -cp "C:\Fiji\jars\*;C:\Fiji\plugins\*" -d . src/fiji/BatchTier1Fiji.java

# Thực thi headless
& "C:\Fiji\java\win64\zulu21.42.19-ca-jdk21.0.7-win_x64\bin\java.exe" "-Djava.awt.headless=true" -cp ".;C:\Fiji\jars\*;C:\Fiji\plugins\*" src.fiji.BatchTier1Fiji
```

---

## 📊 Bảng Ánh Xạ Đầu Ra, Nguồn Gốc Dữ Liệu & Phân Tích Sai Số

| Thư mục đầu ra | Nguồn gốc sinh dữ liệu | Số lượng file | Mục đích sử dụng | Đánh giá sai số & Giới hạn học thuật |
| :--- | :--- | :---: | :--- | :--- |
| `outputs/python/` | Nhân vi phân Python Core thuần NumPy | **220 TIFF** | Dữ liệu gốc của hệ thống tự lập trình | Chuẩn hóa giải tích $r = \lceil k\sigma \rceil$, bảo toàn moment rời rạc Taylor bậc 0, 1, 2. |
| `outputs/fiji_java/` | Java Batch Exporter gọi trực tiếp `imagescience.jar` | **220 TIFF** | Nguồn tham chiếu đối chuẩn Tầng 1 chính thức | Hệ số tương quan Pearson $r > 0.9999$. Sai số tương đối ở đạo hàm bậc 2 ($L_{xx}, \nabla^2 L \sim 0.4\%$, tối đa $0.93\%$ tại $\sigma=8.0$) là do **khác biệt phương pháp rời rạc hóa**: Python Core bảo toàn moment Taylor rời rạc, còn FeatureJ dùng xấp xỉ lấy mẫu liên tục (Continuous Sampling). |
| `outputs/fiji/` | Kịch bản ImageJ Macro (`batch_process.ijm` của Lộc) | **231 TIFF** | Minh chứng thực nghiệm quy trình GUI ImageJ | Gồm 52 Edge + 112 Hessian + 47 Laplacian + 20 Structure Tensor. Thời gian chạy ghi tại `outputs/metrics/fiji_runtime.csv` (165 dòng). |

---

## 📄 Báo Cáo Khoa Học & Bản Mẫu LaTeX IEEE

* Toàn bộ mã nguồn bài báo khoa học nằm trong thư mục: `docs/report_template/`
  - `main.tex`: Báo cáo chi tiết 6 chương định dạng 2 cột chuẩn IEEE (41.800 ký tự, 488 dòng, tích hợp đầy đủ 6 hình ảnh khoa học và 8 trích dẫn BibTeX).
  - `references.bib`: 8 trích dẫn bài báo kinh điển (Witkin 1983, Lindeberg 1994, Lindeberg 1998, Canny 1986, Frangi 1998, Meijering 2004, Arbelaez 2010, Staal 2004).
* **Gói biên dịch 1-click:** File `docs/report_overleaf.zip` (16.9 MB) được gửi kèm khi bàn giao — **không tracked trên Git** vì `.gitignore` loại `docs/*.zip`. Kéo thả trực tiếp lên **[Overleaf.com](https://www.overleaf.com/)** và nhấn *Recompile* để tạo bản in PDF hoàn chỉnh.
