"""Task 23: both-source accuracy with frozen thresholds and audited matching."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from src.core.detectors import canny_nms, detect_canny, detect_ridge, detect_blob
from src.eval.bsds_threshold_grid import (
    load_bsds_items, evaluate_percentile_grid, evaluate_absolute_grid,
    evaluate_prediction, hysteresis_absolute,
    make_refine_grid, select_best_row,
)
from src.eval.metric_utils import (
    ROOT, RESULTS, strict_config, validate_inputs, read_map, normalize_scale,
    erode_square, match_blobs, scores, write_csv,
)

PROTOCOL = Path(__file__).with_name("metrics_protocol.yaml")


def load_protocol():
    p = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    for key in ("bsds_low_percentiles", "bsds_high_percentiles", "ridge_thresholds",
                "blob_thresholds", "edge_reference_low", "edge_reference_high"):
        vals = p.get(key)
        if not isinstance(vals, list) or not vals or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v < 0 for v in vals
        ):
            raise ValueError(f"Invalid protocol grid: {key}")
        if "percentiles" in key and max(vals) > 100:
            raise ValueError(f"Percentile outside [0,100]: {key}")
    return p


def choose_first_best(rows, score_key="mean_f1"):
    """Tie-break by the first pair/threshold in the predeclared grid."""
    if not rows:
        raise ValueError("No threshold candidates")
    return max(rows, key=lambda r: r[score_key])


def get_map(source, image, op, sigma, shape, cfg, normalized=False):
    prefix = "py" if source == "python" else "fiji"
    array = read_map(ROOT / f"outputs/{source}/{prefix}_{image}_{op}_s{float(sigma)}.tif", shape)
    if normalized:
        command, order = ("derivatives", 1) if op in ("lx", "ly") else (
            ("hessian", 2) if op.startswith("hess") else ("laplacian", 2)
        )
        array = normalize_scale(array, sigma, order, source, command, cfg)
    return array


def record(source, task, image, sigma, precision, recall, f1, **extra):
    return dict(source=source, task=task, image=image, sigma=sigma,
                precision=precision, recall=recall, f1=f1, **extra)


def edges(cfg, protocol, out_dir):
    items = load_bsds_items(ROOT / "data/raw", ROOT / "data/gt", 10)
    if len(items) != 10:
        raise ValueError("Expected all 10 BSDS images")
    records, grids, thresholds, refs, ref_grids = [], [], [], [], []
    for sigma in cfg["sigmas"]:
        print(f"Tier 2 BSDS sigma={sigma}: threshold grid on Python", flush=True)
        maps = {}
        for source in ("python", "fiji"):
            maps[source] = {
                item.stem: tuple(get_map(source, item.stem, op, sigma, item.image.shape, cfg, True) for op in ("lx", "ly"))
                for item in items
            }
        nms = {stem: canny_nms(*pair) for stem, pair in maps["python"].items()}
        grid = evaluate_percentile_grid(nms, items, protocol["bsds_low_percentiles"], protocol["bsds_high_percentiles"])
        # Freeze the coarse-to-fine protocol before evaluation. Selection is
        # performed on Python only; Fiji never selects its own thresholds.
        best = select_best_row(grid)
        if protocol.get("bsds_refine", False):
            low, high = make_refine_grid(best["p_low"], best["p_high"])
            fine = evaluate_percentile_grid(nms, items, low, high)
            grid = [dict(stage="coarse", **r) for r in grid] + [dict(stage="fine", **r) for r in fine]
            best = select_best_row(grid)
        pl, ph = best["p_low"], best["p_high"]
        thresholds.append(dict(sigma=sigma, p_low=pl, p_high=ph, selected_on="python",
                               frozen_for_fiji=True, mean_f1_python=best["mean_f1"], n_images=10))
        grids.extend(dict(sigma=sigma, source="python", selected=(r is best), **r) for r in grid)
        for source in ("python", "fiji"):
            for item in items:
                pred = detect_canny(*maps[source][item.stem], p_low=pl, p_high=ph, return_binary=False)
                m = evaluate_prediction(pred, item)
                records.append(record(source, "edge_bsds", item.stem, sigma,
                                      m["precision"], m["recall"], m["f1"],
                                      p_low=pl, p_high=ph, threshold="", tp="", fp="", fn="",
                                      predicted_count=int(pred.sum()), gt_count=int(item.annotator_positives.sum()),
                                      annotators=int(len(item.gt_boundaries)), iou="",
                                      notes="Euclidean 2px; precision any annotator; recall mean annotator"))
        # Original FeatureJ Edges has its own absolute threshold grid.
        edge_maps = {item.stem: get_map("fiji", item.stem, "edge", sigma, item.image.shape, cfg) for item in items}
        rg = evaluate_absolute_grid(edge_maps, items, protocol["edge_reference_low"], protocol["edge_reference_high"])
        rb = choose_first_best(rg)
        ref_grids.extend(dict(sigma=sigma, source="fiji_edge_reference", selected=(r is rb), **r) for r in rg)
        for item in items:
            pred = hysteresis_absolute(edge_maps[item.stem], rb["t_low"], rb["t_high"])
            m = evaluate_prediction(pred, item)
            refs.append(record("fiji_edge_reference", "native_edge_reference", item.stem, sigma,
                               m["precision"], m["recall"], m["f1"], t_low=rb["t_low"], t_high=rb["t_high"],
                               notes="Absolute native plugin units; separate from matched Canny comparison"))
    write_csv(out_dir / "bsds_threshold_grid.csv", grids)
    write_csv(out_dir / "bsds_selected_thresholds.csv", thresholds)
    write_csv(out_dir / "featurej_edge_reference.csv", refs)
    write_csv(out_dir / "featurej_edge_reference_grid.csv", ref_grids)
    return records


def ridges(cfg, protocol, out_dir):
    images = [f"drive_{i:02d}" for i in range(1, 11)]
    data = {"python": {}, "fiji": {}}
    # Common evaluation support for a max over scales: intersection of valid
    # supports, i.e. square erosion at the largest kernel radius.
    k = max(cfg["kernel_k"]["gauss"], cfg["kernel_k"]["lxx"], cfg["kernel_k"]["lx"])
    radii = {s: int(np.ceil(k * s)) for s in cfg["sigmas"]}
    for image in images:
        target = np.asarray(Image.open(ROOT / f"data/gt/drive/{image}_vessels.png")) > 0
        fov = np.asarray(Image.open(ROOT / f"data/gt/drive/{image}_fov.png")) > 0
        valid = erode_square(fov, max(radii.values()))
        if not valid.any():
            raise ValueError(f"Empty FOV after erosion: {image}")
        for source in ("python", "fiji"):
            responses = []
            for sigma in cfg["sigmas"]:
                a, b = [get_map(source, image, op, sigma, target.shape, cfg, True) for op in ("hess-l1", "hess-l2")]
                response = detect_ridge(a, b, sigma=sigma, beta=.5, polarity="dark")
                response[~erode_square(fov, radii[sigma])] = 0
                responses.append(response)
            data[source][image] = (np.maximum.reduce(responses), target, valid)
    grid = []
    for threshold in protocol["ridge_thresholds"]:
        fs = []
        for response, target, valid in data["python"].values():
            pred, truth = (response >= threshold) & valid, target & valid
            fs.append(scores(int((pred & truth).sum()), int(pred.sum()), int(truth.sum()))[2])
        grid.append(dict(threshold=threshold, mean_f1=float(np.mean(fs)), selected_on="python", n_images=10))
    best = choose_first_best(grid)
    for r in grid:
        r["selected"] = r is best
    write_csv(out_dir / "ridge_threshold_grid.csv", grid)
    records = []
    for source in ("python", "fiji"):
        for image, (response, target, valid) in data[source].items():
            pred, truth = (response >= best["threshold"]) & valid, target & valid
            tp, npred, ngt = int((pred & truth).sum()), int(pred.sum()), int(truth.sum())
            p, r, f = scores(tp, npred, ngt)
            union = npred + ngt - tp
            records.append(record(source, "ridge_drive", image, "multiscale", p, r, f,
                                  threshold=best["threshold"], tp=tp, fp=npred-tp, fn=ngt-tp,
                                  predicted_count=npred, gt_count=ngt, iou=tp/union if union else 0.0,
                                  fov_erosion_px=max(radii.values()), valid_pixels=int(valid.sum()),
                                  notes="dark; beta=.5; c=.5*max(S); common FOV intersection over all scales"))
    return records


def blobs(cfg, protocol, out_dir):
    data = {"python": {}, "fiji": {}}
    for image in [f"blob_{i:02d}" for i in range(1, 6)]:
        annotation = json.loads((ROOT / f"data/gt/blob/{image}.json").read_text(encoding="utf-8"))
        for source in ("python", "fiji"):
            stack = np.stack([get_map(source, image, "lap", s, annotation["shape"], cfg, True) for s in cfg["sigmas_blob"]])
            # Generate candidates once at the lowest threshold; filtering by
            # response preserves the exact extrema returned by the core.
            detections = detect_blob(stack, cfg["sigmas_blob"], annotation["polarity"], min(protocol["blob_thresholds"]))
            data[source][image] = (annotation, detections)
    grid = []
    for threshold in protocol["blob_thresholds"]:
        values = []
        for annotation, detections in data["python"].values():
            selected = [d for d in detections if d[4] >= threshold]
            pairs, gt_ids, pred_ids = match_blobs(annotation["objects"], selected, annotation.get("ignore_regions", []))
            values.append(scores(len(pairs), len(pred_ids), len(gt_ids))[2])
        grid.append(dict(threshold=threshold, mean_f1=float(np.mean(values)), selected_on="python", n_images=5))
    best = choose_first_best(grid)
    for r in grid:
        r["selected"] = r is best
    write_csv(out_dir / "blob_threshold_grid.csv", grid)
    records, audit = [], {}
    for source in ("python", "fiji"):
        for image, (annotation, detections) in data[source].items():
            selected = [d for d in detections if d[4] >= best["threshold"]]
            pairs, gt_ids, pred_ids = match_blobs(annotation["objects"], selected, annotation.get("ignore_regions", []))
            tp, npred, ngt = len(pairs), len(pred_ids), len(gt_ids)
            p, r, f = scores(tp, npred, ngt)
            records.append(record(source, "blob_log", image, "multiscale", p, r, f,
                                  threshold=best["threshold"], tp=tp, fp=npred-tp, fn=ngt-tp,
                                  predicted_count=npred, gt_count=ngt, iou="",
                                  ignored_predictions=len(selected)-npred,
                                  ignore_regions=len(annotation.get("ignore_regions", [])),
                                  polarity=annotation["polarity"],
                                  notes="one-to-one maximum cardinality; center<=2px; radius<=20%; configured scales only"))
            audit[f"{source}_{image}"] = dict(
                threshold=best["threshold"], detections=selected, valid_prediction_indices=pred_ids,
                valid_gt_indices=gt_ids, pairs_gt_prediction=pairs,
                ignore_regions=annotation.get("ignore_regions", []),
                detection_format=["y", "x", "sigma", "radius", "response"],
            )
    (out_dir / "blob_matching_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return records


def run_tier2(cfg=None, out_dir=RESULTS):
    cfg = cfg or strict_config()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    protocol = load_protocol()
    records = edges(cfg, protocol, out_dir)
    print("Tier 2 DRIVE: Frangi and frozen threshold", flush=True)
    records += ridges(cfg, protocol, out_dir)
    print("Tier 2 blobs: LoG and one-to-one matching", flush=True)
    records += blobs(cfg, protocol, out_dir)
    fields = ["source", "task", "image", "sigma", "precision", "recall", "f1", "iou", "tp", "fp", "fn",
              "predicted_count", "gt_count", "annotators", "p_low", "p_high", "threshold", "polarity",
              "ignored_predictions", "ignore_regions", "fov_erosion_px", "valid_pixels", "notes"]
    if len(records) != 110 or any(len({r["image"] for r in records if r["source"] == s}) != 25 for s in ("python", "fiji")):
        raise ValueError("Incomplete Tier 2 coverage")
    write_csv(out_dir / "tier2_results_both.csv", records, fields)
    for source in ("python", "fiji"):
        write_csv(out_dir / f"tier2_results_{source}.csv", [r for r in records if r["source"] == source], fields)
    indexed = {(r["source"], r["task"], r["image"], r["sigma"]): r for r in records}
    comparison = []
    for py in [r for r in records if r["source"] == "python"]:
        fj = indexed[("fiji", py["task"], py["image"], py["sigma"])]
        row = dict(task=py["task"], image=py["image"], sigma=py["sigma"])
        for name in ("precision", "recall", "f1", "iou"):
            row[f"python_{name}"] = py.get(name, "")
            row[f"fiji_{name}"] = fj.get(name, "")
        row["delta_f1_fiji_minus_python"] = fj["f1"] - py["f1"]
        comparison.append(row)
    write_csv(out_dir / "tier2_comparison.csv", comparison)
    summary = []
    for source in ("python", "fiji"):
        for task in ("edge_bsds", "ridge_drive", "blob_log"):
            sigmas = cfg["sigmas"] if task == "edge_bsds" else ["multiscale"]
            for sigma in sigmas:
                group = [r for r in records if (r["source"], r["task"], r["sigma"]) == (source, task, sigma)]
                macro = dict(source=source, task=task, sigma=sigma, n_images=len(group),
                             macro_precision=float(np.mean([r["precision"] for r in group])),
                             macro_recall=float(np.mean([r["recall"] for r in group])),
                             macro_f1=float(np.mean([r["f1"] for r in group])),
                             micro_precision="", micro_recall="", micro_f1="")
                if task != "edge_bsds":
                    tp = sum(r["tp"] for r in group)
                    mp, mr, mf = scores(tp, sum(r["predicted_count"] for r in group), sum(r["gt_count"] for r in group))
                    macro.update(micro_precision=mp, micro_recall=mr, micro_f1=mf)
                summary.append(macro)
    write_csv(out_dir / "tier2_summary.csv", summary)
    return records, summary


if __name__ == "__main__":
    validate_inputs()
    run_tier2()
