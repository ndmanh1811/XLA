"""Validated inputs and NumPy evaluation utilities for Duc's task 23.

No scipy.ndimage in the production evaluation path. Coordinates are (x,y)
in pixels; edge tolerance uses Euclidean distance <= 2, including equality.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import tifffile
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "outputs/metrics/duc_08_11"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and not fields:
        raise ValueError(f"Cannot write a schema-less empty report: {path}")
    fields = fields or list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def strict_config(path=None):
    path = Path(path or ROOT / "config.yaml")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise ValueError("config.yaml must be a mapping")
    def no_null(obj, prefix="config"):
        if obj is None:
            raise ValueError(f"Missing measured value: {prefix}")
        if isinstance(obj, dict):
            for k, v in obj.items():
                no_null(v, f"{prefix}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                no_null(v, f"{prefix}[{i}]")
    no_null(cfg)
    for key in ("kernel_k", "border_mode", "featurej_normalized", "eigen_order",
                "sigmas", "sigmas_blob", "structure_pairs", "tier1_images"):
        if key not in cfg:
            raise ValueError(f"Missing config key: {key}")
    for key in ("gauss", "lx", "lxx"):
        v = cfg["kernel_k"].get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v <= 0:
            raise ValueError(f"Invalid kernel_k.{key}: {v}")
    for key in ("derivatives", "laplacian", "hessian", "edges", "structure"):
        if type(cfg["featurej_normalized"].get(key)) is not bool:
            raise ValueError(f"featurej_normalized.{key} must be an explicit bool")
    if cfg["border_mode"] not in ("reflect", "mirror") or cfg["eigen_order"] not in ("absolute", "algebraic"):
        raise ValueError("Invalid border_mode/eigen_order")
    for key in ("sigmas", "sigmas_blob"):
        vals = cfg[key]
        if not isinstance(vals, list) or not vals or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v <= 0 for v in vals
        ) or sorted(set(vals)) != vals:
            raise ValueError(f"Invalid increasing scale grid: {key}")
    pairs = cfg["structure_pairs"]
    if not isinstance(pairs, list) or not pairs or any(
        not isinstance(p, list) or len(p) != 2 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v <= 0 for v in p
        ) for p in pairs
    ):
        raise ValueError("Invalid structure_pairs")
    names = cfg["tier1_images"]
    if not isinstance(names, list) or len(names) != 5 or len(set(names)) != 5 or any(
        not isinstance(n, str) or Path(n).name != n or "/" in n or "\\" in n for n in names
    ):
        raise ValueError("Expected five unique tier1 image stems")
    return cfg


def validate_inputs(root=ROOT):
    """Fail closed: all 25 prepared uint8 inputs and every READY GT hash."""
    root = Path(root)
    with (root / "data/metadata/dataset_inventory.csv").open(encoding="utf-8-sig") as f:
        inventory = list(csv.DictReader(f))
    gt = json.loads((root / "data/gt/manifest.json").read_text(encoding="utf-8"))["images"]
    expected = {f"{kind}_{i:02d}" for kind, n in (("bsds", 10), ("drive", 10), ("blob", 5)) for i in range(1, n + 1)}
    if len(inventory) != 25 or len(gt) != 25 or {r["name"] for r in inventory} != expected or {r["image"] for r in gt} != expected:
        raise ValueError("Dataset/GT must contain exactly the 25 planned images")
    evidence = []
    for r in inventory:
        p = root / r["output"]
        a = np.asarray(Image.open(p))
        if a.ndim != 2 or a.dtype != np.uint8 or min(a.shape) < 256 or sha256(p) != r["output_sha256"]:
            raise ValueError(f"Invalid/changed raw input: {p}")
    for r in gt:
        if r["status"] != "READY":
            raise ValueError(f"GT not READY: {r['image']}")
        a = np.asarray(Image.open(root / r["input"]))
        if tuple(r["shape"]) != a.shape:
            raise ValueError(f"GT shape mismatch: {r['image']}")
        files = [{"path": r["input"], "sha256": r["input_sha256"], "role": "raw"}] + r["files"]
        for entry in files:
            p = root / entry["path"]
            if not p.is_file() or sha256(p) != entry["sha256"]:
                raise ValueError(f"GT/input checksum mismatch: {p}")
            evidence.append({"image": r["image"], **entry})
        if r["image"].startswith("blob_"):
            b = json.loads((root / f"data/gt/blob/{r['image']}.json").read_text(encoding="utf-8"))
            needs_review = b.get("origin") != "analytic_generator"
            if b["status"] != "READY" or (needs_review and b.get("reviewed") is not True) or any(
                o.get("proposal_reviewed") is False for o in b["objects"]
            ):
                raise ValueError(f"Unreviewed blob annotations: {r['image']}")
            if b["image_sha256"] != r["input_sha256"] or b["polarity"] not in ("bright", "dark"):
                raise ValueError(f"Blob input/polarity mismatch: {r['image']}")
    return gt, evidence


def read_map(path, shape):
    path = Path(path)
    with tifffile.TiffFile(path) as tf:
        if len(tf.pages) != 1 or int(tf.pages[0].compression) != 1:
            raise ValueError(f"Expected single-page uncompressed TIFF: {path}")
        a = tf.asarray()
    if a.shape != tuple(shape) or a.dtype != np.float32 or not np.isfinite(a).all():
        raise ValueError(f"Invalid shape/dtype/values: {path}")
    return a.astype(np.float64)


def normalize_scale(array, sigma, order, source, command, cfg):
    if source not in ("python", "fiji"):
        raise ValueError(source)
    already = source == "fiji" and cfg["featurej_normalized"][command]
    return np.asarray(array, dtype=np.float64) * (1.0 if already else float(sigma) ** order)


def binary_dilation(mask, structure):
    mask = np.asarray(mask, dtype=bool)
    structure = np.asarray(structure, dtype=bool)
    ry, rx = np.array(structure.shape) // 2
    pad = np.pad(mask, ((ry, ry), (rx, rx)), constant_values=False)
    h, w = mask.shape
    out = np.zeros_like(mask)
    for y, x in np.argwhere(structure):
        out |= pad[y:y + h, x:x + w]
    return out


def erode_square(mask, radius):
    """Square kernel support erosion, outside image is false, O(HW)."""
    if radius < 0 or int(radius) != radius:
        raise ValueError("radius must be a nonnegative integer")
    radius = int(radius)
    a = np.pad(np.asarray(mask, dtype=np.int64), radius)
    ii = np.pad(a, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    n = 2 * radius + 1
    sums = ii[n:, n:] - ii[:-n, n:] - ii[n:, :-n] + ii[:-n, :-n]
    return sums == n * n


def label(mask, structure=None):
    """8-connected components using row runs and union-find (NumPy/Python)."""
    if structure is not None and not np.array_equal(structure, np.ones((3, 3))):
        raise ValueError("Only 8-connectivity is supported")
    mask = np.asarray(mask, dtype=bool)
    out = np.zeros(mask.shape, dtype=np.int32)
    parent = [0]
    runs = []
    previous = []
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for y, row in enumerate(mask):
        delta = np.diff(np.pad(row.astype(np.int8), (1, 1)))
        starts, ends = np.flatnonzero(delta == 1), np.flatnonzero(delta == -1) - 1
        current = []
        j = 0
        for x0, x1 in zip(starts.tolist(), ends.tolist()):
            idx = len(parent)
            parent.append(idx)
            current.append((x0, x1, idx))
            runs.append((y, x0, x1, idx))
            while j < len(previous) and previous[j][1] < x0 - 1:
                j += 1
            k = j
            while k < len(previous) and previous[k][0] <= x1 + 1:
                a, b = find(idx), find(previous[k][2])
                if a != b:
                    parent[max(a, b)] = min(a, b)
                k += 1
        previous = current
    roots = [find(i) for i in range(len(parent))]
    unique = {r: j for j, r in enumerate(sorted(set(roots)))}
    lut = [unique[r] for r in roots]
    for y, x0, x1, idx in runs:
        out[y, x0:x1 + 1] = lut[idx]
    return out, len(unique) - 1


def in_ignore(x, y, boxes):
    return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in boxes)


def match_blobs(objects, detections, boxes=()):
    """Maximum-cardinality one-to-one matching with both geometric gates.

    Returns original GT/detection indices; detections with centers inside an
    inclusive ignore rectangle are excluded before matching and FP counting.
    """
    gt_ids = [i for i, o in enumerate(objects) if not in_ignore(o["x"], o["y"], boxes)]
    pred_ids = [i for i, d in enumerate(detections) if not in_ignore(d[1], d[0], boxes)]
    edges = {}
    for i in gt_ids:
        g = objects[i]
        if not np.isfinite([g["x"], g["y"], g["radius"]]).all() or g["radius"] <= 0:
            raise ValueError("Invalid GT geometry")
        candidates = []
        for j in pred_ids:
            y, x, _, radius, _ = detections[j]
            dist = float(np.hypot(g["x"] - x, g["y"] - y))
            err = abs(radius - g["radius"]) / g["radius"]
            if dist <= 2.0 and err <= .20 + 1e-12:
                candidates.append((dist, err, j))
        edges[i] = [j for _, _, j in sorted(candidates)]
    assigned = {}
    def augment(i, seen):
        for j in edges[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in assigned or augment(assigned[j], seen):
                assigned[j] = i
                return True
        return False
    for i in gt_ids:
        augment(i, set())
    pairs = sorted((i, j) for j, i in assigned.items())
    return pairs, gt_ids, pred_ids


def scores(tp, predicted, actual):
    if not 0 <= tp <= min(predicted, actual):
        raise ValueError("Inconsistent TP/prediction/GT counts")
    precision = tp / predicted if predicted else 0.0
    recall = tp / actual if actual else 0.0
    f1 = 2 * tp / (predicted + actual) if predicted + actual else 0.0
    return precision, recall, f1
