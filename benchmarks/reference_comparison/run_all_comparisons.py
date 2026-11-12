"""
run_all_comparisons.py - TỔNG HỢP VÀ KẾT XUẤT ĐỐI CHUẨN NUMPY THUẦN vs SCIPY & OPENCV
Tự động chạy toàn bộ quy trình đối chuẩn và sinh hình ảnh đối chiếu 300 DPI ra:
outputs/comparison_custom_vs_libs.png
"""

import sys
import argparse
import csv
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Thư viện ngoài tham chiếu
import scipy.ndimage as ndi
import cv2

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.core.derivatives import (
    gaussian_smooth,
    compute_derivatives_1st,
    compute_derivatives_2nd,
    compute_gradient_magnitude,
    compute_laplacian,
)
from src.core.detectors import detect_canny
from src.config import get_border_mode, get_kernel_k, load_config
from src.eval.metric_utils import sha256
from benchmarks.reference_comparison.report_metrics import measured_summary_text, opencv_border_mode, continuous_metrics, fmt_r

DELIVERY = ROOT / "outputs/benchmarks/reference_comparison"

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def generate_visual_comparison_figure(image_path: str = "data/raw/bsds_01.png", sigma: float = 2.0, p_low: float = 60.0, p_high: float = 85.0):
    full_path = ROOT / image_path
    pil_img = Image.open(full_path).convert("L")
    img_f64 = np.array(pil_img, dtype=np.float64)
    img_u8 = np.array(pil_img, dtype=np.uint8)
    h, w = img_f64.shape
    mode = get_border_mode()
    k0, k1, k2 = [get_kernel_k(i) for i in (0,1,2)]

    # 1. Tính toán Gaussian
    custom_g = gaussian_smooth(img_f64, sigma=sigma, mode=mode)
    scipy_g = ndi.gaussian_filter(img_f64, sigma=sigma, mode=mode, truncate=k0)
    ksize = 2 * int(np.ceil(k0 * sigma)) + 1
    opencv_g = cv2.GaussianBlur(img_f64, (ksize, ksize), sigmaX=sigma, sigmaY=sigma, borderType=opencv_border_mode(mode))
    diff_g = np.abs(custom_g - scipy_g)

    # 2. Tính toán Đạo hàm & Gradient & Laplacian
    lx, ly = compute_derivatives_1st(img_f64, sigma=sigma, mode=mode)
    grad_custom = compute_gradient_magnitude(lx, ly)
    lap_custom = compute_laplacian(img_f64, sigma=sigma, mode=mode)

    lx_scipy = ndi.gaussian_filter(img_f64, sigma=sigma, order=[0, 1], mode=mode, truncate=k1)
    ly_scipy = ndi.gaussian_filter(img_f64, sigma=sigma, order=[1, 0], mode=mode, truncate=k1)
    grad_scipy = np.sqrt(lx_scipy**2 + ly_scipy**2)
    lap_scipy = ndi.gaussian_laplace(img_f64, sigma=sigma, mode=mode, truncate=k2)
    diff_grad = np.abs(grad_custom - grad_scipy)

    # 3. Tính toán Canny
    canny_custom = detect_canny(lx, ly, p_low=p_low, p_high=p_high, return_binary=True)
    non_zero = grad_custom[grad_custom > 0]
    th_high = float(np.percentile(non_zero, p_high)) if non_zero.size else 0.0
    th_low = float(np.percentile(non_zero, p_low)) if non_zero.size else 0.0

    img_smooth_u8 = np.clip(custom_g, 0, 255).astype(np.uint8)
    canny_cv = cv2.Canny(img_smooth_u8, int(th_low), int(th_high), L2gradient=True)

    # Tạo bản đồ Overlay Canny màu:
    # Vàng: Cả 2 cùng phát hiện
    # Xanh lục: chỉ NumPy Core phát hiện; đỏ: chỉ OpenCV phát hiện.
    overlay_rgb = np.zeros((h, w, 3), dtype=np.uint8)
    mask_c = canny_custom > 0
    mask_v = canny_cv > 0
    both = mask_c & mask_v
    only_c = mask_c & (~mask_v)
    only_v = mask_v & (~mask_c)

    overlay_rgb[both] = [255, 255, 0]    # Yellow
    overlay_rgb[only_c] = [0, 255, 0]   # Green
    overlay_rgb[only_v] = [255, 50, 50]  # Red

    # Canny Custom phủ lên ảnh gốc
    img_rgb = np.stack([img_u8, img_u8, img_u8], axis=-1)
    custom_on_raw = img_rgb.copy()
    custom_on_raw[mask_c] = [0, 255, 0]

    # Vẽ biểu đồ 3x5
    fig, axes = plt.subplots(3, 5, figsize=(22, 13))
    plt.subplots_adjust(wspace=0.15, hspace=0.25)

    # Hàng 1: Gaussian
    axes[0, 0].imshow(img_f64, cmap="gray")
    axes[0, 0].set_title(f"Ảnh gốc: {full_path.name}", fontsize=11, fontweight="bold")

    axes[0, 1].imshow(custom_g, cmap="gray")
    axes[0, 1].set_title("1. NumPy Core Gaussian", fontsize=11, fontweight="bold", color="darkblue")

    axes[0, 2].imshow(scipy_g, cmap="gray")
    axes[0, 2].set_title("2. SciPy gaussian_filter", fontsize=11, fontweight="bold")

    axes[0, 3].imshow(opencv_g, cmap="gray")
    axes[0, 3].set_title("3. OpenCV cv2.GaussianBlur", fontsize=11, fontweight="bold")

    im_err_g = axes[0, 4].imshow(diff_g, cmap="hot")
    axes[0, 4].set_title(f"Sai số |NumPy - SciPy|\n(Max = {np.max(diff_g):.2e})", fontsize=10, fontweight="bold", color="darkred")
    plt.colorbar(im_err_g, ax=axes[0, 4], fraction=0.046, pad=0.04)

    # Hàng 2: Gradient & Laplacian
    axes[1, 0].imshow(grad_custom, cmap="viridis")
    axes[1, 0].set_title("4. NumPy Core Gradient", fontsize=11, fontweight="bold", color="darkblue")

    axes[1, 1].imshow(grad_scipy, cmap="viridis")
    axes[1, 1].set_title("5. SciPy Gradient", fontsize=11, fontweight="bold")

    im_err_gr = axes[1, 2].imshow(diff_grad, cmap="magma")
    axes[1, 2].set_title(f"Sai số Gradient (r={fmt_r(continuous_metrics(grad_custom,grad_scipy)['pearson_r'])})\n(Max = {np.max(diff_grad):.2e})", fontsize=10, fontweight="bold", color="darkred")
    plt.colorbar(im_err_gr, ax=axes[1, 2], fraction=0.046, pad=0.04)

    vmax_lap = max(np.percentile(np.abs(lap_custom), 99), 1.0)
    axes[1, 3].imshow(lap_custom, cmap="seismic", vmin=-vmax_lap, vmax=vmax_lap)
    axes[1, 3].set_title("6. NumPy Core Laplacian ∇²L", fontsize=11, fontweight="bold", color="darkblue")

    axes[1, 4].imshow(lap_scipy, cmap="seismic", vmin=-vmax_lap, vmax=vmax_lap)
    axes[1, 4].set_title(f"7. SciPy gaussian_laplace\n(Pearson r={fmt_r(continuous_metrics(lap_custom,lap_scipy)['pearson_r'])})", fontsize=10, fontweight="bold")

    # Hàng 3: Canny & Phân tích biên
    axes[2, 0].imshow(canny_custom, cmap="gray")
    axes[2, 0].set_title(f"8. NumPy Canny\n{np.sum(mask_c)} pixels", fontsize=11, fontweight="bold", color="darkgreen")

    axes[2, 1].imshow(canny_cv, cmap="gray")
    axes[2, 1].set_title(f"9. OpenCV Canny (ảnh đã làm mịn)\n{np.sum(mask_v)} pixels", fontsize=11, fontweight="bold", color="darkred")

    axes[2, 2].imshow(overlay_rgb)
    axes[2, 2].set_title("10. Bản đồ Trùng khớp\n■ Vàng: Cả 2 | ■ Lục: NumPy | ■ Đỏ: CV", fontsize=10, fontweight="bold")

    axes[2, 3].imshow(custom_on_raw)
    axes[2, 3].set_title("11. Phủ biên NumPy lên ảnh gốc", fontsize=11, fontweight="bold", color="darkgreen")

    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Segoe UI"]
    plt.rcParams["axes.unicode_minus"] = False

    # Ô thống kê tổng kết
    axes[2, 4].axis("off")
    summary_text = measured_summary_text({
        "Gauss / SciPy": (custom_g, scipy_g), "Gauss / OpenCV": (custom_g, opencv_g),
        "Gradient / SciPy": (grad_custom, grad_scipy), "Laplacian / SciPy": (lap_custom, lap_scipy),
    }, canny_custom, canny_cv)
    axes[2, 4].text(
        0.05, 0.5, summary_text, fontsize=10, family="sans-serif",
        verticalalignment="center", bbox=dict(boxstyle="round,pad=0.6", facecolor="#f0f8ff", edgecolor="#4682b4")
    )

    for i in range(3):
        for j in range(5):
            if not (i == 2 and j == 4):
                axes[i, j].axis("off")

    fig.suptitle(
        "BẢNG SO SÁNH ĐỐI CHUẨN ĐỊNH LƯỢNG: NUMPY CORE (FROM SCRATCH) vs SCIPY & OPENCV",
        fontsize=15, fontweight="heavy", y=0.98
    )

    out_file = ROOT / "outputs" / "comparison_custom_vs_libs.png"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"\n-> Đã xuất ảnh so sánh trực quan 300 DPI ra: {out_file.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', default='data/raw/bsds_01.png')
    parser.add_argument('--sigma', type=float, default=2.0)
    parser.add_argument('--p-low', type=float, default=60.0)
    parser.add_argument('--p-high', type=float, default=85.0)
    args = parser.parse_args()
    DELIVERY.mkdir(parents=True,exist_ok=True)
    manifest = DELIVERY/'comparison_manifest.json'
    snapshot = reference_inputs(args)
    manifest.write_text(json.dumps(dict(status='RUNNING',command=sys.argv,input_code_sha256=snapshot),indent=2),encoding='utf-8')
    try:
        execute(args,snapshot)
    except Exception as exc:
        manifest.write_text(json.dumps(dict(status='ERROR',error=f'{type(exc).__name__}: {exc}',command=sys.argv),indent=2),encoding='utf-8')
        raise


def reference_inputs(args):
    paths=sorted(Path(__file__).parent.glob('*.py'))+sorted((ROOT/'src/core').glob('*.py'))+[ROOT/'src/config.py',ROOT/'config.yaml',ROOT/args.image]
    return {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):sha256(p) for p in paths}


def execute(args,snapshot):
    print("=" * 80)
    print("  KHỞI CHẠY TỔNG HỢP HỆ THỐNG ĐỐI CHUẨN: NUMPY THUẦN vs SCIPY & OPENCV")
    print("=" * 80)

    # Chạy module 1: Gaussian
    print("\n>>> BÀI TEST 1: ĐỐI CHUẨN BỘ LỌC LÀM MỊN GAUSSIAN")
    from benchmarks.reference_comparison.compare_gaussian import run_gaussian_comparison
    gaussian = run_gaussian_comparison(args.image)

    # Chạy module 2: Derivatives & Laplacian
    print("\n>>> BÀI TEST 2: ĐỐI CHUẨN ĐẠO HÀM VI PHÂN (Lx, Ly, Grad, Lxx, Lyy, Lxy, Laplacian)")
    from benchmarks.reference_comparison.compare_derivatives import run_derivatives_comparison
    derivatives = run_derivatives_comparison(args.image, args.sigma)

    # Chạy module 3: Canny
    print("\n>>> BÀI TEST 3: ĐỐI CHUẨN THUẬT TOÁN CANNY EDGE DETECTION")
    from benchmarks.reference_comparison.compare_canny import run_canny_comparison
    canny = run_canny_comparison(args.image, args.sigma, args.p_low, args.p_high)

    # Sinh ảnh đối chiếu
    print("\n>>> BÀI TEST 4: TỰ ĐỘNG XUẤT ẢNH TRỰC QUAN ĐỐI CHIẾU 300 DPI")
    generate_visual_comparison_figure(args.image, args.sigma, args.p_low, args.p_high)
    write_evidence(gaussian, derivatives, canny, args, snapshot)

    print("\n" + "=" * 80)
    print("  HOÀN THÀNH TẤT CẢ CÁC BÀI ĐỐI CHUẨN THAM CHIẾU NGOÀI!")
    print("=" * 80)


def write_evidence(gaussian, derivatives, canny, args, snapshot):
    DELIVERY.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in gaussian:
        for name,key in [('SciPy','metrics_scipy'),('OpenCV','metrics_cv')]:
            rows.append(dict(image=args.image,operator='Gaussian',reference=name,sigma=r['sigma'],
                             scope='same sigma/support/border; observed float64 response',**r[key]))
    for name,r in derivatives.items():
        rows.append(dict(image=args.image,operator=name,reference='SciPy' if 'SciPy' in name else 'OpenCV',sigma=args.sigma,
                         scope='different sampling/moment/support or Sobel operator; not an equivalence acceptance test',**r['metrics']))
    with (DELIVERY/'continuous_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    overlaps=[]
    for variant,key,threshold in [('raw','agreement_raw','opencv_thresholds_raw'),('gaussian_smoothed','agreement_smooth','opencv_thresholds_smooth')]:
        overlaps.append(dict(image=args.image,variant=variant,sigma=args.sigma,p_low=args.p_low,p_high=args.p_high,
                             opencv_low=canny[threshold][0],opencv_high=canny[threshold][1],**canny[key]))
    with (DELIVERY/'canny_mask_agreement.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(overlaps[0]));writer.writeheader();writer.writerows(overlaps)
    lines=['# Đối chiếu thư viện — số đo thực tế','',
           'Bảng đo trên ảnh/scale của phiên chạy; không tự kết luận 100% PASS hoặc bộ lọc nào ưu việt.','',
           '| Toán tử | Tham chiếu | Sigma | Max error | RMSE | Pearson |',
           '| --- | --- | ---: | ---: | ---: | ---: |']
    for row in rows:
        r='N/A' if row['pearson_r'] is None else f"{row['pearson_r']:.8f}"
        lines.append(f"| {row['operator']} | {row['reference']} | {row['sigma']:g} | {row['max_error']:.6g} | {row['rmse']:.6g} | {r} |")
    lines += ['', '## Phạm vi diễn giải','',
              '- Pearson được tính từ mảng. Mảng hằng có Pearson không xác định, không gán r=1.',
              '- Đạo hàm SciPy có thể khác support trục làm mịn và chuẩn hóa moment; Sobel là toán tử khác.',
              '- IoU/Dice của Canny là độ giao giữa hai thuật toán, không phải điểm GT. Phép ánh xạ ngưỡng minh họa cũ được ghi rõ trong CSV.',
              '- Thành phần liên thông đã loại nhãn nền. Ít thành phần hơn không tự chứng minh phát hiện biên tốt hơn.',
              '- Thời gian Gaussian trong console chỉ là thăm dò trung bình 3 lượt; timing bàn giao vẫn dùng bộ 357 case, warm-up và median riêng.',
              '- Kết quả chính thức so với GT nằm trong outputs/metrics/duc_10_11; không trộn với bảng thư viện này.','']
    (DELIVERY/'KET_QUA_DOI_CHIEU.md').write_text('\n'.join(lines),encoding='utf-8')
    if reference_inputs(args)!=snapshot:
        raise ValueError('Reference-comparison input/code changed during computation; rerun before delivery')
    metadata=dict(status='COMPLETE',recorded_at_utc=datetime.now(timezone.utc).isoformat(),command=sys.argv,
                  parameters=vars(args),config=load_config(),
                  continuous_pairs=len(rows),mask_pairs=len(overlaps),
                  components=dict(custom=canny['components_custom'],opencv_smoothed=canny['components_smooth']),
                  packages={name:importlib.metadata.version(name) for name in ('numpy','scipy','opencv-python','matplotlib')},
                  input_code_sha256=snapshot,
                  outputs={str(p.relative_to(ROOT)):sha256(p) for p in [DELIVERY/'continuous_comparison.csv',DELIVERY/'canny_mask_agreement.csv',DELIVERY/'KET_QUA_DOI_CHIEU.md',ROOT/'outputs/comparison_custom_vs_libs.png']})
    (DELIVERY/'comparison_manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'CSV/JSON evidence: {DELIVERY}')


if __name__ == "__main__":
    main()
