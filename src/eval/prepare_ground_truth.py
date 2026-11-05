"""Task 21 (05/11): original/analytic ground truth and a pending human annotation.

Uses scipy.io only to read original MATLAB labels; no feature detector is run.
"""

import argparse
import csv
import io
import json
import math
import re
import tarfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.io import loadmat
import tifffile

from src.eval.common import ROOT, sha256
from src.eval.prepare_data import synthetic_blob


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value, replace=False):
    path = Path(path)
    text = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if path.exists():
        if read_json(path) == value:
            return
        if not replace:
            raise FileExistsError(f"Refusing to overwrite different annotations: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def write_bytes(path, payload):
    path = Path(path)
    if path.exists():
        if path.read_bytes() == payload:
            return
        raise FileExistsError(f"Different source annotation: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def write_array(path, data):
    path = Path(path)
    if path.exists():
        if path.suffix == ".tif":
            old = tifffile.imread(path)
        else:
            with Image.open(path) as image:
                old = np.asarray(image).copy()
        if old.dtype == data.dtype and np.array_equal(old, data):
            return
        raise FileExistsError(f"Different GT already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".tif":
        tifffile.imwrite(path, data, compression=None, photometric="minisblack")
    else:
        Image.fromarray(data).save(path)


def image_array(path):
    with Image.open(path) as image:
        if image.mode != "L":
            raise ValueError(f"Expected grayscale image: {path}")
        return np.asarray(image).copy()


def binary_mask(value, shape):
    if hasattr(value, "toarray"):
        value = value.toarray()
    value = np.asarray(value)
    if value.shape != shape or not np.isin(value, [0, 1, 255]).all():
        raise ValueError(f"Invalid binary mask shape/values: {value.shape}, expected {shape}")
    return (value != 0).astype(np.uint8) * 255


def bsds_annotations(payload, shape):
    content = loadmat(io.BytesIO(payload), struct_as_record=False, squeeze_me=True)
    people = np.atleast_1d(content["groundTruth"])
    result = []
    for person in people:
        boundary = binary_mask(person.Boundaries, shape)
        labels = np.asarray(person.Segmentation)
        if (labels.shape != shape or labels.dtype.kind not in "iu"
                or labels.min() < 1 or labels.max() > 65535):
            raise ValueError("Invalid original BSDS segmentation labels")
        result.append((boundary, labels.astype(np.uint16)))
    if not result:
        raise ValueError("BSDS file contains no annotators")
    return result


def synthetic_truth(entry, actual):
    if not np.array_equal(actual, synthetic_blob(entry)):
        raise ValueError(f"Raw image no longer matches synthetic generator: {entry['name']}")
    sizes = (3., 5., 7., 8.) if entry["model"] == "disk" else (2., 2.8, 4., 5.7)
    objects = []
    for index, ((x, y), size) in enumerate(zip(((52, 64), (132, 70), (80, 170), (188, 180)), sizes), 1):
        item = {"id": index, "x": x, "y": y,
                "radius": float(size if entry["model"] == "disk" else math.sqrt(2)*size)}
        item["disk_radius" if entry["model"] == "disk" else "gaussian_sigma"] = size
        objects.append(item)
    return {"image": entry["name"], "image_sha256": "", "shape": list(actual.shape),
            "coordinate_system": "zero-based; x=column; y=row; pixel units",
            "origin": "analytic_generator", "status": "READY", "polarity": entry["polarity"],
            "model": entry["model"], "radius_definition": "disk radius; Gaussian equivalent LoG radius=sqrt(2)*sigma",
            "objects": objects}


def pending_cell_truth(name, raw, digest):
    return {"image": name, "image_sha256": digest, "shape": list(raw.shape),
            "coordinate_system": "zero-based; x=column; y=row; pixel units",
            "origin": "manual_annotation", "status": "PENDING_ANNOTATION", "polarity": "bright",
            "reviewed": False, "reviewer": "", "objects": [], "ignore_regions": [],
            "radius_definition": "equivalent-area radius=sqrt(bbox_width*bbox_height)/2",
            "protocol": "Annotate every unambiguous fully visible nucleus/cell; one object per separable nucleus. Mark truncated or ambiguous clusters as ignore regions. Review entire image before completion."}


def validate_cell_truth(truth, name, raw, digest):
    if (truth.get("image") != name or truth.get("image_sha256") != digest
            or truth.get("shape") != list(raw.shape) or truth.get("polarity") != "bright"
            or truth.get("origin") not in ("manual_annotation", "manual_with_component_suggestions")):
        raise ValueError("Cell annotation does not match the exact input image/protocol")
    height, width = raw.shape
    boxes = []
    for item in truth.get("objects", []):
        x, y, radius = (float(item[key]) for key in ("x", "y", "radius"))
        box = [float(v) for v in item["bbox_xyxy"]]
        if (len(box) != 4 or not all(math.isfinite(v) for v in [x, y, radius, *box])
                or not (0 <= box[0] < box[2] < width and 0 <= box[1] < box[3] < height)
                or not math.isclose(x, (box[0]+box[2])/2) or not math.isclose(y, (box[1]+box[3])/2)
                or not math.isclose(radius, math.sqrt((box[2]-box[0])*(box[3]-box[1]))/2)):
            raise ValueError("Invalid manually annotated cell box/center/radius")
        boxes.append(box)
        if item.get("annotation_method") == "threshold_component_suggestion":
            if type(item.get("proposal_reviewed")) is not bool:
                raise ValueError("Each automatic suggestion must record whether it was reviewed")
            if truth.get("reviewed") is True and not item["proposal_reviewed"]:
                raise ValueError("Automatic suggestions remain unreviewed; check or delete them before completion")
    if len({tuple(box) for box in boxes}) != len(boxes):
        raise ValueError("Duplicate cell annotations")
    for box in truth.get("ignore_regions", []):
        if (len(box) != 4 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in box)
                or not (0 <= box[0] < box[2] < width and 0 <= box[1] < box[3] < height)):
            raise ValueError("Invalid ignore region")
        if any(box[0] <= item["x"] <= box[2] and box[1] <= item["y"] <= box[3]
               for item in truth.get("objects", [])):
            raise ValueError("Annotated object center falls in an ignored region")
    if truth.get("reviewed") is True:
        if not isinstance(truth.get("reviewer"), str) or not truth["reviewer"].strip() or not boxes:
            raise ValueError("Completed cell GT needs objects and an identified reviewer")
        if truth.get("status") != "READY":
            raise ValueError("Reviewed cell annotations must have READY status")
        return "READY"
    if truth.get("status") not in ("PENDING_ANNOTATION", "DRAFT"):
        raise ValueError("Unreviewed cell annotations cannot be marked READY")
    return truth["status"]


def overlay(raw, mask=None, objects=None, ignores=None):
    rgb = np.repeat(raw[:, :, None], 3, axis=2)
    if mask is not None:
        rgb[np.asarray(mask) > 0] = [0, 255, 255]
    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)
    for box in ignores or []:
        draw.rectangle(tuple(box), outline="orange", width=2)
    for index, item in enumerate(objects or [], 1):
        x, y, radius = item["x"], item["y"], item["radius"]
        pending = item.get("annotation_method") == "threshold_component_suggestion" and not item.get("proposal_reviewed", False)
        color = "magenta" if pending else "lime"
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline=color, width=1)
        draw.text((x+2, y+2), str(index) + ("?" if pending else ""), fill="magenta" if pending else "yellow")
    return image


def prepare(root):
    entries = read_json(root / "data/manifest.json")["images"]
    inventory = {}
    with (root / "data/metadata/dataset_inventory.csv").open(encoding="utf-8-sig") as stream:
        inventory = {row["name"]: row for row in csv.DictReader(stream)}
    names = [entry["name"] for entry in entries]
    if len(names) != 25 or len(set(names)) != 25 or any(not re.fullmatch(r"[a-z0-9_]+", n) for n in names):
        raise ValueError("Expected 25 unique, safe image names")
    for name in names:
        if sha256(root / f"data/raw/{name}.png") != inventory[name]["output_sha256"]:
            raise ValueError(f"Raw input changed since 02/11: {name}")
    gt = root / "data/gt"
    previews = gt / "previews"
    previews.mkdir(parents=True, exist_ok=True)
    archive_path = root / "data/sources/bsds500/archives/BSR_bsds500.tgz"
    archive_hash = sha256(archive_path)
    records = []
    with tarfile.open(archive_path, "r:gz") as archive:
        for entry in entries:
            name, kind = entry["name"], entry["kind"]
            path = root / f"data/raw/{name}.png"
            raw, digest = image_array(path), sha256(path)
            record = {"image": name, "kind": kind, "input": path.relative_to(root).as_posix(),
                      "input_sha256": digest, "shape": list(raw.shape), "status": "READY",
                      "annotators": 0, "objects": 0, "files": [], "sources": [], "notes": ""}
            def register(target, role):
                record["files"].append({"path": target.relative_to(root).as_posix(),
                                        "role": role, "sha256": sha256(target)})
            if kind == "bsds":
                original_id = Path(entry["source"]).stem
                if not original_id.isdigit():
                    raise ValueError("Invalid BSDS source ID")
                member = f"BSR/BSDS500/data/groundTruth/train/{original_id}.mat"
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError(f"Missing BSDS original annotation: {member}")
                payload = source.read()
                annotations = bsds_annotations(payload, raw.shape)
                original = gt / "bsds" / f"{name}.mat"
                write_bytes(original, payload)
                register(original, "original_mat_all_annotators")
                for index, (boundary, labels) in enumerate(annotations, 1):
                    for suffix, data, role in (("boundaries.png", boundary, "boundary_mask"),
                                                ("segments.tif", labels, "region_labels")):
                        target = gt / "bsds" / name / f"annotator_{index:02d}_{suffix}"
                        write_array(target, data)
                        register(target, role)
                record["annotators"] = len(annotations)
                record["sources"] = [{"archive": archive_path.relative_to(root).as_posix(),
                                        "archive_sha256": archive_hash, "member": member}]
                record["notes"] = "All annotators preserved separately; preview shows annotator 01 only"
                preview = overlay(raw, annotations[0][0])
            elif kind == "drive":
                original_id = Path(entry["source"]).stem.split("_")[0]
                if not original_id.isdigit():
                    raise ValueError("Invalid DRIVE source ID")
                masks = {}
                for directory, filename, label in (("1st_manual", f"{original_id}_manual1.gif", "vessels"),
                                                     ("mask", f"{original_id}_training_mask.gif", "fov")):
                    original = root / "data/sources/drive" / directory / filename
                    with Image.open(original) as image:
                        masks[label] = binary_mask(np.asarray(image.convert("L")), raw.shape)
                    target = gt / "drive" / f"{name}_{label}.png"
                    write_array(target, masks[label])
                    register(target, label)
                    record["sources"].append({"path": original.relative_to(root).as_posix(), "sha256": sha256(original)})
                record["annotators"] = 1
                record["notes"] = f"Original masks, no erosion; vessel pixels outside FOV={int(np.count_nonzero((masks['vessels']>0)&(masks['fov']==0)))}"
                preview = overlay(raw, masks["vessels"])
            else:
                target = gt / "blob" / f"{name}.json"
                if kind == "synthetic_blob":
                    truth = synthetic_truth(entry, raw)
                    truth["image_sha256"] = digest
                    write_json(target, truth)
                    record["sources"] = [{"path": "src/eval/prepare_data.py", "sha256": sha256(root/"src/eval/prepare_data.py")}]
                elif kind == "blob":
                    if not target.exists():
                        write_json(target, pending_cell_truth(name, raw, digest))
                    truth = read_json(target)
                    record["status"] = validate_cell_truth(truth, name, raw, digest)
                    pending = sum(item.get("annotation_method") == "threshold_component_suggestion" and not item.get("proposal_reviewed", False) for item in truth["objects"])
                    record["notes"] = f"Manual review required; pending suggestions={pending}; empty/draft labels excluded from evaluation"
                    record["sources"] = [{"path": "data/" + entry["source"], "annotation_origin": truth["origin"]}]
                else:
                    raise ValueError(f"Unexpected image kind: {kind}")
                record["objects"] = len(truth["objects"])
                register(target, "blob_centers_radii")
                preview = overlay(raw, objects=truth["objects"], ignores=truth.get("ignore_regions"))
            preview_path = previews / f"{name}_overlay.png"
            preview.save(preview_path)
            register(preview_path, "preview_only")
            records.append(record)
    write_json(gt/"manifest.json", {"schema_version": 1, "task": "21", "deadline": "2026-11-05",
                                    "coordinates": "zero-based x=column y=row; pixel units",
                                    "images": records}, replace=True)
    table = root / "data/metadata/ground_truth_inventory.csv"
    with table.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["image", "kind", "status", "width", "height", "annotators", "objects", "gt_files", "preview", "notes"])
        writer.writeheader()
        for row in records:
            writer.writerow({"image": row["image"], "kind": row["kind"], "status": row["status"],
                             "width": row["shape"][1], "height": row["shape"][0],
                             "annotators": row["annotators"], "objects": row["objects"],
                             "gt_files": ";".join(item["path"] for item in row["files"] if item["role"] != "preview_only"),
                             "preview": f"data/gt/previews/{row['image']}_overlay.png", "notes": row["notes"]})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        records = prepare(args.root.resolve())
    except (OSError, ValueError, KeyError) as error:
        print(f"Ground-truth preparation error: {error}")
        return 2
    ready = sum(row["status"] == "READY" for row in records)
    print(f"Ground truth READY: {ready}/{len(records)}. Inventory: data/metadata/ground_truth_inventory.csv")
    print("Manual annotation tool: python -m src.eval.annotate_cells")
    return 0 if ready == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
