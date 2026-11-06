"""
benchmark_tier2.py - Đánh giá định lượng Tầng 2 (So sánh với Ground Truth thực tế)
Người thực hiện: Nguyễn Đức Mạnh (Role 2 — Lead Algorithm Developer)

Khung đánh giá định lượng Tầng 2 trên toàn bộ 25 ảnh so với Ground Truth thực tế:
- Bài toán 1 (Edge - BSDS500, 10 ảnh): Dò biên Canny đa tỷ lệ, so sánh dung sai 2px với đa annotator.
- Bài toán 2 (Ridge - DRIVE, 10 ảnh): Dò mạch máu Frangi qua Hessian, áp mặt nạ FOV xói mòn đa tỷ lệ, tính F1/IoU.
- Bài toán 3 (Blob - Đốm đa tỷ lệ, 5 ảnh): Dò cực trị LoG 3D scale-space, khớp tâm <= 2px & bán kính <= 20%.

Toàn bộ kết quả chi tiết và tổng hợp được lưu vào: outputs/metrics/tier2_results.csv
"""

import sys
import csv
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
METRICS_DIR = ROOT / "outputs" / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)

def get_fov_eroded_mask(fov_mask: np.ndarray, sigma: float, k: float = 4.0) -> np.ndarray:
    """Xói mòn mặt nạ FOV thích ứng theo tỷ lệ sigma: r = ceil(k * sigma)."""
    r = int(np.ceil(k * sigma))
    struct_size = 2 * r + 1
    struct = np.ones((struct_size, struct_size), dtype=bool)
    return binary_erosion(fov_mask, structure=struct)

def evaluate_bsds_edges(sample_limit=10, p_low=60.0, p_high=85.0, records=None):
    """Đánh giá Canny Edge Detection trên ảnh BSDS500 so với Ground Truth đa annotator."""
    print("\n" + "=" * 65)
    print("  1. BENCHMARK BÀI TOÁN DÒ BIÊN (BSDS500 - CANNY EDGE DETECTION)")
    print(f"     Tham số Canny: p_low={p_low:.1f}, p_high={p_high:.1f}")
    print("=" * 65)
    
    results = []
    bsds_files = sorted(list(RAW_DIR.glob("bsds_*.png")))[:sample_limit]
    if not bsds_files:
        print("   [!] Chưa tìm thấy ảnh bsds_*.png trong data/raw/")
        return 0.0
        
    sigmas_available = get_sigmas()
    sigma = 2.0 if 2.0 in sigmas_available else sigmas_available[min(1, len(sigmas_available) - 1)]

    for img_path in bsds_files:
        stem = img_path.stem
        annotator_files = sorted(list((GT_DIR / "bsds" / stem).glob("annotator_*_boundaries.png")))
        if annotator_files:
            gt_boundaries = np.stack([np.array(Image.open(f)) > 0 for f in annotator_files], axis=0)
        elif (GT_DIR / f"{stem}_boundaries.npy").exists():
            gt_boundaries = np.load(GT_DIR / f"{stem}_boundaries.npy")
        else:
            continue
            
        img = np.array(Image.open(img_path), dtype=np.float64)
        
        # Đạo hàm bậc 1 chuẩn hóa gamma=1 (Lindeberg)
        lx, ly = compute_derivatives_1st(img, sigma=sigma)
        lx_norm = (sigma ** 1.0) * lx
        ly_norm = (sigma ** 1.0) * ly
        
        # Dò biên Canny với phân vị cấu hình được
        pred_edge_binary = detect_canny(lx_norm, ly_norm, p_low=p_low, p_high=p_high, return_binary=False)
        
        # Dung sai biên 2 px: giãn nở biên 2 lần
        struct_2px = np.ones((5, 5), dtype=bool)
        
        # Precision: Tỉ lệ pixel dự đoán nằm trong bán kính 2px của ít nhất 1 annotator
        union_gt = np.any(gt_boundaries > 0, axis=0)
        dilated_union_gt = binary_dilation(union_gt, structure=struct_2px)
        
        pred_positive = int(np.sum(pred_edge_binary))
        if pred_positive > 0:
            true_positives = int(np.sum(pred_edge_binary & dilated_union_gt))
            precision = true_positives / pred_positive
        else:
            true_positives = 0
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
        
        if records is not None:
            records.append({
                "task": "BSDS500_Canny_Edge",
                "image": stem,
                "parameter": f"sigma={sigma:.1f}_plow={p_low:.1f}_phigh={p_high:.1f}",
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "iou": "N/A",
                "gt_count": int(union_gt.sum()),
                "detected_count": pred_positive,
                "matched_count": true_positives,
            })
        print(f"   Ảnh {stem}: Precision={precision:.3f}, Recall={recall:.3f} => F1-Score={f1:.3f}")
        
    avg_f1 = float(np.mean([r[3] for r in results])) if results else 0.0
    print(f"   => [KẾT QUẢ BSDS500] F1-Score trung bình: {avg_f1:.3f}")
    return avg_f1

def evaluate_drive_vessels(sample_limit=10, records=None):
    """Đánh giá Frangi Vesselness trên ảnh võng mạc DRIVE với mặt nạ FOV xói mòn đa tỷ lệ."""
    print("\n" + "=" * 65)
    print("  2. BENCHMARK BÀI TOÁN DÒ MẠCH MÁU (DRIVE - FRANGI VESSELNESS)")
    print("     Mặt nạ FOV: Xói mòn thích ứng theo từng sigma r = ceil(k * sigma)")
    print("=" * 65)
    
    results = []
    drive_files = sorted(list(RAW_DIR.glob("drive_*.png")))[:sample_limit]
    if not drive_files:
        print("   [!] Chưa tìm thấy ảnh drive_*.png trong data/raw/")
        return 0.0, 0.0
        
    sigmas = get_sigmas()
    eigen_order = get_eigen_order()
    
    for img_path in drive_files:
        stem = img_path.stem
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
        img = np.array(Image.open(img_path), dtype=np.float64)
        
        # Mặt nạ FOV đánh giá tổng thể (sigma=2.0, k=4.0 -> r=8px, struct 17x17)
        eval_fov = get_fov_eroded_mask(fov_mask, sigma=2.0, k=4.0)
        
        # Chạy Frangi đa tỷ lệ với FOV scale-aware
        max_vesselness = np.zeros_like(img)
        for s in sigmas:
            # Triệt tiêu gờ biên giả cho từng tỷ lệ sigma riêng biệt
            fov_s = get_fov_eroded_mask(fov_mask, sigma=s, k=4.0)
            
            lxx, lyy, lxy = compute_hessian_matrix(img, sigma=s)
            lxx_norm = (s ** 2.0) * lxx
            lyy_norm = (s ** 2.0) * lyy
            lxy_norm = (s ** 2.0) * lxy
            l1, l2 = compute_hessian_eigenvalues(lxx_norm, lyy_norm, lxy_norm, sort_order=eigen_order)
            
            # Mạch máu trong kênh Green là rãnh tối -> polarity='dark'
            v = detect_ridge(l1, l2, sigma=s, beta=0.5, polarity="dark")
            v[~fov_s] = 0.0  # Cắt biên thích ứng tỷ lệ
            max_vesselness = np.maximum(max_vesselness, v)
            
        # Áp dụng ngưỡng phân vị trên vùng FOV xói mòn
        fov_vals = max_vesselness[eval_fov]
        thresh = np.percentile(fov_vals, 85.0) if len(fov_vals) > 0 else 0.5
        pred_vessels = (max_vesselness >= thresh) & eval_fov
        gt_valid = gt_vessels & eval_fov
        
        intersection = int(np.sum(pred_vessels & gt_valid))
        union = int(np.sum(pred_vessels | gt_valid))
        iou = intersection / (union + 1e-10)
        
        pred_cnt = int(np.sum(pred_vessels))
        gt_cnt = int(np.sum(gt_valid))
        prec = intersection / (pred_cnt + 1e-10)
        rec = intersection / (gt_cnt + 1e-10)
        f1 = (2 * prec * rec) / (prec + rec + 1e-10)
        
        results.append((stem, prec, rec, f1, iou))
        
        if records is not None:
            records.append({
                "task": "DRIVE_Frangi_Ridge",
                "image": stem,
                "parameter": "multiscale_sigmas=[1,2,4,8]_thresh=p85_FOVscale",
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "iou": round(iou, 4),
                "gt_count": gt_cnt,
                "detected_count": pred_cnt,
                "matched_count": intersection,
            })
        print(f"   Ảnh {stem}: Precision={prec:.3f}, Recall={rec:.3f} => F1={f1:.3f}, IoU={iou:.3f}")
        
    avg_f1 = float(np.mean([r[3] for r in results])) if results else 0.0
    avg_iou = float(np.mean([r[4] for r in results])) if results else 0.0
    print(f"   => [KẾT QUẢ DRIVE] F1 trung bình: {avg_f1:.3f}, IoU trung bình: {avg_iou:.3f}")
    return avg_f1, avg_iou

def evaluate_blobs(sample_limit=5, records=None):
    """Đánh giá LoG Scale-Space Blob Detection so với Ground Truth."""
    print("\n" + "=" * 65)
    print("  3. BENCHMARK BÀI TOÁN DÒ ĐỐM (BLOBS - LOG SCALE-SPACE)")
    print("=" * 65)
    
    blob_files = sorted(list(RAW_DIR.glob("blob_*.png")))[:sample_limit]
    if not blob_files:
        print("   [!] Chưa tìm thấy ảnh blob_*.png trong data/raw/")
        return 0.0
        
    sigmas_blob = get_blob_sigmas()
    if 11.3 not in sigmas_blob:
        sigmas_blob.append(11.3)
        
    total_matched = 0
    total_gt = 0
    total_pred = 0
    
    for img_path in blob_files:
        stem = img_path.stem
        gt_json_path = GT_DIR / "blob" / f"{stem}.json"
        if not gt_json_path.exists():
            gt_json_path = GT_DIR / f"{stem}_gt.json"
            
        if not gt_json_path.exists():
            continue
            
        with open(gt_json_path, "r", encoding="utf-8") as f:
            gt_data = json.load(f)
            
        gt_blobs = gt_data.get("objects", gt_data.get("blobs", []))
        polarity = gt_data.get("polarity", "bright")
        img = np.array(Image.open(img_path), dtype=np.float64)
        
        # Chồng bản đồ LoG đã chuẩn hóa sigma^2
        lap_stack = []
        for s in sigmas_blob:
            lap = compute_laplacian(img, sigma=s)
            lap_norm = (s ** 2.0) * lap
            lap_stack.append(lap_norm)
        lap_stack = np.stack(lap_stack, axis=0)
        
        # Dò cực trị không gian tỷ lệ (ngưỡng 0.03 * 255)
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
        
        if records is not None:
            records.append({
                "task": "Blobs_LoG_ScaleSpace",
                "image": stem,
                "parameter": f"polarity={polarity}_thresh=0.03",
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "iou": "N/A",
                "gt_count": len(gt_blobs),
                "detected_count": len(detected),
                "matched_count": matched_gt,
            })
        print(f"   Ảnh {stem} ({polarity}): GT={len(gt_blobs)}, Tìm thấy={len(detected)}, Khớp={matched_gt} => F1={f1:.3f}")
        
    overall_f1 = (2 * total_matched) / (total_gt + total_pred + 1e-10)
    print(f"   => [KẾT QUẢ ĐỐM] Tỉ lệ phát hiện trúng đích tổng thể (F1): {overall_f1:.3f}")
    return overall_f1

def main():
    print("=" * 65)
    print("  KHỞI CHẠY KHUNG ĐÁNH GIÁ ĐỊNH LƯỢNG TẦNG 2 (BENCHMARK)")
    print("=" * 65)
    
    all_records = []
    
    # Chạy đủ 25 ảnh: 10 BSDS + 10 DRIVE + 5 Blob (theo spec Tầng 2)
    evaluate_bsds_edges(sample_limit=10, p_low=60.0, p_high=85.0, records=all_records)
    evaluate_drive_vessels(sample_limit=10, records=all_records)
    evaluate_blobs(sample_limit=5, records=all_records)
    
    # Lưu toàn bộ kết quả định lượng ra outputs/metrics/tier2_results.csv
    out_csv = METRICS_DIR / "tier2_results.csv"
    if all_records:
        keys = list(all_records[0].keys())
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_records)
        print(f"\n-> ĐÃ XUẤT TOÀN BỘ KẾT QUẢ ĐỊNH LƯỢNG RA: {out_csv}")
        
    print("\n" + "=" * 65)
    print("  HOÀN TẤT ĐÁNH GIÁ ĐỊNH LƯỢNG TẦNG 2!")
    print("=" * 65)

if __name__ == "__main__":
    main()
