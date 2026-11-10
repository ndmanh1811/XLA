# Giao thức đánh giá Tier 2 (canonical)

Bản mô tả quy ước số học được dùng để sinh tất cả CSV trong `outputs/metrics/`.
Mọi số liệu trong báo cáo, slide và DOCX workflow phải trích từ thư mục này.

## 1. Dung sai biên (Edge matching)

- Dạng phần tử cấu trúc: **đĩa Euclidean bán kính 2 px** (13 pixel), không phải ô vuông 5×5 (25 pixel).
- Ma trận phần tử:
  ```
  0 0 1 0 0
  0 1 1 1 0
  1 1 1 1 1
  0 1 1 1 0
  0 0 1 0 0
  ```
  Tức góc `(±2, ±2)` **không** nằm trong dung sai.
- Áp dụng cho cả vùng GT (dãn union Ground Truth) và vùng dự đoán (dãn bản đồ biên).

## 2. Nhánh Fair BSDS500 — Canny Edge

- NMS tính **một lần** cho mỗi ảnh tại mỗi σ (trên `σ·Lx`, `σ·Ly`).
- Ngưỡng trễ là **phân vị của `nms[nms > 0]`** (chỉ lấy pixel có edge strength khác 0 sau NMS; loại nền đen phẳng >80% diện tích).
- Lưới quét riêng cho từng σ: `p_low ∈ [5,85]`, `p_high ∈ [50,95]` (bước 5), rồi lưới tinh ±2 phần trăm, bước 1.
- Chọn cặp ngưỡng tối ưu F1 trung bình **trên Python**, sau đó đóng băng và áp nguyên vẹn cho Fiji.
- Fiji fair đọc `lx`, `ly` từ macro xuất, nhân `σ`, chạy cùng `detect_canny` (mặc định `--bsds-fiji-mode canny`).
- Chế độ `edge` (FeatureJ Edges + hysteresis) **chỉ dùng làm tham chiếu riêng**, không trộn với bảng fair.

## 3. Empty-NMS

- Ảnh không có pixel nào sau NMS vẫn nằm trong mẫu số với **F1 = 0**, precision = 0, recall = 0. Không được loại bỏ (bí gây bias mean F1 lên cao).

## 4. Tham chiếu FeatureJ Edges

- Bản đồ `edge` (đã NMS nội bộ của plugin) + hysteresis tuyệt đối.
- Ngưỡng quét theo đơn vị đầu ra của plugin (không phải phân vị).
- Báo cáo riêng theo σ, không dùng thay bảng fair Python↔Fiji.

## 5. DRIVE — Frangi Ridge

- Mặt nạ FOV xói mòn `ceil(k·σ)` px, chỉ tính F1/IoU trong vùng này.
- Ngưỡng tuyệt đối p85 FOV-scale.

## 6. Blob — LoG Scale-Space

- Lệch tâm ≤ 2 px, bán kính sai lệch ≤ 20% so với GT.
- `blob_05` là nhãn tự xây dựng (không phải GT chuyên gia), không được overclaim.

## 7. Ngõ ràng buộc kỹ thuật

- Toàn bộ xử lý hình thái học (dilation, gán nhãn thành phần liên thông) trong `src/eval/bsds_threshold_grid.py` dùng **thuần NumPy** (không `scipy.ndimage`), theo `INSTRUCTIONS.md:25`.
- SciPy chỉ được phép trong `tests/` và benchmark thời gian (`benchmark_optimization.py`).
- `config.strict` mặc định `True`; các giá trị trong `config.yaml` đã điền đầy đủ, không còn `null`.

## 8. Tiêu chuẩn nghiệm thu Tier 1 (tham chiếu)

- `rel < 1e-4` và `r > 0.9999` (strict); relaxed: `rel < 1e-2` và `r > 0.9999`.
- Báo cáo phải giữ **35 STRICT / 185 RELAXED / 0 FAIL**; không gọi 185 RELAXED là FAIL trần.

## 9. Số liệu canonical hiện tại (sau修复 đĩa Euclidean, 10 ảnh)

| σ | Python F1 | Fiji F1 | ΔF1 | p_low/p_high | FeatureJ Edges F1 (tham chiếu) |
|---|-----------|---------|-----|--------------|--------------------------------|
| 1.0 | 0.455418 | 0.455478 | +0.000060 | 76 / 94 | 0.488766 |
| 2.0 | 0.477886 | 0.477886 | +0.000000 | 67 / 91 | 0.500818 |
| 4.0 | 0.441491 | 0.441491 | +0.000000 | 49 / 80 | 0.464873 |
| 8.0 | 0.343340 | 0.343340 | +0.000000 | 23 / 50 | 0.354292 |

| Bài toán | Python F1 | Fiji F1 | ΔF1 |
|---|-----------|---------|-----|
| DRIVE Frangi Ridge | 0.680633 | 0.681651 | +0.001019 |
| Blob LoG Scale-Space | 0.893023 | 0.891901 | −0.001122 |
