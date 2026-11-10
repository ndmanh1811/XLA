"""Read-only probes of evaluation contracts and current presentation claims."""
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, mock_open, patch
from zipfile import ZipFile
import csv
import hashlib
import io
import json
import importlib.util
import sys
import numpy as np
from PIL import Image
import tifffile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/10_11/kiem_tra_toan_bo_nhom"
sys.path.insert(0, str(ROOT))
from src.eval import benchmark_tier2 as legacy
from src.eval.metric_utils import match_blobs, scores
from src.core.derivatives import compute_laplacian
from src.core.detectors import detect_blob


def main():
    result = {}
    raw = [np.asarray(Image.open(p)) for p in sorted((ROOT / "data/raw").glob("*.png"))]
    result["raw"] = dict(count=len(raw), all_uint8_gray=all(a.dtype == np.uint8 and a.ndim == 2 for a in raw),
                         minimum_shape=[min(a.shape[i] for a in raw) for i in (0, 1)])
    result["calibration"] = []
    for p in sorted((ROOT / "data/calib").glob("*.tif")):
        with tifffile.TiffFile(p) as t:
            a = t.asarray()
            result["calibration"].append(dict(name=p.name, shape=list(a.shape), dtype=str(a.dtype),
                compression=int(t.pages[0].compression), finite=bool(np.isfinite(a).all())))

    # Exercise the actual canonical evaluator with two GT centers close to one
    # prediction, using mocks only; no real data/GT file is modified.
    fake_raw = Mock()
    fake_raw.glob.return_value = [Path("blob_probe.png")]
    fake_gt = dict(polarity="bright", objects=[dict(x=9., y=10., radius=3.), dict(x=11., y=10., radius=3.)])
    records = []
    with patch.object(legacy, "RAW_DIR", fake_raw), patch.object(Path, "exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps(fake_gt))), \
         patch.object(legacy.Image, "open", return_value=Image.fromarray(np.zeros((32, 32), np.uint8))), \
         patch.object(legacy, "compute_laplacian", return_value=np.zeros((32, 32))), \
         patch.object(legacy, "detect_blob", return_value=[(10., 10., 2., 3., 20.)]), redirect_stdout(io.StringIO()):
        legacy.evaluate_blobs(sample_limit=1, records=records, source="python", blob_sigmas="config")
    result["one_prediction_two_gt_probe"] = records

    gt = json.loads((ROOT / "data/gt/blob/blob_05.json").read_text(encoding="utf-8"))
    boxes = [tuple(r) for r in gt["ignore_regions"]]
    image = np.asarray(Image.open(ROOT / "data/raw/blob_05.png"), dtype=np.float64)
    sigmas = legacy.get_blob_sigmas()
    result["same_blob_detector_ignore_comparison"] = []
    for source in ("python", "fiji"):
        stack = []
        for s in sigmas:
            a = compute_laplacian(image, sigma=s) if source == "python" else np.asarray(tifffile.imread(ROOT / f"outputs/fiji/fiji_blob_05_lap_s{s:.1f}.tif"), dtype=np.float64)
            stack.append(s*s*a)
        detections = detect_blob(np.stack(stack), sigmas=sigmas, polarity=gt["polarity"], threshold=.03*255.)
        legacy_tp = sum(any(np.hypot(g["x"]-d[1], g["y"]-d[0]) <= 2 and abs(g["radius"]-d[3])/g["radius"] <= .2 for d in detections) for g in gt["objects"])
        pairs, gt_ids, pred_ids = match_blobs(gt["objects"], detections, boxes)
        result["same_blob_detector_ignore_comparison"].append(dict(source=source, sigmas=sigmas,
            predictions=len(detections), legacy_tp=legacy_tp,
            legacy_precision=legacy_tp/len(detections), legacy_recall=legacy_tp/len(gt["objects"]),
            legacy_f1=2*legacy_tp/(len(detections)+len(gt["objects"])),
            ignored_predictions=len(detections)-len(pred_ids), one_to_one_tp=len(pairs),
            corrected_precision=scores(len(pairs),len(pred_ids),len(gt_ids))[0],
            corrected_recall=scores(len(pairs),len(pred_ids),len(gt_ids))[1],
            corrected_f1=scores(len(pairs),len(pred_ids),len(gt_ids))[2]))

    with (ROOT / "outputs/metrics/optimization_benchmark.csv").open(encoding="utf-8-sig") as f:
        opt = list(csv.DictReader(f))
    result["optimization_reps"] = dict(Counter(r.get("reps", "MISSING") for r in opt))
    equal = 0; compared = 0
    with ZipFile(ROOT / "outputs/fiji_java_tier1.zip") as z:
        for name in z.namelist():
            if not name.lower().endswith(".tif"):
                continue
            py = ROOT / "outputs/python" / Path(name).name.replace("fiji_", "py_", 1)
            if py.exists():
                compared += 1
                equal += hashlib.sha256(z.read(name)).digest() == hashlib.sha256(py.read_bytes()).digest()
    result["python_vs_fiji_java_sha256"] = dict(compared=compared, identical=equal)
    result["bsds_sigma2_reproduction"] = []
    for source in ("python", "fiji"):
        log = io.StringIO()
        with redirect_stdout(log):
            mean = legacy.evaluate_bsds_edges(sample_limit=10, source=source, sigmas=[2.],
                        thresholds_by_sigma={2.: (67., 91.)}, selection_method="audit_frozen_no_reselection")
        (OUT / f"BSDS_SIGMA2_{source.upper()}_LOG.txt").write_text(log.getvalue(), encoding="utf-8")
        result["bsds_sigma2_reproduction"].append(dict(source=source, mean_f1=mean, expected_rounded=.477886,
                                                       matches_6_decimals=round(mean, 6)==.477886))
    result["slide_builder_dependency"] = dict(python_pptx_installed=importlib.util.find_spec("pptx") is not None,
        declared_in_requirements="python-pptx" in (ROOT / "requirements.txt").read_text(encoding="utf-8"))
    out = OUT / "EVALUATION_PROBES.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
