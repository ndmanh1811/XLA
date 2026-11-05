"""
batch_runner.py - Tự động chạy hàng loạt cho Python Core Engine (Tier 1 & Tier 2)
Xuất toàn bộ bản đồ vi phân chuẩn TIFF 32-bit float vào outputs/python/
theo đúng quy ước đặt tên: py_{tenanh}_{thuattoan}_s{sigma}.tif
"""

import sys
from pathlib import Path
import numpy as np
from PIL import Image
import tifffile

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.config import (
    get_tier1_images,
    get_sigmas,
    get_blob_sigmas,
    get_structure_pairs,
    get_eigen_order,
)
from src.core.derivatives import (
    gaussian_smooth,
    compute_derivatives_1st,
    compute_derivatives_2nd,
    compute_gradient_magnitude,
    compute_laplacian
)
from src.core.hessian import compute_hessian_eigenvalues
from src.core.structure_tensor import (
    compute_structure_tensor,
    compute_structure_tensor_eigenvalues
)

RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "outputs" / "python"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Đọc cấu hình tập trung từ config.yaml (không gõ cứng)
TIER1_IMAGES = get_tier1_images()
SIGMAS_STD = get_sigmas()
SIGMAS_BLOB = get_blob_sigmas()
ST_PAIRS = get_structure_pairs()

def save_tif(path: Path, data: np.ndarray):
    """Lưu mảng 2D thành tệp TIFF 32-bit float không nén."""
    tifffile.imwrite(str(path), data.astype(np.float32))

def process_tier1_image(name: str):
    img_path = RAW_DIR / f"{name}.png"
    if not img_path.exists():
        print(f"   [!] Bỏ qua {name}: chưa có tệp ảnh tại data/raw/{name}.png")
        return
        
    print(f"-> Đang xử lý Tầng 1 cho ảnh: {name}...")
    img = np.array(Image.open(img_path), dtype=np.float64)
    
    # 1. Các bản đồ vi phân ở dãy sigma chuẩn [1.0, 2.0, 4.0, 8.0]
    for s in SIGMAS_STD:
        # Gauss
        g = gaussian_smooth(img, sigma=s)
        save_tif(OUT_DIR / f"py_{name}_gauss_s{s:.1f}.tif", g)
        
        # Lx, Ly
        lx, ly = compute_derivatives_1st(img, sigma=s)
        save_tif(OUT_DIR / f"py_{name}_lx_s{s:.1f}.tif", lx)
        save_tif(OUT_DIR / f"py_{name}_ly_s{s:.1f}.tif", ly)
        
        # Grad
        grad = compute_gradient_magnitude(lx, ly)
        save_tif(OUT_DIR / f"py_{name}_grad_s{s:.1f}.tif", grad)
        
        # Lxx, Lyy, Lxy
        lxx, lyy, lxy = compute_derivatives_2nd(img, sigma=s)
        save_tif(OUT_DIR / f"py_{name}_lxx_s{s:.1f}.tif", lxx)
        save_tif(OUT_DIR / f"py_{name}_lyy_s{s:.1f}.tif", lyy)
        save_tif(OUT_DIR / f"py_{name}_lxy_s{s:.1f}.tif", lxy)
        
        # Laplacian
        lap = compute_laplacian(img, sigma=s)
        save_tif(OUT_DIR / f"py_{name}_lap_s{s:.1f}.tif", lap)
        
        # Hessian eigenvalues theo config
        hl1, hl2 = compute_hessian_eigenvalues(lxx, lyy, lxy, sort_order=get_eigen_order())
        save_tif(OUT_DIR / f"py_{name}_hess-l1_s{s:.1f}.tif", hl1)
        save_tif(OUT_DIR / f"py_{name}_hess-l2_s{s:.1f}.tif", hl2)
        
    # 2. Structure Tensor ở 2 cặp (sigma_d, sigma_i)
    for sd, si in ST_PAIRS:
        j11, j22, j12 = compute_structure_tensor(img, sigma_d=sd, sigma_i=si)
        mu1, mu2 = compute_structure_tensor_eigenvalues(j11, j22, j12)
        save_tif(OUT_DIR / f"py_{name}_st-l1_sd{sd:.1f}_si{si:.1f}.tif", mu1)
        save_tif(OUT_DIR / f"py_{name}_st-l2_sd{sd:.1f}_si{si:.1f}.tif", mu2)
        
    print(f"   ✓ Hoàn tất xuất đầy đủ bản đồ vi phân Tầng 1 cho {name}.")

def main():
    print("=" * 65)
    print("  KHỞI CHẠY BATCH RUNNER: XUẤT CÁC BẢN ĐỒ VI PHÂN TẦNG 1 (PYTHON)")
    print("=" * 65)
    for name in TIER1_IMAGES:
        process_tier1_image(name)
    print("=" * 65)

if __name__ == "__main__":
    main()
