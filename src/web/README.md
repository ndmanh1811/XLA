# Web Demo — BTL Xử Lý Ảnh Số

Demo tương tác so sánh Python Core (NumPy) với các bản đồ Fiji/FeatureJ.

## Chạy

Từ thư mục gốc dự án:

```bash
pip install -r requirements.txt
python -m src.web.app --port 5000
```

Mở `http://127.0.0.1:5000`.

## Nguồn dữ liệu

- Ảnh mẫu: `data/raw` (10 BSDS + 10 DRIVE + 5 blob).
- Ground truth: `data/gt`.
- Bản đồ Fiji: `outputs/fiji`.
- Metric canonical: `outputs/metrics/duc_10_11` (protocol `duc_10_11_v1`).
- 10 figure phân tích: `outputs/analysis/duc_task5_10_11/figures`.

## Quy ước hiển thị & Xử lý đối chuẩn

- Các phép tính lõi dùng `mode="mirror"` để khớp `border_mode: mirror` trong `config.yaml`.
- Preset mặc định dùng đúng tham số canonical:
  - Canny `bsds_01`, σ=2, `p_low=67`, `p_high=91`.
  - Frangi `drive_08`, β=0.5, threshold=0.05, multiscale [1, 2, 4, 8], FOV.
  - Blob `blob_05`, threshold=5.0, polarity bright, 7 scales.
- Panel 3 của Canny là **Fiji gradient |∇L|** (chuẩn hóa nhân σ; nếu thiếu file `grad`, tự động dựng chính xác từ cặp `Lx, Ly` của Fiji; không fallback sang `edge`).
- Hướng gradient (Angle θ) so sánh qua sai số góc quấn $2\pi$ ($|\text{wrap}(\Delta\theta)|$); không áp dụng Pearson tuyến tính cho góc.
- Cặp hiển thị Python và Fiji dùng chung dải động $[v_{\min}, v_{\max}]$ để đảm bảo tương quan biên độ trực quan.
- Panel 3 của Frangi là **Fiji Hessian → Python Frangi (hybrid)**, thời gian tính toán được đo thực tế cho từng công đoạn.
- Panel 3 của Blob là **Fiji Laplacian |LoG| max (response)**, yêu cầu đủ 7 scales mới đối chiếu (không so sánh khập khiễng).
- Giao diện có `AbortController` và bộ đếm tuần tự `requestId` triệt tiêu hoàn toàn race-condition khi bấm nhanh.
- Metric canonical: 35/220 STRICT; 185/220 RELAXED chưa đạt ngưỡng gốc `1e-4`; 0 FAIL.
