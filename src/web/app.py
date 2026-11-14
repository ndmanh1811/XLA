"""Interactive Web Application for BTL Xu Ly Anh So.

Clean Light UI, Fixed 100vh Viewport Layout.
Displays: [Ảnh gốc] | [Kết quả Python] | [Chuẩn Fiji] | [Ground Truth / Bản đồ sai số].
"""
from __future__ import annotations

import base64
import csv
import io
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
import matplotlib
matplotlib.use("Agg")
import numpy as np
from PIL import Image, ImageDraw, UnidentifiedImageError

from src.core.derivatives import (
    compute_derivatives_1st,
    compute_derivatives_2nd,
    compute_gradient_magnitude,
    gaussian_smooth,
)
from src.core.detectors import detect_blob, detect_canny, detect_ridge, hysteresis_from_nms
from src.core.hessian import compute_hessian_eigenvalues
from src.core.structure_tensor import (
    compute_structure_coherence,
    compute_structure_tensor,
    compute_structure_tensor_eigenvalues,
)
from src.eval.bsds_threshold_grid import (
    STRUCT_2PX,
    binary_dilation,
    evaluate_prediction,
    load_bsds_items,
)
from src.eval.metric_utils import ROOT, RESULTS, erode_square, match_blobs, scores, normalize_scale, sha256
from src.eval.analyze_task5 import verify_metric_delivery
from src.web.parameters import web_settings, validate_request
from src.web.comparison import build_reference, compare_maps, shared_limits

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)
CORS(app)

UPLOAD_DIR = Path(__file__).parent / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Cache BSDS items for fast evaluation
_BSDS_ITEMS = None


def get_bsds_items():
    global _BSDS_ITEMS
    if _BSDS_ITEMS is None:
        try:
            _BSDS_ITEMS = {
                item.stem: item
                for item in load_bsds_items(ROOT / "data/raw", ROOT / "data/gt", 10)
            }
        except Exception as e:
            print("Warning: BSDS items failed to load:", e)
            _BSDS_ITEMS = {}
    return _BSDS_ITEMS


def array_to_base64_png(
    arr: np.ndarray,
    cmap: str = "gray",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
) -> str:
    """Convert numpy array to base64 PNG with colormap normalization."""
    buf = io.BytesIO()
    if arr.dtype == bool:
        img = Image.fromarray((arr * 255).astype(np.uint8))
    elif arr.ndim == 2:
        norm = arr.astype(np.float64)
        finite = norm[np.isfinite(norm)]
        if len(finite) == 0:
            norm = np.zeros_like(norm)
            mn, mx = 0.0, 1.0
        else:
            mn = vmin if vmin is not None else float(np.min(finite))
            mx = vmax if vmax is not None else float(np.max(finite))

        if mx > mn:
            norm = np.clip((norm - mn) / (mx - mn), 0.0, 1.0)
        else:
            norm = np.zeros_like(norm)
        norm = np.nan_to_num(norm, nan=0.0, posinf=1.0, neginf=0.0)

        if cmap == "gray":
            img = Image.fromarray((norm * 255.0).astype(np.uint8))
        else:
            colormap = matplotlib.colormaps.get(cmap, matplotlib.colormaps["inferno"])
            rgba = (colormap(norm) * 255.0).astype(np.uint8)
            img = Image.fromarray(rgba)
    elif arr.ndim == 3:
        if arr.dtype != np.uint8:
            arr = np.clip(arr * 255.0 if arr.max() <= 1.0 else arr, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)
    else:
        raise ValueError("Invalid array dimension")

    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def make_overlay(raw: np.ndarray, pred: np.ndarray, truth: Optional[np.ndarray] = None) -> np.ndarray:
    """Create a high-contrast 3-channel overlay."""
    norm_raw = raw.astype(np.float64)
    if norm_raw.max() > 1.0:
        norm_raw /= 255.0
    norm_raw = np.clip(norm_raw, 0.0, 1.0)
    rgb = np.repeat(norm_raw[..., None], 3, axis=2)

    if truth is not None:
        truth_bool = truth.astype(bool)
        pred_bool = pred.astype(bool)
        tp = truth_bool & pred_bool
        fn = truth_bool & (~pred_bool)
        fp = (~truth_bool) & pred_bool

        # False Negative: Red (ground truth missed)
        rgb[fn] = 0.35 * rgb[fn] + 0.65 * np.array([0.9, 0.1, 0.1])
        # False Positive: Cyan (prediction false alarm)
        rgb[fp] = 0.35 * rgb[fp] + 0.65 * np.array([0.0, 0.75, 0.95])
        # True Positive: Yellow/Gold (perfect match)
        rgb[tp] = 0.15 * rgb[tp] + 0.85 * np.array([0.95, 0.85, 0.05])
    else:
        pred_bool = pred.astype(bool)
        rgb[pred_bool] = 0.35 * rgb[pred_bool] + 0.65 * np.array([0.0, 0.75, 0.95])

    return (rgb * 255.0).clip(0, 255).astype(np.uint8)


def make_overlay_masks(
    raw: np.ndarray,
    tp_mask: np.ndarray,
    fp_mask: np.ndarray,
    fn_mask: np.ndarray,
) -> np.ndarray:
    """Overlay with explicit TP/FP/FN masks (used for BSDS 2px matching)."""
    norm_raw = raw.astype(np.float64)
    if norm_raw.max() > 1.0:
        norm_raw /= 255.0
    norm_raw = np.clip(norm_raw, 0.0, 1.0)
    rgb = np.repeat(norm_raw[..., None], 3, axis=2)

    tp = tp_mask.astype(bool)
    fp = fp_mask.astype(bool)
    fn = fn_mask.astype(bool)

    rgb[fn] = 0.35 * rgb[fn] + 0.65 * np.array([0.9, 0.1, 0.1])
    rgb[fp] = 0.35 * rgb[fp] + 0.65 * np.array([0.0, 0.75, 0.95])
    rgb[tp] = 0.15 * rgb[tp] + 0.85 * np.array([0.95, 0.85, 0.05])

    return (rgb * 255.0).clip(0, 255).astype(np.uint8)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/images", methods=["GET"])
def list_images():
    categories = {"bsds": [], "drive": [], "blob": []}
    raw_dir = ROOT / "data/raw"
    if raw_dir.is_dir():
        for p in sorted(raw_dir.glob("*.png")):
            name = p.stem
            for cat in categories:
                if name.startswith(cat):
                    im = Image.open(p)
                    categories[cat].append({
                        "id": name,
                        "name": name,
                        "width": im.width,
                        "height": im.height,
                    })
    return jsonify(categories)


@app.route("/static/figures/<filename>")
def serve_task5_figure(filename):
    manifest_path = ROOT / 'outputs/analysis/duc_task5_10_11/analysis_manifest.json'
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        path = ROOT / 'outputs/analysis/duc_task5_10_11/figures' / filename
        expected = manifest['outputs'].get('figures/' + filename) or manifest['outputs'].get('figures\\' + filename)
        if not expected or sha256(path) != expected:
            return jsonify(error='Biểu đồ chưa khớp manifest; hãy chạy lại phân tích.'), 503
    except (OSError, ValueError, KeyError):
        return jsonify(error='Biểu đồ chưa được xác minh.'), 503
    return send_from_directory(str(ROOT / "outputs/analysis/duc_task5_10_11/figures"), filename)


@app.route('/api/settings')
def get_settings():
    try:
        _, settings = web_settings()
        return jsonify(settings)
    except (OSError, ValueError, StopIteration) as exc:
        return jsonify(error=f'Không đọc được cấu hình: {exc}'), 503


@app.route("/api/upload", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
        return jsonify({"error": "Unsupported image format"}), 400

    image_id = f"custom_{uuid4().hex}"
    save_path = UPLOAD_DIR / f"{image_id}.png"
    try:
        with Image.open(file.stream) as source:
            im = source.convert("L")
            im.save(save_path)
    except (UnidentifiedImageError, OSError, ValueError):
        return jsonify({"error": "File không phải ảnh hợp lệ hoặc không đọc được."}), 400

    return jsonify({
        "id": image_id,
        "name": file.filename,
        "width": im.width,
        "height": im.height,
    })


@app.route("/api/process", methods=["POST"])
def process_image():
    try:
        cfg, settings = web_settings()
    except (OSError, ValueError, StopIteration) as exc:
        return jsonify({"error": f"Cấu hình/tham số thực nghiệm chưa sẵn sàng: {exc}"}), 503
    try:
        data = validate_request(request.get_json(silent=True), settings)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    image_id = data.get("image_id", "bsds_01")
    algo = data.get("algorithm", "canny")
    cmap = data.get("colormap", "inferno")

    # 1. Load Input Image
    if image_id.startswith("custom_"):
        img_path = UPLOAD_DIR / f"{image_id}.png"
    else:
        img_path = ROOT / f"data/raw/{image_id}.png"

    if not img_path.is_file():
        return jsonify({"error": f"Image not found: {image_id}"}), 404

    try:
        with Image.open(img_path) as source:
            raw = np.asarray(source.convert("L"), dtype=np.float64)
    except (UnidentifiedImageError, OSError, ValueError):
        return jsonify({"error": "Không đọc được ảnh đã chọn."}), 400
    h, w = raw.shape

    # 2. Check Ground Truth availability
    has_gt = False
    truth = None
    fov_mask = None
    ignore_regions = []
    blob_objects = []

    if image_id.startswith("bsds"):
        bsds_dict = get_bsds_items()
        if image_id in bsds_dict:
            has_gt = True
            bsds_item = bsds_dict[image_id]
            truth = bsds_item.union_gt
    elif image_id.startswith("drive"):
        vessel_path = ROOT / f"data/gt/drive/{image_id}_vessels.png"
        fov_path = ROOT / f"data/gt/drive/{image_id}_fov.png"
        if vessel_path.is_file() and fov_path.is_file():
            has_gt = True
            truth = np.asarray(Image.open(vessel_path)) > 0
            fov_mask = np.asarray(Image.open(fov_path)) > 0
    elif image_id.startswith("blob"):
        blob_path = ROOT / f"data/gt/blob/{image_id}.json"
        if blob_path.is_file():
            has_gt = True
            gt_data = json.loads(blob_path.read_text(encoding="utf-8"))
            blob_objects = gt_data.get("objects", [])
            ignore_regions = gt_data.get("ignore_regions", [])

    # 3. Parameters
    sigma = float(data.get("sigma", 2.0))
    dtype = data.get("display_type", None)
    sigma_d = float(data.get("sigma_d", 1.0))
    sigma_i = float(data.get("sigma_i", 3.0))

    # 4. Run Python Core Algorithm
    t_deriv = 0.0
    t_detector = 0.0

    py_map = None
    py_pred = None
    gt_display = None
    gt_metrics = {"has_gt": has_gt}
    angle_valid = None
    mode = cfg['border_mode']

    try:
        if algo == "gaussian":
            t0 = time.perf_counter()
            py_map = gaussian_smooth(raw, sigma=sigma, mode=mode)
            t_deriv = (time.perf_counter() - t0) * 1000

        elif algo == "gradient":
            dtype = dtype or "mag"
            t0 = time.perf_counter()
            lx, ly = compute_derivatives_1st(raw, sigma=sigma, mode=mode)
            t_deriv = (time.perf_counter() - t0) * 1000
            if dtype == "lx":
                py_map = lx
            elif dtype == "ly":
                py_map = ly
            elif dtype == "angle":
                py_map = np.arctan2(ly, lx)
                magnitude = np.hypot(lx, ly)
                angle_valid = magnitude > max(1e-12, float(magnitude.max()) * 1e-10)
            else:
                py_map = compute_gradient_magnitude(lx, ly)

        elif algo == "canny":
            # Canonical Canny defaults for sigma=2 (selected on Python, frozen for Fiji).
            p_low = data['p_low']
            p_high = data['p_high']
            apply_nms = bool(data.get("nms", True))

            t0 = time.perf_counter()
            lx, ly = compute_derivatives_1st(raw, sigma=sigma, mode=mode)
            lx = normalize_scale(lx, sigma, 1, 'python', 'derivatives', cfg)
            ly = normalize_scale(ly, sigma, 1, 'python', 'derivatives', cfg)
            t_deriv = (time.perf_counter() - t0) * 1000

            t1 = time.perf_counter()
            py_map = compute_gradient_magnitude(lx, ly)
            if apply_nms:
                py_pred = detect_canny(lx, ly, p_low=p_low, p_high=p_high, return_binary=True)
            else:
                py_pred = hysteresis_from_nms(py_map, p_low=p_low, p_high=p_high, return_binary=True)
            t_detector = (time.perf_counter() - t1) * 1000

            pred_bool = (py_pred > 0).astype(bool)
            if has_gt and image_id.startswith("bsds"):
                bsds_item = bsds_dict[image_id]
                eval_res = evaluate_prediction(pred_bool, bsds_item)
                gt_metrics.update({
                    "precision": round(float(eval_res["precision"]), 4),
                    "recall": round(float(eval_res["recall"]), 4),
                    "f1": round(float(eval_res["f1"]), 4),
                    "tp": int(eval_res["true_positives"]),
                })
                # BSDS F1 uses a 2px tolerance and multi-annotator recall.
                # Paint TP/FP/FN with the same tolerance so the overlay
                # matches the displayed metric instead of raw pixel overlap.
                dilated_pred = binary_dilation(pred_bool, structure=STRUCT_2PX)
                tp_mask = pred_bool & bsds_item.dilated_union_gt
                fp_mask = pred_bool & (~bsds_item.dilated_union_gt)
                fn_mask = truth & (~dilated_pred)
                gt_display = make_overlay_masks(raw, tp_mask, fp_mask, fn_mask)
            else:
                gt_display = make_overlay(raw, pred_bool)

        elif algo == "second_order":
            dtype = dtype or "laplacian"
            t0 = time.perf_counter()
            lxx, lyy, lxy = compute_derivatives_2nd(raw, sigma=sigma, mode=mode)
            if bool(data.get("normalized", True)):
                lxx = normalize_scale(lxx, sigma, 2, 'python', 'derivatives', cfg)
                lyy = normalize_scale(lyy, sigma, 2, 'python', 'derivatives', cfg)
                lxy = normalize_scale(lxy, sigma, 2, 'python', 'derivatives', cfg)
            t_deriv = (time.perf_counter() - t0) * 1000
            if dtype == "lxx":
                py_map = lxx
            elif dtype == "lyy":
                py_map = lyy
            elif dtype == "lxy":
                py_map = lxy
            else:
                py_map = lxx + lyy

        elif algo == "hessian":
            dtype = dtype or "l2"
            t0 = time.perf_counter()
            lxx, lyy, lxy = compute_derivatives_2nd(raw, sigma=sigma, mode=mode)
            lxx = normalize_scale(lxx, sigma, 2, 'python', 'hessian', cfg)
            lyy = normalize_scale(lyy, sigma, 2, 'python', 'hessian', cfg)
            lxy = normalize_scale(lxy, sigma, 2, 'python', 'hessian', cfg)
            t_deriv = (time.perf_counter() - t0) * 1000
            t1 = time.perf_counter()
            l1, l2 = compute_hessian_eigenvalues(lxx, lyy, lxy, sort_order=cfg['eigen_order'])
            t_detector = (time.perf_counter() - t1) * 1000
            py_map = l1 if dtype == "l1" else l2

        elif algo == "frangi":
            beta = float(data.get("beta", 0.5))
            c_raw = data.get("c")
            c = float(c_raw) if c_raw not in (None, "") else None
            polarity = data.get("polarity", "dark")
            thresh = float(data.get("threshold", 0.05))
            use_fov = bool(data.get("use_fov", True))

            multiscale = bool(data.get("multiscale", True))
            scales = cfg['sigmas'] if multiscale else [sigma]
            k_support = max(cfg['kernel_k'].values())

            responses = []
            for s in scales:
                t_part = time.perf_counter()
                lxx, lyy, lxy = compute_derivatives_2nd(raw, sigma=s, mode=mode)
                a = normalize_scale(lxx, s, 2, 'python', 'hessian', cfg)
                b = normalize_scale(lyy, s, 2, 'python', 'hessian', cfg)
                cross = normalize_scale(lxy, s, 2, 'python', 'hessian', cfg)
                l1, l2 = compute_hessian_eigenvalues(a, b, cross, sort_order=cfg['eigen_order'])
                t_deriv += (time.perf_counter() - t_part) * 1000
                t_part = time.perf_counter()
                resp = detect_ridge(l1, l2, sigma=s, beta=beta, c=c, polarity=polarity)
                if use_fov and fov_mask is not None:
                    erode_r = int(np.ceil(k_support * s))
                    resp[~erode_square(fov_mask, erode_r)] = 0.0
                responses.append(resp)
                t_detector += (time.perf_counter() - t_part) * 1000

            t_part = time.perf_counter()
            py_map = np.maximum.reduce(responses)
            t_detector += (time.perf_counter() - t_part) * 1000

            if use_fov and fov_mask is not None:
                max_r = int(np.ceil(k_support * max(scales)))
                valid_mask = erode_square(fov_mask, max_r)
            else:
                valid_mask = np.ones_like(raw, dtype=bool)

            py_pred = (py_map >= thresh) & valid_mask

            if has_gt and image_id.startswith("drive") and truth is not None:
                eval_truth = truth & valid_mask
                eval_pred = py_pred & valid_mask
                tp_val = int((eval_pred & eval_truth).sum())
                fp_val = int((eval_pred & (~eval_truth)).sum())
                fn_val = int(((~eval_pred) & eval_truth).sum())
                p_val, r_val, f_val = scores(tp_val, int(eval_pred.sum()), int(eval_truth.sum()))
                gt_metrics.update({
                    "precision": round(p_val, 4),
                    "recall": round(r_val, 4),
                    "f1": round(f_val, 4),
                    "tp": tp_val,
                })
                gt_display = make_overlay(raw, py_pred, truth & valid_mask)
            else:
                gt_display = make_overlay(raw, py_pred)

        elif algo == "blob":
            scales = cfg['sigmas_blob']
            polarity = data.get("polarity", "bright")
            thresh = float(data.get("threshold", 5.0))
            show_ignore = bool(data.get("show_ignore", True))

            t0 = time.perf_counter()
            stack = []
            for s in scales:
                lxx, lyy, _ = compute_derivatives_2nd(raw, sigma=s, mode=mode)
                lap = normalize_scale(lxx + lyy, s, 2, 'python', 'laplacian', cfg)
                stack.append(lap)
            lap_stack = np.stack(stack, axis=0)
            t_deriv = (time.perf_counter() - t0) * 1000

            t1 = time.perf_counter()
            detections = detect_blob(lap_stack, scales, polarity=polarity, threshold=thresh)
            t_detector = (time.perf_counter() - t1) * 1000

            py_map = np.max(np.abs(lap_stack), axis=0)

            # Draw circles for Python prediction
            pred_pil = Image.fromarray(np.repeat((np.clip(raw / 255.0, 0, 1) * 255).astype(np.uint8)[..., None], 3, axis=2))
            draw_pred = ImageDraw.Draw(pred_pil)
            for d in detections:
                y, x, s, r, _ = d
                draw_pred.ellipse([x - r, y - r, x + r, y + r], outline=(0, 200, 240), width=2)
            py_pred = np.asarray(pred_pil)

            # Ground truth overlay
            gt_pil = Image.fromarray(np.repeat((np.clip(raw / 255.0, 0, 1) * 255).astype(np.uint8)[..., None], 3, axis=2))
            draw_gt = ImageDraw.Draw(gt_pil)
            for obj in blob_objects:
                gx, gy, gr = obj["x"], obj["y"], obj["radius"]
                draw_gt.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], outline=(220, 38, 38), width=1)
            if show_ignore and ignore_regions:
                for box in ignore_regions:
                    draw_gt.rectangle(box, outline=(245, 158, 11), width=2)

            if has_gt and image_id.startswith("blob"):
                pairs, gt_ids, pred_ids = match_blobs(blob_objects, detections, ignore_regions)
                tp_val = len(pairs)
                p_val, r_val, f_val = scores(tp_val, len(pred_ids), len(gt_ids))
                paired_pred_ids = {p_idx for _, p_idx in pairs}
                for g_idx, p_idx in pairs:
                    py_pt, px_pt, _, pr_pt, _ = detections[p_idx]
                    draw_gt.ellipse([px_pt - pr_pt, py_pt - pr_pt, px_pt + pr_pt, py_pt + pr_pt], outline=(234, 179, 8), width=2)
                for p_idx in pred_ids:
                    if p_idx in paired_pred_ids:
                        continue
                    py_pt, px_pt, _, pr_pt, _ = detections[p_idx]
                    draw_gt.ellipse([px_pt - pr_pt, py_pt - pr_pt, px_pt + pr_pt, py_pt + pr_pt], outline=(0, 200, 240), width=2)
                gt_metrics.update({
                    "precision": round(p_val, 4),
                    "recall": round(r_val, 4),
                    "f1": round(f_val, 4),
                    "tp": tp_val,
                })
            gt_display = np.asarray(gt_pil)

        elif algo == "structure_tensor":
            dtype = dtype or "coherence"
            t0 = time.perf_counter()
            j11, j22, j12 = compute_structure_tensor(raw, sigma_d=sigma_d, sigma_i=sigma_i, mode=mode)
            t_deriv = (time.perf_counter() - t0) * 1000
            t1 = time.perf_counter()
            mu1, mu2 = compute_structure_tensor_eigenvalues(j11, j22, j12)
            coh = compute_structure_coherence(mu1, mu2)
            t_detector = (time.perf_counter() - t1) * 1000
            if dtype == "mu1":
                py_map = mu1
            elif dtype == "mu2":
                py_map = mu2
            else:
                py_map = coh

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    # 5. Build only a semantically matching reference; no unrelated fallback.
    reference_scales = cfg['sigmas_blob'] if algo == 'blob' else (cfg['sigmas'] if data['multiscale'] else [sigma])
    fiji_map, fiji_metrics, reference_valid = build_reference(
        image_id, algo, dtype, sigma, sigma_d, sigma_i, raw.shape, cfg,
        normalized=data['normalized'], scales=reference_scales,
        beta=data['beta'], c=data['c'], polarity=data['polarity'],
        fov=fov_mask, use_fov=data['use_fov'])
    diff_map = None
    fiji_b64 = None
    angular = algo == 'gradient' and dtype == 'angle'
    if fiji_map is not None:
        valid = angle_valid & reference_valid if angular else None
        diff_map, measured = compare_maps(py_map, fiji_map, angular=angular, valid=valid)
        fiji_metrics.update(measured)
    signed = (algo == 'gradient' and dtype in ('lx', 'ly')) or algo in ('second_order', 'hessian')
    vmin, vmax = shared_limits(py_map, fiji_map, angular=angular, signed=signed)
    if fiji_map is not None:
        fiji_b64 = array_to_base64_png(fiji_map, cmap=cmap, vmin=vmin, vmax=vmax)
    fiji_metrics['display_range'] = [vmin, vmax]

    # 6. Resolve 4th View (Ground Truth OR Error Difference Map)
    gt_raw_b64 = None
    if truth is not None:
        gt_raw_b64 = array_to_base64_png(truth.astype(bool), cmap="gray")
    elif blob_objects:
        gt_raw_pil = Image.new("L", (w, h), 0)
        draw_raw = ImageDraw.Draw(gt_raw_pil)
        for obj in blob_objects:
            gx, gy, gr = obj["x"], obj["y"], obj["radius"]
            draw_raw.ellipse([gx - gr, gy - gr, gx + gr, gy + gr], outline=255, fill=255)
        gt_raw_b64 = array_to_base64_png(np.asarray(gt_raw_pil) > 0, cmap="gray")

    diff_b64 = None
    if diff_map is not None:
        diff_b64 = array_to_base64_png(diff_map, cmap="magma", vmin=0.0, vmax=max(float(diff_map.max()), 1e-12))

    if gt_display is None:
        if diff_map is not None:
            gt_display = diff_map
            gt_cmap = "magma"
            gt_title = "4. Sai số đáp ứng (|Python - Fiji|)"
        elif truth is not None:
            gt_display = truth.astype(bool)
            gt_cmap = "gray"
            gt_title = "4. Nhãn Ground Truth chuẩn"
        else:
            gt_display = np.zeros_like(raw)
            gt_cmap = "gray"
            gt_title = "4. Chưa có nhãn Ground Truth"
    else:
        gt_cmap = None
        gt_title = "4. Nhãn Ground Truth & Đối chuẩn"

    # Convert images to base64
    img_orig_b64 = array_to_base64_png(raw, cmap="gray", vmin=0, vmax=255)

    py_resp_b64 = array_to_base64_png(py_map, cmap=cmap, vmin=vmin, vmax=vmax)
    py_bin_b64 = array_to_base64_png(py_pred) if py_pred is not None else None

    if gt_cmap:
        img_gt_b64 = array_to_base64_png(gt_display, cmap=gt_cmap)
    else:
        img_gt_b64 = array_to_base64_png(gt_display)

    timing = {
        "derivative_ms": round(t_deriv, 2),
        "detector_ms": round(t_detector, 2),
        "total_ms": round(t_deriv + t_detector, 2),
        "scope": "Python filters + detector, single request; excludes GT, Fiji loading and rendering",
    }

    return jsonify({
        "request_context": {"image_id": image_id, "algorithm": algo},
        "img_original": img_orig_b64,
        "img_python_response": py_resp_b64,
        "img_python_binary": py_bin_b64,
        "img_fiji": fiji_b64,
        "img_gt_overlay": img_gt_b64,
        "img_gt_raw": gt_raw_b64,
        "img_diff": diff_b64,
        "has_gt": has_gt,
        "gt_title": gt_title,
        "timing": timing,
        "fiji_metrics": fiji_metrics,
        "gt_metrics": gt_metrics,
        "image_size": [w, h],
    })


@app.route("/api/benchmarks", methods=["GET"])
def get_benchmarks():
    try:
        verify_metric_delivery()
    except (OSError, ValueError, KeyError) as exc:
        return jsonify(error=f'Metric chưa hợp lệ: {exc}'), 503
    tier1_path = RESULTS / "tier1_report.csv"
    tier2_path = RESULTS / "tier2_summary.csv"
    comp_path = RESULTS / "tier2_comparison.csv"

    def read_csv_rows(p):
        if not p.is_file():
            return []
        with p.open(encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    tier1 = read_csv_rows(tier1_path)
    tier2 = read_csv_rows(tier2_path)
    strict = sum(r['status'] == 'PASS' for r in tier1)
    relaxed = sum(r['status'] == 'FAIL' and float(r['relative_error']) < 1e-2 and float(r['pearson_r']) > .9999 for r in tier1)
    python_rows = [r for r in tier2 if r['source'] == 'python']
    headline = {
        'edge': max((r for r in python_rows if r['task'] == 'edge_bsds'), key=lambda r: float(r['macro_f1'])),
        'ridge': next(r for r in python_rows if r['task'] == 'ridge_drive'),
        'blob': next(r for r in python_rows if r['task'] == 'blob_log'),
    }
    return jsonify({
        "tier1": tier1,
        "tier2_summary": tier2,
        "tier2_comparison": read_csv_rows(comp_path),
        "headlines": headline,
        "tier1_counts": dict(total=len(tier1), strict=strict, strict_failed=len(tier1)-strict,
                              relaxed=relaxed, outside_relaxed=len(tier1)-strict-relaxed),
        "provenance": dict(status='VALID', scope='canonical', source=str(RESULTS.relative_to(ROOT)),
                           manifest_sha256=sha256(RESULTS/'run_manifest.json')),
    })


@app.route("/api/figures", methods=["GET"])
def get_figures():
    fig_dir = ROOT / "outputs/analysis/duc_task5_10_11/figures"
    catalog_path = ROOT / "outputs/analysis/duc_task5_10_11/figure_catalog.csv"
    try:
        verify_metric_delivery()
        analysis = json.loads((fig_dir.parent/'analysis_manifest.json').read_text(encoding='utf-8'))
        if analysis['status'] != 'COMPLETE' or analysis['metric_manifest_sha256'] != sha256(RESULTS/'run_manifest.json'):
            raise ValueError('Phiên phân tích không khớp metric hiện tại.')
        for name, digest in analysis['outputs'].items():
            if sha256(fig_dir.parent/name) != digest:
                raise ValueError(f'Kết quả phân tích đã thay đổi: {name}')
    except (OSError, ValueError, KeyError) as exc:
        return jsonify(error=f'Biểu đồ chưa được xác minh: {exc}'), 503

    catalog = {}
    if catalog_path.is_file():
        with catalog_path.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                stem = r.get("stem", "")
                catalog[f"{stem}.png"] = r.get("title", stem)

    figures = []
    if fig_dir.is_dir():
        for p in sorted(fig_dir.glob("*.png")):
            figures.append({
                "filename": p.name,
                "title": catalog.get(p.name, p.stem.replace("_", " ").title()),
                "url": f"/static/figures/{p.name}",
            })
    return jsonify(figures)


def find_available_port(host: str, preferred_port: int) -> int:
    import socket
    port = preferred_port
    while port < preferred_port + 50:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host, port)) != 0:
                return port
        port += 1
    return preferred_port


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Start BTL XLA Web Demo")
    parser.add_argument("--port", type=int, default=5000, help="Web server port")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address")
    args = parser.parse_args()

    port = find_available_port(args.host, args.port)

    import webbrowser
    def open_browser():
        time.sleep(1.0)
        webbrowser.open(f"http://{args.host}:{port}")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    print(f"[*] Starting BTL XLA Interactive Web Server on http://{args.host}:{port}")
    app.run(host=args.host, port=port, debug=False)


if __name__ == "__main__":
    main()
