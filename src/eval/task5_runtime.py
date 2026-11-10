"""Measure task-24 runtimes on this machine; retain individual repetitions."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time

import numpy as np
from PIL import Image

from src.core.derivatives import compute_derivatives_1st, compute_gradient_magnitude
from src.core.detectors import canny_nms
from src.eval.benchmark_runtime import build_operation
from src.eval.metric_utils import ROOT, sha256, strict_config, validate_inputs, write_csv

TASK5 = ROOT / "outputs/analysis/duc_task5_10_11"


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def timing_summary(samples):
    values = np.asarray(samples, dtype=float)
    if values.size < 3 or not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("At least 3 finite positive runtime samples required")
    return dict(median_ms=float(np.median(values)), q25_ms=float(np.percentile(values, 25)),
                q75_ms=float(np.percentile(values, 75)), min_ms=float(values.min()),
                max_ms=float(values.max()), measured_repeats=int(values.size))


def runtime_fingerprint():
    paths = sorted((ROOT / "src/core").glob("*.py")) + sorted((ROOT / "data/raw").glob("*.png"))
    paths += [ROOT / "config.yaml", ROOT / "src/config.py", ROOT / "src/eval/benchmark_runtime.py",
              Path(__file__), ROOT / "src/fiji/BenchmarkRuntimeDuc.java"]
    return {str(p.relative_to(ROOT)):sha256(p) for p in paths}


def operation(command, image, sigma):
    # Both runtimes are raw gradient/NMS, without scale multiplication or
    # hysteresis: match Edges.run(..., false/true), not the final Canny task.
    if command in ("gradient", "edge"):
        def run():
            lx, ly = compute_derivatives_1st(image, float(sigma))
            return compute_gradient_magnitude(lx, ly) if command == "gradient" else canny_nms(lx, ly)
        return run
    return build_operation(command, image, sigma)


def build_cases(cfg):
    """Reconstruct expected cases from current config, never from old timings."""
    # Derivative engine calls: ten commands, Hessian/ST return two maps per call.
    standard = ("gauss", "lx", "ly", "lxx", "lxy", "lyy", "gradient", "laplacian", "hessian")
    cases = set()
    for image in cfg["tier1_images"]:
        cases.update((image, op, str(float(s))) for op in standard for s in cfg["sigmas"])
        cases.update((image, "structure", f"sd{float(sd)}_si{float(si)}") for sd, si in cfg["structure_pairs"])
    for i in range(1, 11):
        cases.update((f"bsds_{i:02d}", op, str(float(s))) for op in ("lx", "ly", "edge") for s in cfg["sigmas"])
        cases.update((f"drive_{i:02d}", "hessian", str(float(s))) for s in cfg["sigmas"])
    for i in range(1, 6):
        cases.update((f"blob_{i:02d}", "laplacian", str(float(s))) for s in cfg["sigmas_blob"])
    # Legacy edge cases in the old logs are excluded: these are the 357
    # operations needed to produce the current 423-map macro scope.
    return [dict(image=image, command=cmd, sigma=sigma) for image, cmd, sigma in sorted(cases)]


def measure_runtime(out_dir=TASK5, imagej_dir=None, repeats=5):
    cfg = strict_config()
    validate_inputs()
    fingerprint = runtime_fingerprint()
    if repeats != 5:
        raise ValueError("Delivery protocol is exactly one warm-up plus five repeats")
    out_dir = Path(out_dir)
    runtime_dir = out_dir / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    imagej_dir = Path(imagej_dir or ROOT.parent / "ij153-win-java8/ImageJ").resolve()
    jars = [imagej_dir / "ij.jar", imagej_dir / "plugins/jars/imagescience.jar"]
    for p in jars:
        if not p.is_file():
            raise FileNotFoundError(f"ImageJ/ImageScience JAR required: {p}; use --imagej-dir")
    javac = shutil.which("javac")
    if not javac:
        raise FileNotFoundError("JDK javac not found on PATH")
    java = Path(javac).with_name("java.exe" if os.name == "nt" else "java")
    if not java.is_file():
        raise FileNotFoundError(java)
    case_rows = build_cases(cfg)
    write_csv(runtime_dir / "runtime_cases.csv", case_rows)
    source = ROOT / "src/fiji/BenchmarkRuntimeDuc.java"
    classes = runtime_dir / "classes"
    classes.mkdir(exist_ok=True)
    cp = os.pathsep.join(map(str, jars))
    cmd = [javac, "-encoding", "UTF-8", "-cp", cp, "-d", str(classes), str(source)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    engine_samples = runtime_dir / "fiji_engine_samples.csv"
    cmd = [str(java), "-Djava.awt.headless=true", "-Xmx1024m", "-cp", str(classes) + os.pathsep + cp,
           "BenchmarkRuntimeDuc", str(runtime_dir / "runtime_cases.csv"), str(ROOT / "data/raw"),
           str(engine_samples), str(repeats), cfg["eigen_order"]]
    print(f"Measuring ImageScience engine: {len(case_rows)} cases, warm-up + {repeats} repeats", flush=True)
    completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    (runtime_dir / "java_engine_log.txt").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"Java engine failed; see java_engine_log.txt: {completed.stderr[-2000:]}")
    print(completed.stdout, flush=True)
    cache = {}
    samples = []
    for i, case in enumerate(case_rows, 1):
        name, command, sigma = case["image"], case["command"], case["sigma"]
        if name not in cache:
            cache[name] = np.asarray(Image.open(ROOT / f"data/raw/{name}.png"), dtype=np.float64)
        fn = operation(command, cache[name], sigma)
        for iteration in range(repeats + 1):
            start = time.perf_counter_ns()
            result = fn()
            elapsed = (time.perf_counter_ns() - start) / 1e6
            # Keep the result live through the timer (NumPy is eager).
            if result is None:
                raise ValueError("Operation returned no result")
            samples.append(dict(source="python", **case, iteration=iteration,
                                warmup=iteration == 0, runtime_ms=elapsed))
        if i % 40 == 0:
            print(f"Python runtime cases complete: {i}/{len(case_rows)}", flush=True)
    write_csv(runtime_dir / "python_samples.csv", samples)
    all_samples = read_csv(engine_samples) + samples
    grouped = {}
    for s in all_samples:
        key = (s["source"], s["image"], s["command"], s["sigma"])
        grouped.setdefault(key, []).append(s)
    summary = []
    expected = {(source, c["image"], c["command"], c["sigma"]) for c in case_rows for source in ("python", "fiji_engine")}
    if set(grouped) != expected:
        raise ValueError("Runtime case coverage mismatch")
    for (source_name, image, command, sigma), rows in sorted(grouped.items()):
        if sorted(int(r["iteration"]) for r in rows) != list(range(repeats + 1)):
            raise ValueError("Duplicate/missing runtime iterations")
        measured = [float(r["runtime_ms"]) for r in rows if int(r["iteration"]) != 0]
        summary.append(dict(source=source_name, image=image, command=command, sigma=sigma,
                            **timing_summary(measured), warmup_discarded=1,
                            width=int(cache[image].shape[1]), height=int(cache[image].shape[0])))
    write_csv(runtime_dir / "runtime_case_summary.csv", summary)
    paired = []
    index = {(r["source"], r["image"], r["command"], r["sigma"]): r for r in summary}
    for c in case_rows:
        key = (c["image"], c["command"], c["sigma"])
        py, fj = index[("python", *key)], index[("fiji_engine", *key)]
        paired.append(dict(**c, python_median_ms=py["median_ms"], fiji_engine_median_ms=fj["median_ms"],
                           ratio_python_over_engine=py["median_ms"] / fj["median_ms"]))
    write_csv(runtime_dir / "runtime_paired.csv", paired)
    environment = dict(
        started_or_recorded_at_utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(),
        cpu=platform.processor(), logical_cpu_count=os.cpu_count(), python=platform.python_version(), numpy=np.__version__,
        java_executable=str(java), javac=str(javac),
        jvm_version=subprocess.run([str(java), "-version"], capture_output=True, text=True).stderr,
        jars={str(p): sha256(p) for p in jars}, java_source_sha256=sha256(source),
        config_sha256=sha256(ROOT / "config.yaml"), cases=len(case_rows), measured_repeats=5, warmup_discarded=1,
        measurement_inputs_code_sha256=fingerprint,
        execution_order="ImageScience JVM first; Python second; sequential on this machine",
        engine="ImageJ/ImageScience headless API; not GUI macro timing",
        timed_region="kernel/filter/eigenvalue computation only; excludes input reading, Java input duplication and output I/O",
        precision="Python compute float64; ImageScience native precision; not forced to identical internal precision",
        comparability="edge is gradient+NMS, not full hysteresis/GT detector; measure complete Hessian/ST calls once per two outputs",
        caution="Single host/session; no claim of universal speed advantage; per-case warm-up may leave JVM JIT effects",
    )
    (runtime_dir / "runtime_environment.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")
    validate_inputs()
    if runtime_fingerprint() != fingerprint:
        raise ValueError("Runtime code/config/raw changed during measurement; repeat the run")
    environment["sample_files_sha256"] = {
        n:sha256(runtime_dir / n) for n in ("python_samples.csv", "fiji_engine_samples.csv", "runtime_cases.csv", "runtime_case_summary.csv", "runtime_paired.csv", "java_engine_log.txt")
    }
    (runtime_dir / "runtime_environment.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary, paired
