"""
batch_runner.py - Tự động chạy hàng loạt cho Python Core Engine (Tier 1 & Tier 2)
Xuất toàn bộ bản đồ vi phân chuẩn TIFF 32-bit float vào outputs/python/
theo đúng quy ước đặt tên: py_{tenanh}_{thuattoan}_s{sigma}.tif

Hỗ trợ:
- Tier 1: 5 ảnh đại diện (bsds_01, bsds_02, drive_01, blob_01, blob_02) với toàn bộ 11 toán tử.
- Tier 2:
    + 10 ảnh BSDS: Lx, Ly, Grad tại các sigma [1.0, 2.0, 4.0, 8.0]
    + 10 ảnh DRIVE: Hessian L1, L2 tại các sigma [1.0, 2.0, 4.0, 8.0]
    + 5 ảnh Blob: Laplacian tại lưới dày 7 sigma [1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0]
"""

import sys
import argparse
import time
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

TIER1_IMAGES = get_tier1_images()
SIGMAS_STD = get_sigmas()
SIGMAS_BLOB = get_blob_sigmas()
ST_PAIRS = get_structure_pairs()
EIGEN_ORDER = get_eigen_order()

def save_tif(path: Path, data: np.ndarray):
    """Lưu mảng 2D thành tệp TIFF 32-bit float không nén."""
    tifffile.imwrite(str(path), data.astype(np.float32))

def process_tier1_image(name: str):
    """Xuất đầy đủ 11 bản đồ vi phân Tầng 1 cho ảnh đại diện."""
    img_path = RAW_DIR / f"{name}.png"
    if not img_path.exists():
        print(f"   [!] Bỏ qua {name}: chưa có tệp ảnh tại data/raw/{name}.png")
        return
        
    print(f"-> [Tier 1] Đang xử lý: {name}...")
    img = np.array(Image.open(img_path), dtype=np.float64)
    
    for s in SIGMAS_STD:
        g = gaussian_smooth(img, sigma=s)
        save_tif(OUT_DIR / f"py_{name}_gauss_s{s:.1f}.tif", g)
        
        lx, ly = compute_derivatives_1st(img, sigma=s)
        save_tif(OUT_DIR / f"py_{name}_lx_s{s:.1f}.tif", lx)
        save_tif(OUT_DIR / f"py_{name}_ly_s{s:.1f}.tif", ly)
        
        grad = compute_gradient_magnitude(lx, ly)
        save_tif(OUT_DIR / f"py_{name}_grad_s{s:.1f}.tif", grad)
        
        lxx, lyy, lxy = compute_derivatives_2nd(img, sigma=s)
        save_tif(OUT_DIR / f"py_{name}_lxx_s{s:.1f}.tif", lxx)
        save_tif(OUT_DIR / f"py_{name}_lyy_s{s:.1f}.tif", lyy)
        save_tif(OUT_DIR / f"py_{name}_lxy_s{s:.1f}.tif", lxy)
        
        lap = compute_laplacian(img, sigma=s)
        save_tif(OUT_DIR / f"py_{name}_lap_s{s:.1f}.tif", lap)
        
        hl1, hl2 = compute_hessian_eigenvalues(lxx, lyy, lxy, sort_order=EIGEN_ORDER)
        save_tif(OUT_DIR / f"py_{name}_hess-l1_s{s:.1f}.tif", hl1)
        save_tif(OUT_DIR / f"py_{name}_hess-l2_s{s:.1f}.tif", hl2)
        
    for sd, si in ST_PAIRS:
        j11, j22, j12 = compute_structure_tensor(img, sigma_d=sd, sigma_i=si)
        mu1, mu2 = compute_structure_tensor_eigenvalues(j11, j22, j12)
        save_tif(OUT_DIR / f"py_{name}_st-l1_sd{sd:.1f}_si{si:.1f}.tif", mu1)
        save_tif(OUT_DIR / f"py_{name}_st-l2_sd{sd:.1f}_si{si:.1f}.tif", mu2)

def process_tier2():
    """Xuất các bản đồ cần thiết phục vụ đánh giá Tầng 2 trên toàn bộ 25 ảnh."""
    print("-> [Tier 2] Đang xử lý các tập ảnh BSDS, DRIVE, Blobs...")
    
    # 1. 10 ảnh BSDS: cần Lx, Ly, Grad tại các sigma chuẩn
    for i in range(1, 11):
        name = f"bsds_{i:02d}"
        img_path = RAW_DIR / f"{name}.png"
        if not img_path.exists(): continue
        img = np.array(Image.open(img_path), dtype=np.float64)
        for s in SIGMAS_STD:
            lx, ly = compute_derivatives_1st(img, sigma=s)
            grad = compute_gradient_magnitude(lx, ly)
            save_tif(OUT_DIR / f"py_{name}_lx_s{s:.1f}.tif", lx)
            save_tif(OUT_DIR / f"py_{name}_ly_s{s:.1f}.tif", ly)
            save_tif(OUT_DIR / f"py_{name}_grad_s{s:.1f}.tif", grad)
    print("   ✓ Hoàn tất 10 ảnh BSDS (Lx, Ly, Grad).")

    # 2. 10 ảnh DRIVE: cần Hessian L1, L2 tại các sigma chuẩn
    for i in range(1, 11):
        name = f"drive_{i:02d}"
        img_path = RAW_DIR / f"{name}.png"
        if not img_path.exists(): continue
        img = np.array(Image.open(img_path), dtype=np.float64)
        for s in SIGMAS_STD:
            lxx, lyy, lxy = compute_derivatives_2nd(img, sigma=s)
            hl1, hl2 = compute_hessian_eigenvalues(lxx, lyy, lxy, sort_order=EIGEN_ORDER)
            save_tif(OUT_DIR / f"py_{name}_hess-l1_s{s:.1f}.tif", hl1)
            save_tif(OUT_DIR / f"py_{name}_hess-l2_s{s:.1f}.tif", hl2)
    print("   ✓ Hoàn tất 10 ảnh DRIVE (Hessian L1, L2).")

    # 3. 5 ảnh Blob: cần Laplacian tại lưới dày 7 sigma
    for i in range(1, 6):
        name = f"blob_{i:02d}"
        img_path = RAW_DIR / f"{name}.png"
        if not img_path.exists(): continue
        img = np.array(Image.open(img_path), dtype=np.float64)
        for s in SIGMAS_BLOB:
            lap = compute_laplacian(img, sigma=s)
            save_tif(OUT_DIR / f"py_{name}_lap_s{s:.1f}.tif", lap)
    print("   ✓ Hoàn tất 5 ảnh Blob (Laplacian tại 7 sigma).")

def main():
    parser = argparse.ArgumentParser(description="Batch Runner cho Python Core Engine")
    parser.add_argument("--tier1", action="store_true", help="Chỉ chạy Tầng 1 (5 ảnh đại diện)")
    parser.add_argument("--tier2", action="store_true", help="Chỉ chạy Tầng 2 (25 ảnh)")
    args = parser.parse_args()

    run_all = not args.tier1 and not args.tier2

    t0 = time.time()
    print("=" * 70)
    print("  KHỞI CHẠY BATCH RUNNER: XUẤT CÁC BẢN ĐỒ VI PHÂN (PYTHON ENGINE)")
    print("=" * 70)

    if run_all or args.tier1:
        print("\n--- BẮT ĐẦU TẦNG 1 (5 ảnh đại diện) ---")
        for name in TIER1_IMAGES:
            process_tier1_image(name)

    if run_all or args.tier2:
        print("\n--- BẮT ĐẦU TẦNG 2 (25 ảnh) ---")
        process_tier2()

    t1 = time.time()
    print("=" * 70)
    print(f"  HOÀN TẤT XUẤT TOÀN BỘ BẢN ĐỒ trong {t1 - t0:.2f} giây!")
    print(f"  Thư mục đầu ra: {OUT_DIR}")
    print("=" * 70)

if __name__ == "__main__":
    main()
