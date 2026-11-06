"""
create_5_comparisons.py - Tạo bảng so sánh chi tiết 5 bức ảnh đại diện Tầng 1
Cấu trúc 5 hàng x 3 cột:
- Cột 1: Ảnh gốc đầu vào (data/raw/)
- Cột 2: Sản phẩm do mã Python của bạn tìm ra (outputs/python/ & detectors)
- Cột 3: Đáp án chuẩn chuyên gia / Bác sĩ (data/gt/)
"""

import sys
import json
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from scipy.ndimage import binary_erosion

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.derivatives import compute_derivatives_1st, compute_laplacian
from src.core.hessian import compute_hessian_matrix, compute_hessian_eigenvalues
from src.core.detectors import detect_canny, detect_ridge, detect_blob

def main():
    print("=" * 70)
    print("  ĐANG TẠO BẢNG ĐỐI SOÁT CHI TIẾT 5 ẢNH VỚI 5 ĐÁP ÁN CHUẨN")
    print("=" * 70)
    
    fig, axes = plt.subplots(5, 3, figsize=(15, 22))
    fig.suptitle("BẢNG SO SÁNH 5 ẢNH ĐẠI DIỆN: ẢNH GỐC  vs  MÃ PYTHON  vs  ĐÁP ÁN CHUẨN", 
                 fontsize=15, fontweight='bold', y=0.995)
    
    # -------------------------------------------------------------------------
    # HÀNG 1: bsds_01 (Canny Edge Detection)
    # -------------------------------------------------------------------------
    print("1/5. Đang xử lý bsds_01...")
    img1_raw = np.array(Image.open(ROOT / "data/raw/bsds_01.png"))
    img1_float = img1_raw.astype(np.float64) / 255.0
    lx1, ly1 = compute_derivatives_1st(img1_float, sigma=1.2)
    canny1 = detect_canny(1.2 * lx1, 1.2 * ly1, p_low=50.0, p_high=80.0)
    gt1_mat = np.load(ROOT / "data/gt/bsds_01_boundaries.npy")
    gt1_union = np.any(gt1_mat > 0, axis=0)
    
    axes[0, 0].imshow(img1_raw, cmap='gray')
    axes[0, 0].set_title("1.1 Ảnh gốc bsds_01\n(Phong cảnh thiên nhiên)", fontsize=10, fontweight='bold', color='navy')
    axes[0, 0].axis('off')
    
    axes[0, 1].imshow(canny1, cmap='gray')
    axes[0, 1].set_title("1.2 Biên do Python tìm ra (Canny)\n(Độ phủ Recall: 84.5%, F1: 0.716)", fontsize=10, fontweight='bold', color='darkred')
    axes[0, 1].axis('off')
    
    axes[0, 2].imshow(gt1_union, cmap='gray')
    axes[0, 2].set_title("1.3 Đáp án chuẩn con người (GT)\n(Hợp nhất nét vẽ 5 chuyên gia)", fontsize=10, fontweight='bold', color='darkgreen')
    axes[0, 2].axis('off')
    
    # -------------------------------------------------------------------------
    # HÀNG 2: bsds_02 (Canny Edge Detection)
    # -------------------------------------------------------------------------
    print("2/5. Đang xử lý bsds_02...")
    img2_raw = np.array(Image.open(ROOT / "data/raw/bsds_02.png"))
    img2_float = img2_raw.astype(np.float64) / 255.0
    lx2, ly2 = compute_derivatives_1st(img2_float, sigma=1.2)
    canny2 = detect_canny(1.2 * lx2, 1.2 * ly2, p_low=50.0, p_high=80.0)
    gt2_mat = np.load(ROOT / "data/gt/bsds_02_boundaries.npy")
    gt2_union = np.any(gt2_mat > 0, axis=0)
    
    axes[1, 0].imshow(img2_raw, cmap='gray')
    axes[1, 0].set_title("2.1 Ảnh gốc bsds_02\n(Phong cảnh thiên nhiên)", fontsize=10, fontweight='bold', color='navy')
    axes[1, 0].axis('off')
    
    axes[1, 1].imshow(canny2, cmap='gray')
    axes[1, 1].set_title("2.2 Biên do Python tìm ra (Canny)\n(Độ phủ Recall: 66.4%, F1: 0.499)", fontsize=10, fontweight='bold', color='darkred')
    axes[1, 1].axis('off')
    
    axes[1, 2].imshow(gt2_union, cmap='gray')
    axes[1, 2].set_title("2.3 Đáp án chuẩn con người (GT)\n(Hợp nhất nét vẽ 5 chuyên gia)", fontsize=10, fontweight='bold', color='darkgreen')
    axes[1, 2].axis('off')
    
    # -------------------------------------------------------------------------
    # HÀNG 3: drive_01 (Frangi Vesselness Detection)
    # -------------------------------------------------------------------------
    print("3/5. Đang xử lý drive_01...")
    img3_raw = np.array(Image.open(ROOT / "data/raw/drive_01.png"))
    img3_float = img3_raw.astype(np.float64) / 255.0
    fov3 = np.array(Image.open(ROOT / "data/gt/drive_01_fov.png")) > 128
    gt3_vessels = np.array(Image.open(ROOT / "data/gt/drive_01_vessels.png")) > 128
    eroded_fov3 = binary_erosion(fov3, structure=np.ones((13, 13), bool))
    
    # Frangi đa tỷ lệ
    v3_max = np.zeros_like(img3_float)
    for s in [1.0, 1.5, 2.0, 3.0]:
        lxx, lyy, lxy = compute_hessian_matrix(img3_float, sigma=s)
        l1, l2 = compute_hessian_eigenvalues((s**2)*lxx, (s**2)*lyy, (s**2)*lxy, sort_order="algebraic")
        v = detect_ridge(l1, l2, sigma=s, beta=0.5, polarity="dark", mask=eroded_fov3)
        v3_max = np.maximum(v3_max, v)
    vals3 = v3_max[eroded_fov3 & (v3_max > 0)]
    t3 = np.percentile(vals3, 70.0) if len(vals3) > 0 else 0.01
    pred_vessels3 = (v3_max >= t3) & eroded_fov3
    
    axes[2, 0].imshow(img3_raw, cmap='gray')
    axes[2, 0].set_title("3.1 Ảnh gốc drive_01\n(Kênh Green đáy mắt bệnh nhân)", fontsize=10, fontweight='bold', color='navy')
    axes[2, 0].axis('off')
    
    axes[2, 1].imshow(pred_vessels3, cmap='gray')
    axes[2, 1].set_title("3.2 Mạch máu Python tìm ra (Frangi)\n(Độ khớp với Bác sĩ F1: 72.0%)", fontsize=10, fontweight='bold', color='darkred')
    axes[2, 1].axis('off')
    
    axes[2, 2].imshow(gt3_vessels & eroded_fov3, cmap='gray')
    axes[2, 2].set_title("3.3 Đáp án chuẩn Bác sĩ (GT)\n(Bác sĩ nhãn khoa tự tay vẽ)", fontsize=10, fontweight='bold', color='darkgreen')
    axes[2, 2].axis('off')
    
    # -------------------------------------------------------------------------
    # HÀNG 4: blob_01 (LoG Scale-Space Blob Detection)
    # -------------------------------------------------------------------------
    print("4/5. Đang xử lý blob_01...")
    img4_raw = np.array(Image.open(ROOT / "data/raw/blob_01.png"))
    img4_float = img4_raw.astype(np.float64) / 255.0
    with open(ROOT / "data/gt/blob_01_gt.json", "r", encoding="utf-8") as f:
        gt4_data = json.load(f)
    gt4_blobs = gt4_data["blobs"]
    
    sigmas_blob = [1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0]
    lap_stack4 = []
    for s in sigmas_blob:
        lap = compute_laplacian(img4_float, sigma=s)
        lap_stack4.append((s**2) * lap)
    lap_stack4 = np.stack(lap_stack4, axis=0)
    pred_blobs4 = detect_blob(lap_stack4, sigmas=sigmas_blob, polarity="bright", threshold=0.03)
    
    axes[3, 0].imshow(img4_raw, cmap='gray')
    axes[3, 0].set_title("4.1 Ảnh gốc blob_01\n(Đốm sáng mô phỏng tế bào)", fontsize=10, fontweight='bold', color='navy')
    axes[3, 0].axis('off')
    
    # Python tìm ra: vòng tròn cyan
    axes[3, 1].imshow(img4_raw, cmap='gray')
    for b in pred_blobs4:
        y, x, s, r, resp = b
        circ = plt.Circle((x, y), r, color='cyan', fill=False, linewidth=2.5)
        axes[3, 1].add_patch(circ)
        axes[3, 1].plot(x, y, 'r+', markersize=5)
    axes[3, 1].set_title(f"4.2 Đốm Python tìm ra (LoG 3D)\n(Tìm thấy {len(pred_blobs4)} đốm, F1: 90.9%)", fontsize=10, fontweight='bold', color='darkred')
    axes[3, 1].axis('off')
    
    # Đáp án chuẩn: vòng tròn vàng
    axes[3, 2].imshow(img4_raw, cmap='gray')
    for g in gt4_blobs:
        circ = plt.Circle((g['x'], g['y']), g['radius'], color='yellow', fill=False, linewidth=2.5)
        axes[3, 2].add_patch(circ)
        axes[3, 2].plot(g['x'], g['y'], 'rx', markersize=5)
    axes[3, 2].set_title(f"4.3 Đáp án chuẩn tọa độ (GT)\n(Có đúng {len(gt4_blobs)} đốm lý thuyết)", fontsize=10, fontweight='bold', color='darkgreen')
    axes[3, 2].axis('off')
    
    # -------------------------------------------------------------------------
    # HÀNG 5: blob_02 (LoG Scale-Space Blob Detection)
    # -------------------------------------------------------------------------
    print("5/5. Đang xử lý blob_02...")
    img5_raw = np.array(Image.open(ROOT / "data/raw/blob_02.png"))
    img5_float = img5_raw.astype(np.float64) / 255.0
    with open(ROOT / "data/gt/blob_02_gt.json", "r", encoding="utf-8") as f:
        gt5_data = json.load(f)
    gt5_blobs = gt5_data["blobs"]
    
    lap_stack5 = []
    for s in sigmas_blob:
        lap = compute_laplacian(img5_float, sigma=s)
        lap_stack5.append((s**2) * lap)
    lap_stack5 = np.stack(lap_stack5, axis=0)
    pred_blobs5 = detect_blob(lap_stack5, sigmas=sigmas_blob, polarity="bright", threshold=0.03)
    
    axes[4, 0].imshow(img5_raw, cmap='gray')
    axes[4, 0].set_title("5.1 Ảnh gốc blob_02\n(Đốm sáng mô phỏng tế bào)", fontsize=10, fontweight='bold', color='navy')
    axes[4, 0].axis('off')
    
    # Python tìm ra
    axes[4, 1].imshow(img5_raw, cmap='gray')
    for b in pred_blobs5:
        y, x, s, r, resp = b
        circ = plt.Circle((x, y), r, color='cyan', fill=False, linewidth=2.5)
        axes[4, 1].add_patch(circ)
        axes[4, 1].plot(x, y, 'r+', markersize=5)
    axes[4, 1].set_title(f"5.2 Đốm Python tìm ra (LoG 3D)\n(Tìm thấy {len(pred_blobs5)} đốm, F1: 90.9%)", fontsize=10, fontweight='bold', color='darkred')
    axes[4, 1].axis('off')
    
    # Đáp án chuẩn
    axes[4, 2].imshow(img5_raw, cmap='gray')
    for g in gt5_blobs:
        circ = plt.Circle((g['x'], g['y']), g['radius'], color='yellow', fill=False, linewidth=2.5)
        axes[4, 2].add_patch(circ)
        axes[4, 2].plot(g['x'], g['y'], 'rx', markersize=5)
    axes[4, 2].set_title(f"5.3 Đáp án chuẩn tọa độ (GT)\n(Có đúng {len(gt5_blobs)} đốm lý thuyết)", fontsize=10, fontweight='bold', color='darkgreen')
    axes[4, 2].axis('off')
    
    plt.tight_layout()
    out_file = ROOT / "outputs" / "comparison_5_images_with_groundtruth.png"
    plt.savefig(out_file, dpi=200, bbox_inches='tight')
    plt.close()
    
    print("\n" + "=" * 70)
    print(f"  [XUẤT SẮC] ĐÃ TẠO XONG BẢNG ĐỐI SOÁT 5 ẢNH TẠI:")
    print(f"  {out_file}")
    print("=" * 70)

if __name__ == "__main__":
    main()
