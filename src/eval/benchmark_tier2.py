"""
benchmark_tier2.py - Đánh giá định lượng Tầng 2 (So sánh với Ground Truth thực tế)
Nhiệm vụ của: Bùi Trung Đức (Role 1)
Áp dụng trực tiếp các bộ dò do Nguyễn Đức Mạnh (Role 2) lập trình:
- Bài toán 1 (Edge - BSDS500): Dò biên Canny đa tỷ lệ, so sánh dung sai 2px với đa annotator.
- Bài toán 2 (Ridge - DRIVE): Dò mạch máu Frangi qua Hessian, áp mặt nạ FOV xói mòn, tính F1/IoU.
- Bài toán 3 (Blob - Đốm đa tỷ lệ): Dò cực trị LoG 3D scale-space, khớp tâm <= 2px & bán kính <= 20%.
"""

import sys
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, binary_erosion

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.core.derivatives import compute_derivatives_1st, compute_laplacian
from src.core.hessian import compute_hessian_matrix, compute_hessian_eigenvalues
from src.core.detectors import detect_canny, detect_ridge, detect_blob
from src.config import get_eigen_order, get_sigmas, get_blob_sigmas

RAW_DIR = ROOT / "data" / "raw"
GT_DIR = ROOT / "data" / "gt"

def evaluate_bsds_edges(sample_limit=3):
    """Đánh giá Canny Edge Detection trên ảnh BSDS500 so với Ground Truth đa annotator."""
    print("\n" + "=" * 65)
    print("  1. BENCHMARK BÀI TOÁN DÒ BIÊN (BSDS500 - CANNY EDGE DETECTION)")
    print("=" * 65)
    
    results = []
    # Lấy các ảnh bsds
    bsds_files = sorted(list(RAW_DIR.glob("bsds_*.png")))[:sample_limit]
    if not bsds_files:
        print("   [!] Chưa tìm thấy ảnh bsds_*.png trong data/raw/")
        return
        
    for img_path in bsds_files:
        stem = img_path.stem
        # Ưu tiên đọc từ cấu trúc chuẩn data/gt/bsds/{stem}/annotator_*_boundaries.png của Đức
        annotator_files = sorted(list((GT_DIR / "bsds" / stem).glob("annotator_*_boundaries.png")))
        if annotator_files:
            gt_boundaries = np.stack([np.array(Image.open(f)) > 0 for f in annotator_files], axis=0)
        elif (GT_DIR / f"{stem}_boundaries.npy").exists():
            gt_boundaries = np.load(GT_DIR / f"{stem}_boundaries.npy")
        else:
            continue
        # Giữ nguyên dải float64 0-255 theo chuẩn quy ước INSTRUCTIONS
        img = np.array(Image.open(img_path), dtype=np.float64)
        
        # Chạy Canny ở tỷ lệ σ = 2.0 từ config (chuẩn hóa gamma=1: gradient * sigma^1)
        sigmas_available = get_sigmas()
        sigma = 2.0 if 2.0 in sigmas_available else sigmas_available[min(1, len(sigmas_available) - 1)]
        lx, ly = compute_derivatives_1st(img, sigma=sigma)
        # Chuẩn hóa Lindeberg gamma=1
        lx_norm = (sigma ** 1.0) * lx
        ly_norm = (sigma ** 1.0) * ly
        
        # Dò biên Canny
        pred_edge_binary = detect_canny(lx_norm, ly_norm, p_low=60.0, p_high=85.0, return_binary=False)
        
        # Dung sai biên 2 px: giãn nở biên 2 lần
        struct_2px = np.ones((5, 5), dtype=bool)
        
        # Precision: Tỉ lệ pixel dự đoán nằm trong bán kính 2px của ít nhất 1 annotator
        union_gt = np.any(gt_boundaries > 0, axis=0)
        dilated_union_gt = binary_dilation(union_gt, structure=struct_2px)
        
        pred_positive = np.sum(pred_edge_binary)
        if pred_positive > 0:
            true_positives = np.sum(pred_edge_binary & dilated_union_gt)
            precision = true_positives / pred_positive
        else:
            precision = 0.0
            
        # Recall: Trung bình qua từng người gán nhãn
        recalls = []
        dilated_pred = binary_dilation(pred_edge_binary, structure=struct_2px)
        for a_idx in range(gt_boundaries.shape[0]):
            human_boundary = gt_boundaries[a_idx] > 0
            human_positives = np.sum(human_boundary)
            if human_positives > 0:
                rec_a = np.sum(human_boundary & dilated_pred) / human_positives
                recalls.append(rec_a)
        recall = float(np.mean(recalls)) if recalls else 0.0
        
        f1 = (2 * precision * recall) / (precision + recall + 1e-10)
        results.append((stem, precision, recall, f1))
        print(f"   Ảnh {stem}: Precision={precision:.3f}, Recall={recall:.3f} => F1-Score={f1:.3f}")
        
    avg_f1 = np.mean([r[3] for r in results]) if results else 0.0
    print(f"   => [KẾT QUẢ BSDS500] F1-Score trung bình: {avg_f1:.3f}")

def evaluate_drive_vessels(sample_limit=3):
    """Đánh giá Frangi Vesselness trên ảnh võng mạc DRIVE so với nét vẽ bác sĩ."""
    print("\n" + "=" * 65)
    print("  2. BENCHMARK BÀI TOÁN DÒ MẠCH MÁU (DRIVE - FRANGI VESSELNESS)")
    print("=" * 65)
    
    results = []
    drive_files = sorted(list(RAW_DIR.glob("drive_*.png")))[:sample_limit]
    if not drive_files:
        print("   [!] Chưa tìm thấy ảnh drive_*.png trong data/raw/")
        return
        
    sigmas = get_sigmas()
    eigen_order = get_eigen_order()
    
    for img_path in drive_files:
        stem = img_path.stem
        # Ưu tiên đọc từ data/gt/drive/ theo cấu trúc mới của Đức
        vessel_gt_path = GT_DIR / "drive" / f"{stem}_vessels.png"
        if not vessel_gt_path.exists():
            vessel_gt_path = GT_DIR / f"{stem}_vessels.png"
            
        fov_mask_path = GT_DIR / "drive" / f"{stem}_fov.png"
        if not fov_mask_path.exists():
            fov_mask_path = GT_DIR / f"{stem}_fov.png"
        
        if not vessel_gt_path.exists() or not fov_mask_path.exists():
            continue
            
        gt_vessels = np.array(Image.open(vessel_gt_path)) > 128
        fov_mask = np.array(Image.open(fov_mask_path)) > 128
        
        # Bắt buộc áp mặt nạ FOV đã xói mòn theo ceil(k*sigma) = ceil(4.0 * 2.0) = 8px
        # (structuring element 17x17 cho sigma=2.0; cho multiscale nen dung ceil(k * max_sigma))
        struct_erode = np.ones((17, 17), dtype=bool)
        eroded_fov = binary_erosion(fov_mask, structure=struct_erode)
        
        # Giữ nguyên dải float64 0-255 theo chuẩn quy ước INSTRUCTIONS
        img = np.array(Image.open(img_path), dtype=np.float64)
        
        # Chạy Frangi đa tỷ lệ
        max_vesselness = np.zeros_like(img)
        for s in sigmas:
            lxx, lyy, lxy = compute_hessian_matrix(img, sigma=s)
            # Chuẩn hóa gamma=1 (Hessian nhân s^2)
            lxx_norm = (s ** 2.0) * lxx
            lyy_norm = (s ** 2.0) * lyy
            lxy_norm = (s ** 2.0) * lxy
            l1, l2 = compute_hessian_eigenvalues(lxx_norm, lyy_norm, lxy_norm, sort_order=eigen_order)
            # Mạch máu trong kênh green là tối hơn nền -> polarity='dark'
            v = detect_ridge(l1, l2, sigma=s, beta=0.5, polarity="dark")
            max_vesselness = np.maximum(max_vesselness, v)
            
        # Áp dụng ngưỡng phân vị trên vùng FOV
        fov_vals = max_vesselness[eroded_fov]
        thresh = np.percentile(fov_vals, 85.0) if len(fov_vals) > 0 else 0.5
        pred_vessels = (max_vesselness >= thresh) & eroded_fov
        gt_valid = gt_vessels & eroded_fov
        
        intersection = np.sum(pred_vessels & gt_valid)
        union = np.sum(pred_vessels | gt_valid)
        iou = intersection / (union + 1e-10)
        
        prec = intersection / (np.sum(pred_vessels) + 1e-10)
        rec = intersection / (np.sum(gt_valid) + 1e-10)
        f1 = (2 * prec * rec) / (prec + rec + 1e-10)
        
        results.append((stem, prec, rec, f1, iou))
        print(f"   Ảnh {stem}: Precision={prec:.3f}, Recall={rec:.3f} => F1={f1:.3f}, IoU={iou:.3f}")
        
    avg_f1 = np.mean([r[3] for r in results]) if results else 0.0
    avg_iou = np.mean([r[4] for r in results]) if results else 0.0
    print(f"   => [KẾT QUẢ DRIVE] F1 trung bình: {avg_f1:.3f}, IoU trung bình: {avg_iou:.3f}")

def evaluate_blobs(sample_limit=3):
    """Đánh giá LoG Scale-Space Blob Detection so với Ground Truth."""
    print("\n" + "=" * 65)
    print("  3. BENCHMARK BÀI TOÁN DÒ ĐỐM (BLOBS - LOG SCALE-SPACE)")
    print("=" * 65)
    
    blob_files = sorted(list(RAW_DIR.glob("blob_*.png")))[:sample_limit]
    if not blob_files:
        print("   [!] Chưa tìm thấy ảnh blob_*.png trong data/raw/")
        return
        
    # Đọc lưới scale từ config, bổ sung 11.3 nếu cần để bảo toàn đốm lớn nhất
    sigmas_blob = get_blob_sigmas()
    if 11.3 not in sigmas_blob:
        sigmas_blob.append(11.3)
    total_matched = 0
    total_gt = 0
    total_pred = 0
    
    for img_path in blob_files:
        stem = img_path.stem
        # Ưu tiên đọc từ data/gt/blob/ theo cấu trúc mới của Đức
        gt_json_path = GT_DIR / "blob" / f"{stem}.json"
        if not gt_json_path.exists():
            gt_json_path = GT_DIR / f"{stem}_gt.json"
            
        if not gt_json_path.exists():
            continue
            
        with open(gt_json_path, "r", encoding="utf-8") as f:
            gt_data = json.load(f)
            
        gt_blobs = gt_data.get("objects", gt_data.get("blobs", []))
        polarity = gt_data.get("polarity", "bright")
        
        # Giữ nguyên dải float64 0-255 theo chuẩn quy ước INSTRUCTIONS
        img = np.array(Image.open(img_path), dtype=np.float64)
        
        # Chồng bản đồ LoG đã chuẩn hóa sigma^2
        lap_stack = []
        for s in sigmas_blob:
            lap = compute_laplacian(img, sigma=s)
            lap_norm = (s ** 2.0) * lap
            lap_stack.append(lap_norm)
        lap_stack = np.stack(lap_stack, axis=0)
        
        # Dò cực trị không gian tỷ lệ (ngưỡng tương ứng trên dải 0-255)
        detected = detect_blob(lap_stack, sigmas=sigmas_blob, polarity=polarity, threshold=0.03 * 255.0)
        
        # Tiêu chuẩn khớp đúng: tâm lệch <= 2px và bán kính sai lệch <= 20%
        matched_gt = 0
        for g in gt_blobs:
            gx, gy, gr = g["x"], g["y"], g["radius"]
            found = False
            for d in detected:
                dy, dx, ds, dr, resp = d
                dist = np.sqrt((gx - dx)**2 + (gy - dy)**2)
                r_err = abs(gr - dr) / gr
                if dist <= 2.0 and r_err <= 0.20:
                    found = True
                    break
            if found:
                matched_gt += 1
                
        prec = matched_gt / (len(detected) + 1e-10)
        rec = matched_gt / (len(gt_blobs) + 1e-10)
        f1 = (2 * prec * rec) / (prec + rec + 1e-10)
        
        total_matched += matched_gt
        total_gt += len(gt_blobs)
        total_pred += len(detected)
        
        print(f"   Ảnh {stem} ({polarity}): GT={len(gt_blobs)}, Tìm thấy={len(detected)}, Khớp={matched_gt} => F1={f1:.3f}")
        
    overall_f1 = (2 * total_matched) / (total_gt + total_pred + 1e-10)
    print(f"   => [KẾT QUẢ ĐỐM] Tỉ lệ phát hiện trúng đích tổng thể (F1): {overall_f1:.3f}")

def main():
    print("=" * 65)
    print("  KHỞI CHẠY KHUNG ĐÁNH GIÁ ĐỊNH LƯỢNG TẦNG 2 (BENCHMARK)")
    print("=" * 65)
    # Chạy đủ 25 ảnh: 10 BSDS + 10 DRIVE + 5 Blob (theo spec Tầng 2)
    evaluate_bsds_edges(sample_limit=10)
    evaluate_drive_vessels(sample_limit=10)
    evaluate_blobs(sample_limit=5)
    print("\n" + "=" * 65)
    print("  HOÀN TẤT ĐÁNH GIÁ ĐỊNH LƯỢNG TẦNG 2!")
    print("=" * 65)

if __name__ == "__main__":
    main()
