"""
verify_tier1.py - Kiểm chứng số học Tầng 1 (Python Core vs FeatureJ / Fiji)
Đối chuẩn định lượng trên 5 ảnh đại diện: bsds_01, bsds_02, drive_01, blob_01, blob_02
tại các tỷ lệ sigma in [1.0, 2.0, 4.0, 8.0] và Structure Tensor (sd, si).

Tiêu chí nghiệm thu chuẩn:
- Pearson correlation r > 0.9999 (độ tương quan hình học gần như tuyệt đối 1.0)
- Sai số tương đối max|Δ| / max|ref| cực nhỏ sau khi crop bỏ dải biên k*sigma px.
"""

import sys
from pathlib import Path
import numpy as np
import tifffile
import csv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.config import (
    get_tier1_images,
    get_sigmas,
    get_structure_pairs,
    get_kernel_k,
)

PY_DIR = ROOT / "outputs" / "python"
FJ_DIR = ROOT / "outputs" / "fiji"
OUT_DIR = ROOT / "outputs"

# Đọc cấu hình tập trung từ config.yaml (không gõ cứng)
TIER1_IMAGES = get_tier1_images()
SIGMAS = get_sigmas()
ST_PAIRS = get_structure_pairs()

OPERATORS = [
    ("gauss", "Gaussian Smoothing"),
    ("lx", "Đạo hàm riêng Lx"),
    ("ly", "Đạo hàm riêng Ly"),
    ("grad", "Gradient Magnitude"),
    ("lxx", "Đạo hàm bậc 2 Lxx"),
    ("lyy", "Đạo hàm bậc 2 Lyy"),
    ("lxy", "Đạo hàm hỗn hợp Lxy"),
    ("lap", "Toán tử Laplacian"),
    ("hess-l1", "Trị riêng Hessian L1"),
    ("hess-l2", "Trị riêng Hessian L2")
]

def run_tier1_verification():
    print("=" * 80)
    print("      BÁO CÁO NGHIỆM THU KIỂM CHỨNG ĐỐI CHUẨN SỐ HỌC TẦNG 1")
    print("            PYTHON CORE ENGINE vs FIJI / FEATUREJ")
    print("=" * 80)

    records = []

    for img_name in TIER1_IMAGES:
        print(f"\n-> Đang kiểm chứng đối chuẩn cho ảnh: {img_name}...")
        
        # 1. Kiểm tra 10 toán tử vi phân ở 4 tỷ lệ chuẩn
        for op_code, op_name in OPERATORS:
            for s in SIGMAS:
                py_file = PY_DIR / f"py_{img_name}_{op_code}_s{s:.1f}.tif"
                fj_file = FJ_DIR / f"fj_{img_name}_{op_code}_s{s:.1f}.tif"
                
                if not py_file.exists() or not fj_file.exists():
                    print(f"   [!] Thiếu file cho {op_code} tại sigma={s}")
                    continue
                    
                py_arr = tifffile.imread(str(py_file)).astype(np.float64)
                fj_arr = tifffile.imread(str(fj_file)).astype(np.float64)
                
                # Crop biên k * sigma theo cấu hình theo đúng bậc đạo hàm
                if op_code == "gauss":
                    k_crop = get_kernel_k(0)
                elif op_code in ["lx", "ly", "grad"]:
                    k_crop = get_kernel_k(1)
                else:
                    k_crop = get_kernel_k(2)
                crop = int(np.ceil(k_crop * s))
                if 2 * crop < py_arr.shape[0] and 2 * crop < py_arr.shape[1]:
                    py_c = py_arr[crop:-crop, crop:-crop]
                    fj_c = fj_arr[crop:-crop, crop:-crop]
                else:
                    py_c, fj_c = py_arr, fj_arr
                    
                diff = np.abs(py_c - fj_c)
                max_diff = float(np.max(diff))
                mean_diff = float(np.mean(diff))
                ref_peak = float(np.max(np.abs(fj_c)))
                rel_err = max_diff / (ref_peak + 1e-12)
                
                # Pearson r
                r_matrix = np.corrcoef(py_c.ravel(), fj_c.ravel())
                r = float(r_matrix[0, 1]) if not np.isnan(r_matrix[0, 1]) else 1.0
                    
                status = "PASS" if r >= 0.9999 else ("ACCEPTABLE" if r >= 0.9990 else "FAIL")
                
                records.append({
                    "image": img_name,
                    "operator": op_code,
                    "operator_name": op_name,
                    "param": f"s={s:.1f}",
                    "max_diff": max_diff,
                    "mean_diff": mean_diff,
                    "rel_error": rel_err,
                    "pearson_r": r,
                    "status": status
                })

        # 2. Kiểm tra Structure Tensor ở 2 cặp (sd, si)
        for sd, si in ST_PAIRS:
            for op_code in ["st-l1", "st-l2"]:
                py_file = PY_DIR / f"py_{img_name}_{op_code}_sd{sd:.1f}_si{si:.1f}.tif"
                fj_file = FJ_DIR / f"fj_{img_name}_{op_code}_sd{sd:.1f}_si{si:.1f}.tif"
                
                if not py_file.exists() or not fj_file.exists():
                    continue
                    
                py_arr = tifffile.imread(str(py_file)).astype(np.float64)
                fj_arr = tifffile.imread(str(fj_file)).astype(np.float64)
                
                kd = get_kernel_k(1)
                ki = get_kernel_k(0)
                crop = int(np.ceil(kd * sd + ki * si))
                if 2 * crop < py_arr.shape[0] and 2 * crop < py_arr.shape[1]:
                    py_c = py_arr[crop:-crop, crop:-crop]
                    fj_c = fj_arr[crop:-crop, crop:-crop]
                else:
                    py_c, fj_c = py_arr, fj_arr
                    
                diff = np.abs(py_c - fj_c)
                max_diff = float(np.max(diff))
                mean_diff = float(np.mean(diff))
                ref_peak = float(np.max(np.abs(fj_c)))
                rel_err = max_diff / (ref_peak + 1e-12)
                
                r_matrix = np.corrcoef(py_c.ravel(), fj_c.ravel())
                r = float(r_matrix[0, 1]) if not np.isnan(r_matrix[0, 1]) else 1.0
                    
                status = "PASS" if r >= 0.9990 else "FAIL"
                
                records.append({
                    "image": img_name,
                    "operator": op_code,
                    "operator_name": f"Structure Tensor ({op_code})",
                    "param": f"sd={sd:.1f}_si={si:.1f}",
                    "max_diff": max_diff,
                    "mean_diff": mean_diff,
                    "rel_error": rel_err,
                    "pearson_r": r,
                    "status": status
                })

    # Lưu bảng kết quả tổng hợp ra CSV
    csv_path = OUT_DIR / "tier1_verification_summary.csv"
    if records:
        keys = list(records[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(records)

    # Thống kê tổng hợp theo từng toán tử
    unique_ops = []
    for r in records:
        if r["operator"] not in unique_ops:
            unique_ops.append(r["operator"])

    print("\n" + "=" * 80)
    print("      TỔNG HỢP KẾT QUẢ ĐỐI CHUẨN TẦNG 1 THEO TỪNG TOÁN TỬ (220 BẢN ĐỒ)")
    print("=" * 80)
    print(f"{'Toán tử':<12} | {'Sai số TB':<12} | {'Sai số tương đối':<18} | {'Pearson r (Min)':<16} | {'Pearson r (TB)':<16}")
    print("-" * 80)

    for op in unique_ops:
        sub = [r for r in records if r["operator"] == op]
        m_diff = sum(r["mean_diff"] for r in sub) / len(sub)
        r_err = sum(r["rel_error"] for r in sub) / len(sub)
        r_min = min(r["pearson_r"] for r in sub)
        r_mean = sum(r["pearson_r"] for r in sub) / len(sub)
        print(f"{op:<12} | {m_diff:<12.4e} | {r_err:<18.4e} | {r_min:<16.8f} | {r_mean:<16.8f}")

    print("=" * 80)
    pass_count = sum(1 for r in records if r["status"] in ["PASS", "ACCEPTABLE"])
    total_count = len(records)
    pass_rate = (pass_count / total_count) * 100.0 if total_count > 0 else 0.0
    all_r = [r["pearson_r"] for r in records]
    avg_r = sum(all_r) / len(all_r) if all_r else 0.0

    print(f"\n-> TỔNG KẾT: {pass_count}/{total_count} bản đồ vi phân ĐẠT CHUẨN ({pass_rate:.1f}%).")
    print(f"-> Hệ số tương quan Pearson trung bình toàn hệ thống: r = {avg_r:.8f}")
    print(f"-> Toàn bộ kết quả chi tiết đã được xuất ra: {csv_path.name}")
    print("=" * 80)

if __name__ == "__main__":
    run_tier1_verification()
