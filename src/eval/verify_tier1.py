"""
verify_tier1.py - Kiểm chứng số học Tầng 1 (Python Core vs FeatureJ / Fiji)
Đối chuẩn định lượng trên 5 ảnh đại diện: bsds_01, bsds_02, drive_01, blob_01, blob_02
tại các tỷ lệ sigma in [1.0, 2.0, 4.0, 8.0] và Structure Tensor (sd, si).

Tiêu chí nghiệm thu chuẩn (quyuoc.md):
- STRICT:   rel_err < 1e-4  AND  r > 0.9999
- RELAXED:  rel_err < 1e-2  AND  r > 0.9999
- Pearson r > 0.9999 (độ tương quan hình học gần như tuyệt đối 1.0)
- Sai số tương đối max|Δ| / max|ref| cực nhỏ sau khi crop bỏ dải biên k*sigma px.

Lưu ý: Không bỏ qua im lặng khi thiếu file. Tất cả 220 bản đồ vi phân kỳ vọng
được ghi rõ trạng thái: PASS_STRICT / PASS_RELAXED / ACCEPTABLE / FAIL /
MISSING / SKIP_SHAPE.
"""

import sys
from pathlib import Path
import hashlib
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
FJ_DIR = ROOT / "outputs" / "fiji_java"
OUT_DIR = ROOT / "outputs"

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

def find_fiji_file(img_name: str, op_code: str, suffix: str) -> Path:
    """Tìm file FeatureJ chính thức do exporter xuất từ data/raw/ (tiền tố fiji_)."""
    p = FJ_DIR / f"fiji_{img_name}_{op_code}_{suffix}.tif"
    return p

def evaluate_pair(py_arr, fj_arr, op_code, s):
    """Crop, tính sai số và Pearson r giữa mảng Python và Fiji."""
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
    rmse = float(np.sqrt(np.mean((py_c - fj_c) ** 2)))
    ref_peak = float(np.max(np.abs(fj_c)))
    rel_err = max_diff / (ref_peak + 1e-12)

    # PSNR chỉ hợp lệ về mặt vật lý với ảnh làm mịn Gauss L (dải [0, 255])
    if op_code == "gauss":
        psnr_val = 20 * np.log10(255.0 / (rmse + 1e-12))
        psnr_str = f"{psnr_val:.2f} dB"
    else:
        psnr_str = "N/A (Signed)"

    # Pearson r với xử lý an toàn cho vùng phẳng / zero variance
    std_py = float(np.std(py_c))
    std_fj = float(np.std(fj_c))
    if std_py < 1e-12 or std_fj < 1e-12:
        r = 1.0 if max_diff < 1e-4 else 0.0
    else:
        r_matrix = np.corrcoef(py_c.ravel(), fj_c.ravel())
        r = float(r_matrix[0, 1]) if not np.isnan(r_matrix[0, 1]) else (1.0 if max_diff < 1e-4 else 0.0)

    return {
        "max_diff": max_diff,
        "mean_diff": mean_diff,
        "rmse": rmse,
        "psnr": psnr_str,
        "rel_error": rel_err,
        "pearson_r": r,
    }

def status_from_metrics(rel_err, r):
    """Trả về status theo tiêu chí nghiêm ngat (strict) cua quy uoc."""
    if rel_err < 1e-4 and r > 0.9999:
        return "PASS_STRICT"
    elif rel_err < 1e-2 and r > 0.9999:
        return "PASS_RELAXED"
    elif r >= 0.9990:
        return "ACCEPTABLE"
    else:
        return "FAIL"

def _sha256_file(path: Path) -> str:
    """Tính SHA256 theo luồng để không nạp toàn bộ TIFF vào RAM."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_fiji_java_manifest() -> bool:
    """Đối chiếu 220 TIFF với kích thước và SHA256 trong manifest.

    Trả về True nếu toàn bộ khớp; False nếu thiếu file, sai kích thước,
    sai hash hoặc manifest không đủ 220 dòng.
    """
    manifest_path = OUT_DIR / "metrics" / "fiji_java_manifest.csv"
    if not manifest_path.exists():
        print(f"   [!] Cảnh báo: thiếu manifest {manifest_path}; bỏ qua kiểm tra SHA256.")
        return True

    errors = []
    checked = 0
    manifest_names = set()
    with open(manifest_path, "r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if not any(row.values()):
                continue
            name = (row.get("filename") or "").strip()
            if not name:
                errors.append("Manifest có dòng thiếu filename")
                continue
            manifest_names.add(name)

            path = FJ_DIR / name
            if not path.exists():
                errors.append(f"Thiếu file: {name}")
                continue

            expected_size = (row.get("size_bytes") or "").strip()
            if expected_size:
                actual_size = path.stat().st_size
                if int(expected_size) != actual_size:
                    errors.append(
                        f"Sai kích thước: {name} ({actual_size} != {expected_size})"
                    )
            else:
                errors.append(f"Manifest thiếu size_bytes: {name}")

            expected_hash = (row.get("sha256") or "").strip().lower()
            if not expected_hash:
                errors.append(f"Manifest thiếu sha256: {name}")
            actual_hash = _sha256_file(path)
            if expected_hash and expected_hash != actual_hash:
                errors.append(f"Sai SHA256: {name}")

            checked += 1

    if checked != 220:
        errors.append(f"Manifest có {checked} dòng, kỳ vọng 220")

    actual_names = {path.name for path in FJ_DIR.glob("*.tif")}
    extra = sorted(actual_names - manifest_names)
    if extra:
        errors.append(
            f"Thư mục có {len(extra)} TIFF thừa ngoài manifest, ví dụ: {extra[:5]}"
        )

    if errors:
        print(f"   ✗ SHA256: {len(errors)} lỗi toàn vẹn dữ liệu fiji_java")
        for err in errors[:10]:
            print(f"      - {err}")
        if len(errors) > 10:
            print(f"      ... và {len(errors) - 10} lỗi khác")
        return False

    print(f"   ✓ SHA256: {checked}/220 TIFF khớp kích thước và mã băm.")
    return True


def ensure_fiji_java_data():
    """Tự động giải nén outputs/fiji_java_tier1.zip nếu thư mục outputs/fiji_java chưa đủ 220 file."""
    import zipfile
    zip_path = OUT_DIR / "fiji_java_tier1.zip"
    if not FJ_DIR.exists() or len(list(FJ_DIR.glob("*.tif"))) < 220:
        if zip_path.exists():
            print(f"-> Đang tự động giải nén {zip_path.name} vào {FJ_DIR}...")
            FJ_DIR.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(FJ_DIR)
            print(f"   ✓ Đã giải nén {len(list(FJ_DIR.glob('*.tif')))} tệp TIFF.")
        else:
            print(f"   [!] Cảnh báo: Chưa có {zip_path} để giải nén tự động.")

    if not verify_fiji_java_manifest():
        raise RuntimeError(
            "Dữ liệu outputs/fiji_java không khớp manifest SHA256. "
            "Hãy xóa thư mục này và chạy lại để giải nén từ ZIP chuẩn."
        )

def run_tier1_verification():
    print("=" * 80)
    print("      BÁO CÁO NGHIỆM THU KIỂM CHỨNG ĐỐI CHUẨN SỐ HỌC TẦNG 1")
    print("            PYTHON CORE ENGINE vs FIJI / FEATUREJ")
    print("=" * 80)

    ensure_fiji_java_data()

    records = []
    expected_count = 0
    missing_count = 0
    skip_shape_count = 0

    for img_name in TIER1_IMAGES:
        print(f"\n-> Đang kiểm chứng đối chuẩn cho ảnh: {img_name}...")

        # 1. Kiểm tra 10 toán tử vi phân ở 4 tỷ lệ chuẩn
        for op_code, op_name in OPERATORS:
            for s in SIGMAS:
                expected_count += 1
                py_file = PY_DIR / f"py_{img_name}_{op_code}_s{s:.1f}.tif"
                fj_file = find_fiji_file(img_name, op_code, f"s{s:.1f}")

                if not py_file.exists() or not fj_file.exists():
                    missing_count += 1
                    records.append({
                        "image": img_name,
                        "operator": op_code,
                        "operator_name": op_name,
                        "param": f"s={s:.1f}",
                        "max_diff": None,
                        "mean_diff": None,
                        "rmse": None,
                        "psnr": None,
                        "rel_error": None,
                        "pearson_r": None,
                        "status": "MISSING",
                        "reason": "missing_py_or_fiji_file",
                    })
                    continue

                py_arr = tifffile.imread(str(py_file)).astype(np.float64)
                fj_arr = tifffile.imread(str(fj_file)).astype(np.float64)

                if py_arr.shape != fj_arr.shape:
                    skip_shape_count += 1
                    records.append({
                        "image": img_name,
                        "operator": op_code,
                        "operator_name": op_name,
                        "param": f"s={s:.1f}",
                        "max_diff": None,
                        "mean_diff": None,
                        "rmse": None,
                        "psnr": None,
                        "rel_error": None,
                        "pearson_r": None,
                        "status": "SKIP_SHAPE",
                        "reason": f"shape_mismatch_py_{py_arr.shape}_vs_fiji_{fj_arr.shape}",
                    })
                    continue

                metrics = evaluate_pair(py_arr, fj_arr, op_code, s)
                status = status_from_metrics(metrics["rel_error"], metrics["pearson_r"])

                records.append({
                    "image": img_name,
                    "operator": op_code,
                    "operator_name": op_name,
                    "param": f"s={s:.1f}",
                    "max_diff": metrics["max_diff"],
                    "mean_diff": metrics["mean_diff"],
                    "rmse": metrics["rmse"],
                    "psnr": metrics["psnr"],
                    "rel_error": metrics["rel_error"],
                    "pearson_r": metrics["pearson_r"],
                    "status": status,
                    "reason": "",
                })

        # 2. Kiểm tra Structure Tensor ở 2 cặp (sd, si)
        for sd, si in ST_PAIRS:
            for op_code in ["st-l1", "st-l2"]:
                expected_count += 1
                py_file = PY_DIR / f"py_{img_name}_{op_code}_sd{sd:.1f}_si{si:.1f}.tif"
                fj_file = find_fiji_file(img_name, op_code, f"sd{sd:.1f}_si{si:.1f}")

                if not py_file.exists() or not fj_file.exists():
                    missing_count += 1
                    records.append({
                        "image": img_name,
                        "operator": op_code,
                        "operator_name": f"Structure Tensor ({op_code})",
                        "param": f"sd={sd:.1f}_si={si:.1f}",
                        "max_diff": None,
                        "mean_diff": None,
                        "rmse": None,
                        "psnr": None,
                        "rel_error": None,
                        "pearson_r": None,
                        "status": "MISSING",
                        "reason": "missing_py_or_fiji_file",
                    })
                    continue

                py_arr = tifffile.imread(str(py_file)).astype(np.float64)
                fj_arr = tifffile.imread(str(fj_file)).astype(np.float64)

                if py_arr.shape != fj_arr.shape:
                    skip_shape_count += 1
                    records.append({
                        "image": img_name,
                        "operator": op_code,
                        "operator_name": f"Structure Tensor ({op_code})",
                        "param": f"sd={sd:.1f}_si={si:.1f}",
                        "max_diff": None,
                        "mean_diff": None,
                        "rmse": None,
                        "psnr": None,
                        "rel_error": None,
                        "pearson_r": None,
                        "status": "SKIP_SHAPE",
                        "reason": f"shape_mismatch_py_{py_arr.shape}_vs_fiji_{fj_arr.shape}",
                    })
                    continue

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
                rmse = float(np.sqrt(np.mean((py_c - fj_c) ** 2)))
                ref_peak = float(np.max(np.abs(fj_c)))
                rel_err = max_diff / (ref_peak + 1e-12)
                psnr_str = "N/A (Signed)"

                std_py = float(np.std(py_c))
                std_fj = float(np.std(fj_c))
                if std_py < 1e-12 or std_fj < 1e-12:
                    r = 1.0 if max_diff < 1e-4 else 0.0
                else:
                    r_matrix = np.corrcoef(py_c.ravel(), fj_c.ravel())
                    r = float(r_matrix[0, 1]) if not np.isnan(r_matrix[0, 1]) else (1.0 if max_diff < 1e-4 else 0.0)

                status = status_from_metrics(rel_err, r)

                records.append({
                    "image": img_name,
                    "operator": op_code,
                    "operator_name": f"Structure Tensor ({op_code})",
                    "param": f"sd={sd:.1f}_si={si:.1f}",
                    "max_diff": max_diff,
                    "mean_diff": mean_diff,
                    "rmse": rmse,
                    "psnr": psnr_str,
                    "rel_error": rel_err,
                    "pearson_r": r,
                    "status": status,
                    "reason": "",
                })

    found_count = expected_count - missing_count - skip_shape_count

    # Lưu bảng kết quả tổng hợp ra CSV
    csv_path = OUT_DIR / "tier1_verification_summary.csv"
    keys = [
        "image", "operator", "operator_name", "param",
        "max_diff", "mean_diff", "rmse", "psnr",
        "rel_error", "pearson_r", "status", "reason",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(records)

    # Thống kê tổng hợp theo từng toán tử (chi cac record co so lieu)
    valid_records = [r for r in records if r["status"] not in ("MISSING", "SKIP_SHAPE")]
    unique_ops = []
    for r in valid_records:
        if r["operator"] not in unique_ops:
            unique_ops.append(r["operator"])

    print("\n" + "=" * 80)
    print("      TỔNG HỢP KẾT QUẢ ĐỐI CHUẨN TẦNG 1 THEO TỪNG TOÁN TỬ")
    print("=" * 80)
    print(f"{'Toán tử':<12} | {'Sai số TB':<12} | {'Sai số tương đối':<18} | {'Pearson r (Min)':<16} | {'Pearson r (TB)':<16}")
    print("-" * 80)

    for op in unique_ops:
        sub = [r for r in valid_records if r["operator"] == op]
        m_diff = sum(r["mean_diff"] for r in sub) / len(sub)
        r_err = sum(r["rel_error"] for r in sub) / len(sub)
        r_min = min(r["pearson_r"] for r in sub)
        r_mean = sum(r["pearson_r"] for r in sub) / len(sub)
        print(f"{op:<12} | {m_diff:<12.4e} | {r_err:<18.4e} | {r_min:<16.8f} | {r_mean:<16.8f}")

    print("=" * 80)
    pass_strict = sum(1 for r in records if r["status"] == "PASS_STRICT")
    pass_relaxed = sum(1 for r in records if r["status"] == "PASS_RELAXED")
    acceptable = sum(1 for r in records if r["status"] == "ACCEPTABLE")
    fail = sum(1 for r in records if r["status"] == "FAIL")
    all_r = [r["pearson_r"] for r in valid_records]
    avg_r = sum(all_r) / len(all_r) if all_r else 0.0

    print(f"\n-> TỔNG KẾT TIÊU CHUẨN:")
    print(f"   Kỳ vọng:   {expected_count} bản đồ vi phân")
    print(f"   Có sẵn:    {found_count} bản đồ")
    print(f"   Thiếu:     {missing_count} bản đồ (MISSING)")
    print(f"   Bỏ qua:    {skip_shape_count} bản đồ (SKIP_SHAPE)")
    print(f"   PASS_STRICT:  {pass_strict}  (rel < 1e-4 AND r > 0.9999)")
    print(f"   PASS_RELAXED: {pass_relaxed}  (rel < 1e-2 AND r > 0.9999)")
    print(f"   ACCEPTABLE:   {acceptable}  (r >= 0.9990, chưa đạt strict/relaxed)")
    print(f"   FAIL:         {fail}")
    print(f"   Hệ số tương quan Pearson trung bình toàn hệ thống: r = {avg_r:.8f}")
    print(f"-> Toàn bộ kết quả chi tiết đã được xuất ra: {csv_path.name}")
    print("=" * 80)

if __name__ == "__main__":
    run_tier1_verification()
