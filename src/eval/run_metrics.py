"""Run Duc's task 23, with provenance and a separate delivery directory.

Usage (project root): python -m src.eval.run_metrics
No plots, downloads, core edits, GT edits or automatic relaxed acceptance.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys
import time

from src.eval.metric_utils import ROOT, RESULTS, sha256, strict_config, validate_inputs, read_map, write_csv
from src.eval.benchmark_tier1 import expected_maps, run_tier1
from src.eval.metrics_tier2 import PROTOCOL, run_tier2


def expected_source_files(cfg, gt, source):
    prefix = "py" if source == "python" else "fiji"
    names = {suffix for *_, suffix, _ in expected_maps(cfg)}
    for r in gt:
        image = r["image"]
        if image.startswith("bsds"):
            ops, scales = ("lx", "ly"), cfg["sigmas"]
        elif image.startswith("drive"):
            ops, scales = ("hess-l1", "hess-l2"), cfg["sigmas"]
        else:
            ops, scales = ("lap",), cfg["sigmas_blob"]
        for op in ops:
            for s in scales:
                names.add(f"{image}_{op}_s{float(s)}.tif")
        if source == "fiji" and image.startswith("bsds"):
            for s in cfg["sigmas"]:
                names.add(f"{image}_edge_s{float(s)}.tif")
    return [ROOT / f"outputs/{source}/{prefix}_{name}" for name in sorted(names)]


def validate_source_maps(cfg, gt):
    shapes = {r["image"]: r["shape"] for r in gt}
    evidence = []
    for source in ("python", "fiji"):
        paths = expected_source_files(cfg, gt, source)
        missing = [str(p.relative_to(ROOT)) for p in paths if not p.is_file()]
        if missing:
            raise FileNotFoundError(f"{source}: missing {len(missing)} TIFFs; examples: {missing[:5]}")
        for p in paths:
            # Prefix source + two-part image stem (bsds_01 etc.).
            parts = p.name.split("_")
            image = "_".join(parts[1:3])
            read_map(p, shapes[image])
            evidence.append(dict(source=source, image=image, path=str(p.relative_to(ROOT)),
                                 size_bytes=p.stat().st_size, sha256=sha256(p)))
        print(f"Validated {source}: {len(paths)} required float32 TIFFs", flush=True)
    return evidence


def code_snapshot():
    paths = sorted((ROOT / "src").rglob("*.py"))
    paths += [ROOT / "config.yaml", PROTOCOL, ROOT / "INSTRUCTIONS.md", ROOT / "quyuoc.md"]
    return {str(p.relative_to(ROOT)): sha256(p) for p in paths}


def write_delivery_note(out_dir, tier1, smoke, summary):
    count = Counter(r["status"] for r in tier1)
    text = ["# Kết quả công việc 4 — Đức — phiên chuẩn hóa 10/11/2026", "",
            "Đã tính lại từ raw/config và nhãn READY hiện tại; xem run_manifest.json để xác minh phiên chạy.", "",
            "## Fiji so với Python", "",
            f"220 bản đồ Tầng 1: {dict(count)}. Chấm đúng ngưỡng gốc: relative error < 1e-4 **và** Pearson r > 0.9999.",
            "FAIL là kết quả số học không đạt ngưỡng, không phải lỗi chạy chương trình. Không tự nới ngưỡng.",
            "PSNR dùng MAX=255 chỉ cho Gaussian; ô PSNR của toán tử khác để trống có chủ đích.", "",
            "| Smoke test σ=2 | Relative error | Pearson r | Trạng thái |", "| --- | ---: | ---: | --- |"]
    for r in smoke:
        text.append(f"| {r['operator']} | {r['relative_error']:.9g} | {r['pearson_r']:.10g} | {r['status']} |")
    text += ["", "## Precision/Recall/F1 so với ground truth", "",
             "| Nguồn | Bài toán | Sigma | Macro Precision | Macro Recall | Macro F1 | Micro F1 |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: |"]
    for r in summary:
        micro = f"{r['micro_f1']:.6f}" if isinstance(r['micro_f1'], (float, int)) else "—"
        text.append(f"| {r['source']} | {r['task']} | {r['sigma']} | {r['macro_precision']:.6f} | {r['macro_recall']:.6f} | {r['macro_f1']:.6f} | {micro} |")
    text += ["", "## Phạm vi và giới hạn", "",
             "- Ngưỡng chọn trên tập Python nội bộ và áp nguyên vẹn cho Fiji. Đây là kết quả trên tập thực nghiệm đã dùng chọn ngưỡng, không phải điểm test độc lập chính thức BSDS/DRIVE.",
             "- Edge: dung sai Euclidean ≤2 px; precision so với ít nhất một annotator, recall trung bình annotator. TP/FP/FN chung không áp dụng cho cách gộp đa annotator này.",
             "- DRIVE: đánh giá trong giao các vùng FOV hợp lệ qua mọi scale, xói mòn theo support từ config; dùng cùng vùng cho hai nguồn.",
             "- Blob: ghép một-một, tâm ≤2 px, bán kính sai ≤20%; bỏ dự đoán có tâm trong vùng ignore. Nhãn tế bào là nhãn nhóm đã được Đức rà soát, không phải nhãn chính thức do nhà cung cấp xác nhận.",
             "- Detector blob hiện tại bỏ hai đầu lưới scale; giữ đúng 7 sigma đã chốt. Đối tượng ngoài dải kích thước vẫn thuộc GT và có thể làm giảm recall.",
             "- Native FeatureJ Edges là bảng tham chiếu riêng; không trộn với so sánh hai nguồn cùng Canny.",
             "- Bộ này chưa chạy biến thể nhiễu/crop hoặc vẽ biểu đồ/thời gian. Các CSV runtime cũ không được dùng làm bằng chứng đo lặp mới.",
             "- Nguồn bàn giao duy nhất: outputs/metrics/duc_10_11. Các phiên duc_08_11 và pre_fix_10_11 là lịch sử, khác protocol; không trộn số liệu.", ""]
    (out_dir / "KET_QUA_METRIC.md").write_text("\n".join(text), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-generate", action="store_true", help="Reuse Python TIFFs only if provenance matches current code/config/raw")
    args = parser.parse_args()
    started = time.perf_counter()
    RESULTS.mkdir(parents=True, exist_ok=True)
    state = dict(status="RUNNING", started_at_utc=datetime.now(timezone.utc).isoformat(), task=23,
                 root=str(ROOT), command=sys.argv, criterion="relative_error < 1e-4 AND pearson_r > 0.9999",
                 reference="outputs/fiji (ImageJ macro)", scope="25 original images; no noise/crop variants")
    manifest = RESULTS / "run_manifest.json"
    def save():
        manifest.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    save()
    try:
        cfg = strict_config()
        gt, inputs = validate_inputs()
        state["code_config_sha256"] = snapshot = code_snapshot()
        state["python_version"] = platform.python_version()
        state["platform"] = platform.platform()
        state["packages"] = {n: importlib.metadata.version(n) for n in ("numpy", "Pillow", "tifffile", "PyYAML")}
        state["featurej_version"] = "Not independently measured in this run; TIFF source is the supplied Fiji macro export"
        state["protocol"] = "duc_10_11_v1: Euclidean 2px; Python-selected frozen thresholds; common FOV support; one-to-one blobs with ignore; 7 configured blob scales"
        generation_key = {"code_config_sha256": snapshot, "raw": {r["path"]: r["sha256"] for r in inputs if r["role"] == "raw"}}
        provenance = ROOT / "outputs/python/task23_generation.json"
        if args.skip_generate:
            if not provenance.exists() or json.loads(provenance.read_text(encoding="utf-8")) != generation_key:
                raise ValueError("Cannot reuse Python maps: code/config/raw provenance differs. Run without --skip-generate.")
        else:
            from src.core import batch_runner
            print("Generating Python maps from the shared raw inputs...", flush=True)
            for image in cfg["tier1_images"]:
                batch_runner.process_tier1_image(image)
            batch_runner.process_tier2()
            provenance.write_text(json.dumps(generation_key, indent=2), encoding="utf-8")
        maps = validate_source_maps(cfg, gt)
        write_csv(RESULTS / "input_manifest.csv", inputs)
        write_csv(RESULTS / "map_manifest.csv", maps)
        tier1, borders, smoke = run_tier1(cfg, gt, RESULTS)
        if any(r["status"] not in ("PASS", "FAIL", "UNDEFINED") for r in tier1):
            raise ValueError("Incomplete/invalid Tier 1 input maps; see tier1_report.csv")
        records, summary = run_tier2(cfg, RESULTS)
        validate_inputs()  # Detect labels/raw edited during the computation.
        if code_snapshot() != snapshot:
            raise ValueError("Source/config changed during the run; rerun before delivery")
        for r in maps:
            if sha256(ROOT / r["path"]) != r["sha256"]:
                raise ValueError(f"Map modified during the run: {r['path']}")
        write_delivery_note(RESULTS, tier1, smoke, summary)
        # Required interface path; all other current delivery files stay grouped.
        shutil.copyfile(RESULTS / "tier1_report.csv", ROOT / "outputs/metrics/tier1_report.csv")
        state.update(status="COMPLETE", elapsed_seconds=time.perf_counter()-started,
                     finished_at_utc=datetime.now(timezone.utc).isoformat(),
                     tier1_status_counts=dict(Counter(r["status"] for r in tier1)), tier2_rows=len(records),
                     smoke_strict_pass=all(r["status"] == "PASS" for r in smoke),
                     outputs={p.name: sha256(p) for p in sorted(RESULTS.iterdir()) if p.is_file() and p != manifest})
        save()
        print(f"COMPLETE: {RESULTS}\nMetric computation completed; strict PASS/FAIL remains as measured.", flush=True)
    except Exception as exc:
        state.update(status="ERROR", error=f"{type(exc).__name__}: {exc}", elapsed_seconds=time.perf_counter()-started)
        save()
        raise


if __name__ == "__main__":
    main()
