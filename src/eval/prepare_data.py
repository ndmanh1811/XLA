"""Prepare input images for task 20, due 02/11; no GT or evaluation pipeline.

Run: python -m src.eval.prepare_data --manifest data/manifest.json
"""

import argparse
import csv
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

from src.eval.common import ROOT, sha256, write_float_tiff


def write_png(path, array):
    path = Path(path)
    array = np.asarray(array)
    if array.dtype != np.uint8 or array.ndim != 2:
        raise ValueError("Dataset input must be grayscale uint8")
    if path.exists():
        with Image.open(path) as image:
            if image.mode == "L" and np.array_equal(np.asarray(image), array):
                return
        raise FileExistsError(f"Refusing to replace different data: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array).save(path)


def create_calibration(root):
    """Input images for the day 1-2 calibration preparation in INSTRUCTIONS.md."""
    coord = np.arange(256, dtype=np.float64) - 128
    x, y = np.meshgrid(coord, coord)
    impulse = np.zeros((101, 101), dtype=np.float64)
    impulse[50, 50] = 1.0
    border = np.zeros((256, 256), dtype=np.float64)
    border[[0, -1], :] = 1.0
    border[:, [0, -1]] = 1.0
    for name, data in {"ramp": x, "parabola": x*x / 2,
                       "saddle": x*x / 2 - y*y, "dirac": impulse,
                       "bright_border": border}.items():
        write_float_tiff(root / "data/calib" / f"{name}.tif", data)


def read_original(path):
    with Image.open(path) as image:
        if getattr(image, "n_frames", 1) != 1:
            raise ValueError(f"{path}: multipage input is unsupported")
        data = np.asarray(image)
    if data.dtype != np.uint8 or data.ndim not in (2, 3):
        raise ValueError(f"{path}: expected uint8 grayscale or RGB source")
    return data


def synthetic_blob(entry):
    polarity, model = entry["polarity"], entry["model"]
    if polarity not in ("bright", "dark") or model not in ("disk", "gaussian"):
        raise ValueError("Invalid synthetic blob polarity/model")
    y, x = np.mgrid[:256, :256]
    sizes = (3., 5., 7., 8.) if model == "disk" else (2., 2.8, 4., 5.7)
    data = np.zeros((256, 256), dtype=np.float64)
    for (cx, cy), size in zip(((52, 64), (132, 70), (80, 170), (188, 180)), sizes):
        distance2 = (x - cx)**2 + (y - cy)**2
        data += 220 * ((distance2 <= size**2) if model == "disk"
                       else np.exp(-distance2 / (2 * size**2)))
    data = np.clip(np.rint(data), 0, 255).astype(np.uint8)
    return 255 - data if polarity == "dark" else data


def prepare_entry(entry, base, root):
    name, kind = entry["name"], entry["kind"]
    if kind == "synthetic_blob":
        data = synthetic_blob(entry)
        source, source_hash = "generated:src/eval/prepare_data.py", sha256(__file__)
        conversion = f"NumPy {entry['model']}; polarity={entry['polarity']}"
    else:
        value = entry.get("source")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Missing source image path")
        path = Path(value)
        if path.is_absolute():
            raise ValueError("Source paths must be relative to the manifest directory")
        path = (base / path).resolve()
        project = base.resolve().parent
        try:
            relative_source = path.relative_to(project).as_posix()
        except ValueError as error:
            raise ValueError("Source image must be inside the project for portable handoff") from error
        if not path.is_file():
            raise FileNotFoundError(f"Missing source image: {path}")
        source, source_hash = relative_source, sha256(path)
        data = read_original(path)
        if kind in ("bsds", "drive"):
            if data.ndim != 3 or data.shape[2] != 3:
                raise ValueError(f"{kind} needs the original RGB image")
            if kind == "bsds":
                # Exact integer coefficients avoid floating sum-order differences
                # around half-integer values. np.rint uses ties-to-even.
                numerator = data.astype(np.int64) @ np.array([299, 587, 114], dtype=np.int64)
                data = np.rint(numerator / 1000.0).astype(np.uint8)
                conversion = "BT.601 once; nearest ties-to-even; original size"
            else:
                data = data[:, :, 1]
                conversion = "RGB green channel; original size"
        elif kind == "blob":
            if data.ndim != 2 or path.suffix.lower() not in (".png", ".tif", ".tiff"):
                raise ValueError("Biological source must be lossless grayscale uint8 PNG/TIFF")
            conversion = "Existing grayscale uint8; original size; no rescaling"
        else:
            raise ValueError(f"Unsupported image kind: {kind}")
    if min(data.shape) < 256:
        raise ValueError("Dataset images must be at least 256 x 256; no automatic resizing")
    output = root / "data/raw" / f"{name}.png"
    write_png(output, data)
    return {"source": source, "source_sha256": source_hash,
            "output": output.relative_to(root).as_posix(),
            "output_sha256": sha256(output), "width": data.shape[1], "height": data.shape[0],
            "dtype": "uint8", "conversion": conversion, "minimum": int(data.min()),
            "maximum": int(data.max())}


def prepare_manifest(path, root):
    entries = json.loads(path.read_text(encoding="utf-8"))["images"]
    names = [entry["name"] for entry in entries]
    if len(names) != len(set(names)) or any(not re.fullmatch(r"[a-z0-9_]+", name) for name in names):
        raise ValueError("Image names must be unique and contain only a-z, 0-9, underscore")
    counts = {kind: sum(entry["kind"] == kind for entry in entries)
              for kind in ("bsds", "drive", "blob", "synthetic_blob")}
    if (len(entries) != 25 or counts["bsds"] != 10 or counts["drive"] != 10
            or counts["blob"] + counts["synthetic_blob"] != 5 or counts["blob"] < 1):
        raise ValueError("Dataset requires 10 BSDS + 10 DRIVE + 5 blobs, including biological data")
    records = []
    for entry in entries:
        record = {"name": entry["name"], "kind": entry["kind"], "status": "MISSING_OR_INVALID",
                  "source_reference": entry.get("source_reference", ""),
                  "characteristics": entry.get("characteristics", ""),
                  "source": "", "source_sha256": "", "output": "", "output_sha256": "",
                  "width": "", "height": "", "dtype": "", "conversion": "",
                  "minimum": "", "maximum": "", "detail": ""}
        try:
            if not record["source_reference"] or not record["characteristics"]:
                raise ValueError("Both source_reference and characteristics are required")
            record.update(prepare_entry(entry, path.parent, root))
            record["status"] = "PREPARED"
        except (OSError, ValueError, KeyError) as error:
            record["detail"] = str(error)
        records.append(record)
    report = root / "data/metadata/dataset_inventory.csv"
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    return records, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--calib-only", action="store_true")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if not args.calib_only and args.manifest is None:
        parser.error("Use --calib-only or --manifest")
    root = args.root.resolve()
    create_calibration(root)
    print("Calibration input images: 5 uncompressed float32 TIFFs")
    if args.calib_only:
        return 0
    records, report = prepare_manifest(args.manifest.resolve(), root)
    ready = sum(row["status"] == "PREPARED" for row in records)
    print(f"Dataset: {ready}/{len(records)} prepared. Inventory: {report}")
    return 0 if ready == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
