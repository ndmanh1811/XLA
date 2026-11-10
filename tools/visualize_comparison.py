"""
visualize_comparison.py - So sánh trực quan: Ảnh Gốc vs Mã Python vs Đáp án Bác sĩ / Chuyên gia
Đã tinh chỉnh:
- Bài toán DRIVE: Áp mặt nạ FOV xói mòn triệt tiêu viền đen bên ngoài, chạy Frangi đa tỷ lệ
                  (sigma=1.0, 1.5, 2.0, 3.0) và phân đoạn nhị phân hiển thị rõ toàn bộ cây mạch máu.
- Bài toán BSDS:  Áp dụng Canny đã sửa hướng NMS chuẩn xác, bắt trọn vẹn toàn bộ đường viền liên tục.
"""

import sys
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from scipy.ndimage import binary_erosion

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.derivatives import compute_derivatives_1st
from src.core.hessian import compute_hessian_matrix, compute_hessian_eigenvalues
from src.core.detectors import detect_canny, detect_ridge

def main():
    print("=" * 65)
    print("  ĐANG TẠO LẠI ẢNH SO SÁNH TRỰC QUAN THỰC TẾ (CHUẨN XÁC CAO)")
    print("=" * 65)
    
    fig, axes = plt.subplots(2, 3, figsize=(16, 11))
    fig.suptitle("SO SÁNH THỰC TẾ: ẢNH GỐC  vs  MÃ PYTHON TỰ TÍNH  vs  ĐÁP ÁN CHUYÊN GIA", fontsize=15, fontweight='bold')
    
    # -------------------------------------------------------------------------
    # HÀNG 1: BÀI TOÁN DÒ MẠCH MÁU MẮT (DRIVE 01)
    # -------------------------------------------------------------------------
    img_drive = np.array(Image.open(ROOT / "data/raw/drive_01.png"), dtype=np.float64) / 255.0
    gt_vessels = np.array(Image.open(ROOT / "data/gt/drive_01_vessels.png")) > 128
    fov_mask = np.array(Image.open(ROOT / "data/gt/drive_01_fov.png")) > 128
    
    # Xói mòn mặt nạ võng mạc để triệt tiêu hoàn toàn viền tròn ngoài nhãn cầu
    eroded_fov = binary_erosion(fov_mask, structure=np.ones((13, 13), bool))
    
    # Chạy Frangi đa tỷ lệ [1.0, 1.5, 2.0, 3.0]
    sigmas_drive = [1.0, 1.5, 2.0, 3.0]
    vessel_max = np.zeros_like(img_drive)
    
    for s in sigmas_drive:
        lxx, lyy, lxy = compute_hessian_matrix(img_drive, sigma=s)
        # Chuẩn hóa gamma=1 (nhân s^2)
        l1, l2 = compute_hessian_eigenvalues((s**2)*lxx, (s**2)*lyy, (s**2)*lxy, sort_order="algebraic")
        v = detect_ridge(l1, l2, sigma=s, beta=0.5, polarity="dark", mask=eroded_fov)
        vessel_max = np.maximum(vessel_max, v)
        
    # Phân đoạn nhị phân cây mạch máu theo ngưỡng phân vị trong vùng võng mạc
    vals_inside = vessel_max[eroded_fov & (vessel_max > 0)]
    t_vessel = np.percentile(vals_inside, 70.0) if len(vals_inside) > 0 else 0.01
    pred_vessel_binary = (vessel_max >= t_vessel) & eroded_fov
    
    # Ô 1: Ảnh gốc
    axes[0, 0].imshow(img_drive, cmap='gray')
    axes[0, 0].set_title("1. ẢNH GỐC ĐẦU VÀO (drive_01.png)\n(Ảnh chụp đáy mắt thật của bệnh nhân)", fontsize=11, fontweight='bold', color='navy')
    axes[0, 0].axis('off')
    
    # Ô 2: Mạch máu Python tìm ra (Tô màu xanh cyan trên nền đen)
    axes[0, 1].imshow(pred_vessel_binary, cmap='gray')
    axes[0, 1].set_title("2. MẠCH MÁU DO MÃ PYTHON TÌM RA\n(Frangi đa tỷ lệ + Triệt tiêu viền ngoài nhãn cầu)", fontsize=11, fontweight='bold', color='darkred')
    axes[0, 1].axis('off')
    
    # Ô 3: Đáp án bác sĩ
    axes[0, 2].imshow(gt_vessels & eroded_fov, cmap='gray')
    axes[0, 2].set_title("3. ĐÁP ÁN CHUẨN CỦA BÁC SĨ (Ground Truth)\n(Do bác sĩ nhãn khoa tự tay ngồi vẽ)", fontsize=11, fontweight='bold', color='darkgreen')
    axes[0, 2].axis('off')
    
    # -------------------------------------------------------------------------
    # HÀNG 2: BÀI TOÁN DÒ BIÊN THIÊN NHIÊN (BSDS 01)
    # -------------------------------------------------------------------------
    img_bsds = np.array(Image.open(ROOT / "data/raw/bsds_01.png"), dtype=np.float64) / 255.0
    gt_bsds = np.load(ROOT / "data/gt/bsds_01_boundaries.npy")
    gt_bsds_union = np.any(gt_bsds > 0, axis=0)
    
    # Chạy Canny ở sigma=1.2 với ngưỡng phân vị chuẩn
    lx, ly = compute_derivatives_1st(img_bsds, sigma=1.2)
    canny_pred = detect_canny(1.2 * lx, 1.2 * ly, p_low=50.0, p_high=80.0)
    
    # Ô 4: Ảnh gốc thiên nhiên
    axes[1, 0].imshow(img_bsds, cmap='gray')
    axes[1, 0].set_title("4. ẢNH GỐC ĐẦU VÀO (bsds_01.png)\n(Ảnh chụp thiên nhiên thực tế)", fontsize=11, fontweight='bold', color='navy')
    axes[1, 0].axis('off')
    
    # Ô 5: Biên Canny Python tìm ra
    axes[1, 1].imshow(canny_pred, cmap='gray')
    axes[1, 1].set_title("5. ĐƯỜNG BIÊN DO MÃ PYTHON TÌM RA\n(Canny NMS đã hiệu chỉnh hướng ma trận + Hysteresis)", fontsize=11, fontweight='bold', color='darkred')
    axes[1, 1].axis('off')
    
    # Ô 6: Đáp án chuyên gia con người
    axes[1, 2].imshow(gt_bsds_union, cmap='gray')
    axes[1, 2].set_title("6. ĐÁP ÁN CHUẨN CON NGƯỜI (Ground Truth)\n(Tổng hợp nét vẽ của 5 chuyên gia gán nhãn)", fontsize=11, fontweight='bold', color='darkgreen')
    axes[1, 2].axis('off')
    
    plt.tight_layout()
    out_path = ROOT / "outputs" / "real_data_comparison.png"
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close()
    
    print(f"\n=> [THÀNH CÔNG] Đã cập nhật ảnh so sánh mới tại: {out_path}")
    print("=" * 65)

if __name__ == "__main__":
    main()
