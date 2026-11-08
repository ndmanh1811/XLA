"""
benchmark_tier2.py - Đánh giá định lượng Tầng 2 (So sánh với Ground Truth thực tế)
Người thực hiện: Nguyễn Đức Mạnh (Role 2 — Lead Algorithm Developer)

Khung đánh giá định lượng Tầng 2 trên toàn bộ 25 ảnh so với Ground Truth thực tế:
- Bài toán 1 (Edge - BSDS500, 10 ảnh): Dò biên Canny đa tỷ lệ, so sánh dung sai 2px với đa annotator.
- Bài toán 2 (Ridge - DRIVE, 10 ảnh): Dò mạch máu Frangi qua Hessian, áp mặt nạ FOV xói mòn đa tỷ lệ, tính F1/IoU.
- Bài toán 3 (Blob - Đốm đa tỷ lệ, 5 ảnh): Dò cực trị LoG 3D scale-space, khớp tâm <= 2px & bán kính <= 20%.

Hỗ trợ 2 nguồn bản đồ (--source):
- python: tính toán trực tiếp từ nhân NumPy thuần (mặc định, kết quả chính thức).
- fiji:   đọc các bản đồ TIFF do ImageJ Macro của Lộc xuất tại outputs/fiji/.
- both:   chạy cả hai và xuất bảng đối sánh song song tier2_comparison.csv.

Nhánh BSDS của Fiji có 2 chế độ (--bsds-fiji-mode):
- canny: đọc fiji_*_lx/ly, chuẩn hóa sigma rồi gọi detect_canny (mặc định, fair).
- edge:  đọc fiji_*_edge (FeatureJ Edges) và áp hysteresis (tham chiếu riêng).

Toàn bộ kết quả chi tiết và tổng hợp được lưu vào: outputs/metrics/tier2_results.csv
"""

import sys
import csv
import json
from pathlib import Path
import numpy as np
from PIL import Image
import tifffile
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

FIJI_DIR = ROOT / "outputs" / "fiji"


def _fiji_tif(name: str) -> np.ndarray:
    """Đọc một bản đồ 32-bit float do ImageJ Macro của Lộc xuất."""
    path = FIJI_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Thiếu bản đồ Fiji: {path}")
    return np.asarray(tifffile.imread(path), dtype=np.float64)


def hysteresis_from_nms(
    nms: np.ndarray, p_low: float = 60.0, p_high: float = 85.0
) -> np.ndarray:
    """Áp ngưỡng trễ phân vị lên edge strength đã NMS (nhánh Fiji).

    FeatureJ Edge với suppress=[] trả về edge strength sau NMS nội bộ; hàm này
    dùng đúng quy tắc phân vị + loang BFS 8-láng giềng như detect_canny.
    """
    nonzero = nms[nms > 0]
    if len(nonzero) == 0:
        return np.zeros_like(nms, dtype=bool)

    t_high = np.percentile(nonzero, p_high)
    t_low = np.percentile(nonzero, p_low)
    strong = nms >= t_high
    candidate = nms >= t_low

    edge = strong.copy()
    visited = strong.copy()
    h, w = nms.shape
    stack = list(zip(*np.where(strong)))
    while stack:
        cy, cx = stack.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and candidate[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    edge[ny, nx] = True
                    stack.append((ny, nx))
    return edge

def get_fov_eroded_mask(fov_mask: np.ndarray, sigma: float, k: float = 4.0) -> np.ndarray:
    """Xói mòn mặt nạ FOV thích ứng theo tỷ lệ sigma: r = ceil(k * sigma)."""
    r = int(np.ceil(k * sigma))
    struct_size = 2 * r + 1
    struct = np.ones((struct_size, struct_size), dtype=bool)
    return binary_erosion(fov_mask, structure=struct)

def evaluate_bsds_edges(
    sample_limit=10,
    p_low=60.0,
    p_high=85.0,
    records=None,
    source="python",
    fiji_mode="canny",
    task_name="BSDS500_Canny_Edge",
):
    """Đánh giá Canny Edge Detection trên ảnh BSDS500 so với Ground Truth đa annotator.

    Nhánh Fiji:
    - fiji_mode="canny": đọc lx/ly của Macro, nhân sigma rồi gọi detect_canny
      (cùng thuật toán với nhánh Python -> đối sánh công bằng).
    - fiji_mode="edge": đọc bản đồ FeatureJ Edges (đã NMS nội bộ) và chỉ áp
      ngưỡng trễ; đây là tham chiếu riêng, không dùng thay nhánh fair.
    """
    print("\n" + "=" * 65)
    print("  1. BENCHMARK BÀI TOÁN DÒ BIÊN (BSDS500 - CANNY EDGE DETECTION)")
    fiji_note = f" | Fiji mode={fiji_mode}" if source == "fiji" else ""
    print(f"     Nguồn bản đồ: {source.upper()}{fiji_note} | p_low={p_low:.1f}, p_high={p_high:.1f}")
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

        if source == "fiji":
            if fiji_mode == "canny":
                # Nhánh fair: dùng đạo hàm bậc 1 lx/ly của Fiji, chuẩn hóa sigma
                # rồi chạy đúng detect_canny như nhánh Python.
                lx = (sigma ** 1.0) * _fiji_tif(f"fiji_{stem}_lx_s{sigma:.1f}.tif")
                ly = (sigma ** 1.0) * _fiji_tif(f"fiji_{stem}_ly_s{sigma:.1f}.tif")
                pred_edge_binary = detect_canny(
                    lx, ly, p_low=p_low, p_high=p_high, return_binary=False
                )
            else:
                # Tham chiếu riêng: FeatureJ Edge đã NMS nội bộ, chỉ áp ngưỡng trễ.
                nms = _fiji_tif(f"fiji_{stem}_edge_s{sigma:.1f}.tif")
                pred_edge_binary = hysteresis_from_nms(nms, p_low=p_low, p_high=p_high)
        else:
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
                "source": source,
                "task": task_name,
                "image": stem,
                "parameter": f"sigma={sigma:.1f}_plow={p_low:.1f}_phigh={p_high:.1f}",
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "iou": "N/A",
                "gt_count": int(union_gt.sum()),
                "detected_count": pred_positive,
                "matched_count": true_positives,
                "_f1_raw": f1,
            })
        print(f"   Ảnh {stem}: Precision={precision:.3f}, Recall={recall:.3f} => F1-Score={f1:.3f}")
        
    avg_f1 = float(np.mean([r[3] for r in results])) if results else 0.0
    print(f"   => [KẾT QUẢ BSDS500] F1-Score trung bình: {avg_f1:.3f}")
    return avg_f1

def evaluate_drive_vessels(sample_limit=10, records=None, source="python"):
    """Đánh giá Frangi Vesselness trên ảnh võng mạc DRIVE với mặt nạ FOV xói mòn đa tỷ lệ."""
    print("\n" + "=" * 65)
    print("  2. BENCHMARK BÀI TOÁN DÒ MẠCH MÁU (DRIVE - FRANGI VESSELNESS)")
    print(f"     Nguồn bản đồ: {source.upper()}")
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
            
            if source == "fiji":
                # FeatureJ xuất trị riêng Hessian thô (chưa nhân sigma^2) -> chuẩn hóa tại đây
                l1 = (s ** 2.0) * _fiji_tif(f"fiji_{stem}_hess-l1_s{s:.1f}.tif")
                l2 = (s ** 2.0) * _fiji_tif(f"fiji_{stem}_hess-l2_s{s:.1f}.tif")
            else:
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
                "source": source,
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
                "_f1_raw": f1,
                "_iou_raw": iou,
            })
        print(f"   Ảnh {stem}: Precision={prec:.3f}, Recall={rec:.3f} => F1={f1:.3f}, IoU={iou:.3f}")
        
    avg_f1 = float(np.mean([r[3] for r in results])) if results else 0.0
    avg_iou = float(np.mean([r[4] for r in results])) if results else 0.0
    print(f"   => [KẾT QUẢ DRIVE] F1 trung bình: {avg_f1:.3f}, IoU trung bình: {avg_iou:.3f}")
    return avg_f1, avg_iou

def evaluate_blobs(sample_limit=5, records=None, source="python", blob_sigmas="extended"):
    """Đánh giá LoG Scale-Space Blob Detection so với Ground Truth."""
    print("\n" + "=" * 65)
    print("  3. BENCHMARK BÀI TOÁN DÒ ĐỐM (BLOBS - LOG SCALE-SPACE)")
    print(f"     Nguồn bản đồ: {source.upper()}")
    print("=" * 65)
    
    blob_files = sorted(list(RAW_DIR.glob("blob_*.png")))[:sample_limit]
    if not blob_files:
        print("   [!] Chưa tìm thấy ảnh blob_*.png trong data/raw/")
        return 0.0
        
    sigmas_blob = get_blob_sigmas()
    if source == "python" and blob_sigmas == "extended":
        if 11.3 not in sigmas_blob:
            sigmas_blob.append(11.3)
    elif source == "fiji" and blob_sigmas == "extended":
        print("   [!] Fiji không có Laplacian tại sigma=11.3 -> dùng 7 sigma cấu hình.")
    print(f"     Thang đo Blob: {len(sigmas_blob)} sigma = {sigmas_blob}")
        
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
            if source == "fiji":
                # Fiji xuất Laplacian thô (chưa nhân sigma^2) -> chuẩn hóa tại đây
                lap = _fiji_tif(f"fiji_{stem}_lap_s{s:.1f}.tif")
            else:
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
                "source": source,
                "task": "Blobs_LoG_ScaleSpace",
                "image": stem,
                "parameter": f"polarity={polarity}_thresh=0.03_nsigmas={len(sigmas_blob)}",
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "iou": "N/A",
                "gt_count": len(gt_blobs),
                "detected_count": len(detected),
                "matched_count": matched_gt,
                "_f1_raw": f1,
            })
        print(f"   Ảnh {stem} ({polarity}): GT={len(gt_blobs)}, Tìm thấy={len(detected)}, Khớp={matched_gt} => F1={f1:.3f}")
        
    overall_f1 = (2 * total_matched) / (total_gt + total_pred + 1e-10)
    print(f"   => [KẾT QUẢ ĐỐM] Tỉ lệ phát hiện trúng đích tổng thể (F1): {overall_f1:.3f}")
    return overall_f1

def write_records(records, out_path):
    """Ghi danh sách bản ghi kết quả định lượng ra CSV (bỏ các khóa nội bộ)."""
    if not records:
        print(f"   [!] Không có bản ghi nào để ghi vào {out_path}")
        return
    fields = [key for key in records[0].keys() if not key.startswith("_")]
    clean = [{key: rec[key] for key in fields} for rec in records]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(clean)
    print(f"\n-> ĐÃ XUẤT KẾT QUẢ RA: {out_path}")


def write_comparison(records, out_path):
    """Tổng hợp bảng đối sánh Python vs Fiji theo từng ảnh và từng bài toán."""
    grouped = {}
    for rec in records:
        key = (rec["task"], rec["image"])
        grouped.setdefault(key, {})[rec["source"]] = rec

    def _num(value):
        if value in ("N/A", "", None):
            return None
        return float(value)

    rows = []
    for (task, image), pair in grouped.items():
        if "python" not in pair or "fiji" not in pair:
            continue
        py, fj = pair["python"], pair["fiji"]
        py_iou, fj_iou = _num(py["iou"]), _num(fj["iou"])
        py_f1_raw = float(py.get("_f1_raw", py["f1"]))
        fj_f1_raw = float(fj.get("_f1_raw", fj["f1"]))
        py_iou_raw = py.get("_iou_raw", py_iou)
        fj_iou_raw = fj.get("_iou_raw", fj_iou)
        rows.append({
            "task": task,
            "image": image,
            "python_parameter": py["parameter"],
            "fiji_parameter": fj["parameter"],
            "python_precision": py["precision"],
            "python_recall": py["recall"],
            "python_f1": py["f1"],
            "python_iou": py["iou"],
            "fiji_precision": fj["precision"],
            "fiji_recall": fj["recall"],
            "fiji_f1": fj["f1"],
            "fiji_iou": fj["iou"],
            "delta_f1": round(fj_f1_raw - py_f1_raw, 6),
            "delta_iou": (
                round(float(fj_iou_raw) - float(py_iou_raw), 6)
                if py_iou_raw is not None and fj_iou_raw is not None
                else "N/A"
            ),
            "_python_f1_raw": py_f1_raw,
            "_fiji_f1_raw": fj_f1_raw,
        })

    rows.sort(key=lambda r: (r["task"], r["image"]))
    fields = [
        "task", "image", "python_parameter", "fiji_parameter",
        "python_precision", "python_recall", "python_f1", "python_iou",
        "fiji_precision", "fiji_recall", "fiji_f1", "fiji_iou",
        "delta_f1", "delta_iou",
    ]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n-> ĐÃ XUẤT BẢNG ĐỐI SÁNH PYTHON vs FIJI RA: {out_path}")
    by_task = {}
    for row in rows:
        by_task.setdefault(row["task"], []).append(row)
    print(f"   {'Bài toán':<28} {'Python F1':>10} {'Fiji F1':>10} {'ΔF1':>10}")
    print("   " + "-" * 64)
    for task, group in sorted(by_task.items()):
        py_f1 = float(np.mean([r["_python_f1_raw"] for r in group]))
        fj_f1 = float(np.mean([r["_fiji_f1_raw"] for r in group]))
        print(f"   {task:<28} {py_f1:>10.6f} {fj_f1:>10.6f} {fj_f1 - py_f1:>+10.6f}")
    return rows


def parse_args():
    """Hỗ trợ truyền tham số phân vị Canny, số lượng mẫu và nguồn bản đồ từ dòng lệnh."""
    import argparse
    parser = argparse.ArgumentParser(description="Khung đánh giá định lượng Tầng 2 (Ground Truth Benchmark)")
    parser.add_argument("--p-low", type=float, default=60.0, help="Phân vị ngưỡng dưới Canny (mặc định: 60.0)")
    parser.add_argument("--p-high", type=float, default=85.0, help="Phân vị ngưỡng trên Canny (mặc định: 85.0)")
    parser.add_argument("--bsds-samples", type=int, default=10, help="Số lượng ảnh BSDS500 (mặc định: 10)")
    parser.add_argument("--drive-samples", type=int, default=10, help="Số lượng ảnh DRIVE (mặc định: 10)")
    parser.add_argument("--blob-samples", type=int, default=5, help="Số lượng ảnh Blob (mặc định: 5)")
    parser.add_argument(
        "--source", choices=["python", "fiji", "both"], default="python",
        help="Nguồn bản đồ: python (mặc định), fiji (các TIFF của Lộc), hoặc both (đối sánh song song)"
    )
    parser.add_argument(
        "--bsds-fiji-mode", choices=["canny", "edge"], default="canny",
        help="Nhánh BSDS của Fiji: canny = lx/ly + detect_canny (mặc định, fair); "
             "edge = FeatureJ Edges + hysteresis (tham chiếu riêng)"
    )
    parser.add_argument(
        "--edge-reference-out", type=str, default=None,
        help="CSV tham chiếu FeatureJ Edges cho BSDS (mặc định: outputs/metrics/tier2_bsds_edge_reference.csv)"
    )
    parser.add_argument(
        "--blob-sigmas", choices=["config", "extended"], default=None,
        help="Thang đo Blob: config = 7 sigma [1,1.4,2,2.8,4,5.7,8]; extended = thêm 11.3 (chỉ Python). "
             "Mặc định: extended khi chỉ chạy Python, config khi chạy Fiji/both."
    )
    parser.add_argument("--out", type=str, default=None, help="Đường dẫn CSV kết quả chi tiết (tùy chọn)")
    parser.add_argument("--comparison-out", type=str, default=None, help="Đường dẫn CSV đối sánh Python vs Fiji (chỉ dùng với --source both)")
    return parser.parse_known_args()[0]

def main():
    args = parse_args()
    blob_mode = args.blob_sigmas or ("extended" if args.source == "python" else "config")
    sources = ["python", "fiji"] if args.source == "both" else [args.source]

    print("=" * 65)
    print("  KHỞI CHẠY KHUNG ĐÁNH GIÁ ĐỊNH LƯỢNG TẦNG 2 (BENCHMARK)")
    print(f"  Nguồn bản đồ: {args.source.upper()} | Canny: p_low={args.p_low:.1f}, p_high={args.p_high:.1f}")
    print(f"  Nhánh BSDS của Fiji: {args.bsds_fiji_mode}")
    print(f"  Thang đo Blob: {blob_mode} ({7 if blob_mode == 'config' else 8} sigma)")
    print("=" * 65)
    
    all_records = []
    
    # Chạy đủ 25 ảnh: 10 BSDS + 10 DRIVE + 5 Blob (theo spec Tầng 2)
    for source in sources:
        evaluate_bsds_edges(
            sample_limit=args.bsds_samples,
            p_low=args.p_low,
            p_high=args.p_high,
            records=all_records,
            source=source,
            fiji_mode=args.bsds_fiji_mode,
        )
        evaluate_drive_vessels(sample_limit=args.drive_samples, records=all_records, source=source)
        evaluate_blobs(sample_limit=args.blob_samples, records=all_records, source=source, blob_sigmas=blob_mode)

    # Tham chiếu riêng FeatureJ Edges: chỉ ghi khi bảng chính dùng nhánh fair canny.
    if args.source == "both" and args.bsds_fiji_mode == "canny":
        edge_ref_records = []
        evaluate_bsds_edges(
            sample_limit=args.bsds_samples,
            p_low=args.p_low,
            p_high=args.p_high,
            records=edge_ref_records,
            source="fiji",
            fiji_mode="edge",
            task_name="BSDS500_FeatureJ_Edges_Reference",
        )
        edge_ref_csv = (
            Path(args.edge_reference_out)
            if args.edge_reference_out
            else METRICS_DIR / "tier2_bsds_edge_reference.csv"
        )
        write_records(edge_ref_records, edge_ref_csv)
    
    # Lưu toàn bộ kết quả định lượng ra outputs/metrics/tier2_results.csv
    if args.out:
        out_csv = Path(args.out)
    else:
        default_names = {
            "python": "tier2_results.csv",
            "fiji": "tier2_results_fiji.csv",
            "both": "tier2_results_both.csv",
        }
        out_csv = METRICS_DIR / default_names[args.source]

    write_records(all_records, out_csv)

    if args.source == "both":
        comp_csv = Path(args.comparison_out) if args.comparison_out else METRICS_DIR / "tier2_comparison.csv"
        write_comparison(all_records, comp_csv)
        
    print("\n" + "=" * 65)
    print("  HOÀN TẤT ĐÁNH GIÁ ĐỊNH LƯỢNG TẦNG 2!")
    print("=" * 65)

if __name__ == "__main__":
    main()
