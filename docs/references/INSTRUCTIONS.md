# AGENT INSTRUCTIONS: BTL XỬ LÝ ẢNH SỐ (FeatureJ vs Python)

> **HƯỚNG DẪN DÀNH CHO THÀNH VIÊN TRONG NHÓM:**
> Khi bạn sử dụng bất kỳ AI Agent nào (ChatGPT, Claude, Cursor, Copilot, Gemini, Antigravity...), hãy **đính kèm cả 4 file trong thư mục dự án** (`yeucau.md`, `debai.md`, `quyuoc.md`, `INSTRUCTIONS.md`) vào ngữ cảnh chat và gõ câu lệnh:
> 👉 *"Tôi là **[Tên chức danh của bạn]**. Hãy đọc kỹ cả 4 file tài liệu, sau đó hướng dẫn/viết code thực hiện nhiệm vụ tiếp theo của tôi theo đúng các ràng buộc kỹ thuật."*

---

## 1. Bối cảnh dự án & Mục tiêu khoa học (Dành cho AI Agent)

- **Đề tài:** Phát hiện đặc trưng ảnh đa tỷ lệ bằng đạo hàm Gaussian.
- **Mục tiêu cốt lõi:** Cài đặt lại từ đầu (from scratch) các toán tử vi phân Gaussian đa tỷ lệ bằng Python (NumPy), đối chuẩn và kiểm chứng tương đương số học với plugin **FeatureJ** (Fiji/ImageJ), sau đó đánh giá hiệu năng phát hiện cạnh (Edge), gờ (Ridge), đốm (Blob) trên tập dữ liệu chuẩn đối chứng với Ground Truth.
- **Bốn tài liệu nền tảng:**
  1. `yeucau.md`: Yêu cầu chung của giảng viên (Báo cáo ~30 trang, slide ~10 trang; hạn nộp chính thức 19/11, nhóm đặt mục tiêu nộp LMS trước 18/11).
  2. `debai.md`: 9 nội dung chuyên môn (Gaussian, Scale-space, $L_x, L_y, L_{xx}, L_{yy}, L_{xy}$, Gradient, Hessian, Edge, Ridge, Blob).
  3. `quyuoc.md`: Quy chuẩn kỹ thuật chi tiết, bộ tham số, tiêu chuẩn nghiệm thu và quy trình phối hợp.
  4. `INSTRUCTIONS.md`: Chỉ dẫn tác vụ và hợp đồng giao diện dành riêng cho AI Agent của từng vai trò.

---

## 2. Các quy tắc "Bất khả xâm phạm" (Hard Constraints)

Mọi AI Agent khi sinh code hoặc hướng dẫn cho bất kỳ thành viên nào đều **BẮT BUỘC TUÂN THỦ NGHIÊM NGẶT**:

1. **Lõi thuật toán phải tự cài đặt (From Scratch):** Toàn bộ hàm tạo kernel Gaussian 1D, tích chập tách rời 2D, đạo hàm riêng, ma trận Hessian và trị riêng phải tự viết bằng `numpy`. Thư viện `scipy.ndimage` **chỉ được dùng trong kiểm thử độc lập (unit test) và đo benchmark so sánh thời gian**.
2. **Đồng nhất dữ liệu đầu vào (8-bit Grayscale Lossless):**
   - Mọi ảnh trong `data/raw` đều là **ảnh xám 8-bit uint8** lưu lossless (PNG hoặc uncompressed TIFF, tuyệt đối không dùng JPEG).
   - BSDS500: chuyển xám một lần duy nhất theo ITU-R BT.601 ($Y = 0.299R + 0.587G + 0.114B$).
   - DRIVE: trích xuất riêng kênh xanh lục (Green), lưu thành ảnh xám 8-bit uint8 dải $[0, 255]$.
   - Python đọc ảnh vào, ép sang `float64` để tính toán; ép sang `float32` khi ghi ra đĩa.
3. **Ảnh hiệu chuẩn (`data/calib`) là TIFF 32-bit float:** Ảnh đa thức ($I=x, I=x^2/2, I=x^2/2 - y^2$) kích thước $\ge 256 \times 256$ với gốc tọa độ đặt tại tâm ảnh ($x, y \in [-N/2, N/2]$) để chống mất độ chính xác làm tròn float32; ảnh Dirac $\delta$ kích thước $101 \times 101$.
4. **Định dạng kết quả trung gian:** Mọi bản đồ đạo hàm, trị riêng, gradient bắt buộc lưu **TIFF 32-bit float không nén (`.tif`)** bằng `tifffile`, tuyệt đối không dùng PNG/JPG 8-bit.
5. **Quy ước trục:** Trục $x$ là cột (`axis=1`), trục $y$ là hàng (`axis=0`). NumPy truy cập `img[y, x]`. $L_x$ là đạo hàm theo cột, $L_y$ theo hàng.
6. **Cú pháp tên file duy nhất:**
   - 1 scale: `{nguon}_{tenanh}_{thuattoan}_s{sigma}.tif` (chỉ dùng mã nguồn `fiji` hoặc `py`).
   - Structure Tensor (2 scale): `{nguon}_{tenanh}_{thuattoan}_sd{sd}_si{si}.tif`.
7. **Mọi thông số đo từ FeatureJ nằm trong `config.yaml`** (k theo từng bậc, `border_mode`, cờ chuẩn hóa theo từng lệnh, `eigen_order`, danh sách $\sigma$, tên 5 ảnh Tầng 1). Code **không được gõ cứng** các giá trị này; nếu còn `null` thì báo lỗi và dừng. Không được tự đoán giá trị mặc định thay cho kết quả đo.
8. **Quy tắc chuẩn hóa tỷ lệ ($\gamma = 1$):**
   - **Tầng 1 (Fidelity):** Giữ nguyên giá trị thô xuất ra từ plugin/code, không nhân thêm hệ số $\sigma$.
   - **Tầng 2 (Accuracy):** Chỉ dùng **một hàm chuẩn hóa duy nhất** dùng chung: bậc 1 và Gradient nhân $\sigma^1$, bậc 2 (Laplacian, Hessian) nhân $\sigma^2$. Bỏ qua bước nhân với bản đồ Fiji mà `featurej_normalized.<lệnh>` đã là `true`, để không nhân hai lần.
9. **Tiêu chuẩn nghiệm thu số học Tầng 1:**
   - Đo trên 5 ảnh đại diện (2 BSDS + 1 DRIVE + 2 đốm), sau khi crop bỏ dải biên $\lceil k \cdot \sigma \rceil$ px (Structure Tensor crop $\lceil k\sigma_d \rceil + \lceil k\sigma_i \rceil$ px).
   - Nghiệm thu khi $\frac{\max |\Delta|}{\max |\text{ref}|} < 10^{-4}$ (với $\max|\text{ref}|$ tính trong vùng lõi) và Pearson $r > 0.9999$. Chỉ áp dụng cho bản đồ vi phân liên tục.
   - **Nếu không đạt:** không chỉnh code chỉ để ép sai số xuống. Kiểm tra theo thứ tự $k$ và `border_mode`, cờ chuẩn hóa, cách chuẩn hóa tổng trọng số kernel; nếu sai số còn lại mang tính hệ thống thì báo cáo sai số thực, nhóm quyết định nới ngưỡng (có lý do) và ghi vào báo cáo.

---

## 3. Chỉ dẫn chi tiết theo từng chức danh (Role Instructions)

```
┌────────────────────────────────────────────────────────────────────────┐
│  XÁC ĐỊNH VAI TRÒ CỦA NGƯỜI DÙNG ĐANG CHAT ĐỂ KÍCH HOẠT MỤC TƯƠNG ỨNG  │
└────────────────────────────────────────────────────────────────────────┘
```

### VAI TRÒ 1: NGƯỜI PHỤ TRÁCH LẬP TRÌNH PYTHON
*(Nếu người dùng nói: "Tôi là Người phụ trách Lập trình Python")*

- **Mục tiêu:** Xây dựng thư viện Python tự cài đặt từ đầu trong `src/core/`, tối ưu bằng vector hóa NumPy.
- **Cấu trúc mã nguồn cần xây dựng:**
  - `src/core/config.py`: Đọc `config.yaml`; báo lỗi và dừng nếu bất kỳ ô nào còn `null`.
  - `src/core/kernel.py`:
    - Hàm tạo kernel Gaussian 1D giải tích bậc 0, 1, 2 với bán kính $r = \lceil k \cdot \sigma \rceil$.
    - `k` lấy từ `config.yaml` theo từng bậc (không gõ cứng; không có giá trị mặc định).
  - `src/core/convolution.py`:
    - Tích chập tách rời 2D (hàng rồi cột) bằng NumPy.
    - Xử lý biên nhận tham số `mode`: `reflect` (lặp pixel biên: `d c b a | a b c d | d c b a`) hoặc `mirror` (không lặp: `d c b | a b c d | c b a`), theo định nghĩa của SciPy.
  - `src/core/derivatives.py`: $L_x, L_y, L_{xx}, L_{yy}, L_{xy}$, Gradient magnitude $\sqrt{L_x^2 + L_y^2}$, Laplacian $L_{xx} + L_{yy}$.
  - `src/core/hessian.py`: Nghiệm đóng trị riêng ma trận Hessian $(\lambda_1, \lambda_2)$, sắp xếp theo `eigen_order` trong `config.yaml`.
  - `src/core/structure_tensor.py`: Tích phân tensor 2 tỷ lệ $(\sigma_d, \sigma_i)$, xuất $(\mu_1, \mu_2)$; Coherence $= \frac{\mu_1 - \mu_2}{\mu_1 + \mu_2 + 10^{-6}}$.
  - `src/core/detectors.py`: 3 hàm dò mức cao (chỉ nhận mảng số thực, không nhận ảnh gốc):
    + `detect_canny(lx, ly, p_low, p_high)`: NMS theo hướng gradient + ngưỡng trễ. Ngưỡng là **phân vị (0–100)** của độ lớn gradient trong ảnh, không phải giá trị tuyệt đối.
    + `detect_ridge(hess_l1, hess_l2, sigma)`: Frangi với $\beta = 0.5$, $c = 0.5 \cdot \max \sqrt{\lambda_1^2 + \lambda_2^2}$. **Tự sắp xếp hai trị riêng theo $|\lambda|$ bên trong** (vì hai nguồn có thể xếp thứ tự khác nhau). Giữ trị riêng lớn nhất theo độ lớn mang dấu dương (rãnh tối DRIVE). Lấy $\max$ qua các $\sigma$ trên bản đồ đã chuẩn hóa $\sigma^2$.
    + `detect_blob(laplacian_scale_stack, sigmas, polarity)`: Cực trị địa phương LoG 3D. `polarity='bright'` tìm cực tiểu của $\sigma^2\nabla^2 L$, `'dark'` tìm cực đại.
  - **Mốc giao hàng:** khung hàm (đúng chữ ký, trả dữ liệu giả) nộp từ **ngày 3**; hàm hoàn chỉnh bàn giao trước **08/11**.
- **Prompt mẫu cho Agent của bạn:**
  > *"Tôi là Người phụ trách Lập trình Python. Hãy đọc kỹ cả 4 file tài liệu, viết cho tôi `src/core/config.py`, `src/core/kernel.py` và `src/core/convolution.py`. Yêu cầu: tự cài đặt tích chập tách rời 1D from scratch bằng NumPy, `mode` biên là 'reflect' hoặc 'mirror' đọc từ config, bán kính kernel r = ceil(k * sigma) với k đọc từ config theo từng bậc, báo lỗi nếu config còn null."*

---

### VAI TRÒ 2: NGƯỜI PHỤ TRÁCH FIJI / FEATUREJ
*(Nếu người dùng nói: "Tôi là Người phụ trách Fiji / FeatureJ")*

- **Mục tiêu:** Đo đạc giải tích và tham số FeatureJ trong 2 ngày đầu, điền `config.yaml`, viết ImageJ Macro (`.ijm`) xuất TIFF 32-bit float theo đúng quy hoạch và ghi thời gian chạy.
- **Nhiệm vụ cụ thể:**
  1. **Đo đạc giải tích & kiểm tra hộp đen FeatureJ (`data/calib`, TIFF 32-bit float).** Với ảnh dốc/parabol/yên ngựa, chỉ đọc giá trị ở vùng giữa ảnh, cách biên hơn $\lceil k\sigma \rceil$ px.
     - **Đo tự nhân $\sigma$, lặp cho từng lệnh** (Derivatives, Laplacian, Hessian, Edges, Structure):
       + Derivatives, $I = x$: $L_x = +1$ với mọi $\sigma$ là đạo hàm thô; $L_x = \sigma$ là đã nhân. Đồng thời kiểm tra **dấu** (phải ra $+1$).
       + Derivatives, $I = x^2/2$: $L_{xx} = 1$ là thô, $\sigma^2$ là đã nhân.
       + Laplacian, $I = x^2/2$: $1$ là thô, $\sigma^2$ là đã nhân.
       + Hessian, yên ngựa $I = x^2/2 - y^2$ (kỳ vọng thô: $(1, -2)$): so với $\sigma^2 \cdot (1, -2)$.
       + Edges (tắt NMS, không ngưỡng), $I = x$: độ lớn gradient $= 1$ là thô, $\sigma$ là đã nhân.
       + Structure, $I = x$: ghi nhận $\mu_1, \mu_2$ so với kỳ vọng thô.
       + Ghi `featurej_normalized.<lệnh>` cho từng lệnh.
     - **Đo kernel (ảnh Dirac $101 \times 101$, tâm $= 1.0$, $\sigma \in \{1, 2, 4\}$):** Trích **trọng số** kernel của `gauss`, `lx`, `lxx` và so với Gaussian giải tích. Xác nhận tham số "scale" đúng là $\sigma$; tổng trọng số (bằng 1 cho `gauss`, bằng 0 cho đạo hàm); có cắt cụt không và ở bán kính nào. Suy ra $k = r/\sigma$ **riêng cho từng bậc**. Nếu đáp ứng xung khác 0 trên toàn ảnh hoặc trọng số lệch Gaussian giải tích, báo ngay cho nhóm (plugin có thể dùng xấp xỉ khác).
     - **Đo kiểu biên (ảnh viền sáng):** pixel biên được lặp lại $\rightarrow$ `reflect`; không lặp $\rightarrow$ `mirror`.
     - **Đo thứ tự trị riêng:** Hessian trên ảnh yên ngựa. "Largest" $= 1$, "smallest" $= -2$ $\rightarrow$ `algebraic`; cặp ra theo $|\lambda|$ giảm dần (đầu tiên là $-2$) $\rightarrow$ `absolute`.
     - **Lập bảng ánh xạ mã thuật toán sang lệnh FeatureJ** (lệnh, tùy chọn cụ thể) bằng Macro Recorder, đặc biệt cho `grad`, `lxy`, `lap`, `edge`, `hess-l1/l2`, `st-l1/l2`. Xác nhận FeatureJ chỉ có Derivatives, Edges, Hessian, Laplacian, Structure (không có Ridges).
  2. **Viết Macro Fiji tự động (`src/fiji/batch_process.ijm`):**
     - **Ngay sau mỗi lệnh `open()`** trong vòng lặp phải chạy: `run("Set Scale...", "distance=0 known=0 pixel=1 unit=pixel");` (scale lưu theo từng ảnh).
     - **5 ảnh Tầng 1:** xuất đủ `gauss`, `lx`, `ly`, `lxx`, `lxy`, `lyy`, `grad`, `lap`, `hess-l1`, `hess-l2`, `st-l1`, `st-l2` tại $\sigma \in \{1, 2, 4, 8\}$ và ST $(\sigma_d, \sigma_i) \in \{(1,3), (2,6)\}$.
     - **20 ảnh còn lại của Tầng 2:** BSDS xuất `lx`, `ly`, `edge`; DRIVE xuất `hess-l1`, `hess-l2`; ảnh đốm xuất `lap`.
     - **Ảnh đốm (cả hai tầng):** thêm `lap` tại lưới $\sigma$ dày, nhập đúng chuỗi $\{1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0\}$.
     - **Ghi thời gian chạy** từng lệnh bằng `getTime()` vào `outputs/metrics/fiji_runtime.csv`.
     - Lưu TIFF 32-bit float vào `outputs/fiji/` theo mẫu: `fiji_{tenanh}_{thuattoan}_s{sigma}.tif`.
- **Prompt mẫu cho Agent của bạn:**
  > *"Tôi là Người phụ trách Fiji / FeatureJ. Hãy đọc kỹ cả 4 file tài liệu, viết cho tôi `src/fiji/batch_process.ijm` để tự động chạy FeatureJ. Yêu cầu: chạy Set Scale (pixel) ngay sau mỗi lệnh open, đủ mọi bản đồ cho 5 ảnh Tầng 1, chỉ các bản đồ cần thiết cho 20 ảnh còn lại, lưới sigma dày cho ảnh đốm, lưu TIFF 32-bit float đúng quy ước đặt tên và ghi thời gian chạy ra CSV."*

---

### VAI TRÒ 3: NGƯỜI PHỤ TRÁCH DỮ LIỆU & ĐÁNH GIÁ THỰC NGHIỆM
*(Nếu người dùng nói: "Tôi là Người phụ trách Dữ liệu & Đánh giá")*

- **Mục tiêu:** Chuẩn bị bộ dữ liệu 8-bit chuẩn; viết script Smoke Test, benchmark Tầng 1 và Tầng 2; xuất đồ thị và bảng số liệu.
- **Nhiệm vụ cụ thể:**
  1. **Chuẩn bị dữ liệu (`src/eval/prepare_data.py`):**
     - 25 ảnh vào `data/raw` (xám 8-bit uint8 lossless): 10 BSDS500 (BT.601), 10 DRIVE (kênh Green), 5 ảnh đốm tổng hợp và tế bào sinh học (tối thiểu $256 \times 256$).
     - Ground Truth vào `data/gt`: toàn bộ nhãn của các người gán nhãn BSDS, nhãn mạch máu và **mặt nạ FOV** của DRIVE, tâm và bán kính đốm.
     - Tạo `data/calib` (TIFF 32-bit float): $I = x$, $I = x^2/2$, $I = x^2/2 - y^2$, Dirac $\delta$ ($101\times101$), ảnh viền sáng.
     - Năm ảnh Tầng 1 cố định: `bsds_01`, `bsds_02`, `drive_01`, `blob_01`, `blob_02`.
  2. **Smoke Test & Benchmark Tầng 1 (`src/eval/benchmark_tier1.py`):**
     - Smoke test: `bsds_01` tại $\sigma = 2.0$ cho $L_x, L_y, L_{xx}$. Đạt ngưỡng nghiệm thu $\rightarrow$ thông báo khóa lõi vi phân. (Không dùng ảnh dốc để nghiệm thu, vì $L_y$ và $L_{xx}$ bằng 0 làm tỉ số không xác định.)
     - Benchmark 5 ảnh Tầng 1: crop theo $k$ của từng bậc, tính MAE, RMSE, Max Error, Pearson $r$; xuất `outputs/metrics/tier1_report.csv`. Báo cáo riêng sai số ở vùng biên.
     - Xử lý theo quy tắc "nếu không đạt" ở Hard Constraint 9.
  3. **Benchmark Tầng 2 (`src/eval/benchmark_tier2.py`):**
     - Import hàm dò từ `src.core.detectors`; chạy trên đầu ra của cả Fiji và Python (viết pipeline song song bằng khung hàm từ ngày 3).
     - **Edge (BSDS):** Dung sai 2 px. Precision: tỉ lệ pixel dò được nằm trong 2 px của biên của ít nhất một người gán nhãn. Recall: trung bình theo từng người gán nhãn. Ngưỡng là phân vị độ lớn gradient; quét lưới, chọn bộ tối ưu F1 trung bình **riêng cho từng $\sigma$**, áp giống nhau cho Fiji và Python. Hai nhánh: `detect_canny` trên `lx`, `ly` của cả hai nguồn, và FeatureJ Edges nguyên bản (ngưỡng theo đơn vị của plugin) làm tham chiếu riêng.
     - **Ridge (DRIVE):** Áp mặt nạ FOV **đã xói mòn** $\lceil k\sigma \rceil$ px, chỉ tính F1/IoU trong vùng này.
     - **Blob:** Khai báo cực tính (`bright`/`dark`) của từng ảnh. Khớp đúng khi tâm lệch $\le 2$ px và bán kính sai $\le 20\%$.
     - Vẽ biểu đồ Precision-Recall, F1 theo $\sigma$, và đồ thị thời gian chạy Python so với Fiji (từ `fiji_runtime.csv`; lặp nhiều lần, bỏ lần chạy đầu).
- **Prompt mẫu cho Agent của bạn:**
  > *"Tôi là Người phụ trách Dữ liệu & Đánh giá. Hãy đọc kỹ cả 4 file tài liệu, viết cho tôi `src/eval/benchmark_tier1.py` để tự động ghép cặp file giữa `outputs/python/` và `outputs/fiji/` trên 5 ảnh Tầng 1 (đọc từ config.yaml), crop viền theo k của từng bậc, tính MAE, RMSE, Max Error, Pearson r, nghiệm thu khi max|Delta|/max|ref| < 1e-4 và r > 0.9999, xuất CSV."*

---

### VAI TRÒ 4: NGƯỜI PHỤ TRÁCH LÝ THUYẾT & BÁO CÁO
*(Nếu người dùng nói: "Tôi là Người phụ trách Lý thuyết & Báo cáo")*

- **Mục tiêu:** Xây dựng cơ sở lý thuyết toán học; quản lý khung mẫu và tổng biên tập báo cáo (~30 trang, chuẩn IEEE) và slide (~10 trang).
- **Nhiệm vụ cụ thể:**
  1. **Mô hình toán học giải tích:**
     - Phương trình truyền nhiệt trong không gian tỷ lệ:
       $$\partial_s L = \tfrac{1}{2} \nabla^2 L \quad (s = \sigma^2), \qquad \text{hoặc} \quad \partial_t L = \nabla^2 L \quad (t = \sigma^2/2)$$
     - Chuẩn hóa tỷ lệ Lindeberg $\gamma = 1$: $\partial_{x,\text{norm}} = \sigma \partial_x$, $\partial_{xx,\text{norm}} = \sigma^2 \partial_{xx}$.
     - Cơ sở hình học vi phân của ma trận Hessian, tính chất trị riêng $\lambda_1, \lambda_2$ và tensor cấu trúc $\mu_1, \mu_2$.
     - Phối hợp với Người phụ trách Fiji để ghi công thức rời rạc hóa đúng theo kết quả đo.
  2. **Quản lý khung báo cáo (~30 trang):**
     - Chương 1: Giới thiệu & Tổng quan (~2 trang).
     - Chương 2: Cơ sở lý thuyết Scale-space & Đạo hàm Gaussian (~7–8 trang).
     - Chương 3: Khảo sát plugin FeatureJ & Workflow Fiji (~6 trang).
     - Chương 4: Cài đặt thuật toán & Tối ưu hóa bằng Python (~6–7 trang).
     - Chương 5: Thực nghiệm, Đánh giá 2 tầng & Phân tích (~7–8 trang).
     - Chương 6: Kết luận & Tài liệu tham khảo IEEE (~2 trang).
     - *(Tổng cộng ~30–33 trang.)*
     - **Mốc nộp cuốn chiếu:** 12/11 bản nháp từng phần $\rightarrow$ 14/11 hợp nhất $\rightarrow$ 16/11 rà soát (chính tả, công thức, bảng biểu 300 DPI có colorbar, trích dẫn IEEE) $\rightarrow$ 18/11 nộp LMS.
- **Prompt mẫu cho Agent của bạn:**
  > *"Tôi là Người phụ trách Lý thuyết & Báo cáo. Hãy đọc kỹ cả 4 file tài liệu, viết cho tôi bản thảo 'Chương 2: Cơ sở lý thuyết Scale-space và Đạo hàm Gaussian' gồm phương trình truyền nhiệt, chứng minh tính khả tách của kernel Gaussian 2D, công thức chuẩn hóa tỷ lệ Lindeberg và ý nghĩa hình học của trị riêng ma trận Hessian, dưới dạng LaTeX chuẩn IEEE."*

---

## 4. Checklist quy trình triển khai nhóm

- [ ] **Ngày 1–2 (31/10 – 02/11): Chuẩn bị & Hiệu chuẩn giải tích**
  - Dữ liệu: Tạo `data/calib` (dốc, parabol, yên ngựa, Dirac, viền sáng; 32-bit float) và 25 ảnh `data/raw`.
  - Fiji: Đo cờ chuẩn hóa từng lệnh, $k$ từng bậc, kiểu biên, thứ tự trị riêng; nộp bảng ánh xạ lệnh FeatureJ; điền `config.yaml`.
  - Python: Dựng `src/core/`, `config.py`, kernel và tích chập (đọc $k$, `mode` từ config).
  - Báo cáo: Dựng khung IEEE trên Overleaf/Word.
- [ ] **Ngày 3 (03/11): Khung giao diện**
  - Python nộp khung `detect_canny`, `detect_ridge`, `detect_blob` (đúng chữ ký, dữ liệu giả).
  - Dữ liệu bắt đầu viết pipeline Tầng 2 trên khung hàm đó.
- [ ] **Ngày 3–5 (03/11 – 05/11): Khóa thông số & Smoke Test**
  - Fiji bàn giao `config.yaml` đã điền đủ.
  - Smoke Test 2 bước (giải tích, rồi `bsds_01` tại $\sigma = 2.0$). Đạt nghiệm thu $\rightarrow$ **khóa lõi vi phân**.
- [ ] **Ngày 6–11 (06/11 – 11/11): Chạy Batch & Đánh giá**
  - Python bàn giao hàm dò hoàn chỉnh trước **08/11**.
  - Fiji chạy Macro (5 ảnh Tầng 1 đủ bản đồ; 20 ảnh Tầng 2 bản đồ cần thiết; ghi thời gian chạy).
  - Dữ liệu chạy Tầng 1 (CSV) và Tầng 2 (Precision, Recall, F1, IoU), vẽ biểu đồ.
- [ ] **Ngày 12–18 (12/11 – 18/11): Hợp nhất & Nộp**
  - 12/11: Nộp bản nháp phần mình. 14/11: Hợp nhất. 16/11: Rà soát. 17/11: Hoàn thiện 10 slide. 18/11: Nộp link LMS (hạn chính thức 19/11).
