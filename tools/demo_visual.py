"""
demo_visual.py - Minh họa trực quan các thuật toán trích xuất đặc trưng
Dành cho: Nguyễn Đức Mạnh (Role 2)
Mục đích: Chạy thử toàn bộ các bộ dò đặc trưng (Canny, Frangi, LoG Blob)
          trên một ảnh tổng hợp và xuất biểu đồ trực quan hóa.
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# Đảm bảo in tiếng Việt chuẩn
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Thêm thư mục gốc vào path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.derivatives import (
    compute_derivatives_1st,
    compute_gradient_magnitude,
    compute_laplacian
)
from src.core.hessian import compute_hessian_matrix, compute_hessian_eigenvalues
from src.core.detectors import detect_canny, detect_ridge, detect_blob

def create_synthetic_scene(size=256):
    """Tạo ảnh tổng hợp chứa biên sắc nhọn, cấu trúc dạng mạch/ống và đốm tròn."""
    img = np.zeros((size, size), dtype=np.float64)
    y, x = np.ogrid[:size, :size]
    
    # 1. Khối hộp chữ nhật (để test Canny Edge)
    box = (y >= 40) & (y <= 110) & (x >= 30) & (x <= 100)
    img[box] = 0.8
    
    # 2. Cấu trúc ống / mạch máu cong (để test Frangi Vesselness)
    curve_y = 180 + 30 * np.sin(x[0] / 30.0)
    vessel_mask = np.abs(y - curve_y) <= 3
    img[vessel_mask] = 1.0
    
    # Đường nhánh phụ
    branch_mask = (x >= 140) & (x <= 200) & (np.abs(y - (180 - (x - 140) * 0.8)) <= 2.5)
    img[branch_mask] = 0.9

    # 3. Các đốm Gaussian đa bán kính (để test Blob LoG)
    # Đốm nhỏ r=3 (sigma ≈ 2.1)
    d2_small = (x - 180)**2 + (y - 60)**2
    img += 0.8 * np.exp(-d2_small / (2 * (3.0**2)))
    
    # Đốm vừa r=6 (sigma ≈ 4.2)
    d2_med = (x - 220)**2 + (y - 100)**2
    img += 0.9 * np.exp(-d2_med / (2 * (6.0**2)))
    
    # Đốm lớn r=10 (sigma ≈ 7.0)
    d2_large = (x - 70)**2 + (y - 190)**2
    img += 1.0 * np.exp(-d2_large / (2 * (10.0**2)))
    
    # Thêm một chút nhiễu nhẹ
    rng = np.random.default_rng(42)
    img += rng.normal(0, 0.015, img.shape)
    
    return np.clip(img, 0.0, 1.0)

def main():
    print("=" * 65)
    print("  KHỞI CHẠY VISUAL DEMO: ĐỘNG CƠ TRÍCH XUẤT ĐẶC TRƯNG PYTHON CORE")
    print("=" * 65)
    
    # 1. Sinh ảnh thử nghiệm
    print("1. Đang tạo ảnh tổng hợp mẫu (gồm hộp cạnh, mạch máu, và đốm)...")
    img = create_synthetic_scene(256)
    
    # 2. Chạy Canny Edge Detection (sigma = 1.5)
    print("2. Đang chạy Canny Edge Detector (sigma=1.5, p_low=70, p_high=90)...")
    lx, ly = compute_derivatives_1st(img, sigma=1.5)
    canny_mask = detect_canny(lx, ly, p_low=70.0, p_high=90.0)
    grad_mag = compute_gradient_magnitude(lx, ly)
    
    # 3. Chạy Frangi Vesselness qua Hessian (sigma = 2.0, chuẩn hóa gamma=1)
    print("3. Đang chạy Frangi Vesselness Detector (sigma=2.0, lọc cấu trúc sáng)...")
    lxx, lyy, lxy = compute_hessian_matrix(img, sigma=2.0)
    # Chuẩn hóa gamma=1 cho Hessian: nhân sigma^2
    lxx_norm = (2.0 ** 2) * lxx
    lyy_norm = (2.0 ** 2) * lyy
    lxy_norm = (2.0 ** 2) * lxy
    h_l1, h_l2 = compute_hessian_eigenvalues(lxx_norm, lyy_norm, lxy_norm, sort_order='algebraic')
    vessel_map = detect_ridge(h_l1, h_l2, sigma=2.0, beta=0.5, polarity='bright')
    
    # 4. Chạy LoG Blob Detection (sigma_list = 1.0 -> 11.3)
    print("4. Đang chạy LoG Blob Detector đa tỷ lệ (dò đốm sáng)...")
    sigmas_blob = [1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0, 11.3]
    lap_stack = []
    for s in sigmas_blob:
        lap = compute_laplacian(img, sigma=s)
        # Chuẩn hóa gamma=1: nhân s^2
        lap_norm = (s ** 2) * lap
        lap_stack.append(lap_norm)
    lap_stack = np.stack(lap_stack, axis=0)
    
    blobs = detect_blob(lap_stack, sigmas=sigmas_blob, polarity='bright', threshold=0.03)
    print(f"   => Tìm thấy {len(blobs)} đốm đa tỷ lệ:")
    for b in blobs:
        y, x, s, r, resp = b
        print(f"      - Đốm tại (y={y}, x={x}), sigma={s:.1f}, bán kính r={r:.1f}px (đáp ứng={resp:.3f})")
        
    # 5. Vẽ đồ họa trực quan 2x3
    print("5. Đang kết xuất hình ảnh trực quan...")
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle("DEMO TRÍCH XUẤT ĐẶC TRƯNG ĐA TỶ LỆ - PYTHON CORE ENGINE (NGUYỄN ĐỨC MẠNH)", fontsize=14, fontweight='bold')
    
    # Ô 1: Ảnh gốc
    axes[0, 0].imshow(img, cmap='gray')
    axes[0, 0].set_title("1. Ảnh gốc thử nghiệm (Synthetic)")
    axes[0, 0].axis('off')
    
    # Ô 2: Độ lớn Gradient
    axes[0, 1].imshow(grad_mag, cmap='inferno')
    axes[0, 1].set_title("2. Độ lớn Gradient (σ = 1.5)")
    axes[0, 1].axis('off')
    
    # Ô 3: Canny Edge Detection
    axes[0, 2].imshow(canny_mask, cmap='gray')
    axes[0, 2].set_title("3. Dò biên Canny (p_low=70%, p_high=90%)")
    axes[0, 2].axis('off')
    
    # Ô 4: Frangi Vesselness
    axes[1, 0].imshow(vessel_map, cmap='magma')
    axes[1, 0].set_title("4. Frangi Vesselness (Lọc mạch sáng)")
    axes[1, 0].axis('off')
    
    # Ô 5: Dò đốm LoG Scale-Space
    axes[1, 1].imshow(img, cmap='gray')
    for b in blobs:
        y, x, s, r, resp = b
        circ = plt.Circle((x, y), r, color='cyan', fill=False, linewidth=2)
        axes[1, 1].add_patch(circ)
        axes[1, 1].plot(x, y, 'r+', markersize=6)
    axes[1, 1].set_title(f"5. Dò đốm LoG Scale-Space ({len(blobs)} đốm phát hiện)")
    axes[1, 1].axis('off')
    
    # Ô 6: Ghép tổng hợp các đặc trưng
    composite = np.zeros((*img.shape, 3), dtype=np.float64)
    composite[..., 0] = (canny_mask > 0).astype(float)        # Đỏ: Biên Canny
    composite[..., 1] = vessel_map / (vessel_map.max() + 1e-6) # Xanh lá: Mạch Frangi
    axes[1, 2].imshow(composite)
    for b in blobs:
        y, x, s, r, resp = b
        circ = plt.Circle((x, y), r, color='yellow', fill=False, linewidth=2)
        axes[1, 2].add_patch(circ)
    axes[1, 2].set_title("6. Tổng hợp: Đỏ (Biên), Lục (Mạch), Vàng (Đốm)")
    axes[1, 2].axis('off')
    
    plt.tight_layout()
    
    output_dir = ROOT / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "demo_features.png"
    plt.savefig(out_file, dpi=200, bbox_inches='tight')
    plt.close()
    
    print(f"\n=> [THÀNH CÔNG] Đã lưu kết quả trực quan tại: {out_file}")
    print("=" * 65)

if __name__ == "__main__":
    main()
