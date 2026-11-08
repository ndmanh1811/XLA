"""Task 23: raw TIFF fidelity, strict criteria, separate core/border reports."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eval.metric_utils import RESULTS, read_map, strict_config, validate_inputs, write_csv

OPERATORS = ("gauss", "lx", "ly", "lxx", "lxy", "lyy", "grad", "lap", "hess-l1", "hess-l2")


def expected_maps(cfg):
    for image in cfg["tier1_images"]:
        for sigma in cfg["sigmas"]:
            for op in OPERATORS:
                order = 0 if op == "gauss" else 1 if op in ("lx", "ly", "grad") else 2
                key = {0: "gauss", 1: "lx", 2: "lxx"}[order]
                crop = int(np.ceil(cfg["kernel_k"][key] * sigma))
                yield image, op, float(sigma), "", f"{image}_{op}_s{float(sigma)}.tif", crop
        for sd, si in cfg["structure_pairs"]:
            crop = int(np.ceil(cfg["kernel_k"]["lx"] * sd)) + int(np.ceil(cfg["kernel_k"]["gauss"] * si))
            for op in ("st-l1", "st-l2"):
                yield image, op, float(sd), float(si), f"{image}_{op}_sd{float(sd)}_si{float(si)}.tif", crop


def continuous_metrics(py, ref, gaussian=False):
    py, ref = np.asarray(py, dtype=np.float64), np.asarray(ref, dtype=np.float64)
    if py.size == 0 or py.shape != ref.shape or not np.isfinite(py).all() or not np.isfinite(ref).all():
        raise ValueError("Empty, nonfinite or mismatched metric arrays")
    delta = py - ref
    mse = float(np.mean(delta ** 2))
    rmse = float(np.sqrt(mse))
    maximum = float(np.max(np.abs(delta)))
    peak = float(np.max(np.abs(ref)))
    x, y = py.ravel() - np.mean(py), ref.ravel() - np.mean(ref)
    denom = float(np.linalg.norm(x) * np.linalg.norm(y))
    r = float(np.clip(np.dot(x, y) / denom, -1, 1)) if denom > 0 else None
    relative = maximum / peak if peak > 0 else None
    status = "UNDEFINED" if r is None or relative is None else (
        "PASS" if relative < 1e-4 and r > .9999 else "FAIL"
    )
    return dict(n_pixels=int(py.size), mse=mse, mae=float(np.mean(np.abs(delta))),
                rmse=rmse, max_error=maximum, reference_peak=peak,
                relative_error=relative, pearson_r=r,
                psnr_db=(float("inf") if mse == 0 else float(20 * np.log10(255 / rmse))) if gaussian else "",
                psnr_data_range=255 if gaussian else "", status=status,
                reason="zero_reference_or_constant_map" if status == "UNDEFINED" else "")


def run_tier1(cfg=None, gt=None, out_dir=RESULTS, py_dir=None, fiji_dir=None):
    cfg = cfg or strict_config()
    gt = gt if gt is not None else validate_inputs()[0]
    shapes = {r["image"]: r["shape"] for r in gt}
    out_dir = Path(out_dir)
    py_dir = Path(py_dir or ROOT / "outputs/python")
    fiji_dir = Path(fiji_dir or ROOT / "outputs/fiji")
    rows, borders, smoke = [], [], []
    for image, op, sigma, si, suffix, crop in expected_maps(cfg):
        pp, fp = py_dir / ("py_" + suffix), fiji_dir / ("fiji_" + suffix)
        meta = dict(image=image, operator=op, sigma=sigma, sigma_i=si, crop_px=crop,
                    python_file=str(pp.relative_to(ROOT)) if pp.is_relative_to(ROOT) else str(pp),
                    fiji_file=str(fp.relative_to(ROOT)) if fp.is_relative_to(ROOT) else str(fp),
                    reference_source=fiji_dir.name)
        try:
            a, b = read_map(pp, shapes[image]), read_map(fp, shapes[image])
            h, w = a.shape
            if crop <= 0 or 2 * crop >= min(h, w):
                raise ValueError("Crop removes entire core or is nonpositive")
            core = np.zeros((h, w), dtype=bool)
            core[crop:h-crop, crop:w-crop] = True
            measured = continuous_metrics(a[core], b[core], op == "gauss")
            row = {**meta, "region": "core", **measured}
            border = {**meta, "region": "border", **continuous_metrics(a[~core], b[~core], op == "gauss")}
            border["status"] = "INFORMATIONAL"
        except (OSError, ValueError, KeyError) as exc:
            blank = {k: "" for k in continuous_metrics(np.array([1., 2.]), np.array([1., 2.]))}
            row = {**meta, "region": "core", **blank, "status": "MISSING" if not pp.exists() or not fp.exists() else "INVALID", "reason": str(exc)}
            border = {**row, "region": "border"}
        rows.append(row)
        borders.append(border)
        if image == "bsds_01" and sigma == 2.0 and si == "" and op in ("lx", "ly", "lxx"):
            smoke.append(row)
    write_csv(out_dir / "tier1_report.csv", rows)
    write_csv(out_dir / "tier1_border_report.csv", borders)
    write_csv(out_dir / "smoke_test_report.csv", smoke)
    print(f"Tier 1: {len(rows)} maps, {sum(r['status']=='PASS' for r in rows)} PASS (strict), {sum(r['status']=='FAIL' for r in rows)} FAIL", flush=True)
    return rows, borders, smoke


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=RESULTS)
    parser.add_argument("--fiji-dir", type=Path, default=ROOT / "outputs/fiji")
    args = parser.parse_args()
    run_tier1(out_dir=args.out_dir, fiji_dir=args.fiji_dir)
