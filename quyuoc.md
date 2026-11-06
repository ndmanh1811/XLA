# QUY ƯỚC CHUNG BTL XỬ LÝ ẢNH (FeatureJ)
*(Quy chuẩn kỹ thuật chính thức - Ghim nội bộ nhóm)*

Tài liệu này là quy chuẩn kỹ thuật bắt buộc giữa các thành viên trong nhóm, phục vụ triển khai code, thực nghiệm đối sánh định lượng và đưa vào **Chương Thực nghiệm & Đánh giá** của báo cáo.

**Nguyên tắc chung:** mọi thông số của FeatureJ (bán kính cắt kernel, kiểu biên, chuẩn hóa tỷ lệ, thứ tự trị riêng) là **kết quả đo**, không phải giả định. Giá trị đo được ghi vào `config.yaml` (Mục 1); code Python và script đánh giá chỉ đọc từ file này, không tự gõ cứng.

---

## Bảng phân định trách nhiệm kỹ thuật

| Chức danh kỹ thuật | Trọng tâm nhiệm vụ |
| :--- | :--- |
| **Người phụ trách Lập trình Python** | Cài đặt thuật toán cốt lõi from scratch bằng NumPy, tích chập tách rời, ma trận Hessian, Structure Tensor, các hàm dò Canny, Frangi, Blob; tối ưu hóa mã nguồn. |
| **Người phụ trách Fiji / FeatureJ** | Đo đạc tham số thực nghiệm (k, xử lý biên, cờ chuẩn hóa tỷ lệ theo từng lệnh, thứ tự trị riêng), lập bảng ánh xạ mã thuật toán sang lệnh FeatureJ, viết ImageJ Macro xuất ảnh theo lô và ghi thời gian chạy. |
| **Người phụ trách Dữ liệu & Đánh giá** | Tiền xử lý bộ 25 ảnh xám 8-bit, chuẩn bị ground truth & mặt nạ FOV, viết script đo sai số Tầng 1 và chạy benchmark Tầng 2, vẽ biểu đồ. |
| **Người phụ trách Lý thuyết & Báo cáo** | Xây dựng mô hình toán học giải tích, công thức chuẩn hóa tỷ lệ Lindeberg, quản lý khung mẫu và tổng biên tập báo cáo ~30 trang (chuẩn IEEE). |

---

## 1. Dữ liệu và tệp tin

- **Cấu trúc thư mục dự án:**
  - `config.yaml`: File cấu hình chung (xem bên dưới). Mọi script đều đọc từ đây.
  - `data/calib`: Ảnh hiệu chuẩn, **bắt buộc TIFF 32-bit float**:
    + Ảnh đa thức ($I = x$, parabol $I = x^2/2$, yên ngựa $I = x^2/2 - y^2$): kích thước tối thiểu $\ge 256 \times 256$ để vùng lõi còn đủ lớn ($\ge 176 \times 176$ ở $\sigma=8$), **gốc tọa độ đặt tại tâm ảnh** ($x, y \in [-N/2, N/2]$) để giảm biên độ 4 lần, chống mất độ chính xác làm tròn khi trừ số lớn ở float32.
    + Ảnh xung Dirac $\delta$: kích thước $101 \times 101$, pixel tâm $= 1.0$ (chỉ đo $\sigma \le 4$, vùng lõi còn $61 \times 61$).
    + Ảnh có viền sáng: đo kiểu xử lý biên (reflect/mirror).
  - `data/raw`: Chứa 25 ảnh gốc xám 8-bit uint8 do **Người phụ trách Dữ liệu & Đánh giá** chuyển 1 lần duy nhất, lưu lossless bằng PNG hoặc uncompressed TIFF (tuyệt đối không dùng JPEG).
    + Với BSDS500: chuyển xám theo chuẩn ITU-R BT.601 ($0.299R + 0.587G + 0.114B$).
    + Với DRIVE: trích xuất riêng kênh Green, lưu thành ảnh xám 8-bit uint8 $[0, 255]$.
    + Cả Fiji và Python chỉ đọc file này, không tự chuyển màu ở runtime. Python tự ép sang `float64` khi tính.
  - `data/gt`: Ground truth tương ứng (biên BSDS kèm toàn bộ nhãn của các người gán nhãn, mạch máu DRIVE kèm mặt nạ FOV, tâm và bán kính đốm).
  - `outputs/fiji`: Ảnh TIFF 32-bit float do Fiji Macro xuất ra.
  - `outputs/python`: Ảnh TIFF 32-bit float do Python xuất ra.
  - `outputs/metrics`: File CSV, log đo sai số Tầng 1, biểu đồ Tầng 2, file thời gian chạy.
  - `src/`: Mã nguồn (`src/core/` thuật toán Python, `src/fiji/` macro ImageJ, `src/eval/` script chấm định lượng).
- **File cấu hình `config.yaml` (các ô `null` là giá trị chờ đo, code phải báo lỗi và dừng nếu còn `null`):**
  ```yaml
  kernel_k:                 # k = r / sigma, đo riêng cho từng bậc
    gauss: null
    lx: null
    lxx: null
  border_mode: null          # reflect | mirror (theo định nghĩa SciPy, Mục 3)
  featurej_normalized:       # đã tự nhân sigma hay chưa, đo riêng từng lệnh
    derivatives: null
    laplacian: null
    hessian: null
    edges: null
    structure: null
  eigen_order: null          # algebraic | absolute
  sigmas: [1.0, 2.0, 4.0, 8.0]
  sigmas_blob: [1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0]
  structure_pairs: [[1.0, 3.0], [2.0, 6.0]]  # [[sigma_d (vi phân), sigma_i (tích phân)], ...]
  tier1_images: [bsds_01, bsds_02, drive_01, blob_01, blob_02]
  ```
- **Quy chuẩn Fiji/ImageJ:** Với **mỗi ảnh** được mở, chạy ngay sau lệnh `open()` lệnh `run("Set Scale...", "distance=0 known=0 pixel=1 unit=pixel");` để đơn vị của $\sigma$ tính theo **pixel** (scale lưu theo từng ảnh nên đặt một lần ở đầu macro là không đủ).
- **Quy chuẩn độ chính xác số học (Python):**
  - Python tính toán bằng `float64`, ép kiểu sang `float32` khi lưu.
  - Kết quả trung gian bắt buộc lưu định dạng **TIFF 32-bit float không nén (`.tif`)**, tuyệt đối không dùng PNG/JPG 8-bit để không bị cắt xén giá trị âm và mất độ chính xác.
- **Quy ước trục tọa độ:**
  - Trục $x$ là chiều ngang (cột - `axis=1`), trục $y$ là chiều dọc (hàng - `axis=0`). Trong NumPy: `img[y, x]`.
  - $L_x$ là đạo hàm theo cột, $L_y$ là đạo hàm theo hàng.
- **Quy ước đặt tên tệp:**
  - Cú pháp chuẩn: `{nguon}_{tenanh}_{thuattoan}_s{sigma}.tif`
    *Ví dụ:* `fiji_img01_lxx_s2.0.tif` và `py_img01_lxx_s2.0.tif`.
  - Structure Tensor (2 scale): `{nguon}_{tenanh}_{thuattoan}_sd{sigma_d}_si{sigma_i}.tif`
    *Ví dụ:* `fiji_img01_st-l1_sd1.0_si3.0.tif`.
  - **Mã nguồn duy nhất:** chỉ dùng `fiji` và `py`.
  - **Mã thuật toán:** `gauss`, `lx`, `ly`, `lxx`, `lxy`, `lyy`, `grad`, `lap`, `hess-l1`, `hess-l2`, `edge`, `st-l1`, `st-l2`.
  - **Bảng ánh xạ mã thuật toán sang lệnh FeatureJ** (menu, tùy chọn cụ thể) do Người phụ trách Fiji lập và nộp cùng kết quả đo ở Mục 3. Không ai tự suy đoán lệnh nào xuất ra bản đồ nào (đặc biệt `grad`, `lxy`, `lap`, `edge`).
  - **Độ kết hợp cấu trúc (Coherence):** Không do FeatureJ xuất mà tính ở bước đánh giá từ trị riêng Structure Tensor ($\mu_1 \ge \mu_2 \ge 0$):
    $$\text{Coherence} = \frac{\mu_1 - \mu_2}{\mu_1 + \mu_2 + 10^{-6}}$$
- **Ảnh tổng hợp:** Kích thước tối thiểu $\ge 256 \times 256$ để vùng lõi sau khi crop viền ở $\sigma=8$ (khoảng $40\text{ px}$ mỗi cạnh) vẫn còn $\ge 176 \times 176$.
- **Môi trường tái lập:** Ghi rõ phiên bản OS, Fiji, ImageScience/FeatureJ, Python, NumPy, SciPy, tifffile vào `README.md` và Báo cáo.

---

## 2. Tham số và phạm vi triển khai

- **Dãy tỷ lệ $\sigma$ tổng quát:** $\sigma \in \{1.0, 2.0, 4.0, 8.0\}$ pixel.
- **Structure Tensor:** Chạy 2 cặp cố định $(\sigma_d, \sigma_i) \in \{(1.0, 3.0), (2.0, 6.0)\}$.
- **Lưới tỷ lệ dày cho Blob Detection:** nhập chính xác chuỗi số thực ở cả hai bên:
  $$\sigma \in \{1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0\}$$
  (Không dùng giá trị $2^{k/2}$ tính toán ở Python để khớp 100% với tham số gõ vào Fiji.) Bán kính đốm tổng hợp $r = \sigma\sqrt{2} \approx 1.4 \div 11.3\text{ px}$.
- **Phân định mức độ cài đặt:**
  - **Khớp 1-1 với FeatureJ:** Gaussian smoothing, đạo hàm bậc 1 ($L_x, L_y$), bậc 2 ($L_{xx}, L_{yy}, L_{xy}$), Gradient magnitude, Laplacian, trị riêng Hessian ($\lambda_1, \lambda_2$), trị riêng Structure Tensor ($\mu_1, \mu_2$).
  - **Cài đặt mở rộng bằng Python:**
    + Edge: Canny hoàn chỉnh (Non-maximum suppression + ngưỡng trễ hysteresis).
    + Ridge: Frangi vesselness filter 2D dựng từ bản đồ Hessian (FeatureJ không có plugin Ridge riêng).
    + Blob: Cực trị không gian tỷ lệ (LoG chuẩn hóa là phương pháp chính, DoH là tùy chọn).

---

## 3. Thông số chờ đo từ Fiji (Khóa thông số trong 2 ngày đầu)

Trước khi **Người phụ trách Lập trình Python** khóa code kernel, **Người phụ trách Fiji / FeatureJ** hoàn tất các phép đo sau và điền vào `config.yaml`. Với ảnh dốc/parabol/yên ngựa, **chỉ đọc giá trị ở vùng giữa ảnh**, cách biên hơn $\lceil k\sigma \rceil$ pixel.

1. **Kiểm tra tự nhân $\sigma$ bằng giải tích, lặp cho từng lệnh FeatureJ sẽ dùng** (Derivatives, Laplacian, Hessian, Edges, Structure), vì mỗi lệnh có thể xử lý chuẩn hóa khác nhau:
   - Derivatives, ảnh $I = x$: nếu $L_x = +1$ với mọi $\sigma$ thì xuất đạo hàm thô; nếu $L_x = \sigma$ thì đã nhân $\sigma^1$. Phép đo này đồng thời kiểm tra **dấu** của trục (phải ra $+1$).
   - Derivatives, ảnh $I = x^2/2$: $L_{xx} = 1$ là thô, $\sigma^2$ là đã nhân.
   - Laplacian, ảnh $I = x^2/2$: giá trị $1$ là thô, $\sigma^2$ là đã nhân.
   - Hessian, ảnh yên ngựa $I = x^2/2 - y^2$: kỳ vọng thô là $(1, -2)$; đã nhân là $\sigma^2 \cdot (1, -2)$.
   - Edges (không bật NMS, không ngưỡng), ảnh $I = x$: độ lớn gradient $= 1$ là thô, $\sigma$ là đã nhân.
   - Structure, ảnh $I = x$: ghi nhận giá trị $\mu_1, \mu_2$ và so với kỳ vọng thô.
   - Ghi cờ `featurej_normalized.<lệnh> = true/false` cho từng lệnh.
2. **Kernel và biên (ảnh Dirac, ảnh viền sáng):**
   - Trích **trọng số kernel** thực của FeatureJ từ ảnh Dirac (`gauss`, `lx`, `lxx`) tại $\sigma \in \{1, 2, 4\}$ và so với Gaussian giải tích. Xác nhận: (a) tham số "scale" của FeatureJ đúng là $\sigma$; (b) tổng trọng số (bằng 1 cho `gauss`, bằng 0 cho đạo hàm); (c) kernel có cắt cụt không và cắt ở bán kính nào. Từ đó suy ra $k = r/\sigma$ **riêng cho từng bậc**. Nếu đáp ứng xung khác 0 trên toàn ảnh hoặc trọng số lệch Gaussian giải tích, plugin có thể dùng xấp xỉ khác (ví dụ lọc đệ quy): báo ngay cho nhóm, áp dụng quy tắc ở Mục 4.
   - Kiểu biên theo định nghĩa SciPy, bằng ảnh viền sáng:
     + Pixel biên được lặp lại: `d c b a | a b c d | d c b a` $\rightarrow$ `reflect`.
     + Pixel biên không lặp: `d c b | a b c d | c b a` $\rightarrow$ `mirror`.
3. **Thứ tự trị riêng:** Chạy Hessian trên ảnh yên ngựa $I = x^2/2 - y^2$. Nếu "largest" ra $1$ và "smallest" ra $-2$ thì thứ tự đại số ($\lambda_{\max} \ge \lambda_{\min}$); nếu cặp ra theo $|\lambda|$ giảm dần (đầu ra đầu tiên là $-2$) thì thứ tự theo độ lớn tuyệt đối. Ghi vào `eigen_order`. Ghi thêm cách FeatureJ Structure đặt tên hai trị riêng.
4. **Bảng ánh xạ mã thuật toán sang lệnh FeatureJ:** Nộp một bảng (mã thuật toán, lệnh FeatureJ, các tùy chọn cụ thể) lấy từ Macro Recorder của Fiji. Xác nhận menu thực tế (FeatureJ không có Ridges; Structure chỉ xuất 2 trị riêng).
5. **Quy trình khóa công thức:**
   - Người phụ trách Fiji / FeatureJ đo $\rightarrow$ Người phụ trách Lý thuyết & Báo cáo mô tả công thức giải tích và rời rạc hóa $\rightarrow$ Người phụ trách Lập trình Python xác nhận bằng code kiểm thử. Nếu kết quả đo khác giả định ban đầu, Mục 4 được cập nhật theo sự thống nhất của nhóm.

---

## 4. Khung đánh giá định lượng 2 tầng

### Tầng 1: Python so với Fiji (Kiểm chứng độ trung thực số học)
- **Tập dữ liệu (5 ảnh đại diện, tập con của 25 ảnh):** `bsds_01`, `bsds_02`, `drive_01` (kênh Green), `blob_01`, `blob_02`.
- **Yêu cầu xuất file:** Xuất đầy đủ các bản đồ vi phân (`gauss`, `lx`, `ly`, `lxx`, `lxy`, `lyy`, `grad`, `lap`, `hess-l1`, `hess-l2`, `st-l1`, `st-l2`) tại $\sigma \in \{1, 2, 4, 8\}$ và Structure Tensor $(\sigma_d, \sigma_i) \in \{(1, 3), (2, 6)\}$.
- **Chỉ số:** MAE, RMSE, Max Absolute Error ($\max |\Delta|$), Pearson $r$. Chỉ áp dụng cho bản đồ vi phân liên tục, không dùng cho bản đồ nhị phân, không dùng PSNR cho bản đồ đạo hàm có dấu.
- **Tiêu chuẩn nghiệm thu:**
  $$\frac{\max |\Delta|}{\max |\text{ref}|} < 10^{-4} \quad \text{và} \quad r > 0.9999$$
  ($\max |\text{ref}|$ tính trong vùng lõi sau khi crop.)
- **Vùng tính toán (Mask Crop):**
  - Loại trừ dải viền $\lceil k \cdot \sigma \rceil$ px (theo $k$ của từng bậc).
  - Riêng Structure Tensor: loại trừ $\lceil k \cdot \sigma_d \rceil + \lceil k \cdot \sigma_i \rceil$ px.
  - Báo cáo thêm một mục phụ phân tích sai số riêng tại vùng biên.
- **Hệ số tỷ lệ:** Giữ nguyên giá trị thô, không nhân thêm hệ số scale.
- **Quy tắc khi không đạt ngưỡng:** Không chỉnh code chỉ để ép sai số xuống. Kiểm tra theo thứ tự: (1) $k$ và `border_mode`; (2) cờ chuẩn hóa; (3) cách chuẩn hóa tổng trọng số kernel. Nếu sai số còn lại mang tính hệ thống do FeatureJ dùng xấp xỉ khác, nhóm ghi nhận sai số thực, họp quyết định nới ngưỡng (ví dụ $10^{-3}$) kèm lý do, và nêu rõ trong báo cáo. Đây cũng là một kết quả thực nghiệm có giá trị.

### Tầng 2: So sánh với Ground Truth (Đánh giá hiệu quả bài toán thực tế)
- **Tập dữ liệu (25 ảnh):**
  - 10 ảnh BSDS500 (Edge Detection).
  - 10 ảnh DRIVE kênh Green (Ridge Detection).
  - 5 ảnh đốm tổng hợp và tế bào sinh học (Blob Detection).
  *(5 ảnh Tầng 1 là tập con của 25 ảnh này.)*
- **Quy hoạch xuất file gọn nhẹ:** Với 20 ảnh còn lại, chỉ xuất bản đồ phục vụ bài toán: BSDS (`lx`, `ly`, `edge`), DRIVE (`hess-l1`, `hess-l2`), đốm (`lap` tại lưới $\sigma$ dày). Ảnh đốm của cả hai tầng đều có `lap` tại lưới dày.
- **Chuẩn hóa tỷ lệ ($\gamma = 1$ Lindeberg):** Đóng gói trong **một hàm duy nhất dùng chung**:
  - Đạo hàm bậc 1 và Gradient: nhân $\sigma^1$.
  - Đạo hàm bậc 2, Laplacian, Hessian: nhân $\sigma^2$.
  - Với bản đồ nào của Fiji đã được FeatureJ nhân sẵn (theo `featurej_normalized.<lệnh>`), hàm bỏ qua bước nhân để không nhân hai lần.
- **Tiêu chí chấm từng bài toán:**
  - **Edge (BSDS500):**
    + Dung sai biên 2 px. Precision: tỉ lệ pixel dò được nằm trong 2 px của biên của ít nhất một người gán nhãn. Recall: trung bình theo từng người gán nhãn của tỉ lệ biên người đó được dò trúng trong 2 px.
    + Ngưỡng trễ biểu diễn bằng **phân vị của độ lớn gradient** trong từng ảnh (không dùng giá trị tuyệt đối, vì độ lớn gradient đổi theo $\sigma$ và theo tương phản ảnh). Quét lưới phân vị và chọn bộ ngưỡng tối ưu F1 trung bình **riêng cho từng $\sigma$**; áp giống nhau cho Fiji và Python. Báo cáo F1 theo $\sigma$.
    + Hai nhánh so sánh: (A) `detect_canny` chạy trên `lx`, `ly` của cả hai nguồn (công bằng thuật toán); (B) `FeatureJ Edges` nguyên bản làm tham chiếu, ngưỡng quét theo đơn vị riêng của plugin, báo cáo riêng.
  - **Ridge (DRIVE):**
    + Frangi với $\beta = 0.5$ và $c = 0.5 \cdot \max_{x,y} \sqrt{\lambda_1^2 + \lambda_2^2}$ (tính trên bản đồ đã chuẩn hóa $\sigma^2$, riêng cho từng $\sigma$ và từng ảnh).
    + Cực tính: mạch máu trong kênh Green là rãnh tối, giữ điểm có trị riêng có độ lớn lớn nhất mang **dấu dương**. Lấy $\max$ qua các $\sigma$.
    + Hai nguồn có thể xếp thứ tự trị riêng khác nhau, nên `detect_ridge` tự sắp theo $|\lambda|$ bên trong.
    + **Bắt buộc áp mặt nạ FOV đã xói mòn** $\lceil k\sigma \rceil$ px, để tránh đáp ứng gờ giả ở biên FOV; chỉ tính F1/IoU trong vùng này.
  - **Blob:**
    + Cực tính: đốm sáng trên nền tối là **cực tiểu** của $\sigma^2 \nabla^2 L$; đốm tối là cực đại. Ghi rõ loại đốm của từng ảnh.
    + Khớp đúng khi tâm lệch $\le 2\text{ px}$ và bán kính sai lệch $\le 20\%$ so với Ground Truth.
- **Thời gian chạy:** Python đo bằng bộ đếm thời gian trong code; Fiji ghi `getTime()` vào CSV trong macro. Lặp mỗi phép đo nhiều lần, bỏ lần đầu (khởi động JVM/cache).

---

## 5. Phân việc khâu dò và chấm (Tách bạch Interface)

- **Người phụ trách Lập trình Python:** viết các hàm dò nhận mảng số thực (không nhận ảnh gốc):
  - `detect_canny(lx, ly, p_low, p_high)`: nhận bản đồ $L_x, L_y$; ngưỡng là phân vị (0–100) của độ lớn gradient.
  - `detect_ridge(hess_l1, hess_l2, sigma)`: nhận cặp trị riêng Hessian, tự sắp theo $|\lambda|$.
  - `detect_blob(laplacian_scale_stack, sigmas, polarity)`: nhận chồng bản đồ Laplacian theo $\sigma$, `polarity` là `bright` hoặc `dark`.
  - **Khung hàm** (đúng chữ ký, trả dữ liệu giả) nộp từ **ngày 3**, để Người phụ trách Dữ liệu & Đánh giá viết pipeline song song. Hàm hoàn chỉnh bàn giao trước **08/11**.
- **Người phụ trách Dữ liệu & Đánh giá:** chuẩn bị Ground Truth và FOV, quét ngưỡng, chạy **chính các hàm dò trên** cho cả đầu ra Fiji lẫn Python để đảm bảo nhất quán thuật toán hậu xử lý.

---

## 6. Quy trình triển khai & Quản lý chất lượng

1. **Smoke Test thông luồng sớm:**
   - **Bước 1 (Giải tích):** Ảnh dốc $I = x$ ($L_x = 1$), parabol $I = x^2/2$ ($L_{xx} = 1$) và yên ngựa để kiểm tra dấu, cờ chuẩn hóa, thứ tự trị riêng (Mục 3).
   - **Bước 2 (Số học):** Ảnh thật bất đối xứng `bsds_01` tại $\sigma = 2.0$ cho $L_x, L_y, L_{xx}$. Đạt $\frac{\max|\Delta|}{\max|\text{ref}|} < 10^{-4}$ và $r > 0.9999$ $\rightarrow$ khóa lõi vi phân. (Ảnh dốc không dùng để nghiệm thu, vì $L_y$ và $L_{xx}$ bằng 0 làm tỉ số không xác định.)
2. **Kế hoạch viết báo cáo cuốn chiếu (~30 trang, chuẩn IEEE):**
   - Phân bổ: Giới thiệu (~2 tr), Lý thuyết (~7–8 tr), FeatureJ (~6 tr), Python (~6–7 tr), Thực nghiệm (~7–8 tr), Kết luận & Tài liệu tham khảo (~2 tr) $\approx 30–33$ trang.
   - Bản đồ đạo hàm xuất tối thiểu 300 DPI, có thanh đo màu (**colorbar**) phân định rõ miền âm và dương.
   - Mốc tiến độ:
     + **12/11:** Nộp toàn bộ bản nháp phần mình.
     + **14/11:** Hợp nhất báo cáo vào khung chung.
     + **16/11:** Rà soát hình ảnh, bảng biểu, trích dẫn IEEE.
     + **17/11:** Hoàn thiện 10 slide thuyết trình.
     + **18/11:** Nộp link LMS (deadline chính thức 19/11, dành 1 ngày dự phòng).
