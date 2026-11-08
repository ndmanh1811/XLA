"""
generate_publication_figures.py - Tối ưu hóa chất lượng đồ họa đầu ra
Xuất các biểu đồ và hình ảnh minh họa chất lượng cao chuẩn bài báo IEEE (300 DPI)
cho Báo cáo kỹ thuật và Slide bảo vệ BTL.

Bao gồm:
1. showcase_scientific_diverging_maps.png: Bản đồ vi phân dùng Colormap phân kỳ (Diverging Colormap)
   với mốc 0 ở giữa (Dương: Đỏ, Âm: Xanh, 0: Trắng).
2. showcase_detector_overlays.png: Ảnh phủ màu (Overlay) phát hiện đặc trưng trực quan trên ảnh thật.
3. showcase_multiscale_frangi.png: Minh chứng không gian tỷ lệ (Scale-space) cho mạch máu DRIVE.
"""

import sys
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

from src.core.derivatives import (
    compute_derivatives_1st,
    compute_derivatives_2nd,
    compute_laplacian,
    compute_gradient_magnitude
)
from src.core.hessian import compute_hessian_matrix, compute_hessian_eigenvalues
from src.core.detectors import detect_canny, detect_ridge, detect_blob

def figure_1_diverging_maps():
    """Tạo biểu đồ bản đồ vi phân chuẩn khoa học với colormap seismic đối xứng."""
    img_path = RAW_DIR / "bsds_01.png"
    if not img_path.exists():
        return
    img = np.array(Image.open(img_path), dtype=np.float64) / 255.0
    sigma = 2.0

    lx, ly = compute_derivatives_1st(img, sigma=sigma)
    lxx, lyy, lxy = compute_derivatives_2nd(img, sigma=sigma)
    lap = compute_laplacian(img, sigma=sigma)

    fig, axes = plt.subplots(2, 2, figsize=(10, 8), dpi=200)

    # 1. Lx
    vmax_lx = max(abs(np.percentile(lx, 1)), abs(np.percentile(lx, 99)))
    im0 = axes[0, 0].imshow(lx, cmap="seismic", vmin=-vmax_lx, vmax=vmax_lx)
    axes[0, 0].set_title(r"Đạo hàm riêng ngang $L_x$ ($\sigma=2.0$)", fontsize=11, fontweight="bold")
    axes[0, 0].axis("off")
    fig.colorbar(im0, ax=axes[0, 0], fraction=0.046, pad=0.04)

    # 2. Ly
    vmax_ly = max(abs(np.percentile(ly, 1)), abs(np.percentile(ly, 99)))
    im1 = axes[0, 1].imshow(ly, cmap="seismic", vmin=-vmax_ly, vmax=vmax_ly)
    axes[0, 1].set_title(r"Đạo hàm riêng dọc $L_y$ ($\sigma=2.0$)", fontsize=11, fontweight="bold")
    axes[0, 1].axis("off")
    fig.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)

    # 3. Lxx
    vmax_lxx = max(abs(np.percentile(lxx, 1)), abs(np.percentile(lxx, 99)))
    im2 = axes[1, 0].imshow(lxx, cmap="seismic", vmin=-vmax_lxx, vmax=vmax_lxx)
    axes[1, 0].set_title(r"Đạo hàm cấp hai $L_{xx}$ ($\sigma=2.0$)", fontsize=11, fontweight="bold")
    axes[1, 0].axis("off")
    fig.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.04)

    # 4. Laplacian
    vmax_lap = max(abs(np.percentile(lap, 1)), abs(np.percentile(lap, 99)))
    im3 = axes[1, 1].imshow(lap, cmap="seismic", vmin=-vmax_lap, vmax=vmax_lap)
    axes[1, 1].set_title(r"Toán tử Laplacian $\nabla^2 L$ ($\sigma=2.0$)", fontsize=11, fontweight="bold")
    axes[1, 1].axis("off")
    fig.colorbar(im3, ax=axes[1, 1], fraction=0.046, pad=0.04)

    plt.tight_layout()
    out_file = OUT_DIR / "showcase_scientific_diverging_maps.png"
    plt.savefig(out_file, bbox_inches="tight")
    plt.close()
    print(f"[OK] Xuất biểu đồ vi phân khoa học: {out_file.name}")

def figure_2_detector_overlays():
    """Tạo ảnh overlay màu rực rỡ chứng minh độ chính xác của 3 bộ dò."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), dpi=200)

    # (a) Canny Overlay trên BSDS
    img_b_path = RAW_DIR / "bsds_01.png"
    if img_b_path.exists():
        img_b = np.array(Image.open(img_b_path), dtype=np.float64) / 255.0
        lx, ly = compute_derivatives_1st(img_b, sigma=1.5)
        canny_edges = detect_canny(lx, ly, p_low=55.0, p_high=85.0, return_binary=True)
        
        # Tạo ảnh màu RGB từ ảnh xám
        overlay_b = np.stack([img_b, img_b, img_b], axis=-1)
        # Điểm biên tô màu xanh lá dạ quang (Green: [0, 1, 0])
        overlay_b[canny_edges > 0] = [0.0, 1.0, 0.2]
        axes[0].imshow(overlay_b)
        axes[0].set_title("1. Biên Canny (BSDS500)\nOverlay Xanh lá trên ảnh gốc", fontsize=11, fontweight="bold")
        axes[0].axis("off")

    # (b) Frangi Vessel Overlay trên DRIVE
    img_d_path = RAW_DIR / "drive_01.png"
    if img_d_path.exists():
        img_d = np.array(Image.open(img_d_path), dtype=np.float64) / 255.0
        lxx, lyy, lxy = compute_hessian_matrix(img_d, sigma=1.5)
        l1, l2 = compute_hessian_eigenvalues(lxx, lyy, lxy, sort_order="algebraic")
        vessels = detect_ridge(l1, l2, sigma=1.5, beta=0.5, polarity="dark")
        vessel_mask = vessels > np.percentile(vessels, 88.0)
        
        overlay_d = np.stack([img_d, img_d, img_d], axis=-1)
        # Mạch máu tô màu Cyan dạ quang (Cyan: [0, 1, 1])
        overlay_d[vessel_mask] = [0.0, 0.9, 1.0]
        axes[1].imshow(overlay_d)
        axes[1].set_title("2. Mạch máu Frangi (DRIVE)\nOverlay Cyan dạ quang", fontsize=11, fontweight="bold")
        axes[1].axis("off")

    # (c) LoG Blob Detection Circles
    img_bl_path = RAW_DIR / "blob_01.png"
    if img_bl_path.exists():
        img_bl = np.array(Image.open(img_bl_path), dtype=np.float64) / 255.0
        sigmas_b = [1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0]
        stack = []
        for s in sigmas_b:
            lp = compute_laplacian(img_bl, sigma=s)
            stack.append((s ** 2.0) * lp)
        stack = np.stack(stack, axis=0)
        detected_blobs = detect_blob(stack, sigmas=sigmas_b, polarity="bright", threshold=0.03)

        axes[2].imshow(img_bl, cmap="gray")
        for blob in detected_blobs:
            by, bx, bs, br, bresp = blob
            circle = patches.Circle((bx, by), br, fill=False, edgecolor="yellow", linewidth=2.0)
            axes[2].add_patch(circle)
            axes[2].plot(bx, by, "r+", markersize=6)
            
        axes[2].set_title(f"3. Đốm LoG Scale-Space (Blobs)\nKhớp {len(detected_blobs)} đốm đa bán kính", fontsize=11, fontweight="bold")
        axes[2].axis("off")

    plt.tight_layout()
    out_file = OUT_DIR / "showcase_detector_overlays.png"
    plt.savefig(out_file, bbox_inches="tight")
    plt.close()
    print(f"[OK] Xuất ảnh phủ màu phát hiện đặc trưng: {out_file.name}")

def figure_3_multiscale_vessels():
    """Minh họa tác động của không gian tỷ lệ sigma lên bộ lọc Frangi."""
    img_path = RAW_DIR / "drive_01.png"
    if not img_path.exists():
        return
    img = np.array(Image.open(img_path), dtype=np.float64) / 255.0
    sigmas = [1.0, 2.0, 3.0, 4.0]

    fig, axes = plt.subplots(1, 4, figsize=(16, 4), dpi=200)

    for i, s in enumerate(sigmas):
        lxx, lyy, lxy = compute_hessian_matrix(img, sigma=s)
        lxx_norm = (s ** 2.0) * lxx
        lyy_norm = (s ** 2.0) * lyy
        lxy_norm = (s ** 2.0) * lxy
        l1, l2 = compute_hessian_eigenvalues(lxx_norm, lyy_norm, lxy_norm, sort_order="algebraic")
        v = detect_ridge(l1, l2, sigma=s, beta=0.5, polarity="dark")

        axes[i].imshow(v, cmap="hot")
        axes[i].set_title(rf"$\sigma = {s:.1f}$" + f"\n({ 'Mao mạch nhỏ' if s <= 1.5 else ('Thân mạch vừa' if s <= 2.5 else 'Thân mạch lớn') })", fontsize=10, fontweight="bold")
        axes[i].axis("off")

    plt.suptitle("Phân tích không gian tỷ lệ (Scale-space) trên mạch máu võng mạc bằng bộ lọc Frangi", fontsize=13, fontweight="bold", y=1.05)
    plt.tight_layout()
    out_file = OUT_DIR / "showcase_multiscale_frangi.png"
    plt.savefig(out_file, bbox_inches="tight")
    plt.close()
    print(f"[OK] Xuất biểu đồ Frangi đa tỷ lệ: {out_file.name}")

def main():
    print("=" * 65)
    print("  KẾT XUẤT BỘ HÌNH ẢNH MINH HỌA KHOA HỌC CHUẨN IEEE (300 DPI)")
    print("=" * 65)
    figure_1_diverging_maps()
    figure_2_detector_overlays()
    figure_3_multiscale_vessels()
    print("=" * 65)
    print("  HOÀN TẤT XUẤT 3 TỆP ĐỒ HỌA CHẤT LƯỢNG CAO TRONG outputs/!")
    print("=" * 65)

if __name__ == "__main__":
    main()
