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
│       ├── benchmark_tier2.py     #   Đánh giá Tầng 2 (Python + Fiji, quét lưới ngưỡng theo σ, GT 25 ảnh)
│       ├── benchmark_runtime.py   #   Đo thời gian Python theo phạm vi fiji_runtime.csv
│       ├── bsds_threshold_grid.py #   Công cụ quét lưới ngưỡng BSDS theo từng σ (NMS cache, hysteresis nhanh)
│       ├── plot_bsds_thresholds.py#   Vẽ 4 biểu đồ điều khiển Tier 2 (PR, F1-vs-σ, heatmap, runtime)
│       └── validate_fiji_outputs.py # Kiểm tra 435 TIFF Fiji (tên, định dạng, manifest, runtime)
├── outputs/                       # DỮ LIỆU ĐẦU RA VÀ ĐỐI CHUẨN
│   ├── python/                    #   220 bản đồ vi phân chuẩn xuất từ Python Core (TIFF 32-bit float)
│   ├── fiji/                      #   435 bản đồ: 423 trong phạm vi macro hợp nhất + 12 TIFF edge cũ (61aedec)
│   ├── fiji_java/                 #   220 bản đồ vi phân do BatchTier1Fiji.java xuất (đối chuẩn Tầng 1)
│   ├── fiji_java_tier1.zip        #   Kho lưu trữ nén 220 TIFF Tier 1 (92.58 MiB)
│   ├── tier1_verification_summary.csv # Kết quả đối chuẩn pixel-to-pixel chi tiết 220 bản đồ
│   └── metrics/                   #   Bảng số liệu thực nghiệm (tier2_results*.csv, tier2_comparison.csv, fiji_runtime_java.csv)
├── docs/                          # TÀI LIỆU VÀ BÁO CÁO KHOA HỌC
│   ├── report_template/           #   Mã nguồn LaTeX báo cáo chuẩn IEEE (main.tex, references.bib, figures/)
│   └── report_overleaf.zip        #   Gói 1-click (gửi kèm, không tracked trên Git)
└── tests/                         # KIỂM THỬ TỰ ĐỘNG
    ├── test_core.py               #   5 unit test nhân lõi (kernel, chập, đa thức, tensor, bộ dò)
    ├── test_bsds_grid.py          #   5 unit test lưới ngưỡng BSDS (hysteresis pixel-identical, grid)
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
* **Cơ chế tự động giải nén và kiểm tra toàn vẹn:** Nếu thư mục `outputs/fiji_java/` chưa có đủ 220 file TIFF (ví dụ khi mới clone repo về máy mới), script sẽ **tự động giải nén** từ kho lưu trữ `outputs/fiji_java_tier1.zip` (92.58 MiB). Sau đó `ensure_fiji_java_data()` đối chiếu từng file với kích thước và mã băm SHA256 trong `outputs/metrics/fiji_java_manifest.csv`; nếu sai lệch, script dừng ngay với lỗi toàn vẹn thay vì tiếp tục nghiệm thu trên dữ liệu hỏng.
* **Kết quả nghiệm thu thực tế:**
  - **Kỳ vọng:** 220 bản đồ vi phân | **Có sẵn:** 220 bản đồ | **Thiếu:** 0 file | **Bỏ qua:** 0 file.
  - **PASS STRICT:** 35 bản đồ ($\text{rel} < 10^{-4} \land r > 0.9999$): 20 bản đồ Gauss (5 ảnh × 4 $\sigma$) + 15 bản đồ đạo hàm bậc 1 tại $\sigma=1.0$ (5 `lx`, 5 `ly`, 5 `grad`).
  - **PASS RELAXED:** 185 bản đồ ($\text{rel} < 10^{-2} \land r > 0.9999$ - đạo hàm bậc 1, bậc 2, Hessian, Structure Tensor).
  - **FAIL:** 0 | **ACCEPTABLE:** 0.
  - **Tương quan Pearson trung bình toàn hệ thống:** $r = 0.99999710$ (thấp nhất $r_{\min} = 0.99996553$).

### 4. Đánh giá thực nghiệm Tầng 2 (Tier 2 Benchmark: Ground Truth Evaluation)
Đánh giá định lượng trên 25 ảnh thực tế với Ground Truth chuyên gia, áp dụng xói mòn FOV thích ứng đa tỷ lệ $r = \lceil 4.0\sigma \rceil$ và hỗ trợ tham số hóa Canny từ dòng lệnh:
```bash
# Lệnh chuẩn: chạy cả Python và Fiji, quét lưới phân vị riêng cho từng sigma
# (mặc định --bsds-threshold-mode grid --bsds-sigmas config)
python src/eval/benchmark_tier2.py --source both --blob-sigmas config

# Nhánh chính thức chỉ Python (mặc định, Blob 8 sigma mở rộng)
python src/eval/benchmark_tier2.py --source python

# Chỉ đọc bản đồ TIFF của Fiji (nhánh fair: lx/ly x sigma + detect_canny)
python src/eval/benchmark_tier2.py --source fiji

# Chế độ lịch sử: một cặp p_low/p_high cố định tại sigma=2.0 (không quét lưới)
python src/eval/benchmark_tier2.py --source both --bsds-threshold-mode fixed --p-low 60.0 --p-high 85.0
```
* **Ghi chú nhánh BSDS của Fiji:** mặc định `--bsds-fiji-mode canny` dùng `lx/ly × σ` + `detect_canny` (cùng thuật toán với Python). Bộ ngưỡng phân vị được chọn trên Python (F1 trung bình cao nhất, tie-break precision cao hơn rồi ngưỡng cao hơn), sau đó **đóng băng và áp nguyên vẹn cho Fiji**. Chế độ `edge` chỉ dùng để tái lập tham chiếu FeatureJ Edges (ngưỡng tuyệt đối, báo cáo riêng).
* **Kết quả xuất ra file:**
  - `outputs/metrics/tier2_results.csv`: nhánh Python chính thức (25 dòng).
  - `outputs/metrics/tier2_results_fiji.csv`: nhánh Fiji fair (25 dòng).
  - `outputs/metrics/tier2_results_both.csv`: gộp cả hai nhánh (110 dòng: 40 BSDS + 10 DRIVE + 5 Blob mỗi nhánh, có cột `source` và `sigma`).
  - `outputs/metrics/tier2_comparison.csv`: bảng đối sánh song song Python vs Fiji (55 dòng: 40 BSDS theo 4 $\sigma$ + 10 DRIVE + 5 Blob, có cột `sigma`).
  - `outputs/metrics/tier2_bsds_sigma_grid.csv`: lưới ngưỡng đầy đủ (1172 dòng: thô 17 cặp × 4 σ × 2 nguồn + tinh 24 cặp × 4 σ × Python).
  - `outputs/metrics/tier2_bsds_thresholds.csv`: ngưỡng tối ưu theo $\sigma$ (4 dòng, chọn trên Python, đóng băng cho Fiji).
  - `outputs/metrics/tier2_bsds_by_sigma.csv`: bảng tổng hợp F1 theo $\sigma$ (4 dòng: Python, Fiji, tham chiếu FeatureJ Edges).
  - `outputs/metrics/tier2_bsds_edge_reference.csv`: tham chiếu FeatureJ Edges chi tiết từng ảnh (40 dòng: 10 ảnh × 4 $\sigma$).
  - `outputs/metrics/tier2_bsds_edge_reference_grid.csv`: lưới ngưỡng tuyệt đối tham chiếu (626 dòng).
  - `outputs/metrics/tier2_bsds_edge_reference_by_sigma.csv`: tổng hợp tham chiếu theo $\sigma$ (4 dòng).
  - `outputs/metrics/python_runtime.csv`: thời gian chạy Python (369 dòng, schema giống `fiji_runtime.csv`; bỏ lần chạy đầu, lấy trung vị).
  - `outputs/metrics/fiji_runtime.csv`: thời gian chạy Fiji do macro của Lộc xuất (369 dòng).
* **Bảng tổng hợp F1 theo $\sigma$ (BSDS500 - Canny Edge fair, 10 ảnh, dung sai ±2 px; ngưỡng chọn trên Python, áp cho Fiji):**

| $\sigma$ | Python $p_{low}/p_{high}$ | Python $F_1$ | Fiji $F_1$ | $\Delta F_1$ | FeatureJ Edges $F_1$ (tham chiếu) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 1.0 | 80 / 94 | 0.490868 | 0.490909 | **+0.000041** | 0.527289 |
| 2.0 | 67 / 91 | 0.516600 | 0.516600 | **+0.000000** | 0.543644 |
| 4.0 | 49 / 80 | 0.490542 | 0.490542 | **+0.000000** | 0.519099 |
| 8.0 | 23 / 50 | 0.395759 | 0.395759 | **+0.000000** | 0.413642 |

| Bài toán khác | Python $F_1$ | Fiji $F_1$ | $\Delta F_1$ |
| :--- | :---: | :---: | :---: |
| DRIVE - Frangi Vesselness (10 ảnh, multiscale) | 0.680633 | 0.681651 | **+0.001019** |
| Blobs - LoG Scale-Space (5 ảnh, 7σ config) | 0.893023 | 0.891901 | **−0.001122** |

  - Các giá trị $F_1$ là trung bình trên F1 **chưa làm tròn** (6 chữ số); CSV từng ảnh vẫn giữ 4 chữ số.
  - **Nhánh BSDS fair:** Fiji dùng chính `lx`, `ly` do macro xuất, nhân $\sigma$ rồi chạy cùng `detect_canny` như Python (dung sai ±2 px).
  - **Tham chiếu riêng FeatureJ Edges:** bản đồ `edge` (đã NMS nội bộ) + hysteresis, ngưỡng tuyệt đối riêng cho từng $\sigma$; chỉ dùng làm tham chiếu, **không** dùng thay bảng fair.
  - DRIVE: IoU trung bình Python = 0.5184, Fiji = 0.5195.
  - `blob_05`: Python 140/326 (F1 = 0.4651) vs Fiji 139/329 (F1 = 0.4595). Kết quả chính thức 8σ của Python trong `tier2_results.csv` vẫn là 140/329 (F1 = 0.463).
  - Sai lệch $|\Delta F_1| \le 0.0012$ đến từ xấp xỉ rời rạc của đạo hàm bậc 2 và cách NMS nội bộ khác nhau giữa FeatureJ và NumPy, không phải lỗi logic (Tầng 1 đã chứng minh $r > 0.9999$ cho mọi toán tử).
  - Ghi nhận ràng buộc chọn ngưỡng: ngưỡng được điều chỉnh và đánh giá trên cùng 10 ảnh BSDS; coi đây là một hạn chế và báo cáo trong Limitations của bài cáo.
* **Hiệu năng định lượng đạt được (nhánh Python chính thức):**
  - **Bài toán Biên (BSDS500 - Canny Edge, 10 ảnh):** F1 cao nhất tại $\sigma=2.0$ là **0.516600** ($p_{low}=67$, $p_{high}=91$); số $0.494$ tại $p60/p85$, $\sigma=2.0$ chỉ là kết quả lịch sử (chế độ `fixed`).
  - **Bài toán Mạch máu (DRIVE - Frangi Vesselness, 10 ảnh):** $F_1 = 0.681$, $\text{IoU} = 0.518$ (trong vùng FOV xói mòn thích ứng).
  - **Bài toán Đốm (Blobs - LoG Scale-Space, 5 ảnh):**
    - `blob_01` đến `blob_04` (đốm giải tích): **$F_1 = 1.000$ tuyệt đối** (khớp 100% tâm và bán kính).
    - `blob_05` (tế bào sinh học tự gán nhãn): **$F_1 = 0.463$** (phát hiện chính xác 140/276 tế bào).
    - Đánh giá tổng hợp tập đốm: Trung bình cộng 5 ảnh đạt **macro-$F_1 = 0.8926$**; tính gộp toàn bộ 292 đối tượng (micro-average) đạt **micro-$F_1 = 0.4898$**.
* **Biểu đồ trong `outputs/figures/`:**
  - `tier2_bsds_pr_curves.png`: Precision–Recall tại bộ ngưỡng đã chọn, từng $\sigma$.
  - `tier2_bsds_f1_vs_sigma.png`: F1 trung bình vs $\sigma$ (Python, Fiji, tham chiếu FeatureJ Edges).
  - `tier2_bsds_f1_heatmap.png`: bản đồ nhiệt F1 của Python trên lưới $(p_{low}, p_{high})$ tại $\sigma=2.0$.
  - `tier2_runtime_comparison.png`: so sánh thời gian chạy trung vị Python vs Fiji theo loại phép toán.

### 5. Benchmark tối ưu chương trình (STT 14)

Đánh giá cải tiến tốc độ khi tách chập 2D thành hai phép chập 1D nối tiếp:

- Phép chập 2D trực tiếp: chi phí $\mathcal{O}(K_x \cdot K_y \cdot HW)$.
- Tách chập 1D: chi phí $\mathcal{O}((K_x + K_y) \cdot HW)$.

Script đo: `src/eval/benchmark_optimization.py` (chỉ dùng để đo, không đưa vào `src/core`).

```bash
python src/eval/benchmark_optimization.py
```

* **Output:** `outputs/metrics/optimization_benchmark.csv` (36 dòng: 3 ảnh × 4 sigma × 3 toán tử).
* **Đúng đắn:** sai số tuyệt đối giữa naive và separable $\sim 10^{-13}$ trên mọi case.
* **Kết quả đại diện (trung bình trên 3 ảnh bsds\_01, drive\_01, blob\_01):**

| Toán tử | $\sigma$ | Naive (ms) | Tách 1D (ms) | Tăng tốc thực | Lý thuyết |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Gauss | 1.0 | 24.06 | 9.14 | 2.44 | 3.50 |
| Gauss | 2.0 | 80.77 | 13.73 | 5.43 | 6.50 |
| Gauss | 4.0 | 318.00 | 25.64 | 11.46 | 12.50 |
| Gauss | 8.0 | 1197.77 | 47.79 | 22.89 | 24.50 |
| $L_x$ | 1.0 | 30.87 | 9.42 | 2.86 | 3.94 |
| $L_x$ | 2.0 | 107.32 | 15.81 | 6.34 | 7.37 |
| $L_x$ | 4.0 | 409.26 | 28.07 | 14.18 | 14.22 |
| $L_x$ | 8.0 | 1573.68 | 56.47 | 27.24 | 27.94 |
| $L_{xx}$ | 1.0 | 31.61 | 9.04 | 3.12 | 3.94 |
| $L_{xx}$ | 2.0 | 106.67 | 17.81 | 5.57 | 7.37 |
| $L_{xx}$ | 4.0 | 404.20 | 28.88 | 12.76 | 14.22 |
| $L_{xx}$ | 8.0 | 1580.24 | 54.99 | 28.99 | 27.94 |

* **Giải thích:** tốc độ tăng thực tế khớp sát hệ số lý thuyết $\frac{K_x \cdot K_y}{K_x + K_y}$. Sai lệch nhỏ do chi phí đệm bộ nhớ, kernel chữ nhật ($L_x, L_{xx}$) và overhead cấp phát mảng trong NumPy. Tại $\sigma=8$, $L_{xx}$ đạt tăng tốc $\approx 29\times$ thực nghiệm (lý thuyết $27.9\times$), chứ không phải con số $32.5\times$ chỉ áp cho kernel vuông $K=65$ (Gauss $\sigma=8$).

### 6. Kiểm tra toàn vẹn bộ 435 TIFF Fiji (Macro Outputs)
Đối chiếu bộ file thực tế với bộ kỳ vọng **423 file trong phạm vi macro hợp nhất + 12 file `edge` legacy** = 435 file, đồng thời kiểm tra manifest, runtime và định dạng từng TIFF:
```bash
python src/eval/validate_fiji_outputs.py
# Kết quả kỳ vọng: PASS: 435/435 file đúng bộ kỳ vọng, manifest, runtime và định dạng.
```
Script kiểm tra: đủ/không thừa file so với quy tắc sinh tên từ `config.yaml`; 435 dòng manifest không trùng, `name_ok=1`, `depth_ok=1`, `bit_depth=32`; 369 dòng runtime (303 một đầu ra + 66 hai đầu ra) phủ đủ 435 file; mọi TIFF là `float32`, đúng kích thước ảnh gốc và không có NaN/Inf.

### 7. Tái sinh toàn bộ 220 bản đồ FeatureJ bằng Java Exporter (Tùy chọn)
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
| `outputs/fiji/` | Kịch bản ImageJ Macro hợp nhất (`batch_process.ijm` của Lộc) + 12 TIFF `edge` cũ từ commit `61aedec` | **435 TIFF** | Minh chứng thực nghiệm quy trình GUI ImageJ | Gồm **423 TIFF trong phạm vi macro hợp nhất** và **12 TIFF `edge` legacy** (`blob_01`, `blob_02`, `drive_01` × 4 $\sigma$) tạo trước khi hợp nhất. Thời gian chạy ghi tại `outputs/metrics/fiji_runtime.csv` (369 dòng dữ liệu, gồm cả 12 dòng legacy). Toàn bộ 435 file được kiểm tra định dạng 32-bit, quy ước đặt tên và đủ bộ kỳ vọng bằng `src/eval/validate_fiji_outputs.py`. |

---

## 📄 Báo Cáo Khoa Học & Bản Mẫu LaTeX IEEE

* Toàn bộ mã nguồn bài báo khoa học nằm trong thư mục: `docs/report_template/`
  - `main.tex`: Báo cáo chi tiết 6 chương định dạng 2 cột chuẩn IEEE (41.800 ký tự, 488 dòng, tích hợp đầy đủ 6 hình ảnh khoa học và 8 trích dẫn BibTeX).
  - `references.bib`: 8 trích dẫn bài báo kinh điển (Witkin 1983, Lindeberg 1994, Lindeberg 1998, Canny 1986, Frangi 1998, Meijering 2004, Arbelaez 2010, Staal 2004).
* **Gói biên dịch 1-click:** File `docs/report_overleaf.zip` (16.9 MB) được gửi kèm khi bàn giao — **không tracked trên Git** vì `.gitignore` loại `docs/*.zip`. Kéo thả trực tiếp lên **[Overleaf.com](https://www.overleaf.com/)** và nhấn *Recompile* để tạo bản in PDF hoàn chỉnh.
