"""
validate_fiji_outputs.py - Kiểm tra toàn vẹn bộ TIFF đầu ra của ImageJ Macro.

Phạm vi kiểm tra (435 file):
- 423 file do macro hợp nhất `src/fiji/batch_process.ijm` sinh ra.
- 12 file `edge` legacy của các ảnh tier1 không thuộc BSDS
  (`blob_01`, `blob_02`, `drive_01` x 4 sigma), tạo từ commit `61aedec`.
  Hai nhóm này cộng lại đúng 435 file đang có trong `outputs/fiji/`.

Các bước:
1. Dựng bộ tên kỳ vọng từ `config.yaml` (sigma, blob sigma, structure pair,
   tier1 image) và đối chiếu với file thực tế trên đĩa.
2. Đối chiếu `outputs/metrics/fiji_output_manifest.csv`: đủ dòng, không trùng,
   `name_ok=1`, `depth_ok=1`, `bit_depth=32`.
3. Đối chiếu `outputs/metrics/fiji_runtime.csv`: đủ 369 dòng (303 dòng một đầu
   ra + 66 dòng hai đầu ra), phủ đúng 435 file.
4. Kiểm tra định dạng từng TIFF: float32, đúng kích thước ảnh gốc, không
   NaN/Inf.

Script chỉ đọc dữ liệu, không sửa file. Mã thoát 0 nếu PASS, 1 nếu FAIL.

Ví dụ:
    python src/eval/validate_fiji_outputs.py
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.config import (  # noqa: E402
    get_blob_sigmas,
    get_sigmas,
    get_structure_pairs,
    get_tier1_images,
)

DEFAULT_FIJI_DIR = ROOT / "outputs" / "fiji"
DEFAULT_METRICS_DIR = ROOT / "outputs" / "metrics"
DEFAULT_RAW_DIR = ROOT / "data" / "raw"

# 12 file edge legacy: 3 ảnh tier1 không phải BSDS x 4 sigma.
LEGACY_EDGE_IMAGES = ("blob_01", "blob_02", "drive_01")

TIER1_STANDARD_OPS = (
    "gauss", "lx", "ly", "lxx", "lxy", "lyy", "grad", "lap",
    "hess-l1", "hess-l2",
)

EXPECTED_RUNTIME_ROWS = 369
EXPECTED_DOUBLE_OUTPUT_ROWS = 66


def _fmt(value) -> str:
    """Định dạng số sigma giống tên file do macro sinh ra (1.0, 2.8, ...)."""
    return str(float(value))


def _raw_stems(raw_dir: Path):
    return sorted(path.stem for path in raw_dir.glob("*.png"))


def build_expected_sets(raw_stems):
    """Trả về (macro_scope, legacy, all_expected) dưới dạng set tên file."""
    sigmas = get_sigmas()
    blob_sigmas = get_blob_sigmas()
    pairs = get_structure_pairs()
    tier1 = set(get_tier1_images())

    bsds = {stem for stem in raw_stems if stem.startswith("bsds_")}
    drive = {stem for stem in raw_stems if stem.startswith("drive_")}
    blob = {stem for stem in raw_stems if stem.startswith("blob_")}

    macro = set()

    for stem in raw_stems:
        if stem in tier1:
            for sigma in sigmas:
                for op in TIER1_STANDARD_OPS:
                    macro.add(f"fiji_{stem}_{op}_s{_fmt(sigma)}.tif")
            for sd, si in pairs:
                suffix = f"sd{_fmt(sd)}_si{_fmt(si)}"
                macro.add(f"fiji_{stem}_st-l1_{suffix}.tif")
                macro.add(f"fiji_{stem}_st-l2_{suffix}.tif")
        elif stem in bsds:
            for sigma in sigmas:
                macro.add(f"fiji_{stem}_lx_s{_fmt(sigma)}.tif")
                macro.add(f"fiji_{stem}_ly_s{_fmt(sigma)}.tif")
        elif stem in drive:
            for sigma in sigmas:
                macro.add(f"fiji_{stem}_hess-l1_s{_fmt(sigma)}.tif")
                macro.add(f"fiji_{stem}_hess-l2_s{_fmt(sigma)}.tif")

        # FeatureJ Edges chạy cho mọi ảnh BSDS, kể cả ảnh tier1.
        if stem in bsds:
            for sigma in sigmas:
                macro.add(f"fiji_{stem}_edge_s{_fmt(sigma)}.tif")

        # Lưới Laplacian dày cho mọi ảnh blob (set tự bỏ qua file trùng).
        if stem in blob:
            for sigma in blob_sigmas:
                macro.add(f"fiji_{stem}_lap_s{_fmt(sigma)}.tif")

    legacy = {
        f"fiji_{stem}_edge_s{_fmt(sigma)}.tif"
        for stem in LEGACY_EDGE_IMAGES
        for sigma in sigmas
    }
    return macro, legacy, macro | legacy


def read_csv_rows(path: Path):
    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        return [row for row in csv.DictReader(handle) if any(row.values())]


def check_inventory(actual, expected, errors):
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        errors.append(f"Thiếu {len(missing)} file, ví dụ: {missing[:10]}")
    if extra:
        errors.append(f"Thừa {len(extra)} file, ví dụ: {extra[:10]}")
    return missing, extra


def check_manifest(rows, expected, errors):
    names = []
    for row in rows:
        name = (row.get("file") or "").strip()
        if not name:
            continue
        names.append(name)
        if str(row.get("name_ok", "")).strip() not in ("1", "1.0"):
            errors.append(f"Manifest báo name_ok != 1: {name}")
        if str(row.get("depth_ok", "")).strip() not in ("1", "1.0"):
            errors.append(f"Manifest báo depth_ok != 1: {name}")
        try:
            bit_depth = int(float(row.get("bit_depth", "0")))
        except ValueError:
            bit_depth = 0
        if bit_depth != 32:
            errors.append(f"Manifest báo bit_depth != 32: {name}")

    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        errors.append(f"Manifest trùng {len(duplicates)} tên: {duplicates[:10]}")
    check_inventory(set(names), expected, errors)
    return names


def check_runtime(rows, expected, errors):
    covered = set()
    single_rows = 0
    double_rows = 0

    for row in rows:
        files = [part.strip() for part in (row.get("output_files") or "").split(";") if part.strip()]
        if len(files) == 1:
            single_rows += 1
        elif len(files) == 2:
            double_rows += 1
        else:
            errors.append(f"Runtime có {len(files)} output_files: {row}")
        covered.update(files)

        if (row.get("source") or "").strip() != "fiji":
            errors.append(f"Runtime source != fiji: {row}")

        for name in files:
            sigma = (row.get("sigma") or "").strip()
            if sigma and sigma not in name:
                errors.append(f"Runtime sigma={sigma} không khớp tên file: {name}")

    if len(rows) != EXPECTED_RUNTIME_ROWS:
        errors.append(
            f"Runtime có {len(rows)} dòng, kỳ vọng {EXPECTED_RUNTIME_ROWS}"
        )
    if double_rows != EXPECTED_DOUBLE_OUTPUT_ROWS:
        errors.append(
            f"Runtime có {double_rows} dòng hai đầu ra, kỳ vọng {EXPECTED_DOUBLE_OUTPUT_ROWS}"
        )
    if single_rows != EXPECTED_RUNTIME_ROWS - EXPECTED_DOUBLE_OUTPUT_ROWS:
        errors.append(
            f"Runtime có {single_rows} dòng một đầu ra, kỳ vọng "
            f"{EXPECTED_RUNTIME_ROWS - EXPECTED_DOUBLE_OUTPUT_ROWS}"
        )
    check_inventory(covered, expected, errors)
    return single_rows, double_rows


def check_pixels(expected, raw_dir, fiji_dir, errors):
    checked = 0
    dims_cache = {}
    for name in sorted(expected):
        stem = name[len("fiji_"):].split("_", 1)[0]
        # Tên stem có thể chứa dấu gạch dưới (vd. bsds_01) -> lấy tới trước op.
        for op_marker in ("_gauss_", "_lx_", "_ly_", "_lxx_", "_lxy_", "_lyy_",
                          "_grad_", "_lap_", "_hess-l1_", "_hess-l2_",
                          "_edge_", "_st-l1_", "_st-l2_"):
            if op_marker in name:
                stem = name[len("fiji_"):].split(op_marker, 1)[0]
                break

        if stem not in dims_cache:
            img_path = raw_dir / f"{stem}.png"
            if not img_path.exists():
                errors.append(f"Thiếu ảnh gốc để đối chiếu kích thước: {img_path}")
                dims_cache[stem] = None
            else:
                with Image.open(img_path) as img:
                    dims_cache[stem] = (img.height, img.width)
        dims = dims_cache[stem]
        if dims is None:
            continue

        path = fiji_dir / name
        try:
            arr = np.asarray(tifffile.imread(path))
        except Exception as exc:  # pragma: no cover - lỗi I/O hiếm
            errors.append(f"Không đọc được {name}: {exc}")
            continue

        if arr.dtype != np.float32:
            errors.append(f"{name}: dtype={arr.dtype}, kỳ vọng float32")
        if arr.shape != dims:
            errors.append(f"{name}: shape={arr.shape}, kỳ vọng {dims}")
        if not np.all(np.isfinite(arr)):
            errors.append(f"{name}: có NaN/Inf")
        checked += 1
    return checked


def main():
    parser = argparse.ArgumentParser(
        description="Kiểm tra toàn vẹn 435 TIFF đầu ra của ImageJ Macro"
    )
    parser.add_argument("--fiji-dir", type=Path, default=DEFAULT_FIJI_DIR)
    parser.add_argument("--metrics-dir", type=Path, default=DEFAULT_METRICS_DIR)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument(
        "--skip-pixels", action="store_true",
        help="Chỉ kiểm tra danh mục/manifest/runtime, bỏ qua đọc toàn bộ pixel",
    )
    args = parser.parse_args()

    print("=" * 68)
    print("      KIỂM TRA TOÀN VẸN BỘ TIFF FIJI / IMAGEJ MACRO")
    print("=" * 68)

    errors = []
    raw_stems = _raw_stems(args.raw_dir)
    macro, legacy, expected = build_expected_sets(raw_stems)

    print(f"[1/5] Bộ kỳ vọng: {len(macro)} macro + {len(legacy)} legacy = {len(expected)} file")
    if len(macro) != 423 or len(legacy) != 12 or len(expected) != 435:
        errors.append(
            f"Bộ kỳ vọng sai: macro={len(macro)} (423), legacy={len(legacy)} (12), "
            f"tổng={len(expected)} (435)"
        )

    actual = {path.name for path in args.fiji_dir.glob("*.tif")}
    print(f"[2/5] File trên đĩa: {len(actual)} TIFF")
    check_inventory(actual, expected, errors)

    manifest_path = args.metrics_dir / "fiji_output_manifest.csv"
    if not manifest_path.exists():
        errors.append(f"Thiếu manifest: {manifest_path}")
        manifest_names = []
        manifest_rows = []
    else:
        manifest_rows = read_csv_rows(manifest_path)
        manifest_names = check_manifest(manifest_rows, expected, errors)
        print(
            f"[3/5] Manifest: {len(manifest_rows)} dòng, "
            f"{len(set(manifest_names))} tên duy nhất"
        )

    runtime_path = args.metrics_dir / "fiji_runtime.csv"
    if not runtime_path.exists():
        errors.append(f"Thiếu runtime: {runtime_path}")
        single_rows = double_rows = 0
    else:
        runtime_rows = read_csv_rows(runtime_path)
        single_rows, double_rows = check_runtime(runtime_rows, expected, errors)
        print(
            f"[4/5] Runtime: {len(runtime_rows)} dòng "
            f"({single_rows} một đầu ra + {double_rows} hai đầu ra)"
        )

    if args.skip_pixels:
        print("[5/5] Bỏ qua kiểm tra pixel (--skip-pixels)")
    else:
        checked = check_pixels(expected, args.raw_dir, args.fiji_dir, errors)
        print(f"[5/5] Định dạng: đã đọc {checked}/{len(expected)} TIFF float32")

    print("-" * 68)
    if errors:
        print(f"=> FAIL: {len(errors)} lỗi")
        for err in errors[:30]:
            print(f"   - {err}")
        if len(errors) > 30:
            print(f"   ... và {len(errors) - 30} lỗi khác")
        return 1

    print("=> PASS: 435/435 file đúng bộ kỳ vọng, manifest, runtime và định dạng.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
