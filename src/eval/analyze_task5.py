"""Task 24: reproducible figures, runtime comparison and Vietnamese analysis.

Run: python -m src.eval.analyze_task5
Task-23 metric files are read-only. Charts export PNG (300 dpi), SVG and PDF.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import html
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

from src.eval.metric_utils import ROOT, RESULTS, sha256, strict_config, validate_inputs, write_csv
from src.eval.task5_runtime import TASK5, build_cases, measure_runtime, read_csv, runtime_fingerprint

COLORS = {"python": "#007C91", "fiji": "#D47700", "fiji_engine": "#D47700"}
LABELS = {"python": "Python / NumPy", "fiji": "Fiji maps", "fiji_engine": "ImageScience / Java"}
OPS = ["gauss", "lx", "ly", "lxx", "lxy", "lyy", "grad", "lap", "hess-l1", "hess-l2", "st-l1", "st-l2"]


def verify_metric_delivery():
    manifest = json.loads((RESULTS / "run_manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "COMPLETE":
        raise ValueError("Task 23 must be COMPLETE before plotting")
    for name, digest in manifest["outputs"].items():
        if sha256(RESULTS / name) != digest:
            raise ValueError(f"Task 23 output changed: {name}")
    # Check recorded dependencies, allowing newly added task-24 modules.
    for name, digest in manifest["code_config_sha256"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"Task 23 dependency changed: {name}; regenerate metrics first")
    validate_inputs()
    return manifest


def tier1_summary(rows):
    if len(rows) != 220:
        raise ValueError("Expected 220 Tier 1 records")
    result = []
    for op in OPS:
        group = [r for r in rows if r["operator"] == op]
        if not group or any(r["status"] not in ("PASS", "FAIL") for r in group):
            raise ValueError(f"Incomplete/undefined Tier 1 group: {op}")
        result.append(dict(operator=op, maps=len(group), passed=sum(r["status"] == "PASS" for r in group),
                           failed=sum(r["status"] == "FAIL" for r in group),
                           median_relative_error=float(np.median([float(r["relative_error"]) for r in group])),
                           max_relative_error=max(float(r["relative_error"]) for r in group),
                           minimum_pearson=min(float(r["pearson_r"]) for r in group)))
    return result


def edge_summary(rows, native):
    result = []
    sigmas = sorted({float(r["sigma"]) for r in rows if r["task"] == "edge_bsds"})
    for s in sigmas:
        row = dict(sigma=s)
        for source in ("python", "fiji"):
            group = [r for r in rows if r["source"] == source and r["task"] == "edge_bsds" and float(r["sigma"]) == s]
            if len(group) != 10:
                raise ValueError("Missing BSDS image in sigma summary")
            for key in ("precision", "recall", "f1"):
                row[f"{source}_{key}"] = float(np.mean([float(r[key]) for r in group]))
        refs = [r for r in native if float(r["sigma"]) == s]
        if len(refs) != 10:
            raise ValueError("Incomplete native Edge reference")
        row["native_reference_f1"] = float(np.mean([float(r["f1"]) for r in refs]))
        row["delta_f1_fiji_minus_python"] = row["fiji_f1"] - row["python_f1"]
        result.append(row)
    return result


def validate_runtime(directory, cfg):
    directory = Path(directory)
    env = json.loads((directory / "runtime_environment.json").read_text(encoding="utf-8"))
    if env["config_sha256"] != sha256(ROOT / "config.yaml") or env["measured_repeats"] != 5 or env["warmup_discarded"] != 1:
        raise ValueError("Runtime config/protocol mismatch; use --remeasure-runtime")
    if env.get("measurement_inputs_code_sha256") != runtime_fingerprint():
        raise ValueError("Runtime inputs/code provenance differs; use --remeasure-runtime")
    for name, digest in env.get("sample_files_sha256", {}).items():
        if sha256(directory / name) != digest:
            raise ValueError(f"Runtime file checksum mismatch: {name}")
    expected = {(s, r["image"], r["command"], r["sigma"]) for r in build_cases(cfg) for s in ("python", "fiji_engine")}
    raw = read_csv(directory / "python_samples.csv") + read_csv(directory / "fiji_engine_samples.csv")
    grouped = defaultdict(list)
    for r in raw:
        grouped[(r["source"], r["image"], r["command"], r["sigma"])].append(r)
    if set(grouped) != expected:
        raise ValueError("Incomplete runtime source/case coverage")
    for key, group in grouped.items():
        if sorted(int(r["iteration"]) for r in group) != list(range(6)):
            raise ValueError(f"Missing/duplicate repeats: {key}")
        for r in group:
            if str(r["warmup"]).lower() != str(int(r["iteration"]) == 0).lower():
                raise ValueError("Warm-up flag disagrees with iteration")
            if not np.isfinite(float(r["runtime_ms"])) or float(r["runtime_ms"]) <= 0:
                raise ValueError("Invalid runtime")
    summary = read_csv(directory / "runtime_case_summary.csv")
    if len(summary) != len(expected):
        raise ValueError("Runtime summary row count mismatch")
    for r in summary:
        key = (r["source"], r["image"], r["command"], r["sigma"])
        samples = [float(s["runtime_ms"]) for s in grouped[key] if int(s["iteration"]) > 0]
        if int(r["measured_repeats"]) != 5 or not np.isclose(float(r["median_ms"]), np.median(samples), rtol=1e-9):
            raise ValueError("Runtime median does not match retained samples")
    paired = read_csv(directory / "runtime_paired.csv")
    index = {(r["source"], r["image"], r["command"], r["sigma"]): r for r in summary}
    if len(paired) * 2 != len(expected):
        raise ValueError("Incomplete runtime pairs")
    for r in paired:
        key = (r["image"], r["command"], r["sigma"])
        py, fj = index[("python", *key)], index[("fiji_engine", *key)]
        if not np.isclose(float(r["ratio_python_over_engine"]), float(py["median_ms"]) / float(fj["median_ms"]), rtol=1e-9):
            raise ValueError("Runtime pair ratio mismatch")
    return summary, paired, env


def export(fig, stem, title, caption, catalog):
    directory = TASK5 / "figures"
    directory.mkdir(parents=True, exist_ok=True)
    fig.savefig(directory / f"{stem}.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(directory / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    fig.savefig(directory / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    catalog.append(dict(stem=stem, title=title, caption=caption))


def draw_figures(t1, border, t2, summary, edge, runtime, paired):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 12,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": .18, "pdf.fonttype": 42})
    catalog = []
    ts = tier1_summary(t1)
    fig, axes = plt.subplots(1, 2, figsize=(12, 6), layout="constrained")
    scales = sorted({float(r["sigma"]) for r in t1 if r["sigma_i"] == ""})
    matrix = np.full((len(OPS), len(scales)), np.nan)
    for i, op in enumerate(OPS):
        for j, s in enumerate(scales):
            values = [float(r["relative_error"]) for r in t1 if r["operator"] == op and float(r["sigma"]) == s]
            if values:
                matrix[i,j] = max(values)
    masked = np.ma.masked_invalid(matrix)
    mesh = axes[0].imshow(masked, aspect="auto", cmap="YlOrRd", norm=LogNorm(vmin=1e-8, vmax=max(.01, np.nanmax(matrix))))
    axes[0].set(xticks=range(len(scales)), xticklabels=scales, yticks=range(len(OPS)), yticklabels=OPS,
                xlabel="σ (ST: σd; σi lấy từ config)", title="Sai số tương đối lớn nhất qua 5 ảnh")
    for i in range(len(OPS)):
        for j in range(len(scales)):
            if np.isfinite(matrix[i,j]):
                axes[0].text(j, i, f"{matrix[i,j]:.1e}", ha="center", va="center", fontsize=8,
                             color="white" if matrix[i,j] > 2e-4 else "black")
    fig.colorbar(mesh, ax=axes[0], label="max|Python−Fiji| / max|Fiji| (lõi)", shrink=.8)
    y = np.arange(len(OPS))
    axes[1].barh(y, [r["passed"] for r in ts], color=COLORS["python"], label="Đạt cả hai ngưỡng gốc")
    axes[1].barh(y, [r["failed"] for r in ts], left=[r["passed"] for r in ts], color="#B04A45", label="Chưa đạt")
    passed = sum(r["passed"] for r in ts)
    axes[1].set(yticks=y, yticklabels=OPS, xlabel="Số bản đồ", title=f"{passed} PASS / {len(t1)}; {len(t1)-passed} chưa đạt")
    axes[1].invert_yaxis(); axes[1].legend(loc="lower right", fontsize=8)
    export(fig, "01_doi_chuan_tang1", "Đối chuẩn số học Tầng 1",
           "220 cặp; relative error <1e-4 và Pearson >0.9999. ST chỉ có hai cặp scale, ô trống không phải thiếu file.", catalog)

    indexed = {(r["image"], r["operator"], r["sigma"], r["sigma_i"]): r for r in border}
    fig, ax = plt.subplots(figsize=(8, 6), layout="constrained")
    border_points = []
    for i, op in enumerate(OPS):
        points = []
        for r in t1:
            if r["operator"] == op:
                b = indexed[(r["image"], r["operator"], r["sigma"], r["sigma_i"])]
                peak = float(r["reference_peak"])
                core_value, border_value = float(r["rmse"])/peak, float(b["rmse"])/peak
                points.append((core_value, border_value))
                border_points.append(dict(image=r["image"], operator=op, sigma=r["sigma"], sigma_i=r["sigma_i"],
                                          core_normalized_rmse=core_value, border_normalized_rmse=border_value,
                                          normalization="same core reference_peak for both regions"))
        a = np.asarray(points)
        ax.scatter(a[:,0], a[:,1], label=op, s=22, alpha=.75, marker=["o", "s", "^"][i//4])
    write_csv(TASK5 / "tables/border_core_comparison.csv", border_points)
    upper = max(max(p["core_normalized_rmse"], p["border_normalized_rmse"]) for p in border_points) * 2
    ax.plot([0, upper], [0, upper], "--", color="gray", linewidth=1, label="Biên = lõi")
    ax.set_xscale("symlog", linthresh=1e-8)
    ax.set_yscale("symlog", linthresh=1e-8)
    ax.set(xlim=(0, upper), ylim=(0, upper),
           xlabel="RMSE lõi / peak lõi (symlog)", ylabel="RMSE biên / cùng peak lõi (symlog)",
           title="Sai số biên và lõi — từng cặp TIFF")
    ax.legend(ncol=3, fontsize=8, loc="upper left")
    export(fig, "02_sai_so_bien_va_loi", "Sai số vùng biên",
           "Mỗi điểm là một cặp TIFF. Cùng peak lõi trên cả hai trục; phía trên đường chéo là RMSE biên lớn hơn. Thang symlog tuyến tính gần 0 (<=1e-8), giữ cả điểm bằng 0; không bỏ các biên ảnh tổng hợp có sai số cực nhỏ.", catalog)

    fig, ax = plt.subplots(figsize=(8, 4.7), layout="constrained")
    for image in sorted({r["image"] for r in t1}):
        group = sorted([r for r in t1 if r["image"] == image and r["operator"] == "gauss"], key=lambda r: float(r["sigma"]))
        ax.plot([float(r["sigma"]) for r in group], [float(r["psnr_db"]) for r in group], "o-", label=image)
    ax.set(xlabel="σ (pixel)", ylabel="PSNR (dB), MAX=255", title="PSNR chỉ cho Gaussian smoothing", xticks=scales)
    ax.legend(ncol=3, fontsize=9)
    export(fig, "03_psnr_gaussian", "PSNR Gaussian",
           "20 bản đồ Gaussian, chấm vùng lõi. PSNR cao phản ánh sai số nhỏ; không áp dụng chỉ số này cho đạo hàm có dấu.", catalog)

    fig, (ax, diff) = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    xs = [r["sigma"] for r in edge]
    for source in ("python", "fiji"):
        ax.plot(xs, [r[f"{source}_f1"] for r in edge], "o-" if source == "python" else "s--", color=COLORS[source], label=LABELS[source])
    ax.plot(xs, [r["native_reference_f1"] for r in edge], ":^", color="#777777", label="Native Edges (tham chiếu riêng)")
    ax.set(ylim=(0,1), xticks=xs, xlabel="σ (pixel)", ylabel="Macro F1, 10 BSDS", title="F1 theo σ — cùng Canny ở hai nguồn")
    ax.legend(fontsize=8)
    diff.bar([str(s) for s in xs], [r["delta_f1_fiji_minus_python"] for r in edge], color=COLORS["fiji"])
    diff.axhline(0, color="black", linewidth=.8)
    diff.set(xlabel="σ (pixel)", ylabel="F1 Fiji − F1 Python", title="Chênh lệch thực (không phóng đại F1 chính)")
    diff.ticklabel_format(axis="y", style="sci", scilimits=(0,0))
    export(fig, "04_f1_theo_sigma", "Cạnh: F1 theo sigma",
           "Canny dùng ngưỡng chọn trên Python rồi đóng băng cho Fiji tại từng σ. Native Edges có thuật toán/ngưỡng riêng.", catalog)

    grid = read_csv(RESULTS / "bsds_threshold_grid.csv")
    fig, ax = plt.subplots(figsize=(7.5, 6), layout="constrained")
    for i, s in enumerate(xs):
        g = [r for r in grid if float(r["sigma"]) == s]
        color = plt.get_cmap("tab10")(i)
        ax.scatter([float(r["mean_recall"]) for r in g], [float(r["mean_precision"]) for r in g], s=24, alpha=.5, color=color, label=f"Python grid σ={s:g}")
        best = next(r for r in g if r["selected"].lower() == "true")
        ax.scatter(float(best["mean_recall"]), float(best["mean_precision"]), color=color, s=180, marker="*", edgecolors="black")
        fj = next(r for r in edge if r["sigma"] == s)
        ax.scatter(fj["fiji_recall"], fj["fiji_precision"], marker="s", s=90, facecolors="none", edgecolors=[color], linewidths=1.8)
    ax.set(xlim=(0,1), ylim=(0,1), xlabel="Macro Recall", ylabel="Macro Precision", title="Precision–Recall: các điểm vận hành trong lưới")
    ax.legend(fontsize=8)
    export(fig, "05_precision_recall", "Các điểm Precision–Recall",
           "Chấm nhỏ: lưới Python; sao: cặp được chọn; ô vuông: Fiji tại cùng cặp. Đây là các điểm lưới hai ngưỡng, không phải đường PR liên tục; không tính AP/AUC.", catalog)

    fig, axes = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    lows = sorted({float(r["p_low"]) for r in grid}); highs = sorted({float(r["p_high"]) for r in grid})
    for ax, s in zip(axes.flat, xs):
        g = [r for r in grid if float(r["sigma"]) == s]
        a = np.array([[float(next(r for r in g if float(r["p_low"]) == lo and float(r["p_high"]) == hi)["mean_f1"]) for hi in highs] for lo in lows])
        im = ax.imshow(a, aspect="auto", vmin=0, vmax=1, cmap="YlGnBu")
        for iy, lo in enumerate(lows):
            for ix, hi in enumerate(highs):
                ax.text(ix, iy, f"{a[iy,ix]:.3f}", ha="center", va="center", fontsize=9)
        best = next(r for r in g if r["selected"].lower() == "true")
        ax.plot(highs.index(float(best["p_high"])), lows.index(float(best["p_low"])), "s", ms=32, markerfacecolor="none", markeredgecolor="#D47700", markeredgewidth=2)
        ax.set(xticks=range(len(highs)), xticklabels=highs, yticks=range(len(lows)), yticklabels=lows,
               xlabel="p_high", ylabel="p_low", title=f"σ={s:g}, F1 Python trung bình")
    fig.colorbar(im, ax=axes.ravel().tolist(), label="Macro F1", shrink=.8)
    export(fig, "06_luoi_nguong_canny", "Lựa chọn ngưỡng Canny",
           "Mỗi ô là mean F1 trên 10 ảnh Python. Khung cam chọn trong lưới đã thiết kế; không phải tối ưu trên mọi ngưỡng có thể.", catalog)

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), layout="constrained")
    for ax, task, title in zip(axes, ("ridge_drive", "blob_log"), ("DRIVE — Frangi đa tỷ lệ", "Blob — bốn ảnh tổng hợp và một ảnh tế bào")):
        images = sorted({r["image"] for r in t2 if r["task"] == task})
        x = np.arange(len(images))
        for source, offset in (("python", -.18), ("fiji", .18)):
            values = [float(next(r for r in t2 if (r["task"],r["source"],r["image"]) == (task,source,image))["f1"]) for image in images]
            ax.bar(x+offset, values, width=.35, color=COLORS[source], label=LABELS[source])
        ax.set(xticks=x, xticklabels=images, ylim=(0,1.08), ylabel="F1 mỗi ảnh", title=title)
        ax.legend(fontsize=8, loc="upper right")
    export(fig, "07_f1_tung_anh", "Ridge và Blob: kết quả từng ảnh",
           "Cùng ngưỡng giữa hai nguồn. F1 thấp trên blob_05 thể hiện khoảng cách từ ảnh tổng hợp tới ảnh sinh học.", catalog)

    fig, ax = plt.subplots(figsize=(7, 4.8), layout="constrained")
    for i, source in enumerate(("python", "fiji")):
        row = next(r for r in summary if r["source"] == source and r["task"] == "blob_log")
        vals = [float(row["macro_f1"]), float(row["micro_f1"])]
        bars = ax.bar(np.arange(2)+(i-.5)*.34, vals, width=.33, color=COLORS[source], label=LABELS[source])
        ax.bar_label(bars, fmt="%.3f", padding=3)
    ax.set(xticks=[0,1], xticklabels=["Macro F1 (mỗi ảnh một trọng số)", "Micro F1 (gộp các đối tượng)"], ylim=(0,1.05), ylabel="F1", title="Blob: phải báo cáo cả macro và micro")
    ax.legend(fontsize=8)
    export(fig, "08_blob_macro_micro", "Macro và micro F1 của blob",
           "Bốn ảnh tổng hợp có 4 đối tượng mỗi ảnh, ảnh tế bào có 276. Macro cao không đại diện cho khả năng phát hiện tế bào.", catalog)

    commands = sorted({r["command"] for r in runtime})
    rt_table = []
    for command in commands:
        group = [r for r in paired if r["command"] == command]
        row = dict(command=command, n_cases=len(group))
        for name, key in (("python", "python_median_ms"), ("fiji_engine", "fiji_engine_median_ms"), ("ratio", "ratio_python_over_engine")):
            vals = [float(r[key]) for r in group]
            row.update({f"{name}_median":float(np.median(vals)), f"{name}_q25":float(np.percentile(vals,25)), f"{name}_q75":float(np.percentile(vals,75))})
        rt_table.append(row)
    write_csv(TASK5 / "tables/runtime_by_command.csv", rt_table)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    x = np.arange(len(commands))
    for source, offset in (("python", -.15), ("fiji_engine", .15)):
        mid = np.array([r[f"{source}_median"] for r in rt_table])
        lo = mid - [r[f"{source}_q25"] for r in rt_table]; hi = [r[f"{source}_q75"] for r in rt_table] - mid
        axes[0].errorbar(x+offset, mid, yerr=np.array([lo,hi]), fmt="o", capsize=3, color=COLORS[source], label=LABELS[source])
    axes[0].set(xticks=x, xticklabels=commands, yscale="log", ylabel="Thời gian lõi (ms, log)", title="Median các case; thanh = IQR giữa case")
    axes[0].tick_params(axis="x", rotation=55); axes[0].legend(fontsize=8)
    med = np.array([r["ratio_median"] for r in rt_table])
    axes[1].errorbar(x, med, yerr=np.array([med-[r["ratio_q25"] for r in rt_table], [r["ratio_q75"] for r in rt_table]-med]), fmt="o", capsize=3, color="#60538E")
    axes[1].axhline(1, ls="--", color="black", lw=1)
    axes[1].set(xticks=x, xticklabels=commands, yscale="log", ylabel="Median tỷ số thời gian Python / ImageScience", title="Từng case được ghép cùng ảnh/lệnh/scale")
    axes[1].tick_params(axis="x", rotation=55)
    export(fig, "09_thoi_gian_theo_lenh", "Thời gian chạy theo phép toán",
           "357 case, mỗi case bỏ 1 warm-up và lấy median 5 lần đo. IQR thể hiện phân bố giữa case; trên 1 ở biểu đồ tỷ số nghĩa là Python mất nhiều thời gian hơn. Lõi ImageScience headless, không phải GUI Fiji.", catalog)

    cfg = strict_config()
    fig, axes = plt.subplots(2,2, figsize=(11, 7), layout="constrained")
    runtime_scales = []
    for ax, cmd in zip(axes.flat, ("gauss", "lx", "hessian", "laplacian")):
        for source in ("python", "fiji_engine"):
            vals = []
            for s in cfg["sigmas"]:
                g = [float(r["median_ms"]) for r in runtime if r["source"] == source and r["command"] == cmd and r["image"] in cfg["tier1_images"] and r["sigma"] == str(float(s))]
                if len(g) != 5:
                    raise ValueError("Unbalanced image cohort in runtime-vs-scale plot")
                value = float(np.median(g)); vals.append(value)
                runtime_scales.append(dict(source=source, command=cmd, sigma=s, n_images=5, median_case_ms=value))
            ax.plot(cfg["sigmas"], vals, "o-", color=COLORS[source], label=LABELS[source])
        ax.set(xticks=cfg["sigmas"], ylim=(0,None), xlabel="σ (pixel)", ylabel="Median thời gian lõi (ms)", title=f"{cmd}: cùng 5 ảnh Tầng 1")
        ax.legend(fontsize=8)
    write_csv(TASK5 / "tables/runtime_by_sigma.csv", runtime_scales)
    export(fig, "10_thoi_gian_theo_sigma", "Thời gian chạy theo sigma",
           "Giữ cố định cùng 5 ảnh Tầng 1 cho cả bốn lệnh và mọi sigma. Mỗi điểm là median 5 case; mỗi case là median 5 lần sau warm-up.", catalog)
    return catalog, rt_table


def write_analysis(t1, t2, summary, edge, rt_table, paired, catalog):
    ts = tier1_summary(t1)
    best = max(edge, key=lambda r:r["python_f1"])
    blob = {r["source"]:r for r in summary if r["task"] == "blob_log"}
    ridge = {r["source"]:r for r in summary if r["task"] == "ridge_drive"}
    worst = max(t1, key=lambda r:float(r["relative_error"]))
    delta = max(abs(r["delta_f1_fiji_minus_python"]) for r in edge)
    ratios = [float(r["ratio_python_over_engine"]) for r in paired]
    status = Counter(r["status"] for r in t1)
    lines = ["# Đức — Công việc 5: Biểu đồ và phân tích kết quả", "",
             "**STT 24 trong bảng phân công, hạn 14/11.** Thực hiện ngày 08/11/2026, trên bộ metric công việc 4 và phép đo thời gian mới.", "",
             "## 1. Dữ liệu và phương pháp", "",
             "Bộ thực nghiệm gồm 10 BSDS500, 10 DRIVE và 5 blob (4 tổng hợp, 1 ảnh tế bào). Hai nguồn dùng cùng ảnh grayscale uint8, cùng scale/config và cùng detector hậu xử lý. Đầu ra công việc 4 được đọc nguyên trạng, xác minh checksum; không sửa lõi, GT, ngưỡng nghiệm thu hoặc chọn lại ngưỡng khi vẽ.", "",
             "Tầng 1 đối chiếu 220 cặp TIFF trên 5 ảnh đại diện. Tầng 2 có 55 dòng mỗi nguồn: 40 BSDS theo 4 sigma, 10 DRIVE đa tỷ lệ và 5 blob đa tỷ lệ. Precision/Recall/F1 dưới đây là kết quả nội bộ trên chính tập dùng chọn ngưỡng, không phải điểm test độc lập chính thức.", "",
             "## 2. Đối chuẩn số học và sai số biên", "",
             f"Kết quả đúng tiêu chuẩn gốc là **{status['PASS']}/220 PASS và {status['FAIL']}/220 chưa đạt**. Điều kiện là đồng thời relative error < 1e-4 và Pearson r > 0.9999. Chỉ Pearson cao không đủ chứng minh tương đương biên độ.", "",
             "| Toán tử | Đạt / tổng | Sai số tương đối lớn nhất | Pearson nhỏ nhất |",
             "| --- | ---: | ---: | ---: |"]
    lines += [f"| {r['operator']} | {r['passed']}/{r['maps']} | {r['max_relative_error']:.6g} | {r['minimum_pearson']:.10g} |" for r in ts]
    lines += ["", f"Sai số tương đối lớn nhất xuất hiện ở `{worst['image']}`, `{worst['operator']}`, sigma={worst['sigma']}: **{float(worst['relative_error']):.6g}**. Đây là sai số vùng lõi, vì vậy không thể quy toàn bộ khác biệt cho xử lý biên.", "",
              "Gaussian cho kết quả gần nhau ở độ chính xác lưu float32; PSNR chỉ được trình bày cho Gaussian với MAX=255. Giá trị PSNR rất cao không có nghĩa toàn bộ hệ thống phát hiện đặc trưng chính xác tương ứng. Với đạo hàm/Hessian/ST, dùng sai số và Pearson theo tài liệu.", "",
              "Kernel Python hiện có bước bảo toàn moment rời rạc. Khác biệt với cách rời rạc hóa/chuẩn hóa của FeatureJ là giả thuyết cần đối chiếu đáp ứng xung và phép đo hiệu chuẩn; biểu đồ không tự chứng minh đây là nguyên nhân duy nhất. Không đổi kernel chỉ để giảm số FAIL.", "",
              "Hình sai số biên/lõi dùng cùng peak tham chiếu lõi trên cả hai trục. Điểm trên đường chéo cho biết RMSE biên lớn hơn lõi; mỗi điểm vẫn đại diện toán tử/ảnh/scale riêng, không gộp sai số có đơn vị khác nhau thành một MSE chung. Dùng symlog với vùng tuyến tính <=1e-8 để giữ cả sai số bằng 0/rất nhỏ, đặc biệt ở nền blob tổng hợp; không tự bỏ điểm không vẽ được trên log thông thường. Bảng `tables/border_core_comparison.csv` giữ nguyên đủ 220 điểm. Các bảng biên đã tách khỏi điều kiện nghiệm thu lõi.", "",
              "## 3. Cạnh: ảnh hưởng của sigma, Precision–Recall và ngưỡng", "",
              "| σ | F1 Python | F1 Fiji (cùng Canny) | Fiji − Python | Native Edges (tham chiếu) |",
              "| ---: | ---: | ---: | ---: | ---: |"]
    lines += [f"| {r['sigma']:g} | {r['python_f1']:.6f} | {r['fiji_f1']:.6f} | {r['delta_f1_fiji_minus_python']:+.8f} | {r['native_reference_f1']:.6f} |" for r in edge]
    lines += ["", f"Trong bốn sigma khảo sát, Python đạt mean F1 cao nhất tại **sigma={best['sigma']:g}, F1={best['python_f1']:.6f}**. Ở sigma nhỏ, có thể giữ nhiều chi tiết/texture và tăng cạnh giả; sigma lớn làm mất cạnh yếu hoặc dịch chuyển cấu trúc mảnh. Đây là diễn giải phù hợp xu hướng quan sát, không phải chứng minh nhân quả trên mọi ảnh.", "",
              f"Sai khác mean F1 lớn nhất giữa hai nguồn cùng Canny là **{delta:.8f}**. Hai đường F1 gần trùng cho thấy độ ổn định của hậu xử lý trên tập này, nhưng không thay thế điều kiện sai số nghiêm ngặt Tầng 1. Một bản đồ có thể không đạt biên độ tuyệt đối mà mặt nạ sau ngưỡng vẫn gần nhau.", "",
              "Hình Precision–Recall trình bày các điểm của lưới hai ngưỡng phân vị. Sao là cặp chọn trên Python; ô vuông là Fiji dùng nguyên cặp ấy. Không nối thành đường PR liên tục và không suy ra AP/AUC từ 12 cặp này. F1 tối ưu được hiểu là tốt nhất **trong lưới đã thiết kế**, không khẳng định tối ưu toàn cục.", "",
              "Native FeatureJ Edges có NMS/ngưỡng riêng, được vẽ bằng đường tham chiếu riêng. Chênh lệch với Canny có thể đến từ hậu xử lý và lựa chọn ngưỡng, không được dùng để kết luận lõi vi phân của một nguồn tốt hơn nguồn kia.", "",
              "## 4. Ridge và blob: ưu điểm, hạn chế thực tế", "",
              f"DRIVE có macro F1 **{float(ridge['python']['macro_f1']):.6f}** (Python) và **{float(ridge['fiji']['macro_f1']):.6f}** (Fiji). Python có macro precision **{float(ridge['python']['macro_precision']):.6f}**, recall **{float(ridge['python']['macro_recall']):.6f}**: trong protocol hiện tại, đáp ứng được giữ khá chọn lọc nhưng còn bỏ sót mạch. Khả năng mất các nhánh yếu/mảnh cần kiểm tra thêm bằng overlay trước khi khẳng định nguyên nhân.", "",
              "Vùng chấm DRIVE là giao các FOV sau xói mòn theo mọi scale, support lớn nhất 32 px ở config hiện tại. Kết quả không so trực tiếp với bảng dùng FOV sigma=2 hay percentile 85 ở phiên bản cũ. Hai nguồn dùng cùng vùng và ngưỡng chọn trên Python. Biểu đồ từng ảnh cho thấy mức độ biến thiên, tránh chỉ nêu một giá trị trung bình.", "",
              f"Bốn ảnh blob tổng hợp đạt F1=1 ở cả hai nguồn. Với `blob_05`, F1 chỉ **{float(next(r for r in t2 if r['source']=='python' and r['image']=='blob_05')['f1']):.6f}** và **{float(next(r for r in t2 if r['source']=='fiji' and r['image']=='blob_05')['f1']):.6f}**. Điều này cho thấy kết quả trên hình học tổng hợp chưa đại diện đầy đủ cho dữ liệu tế bào có tương phản/kích thước đa dạng.", "",
              f"Blob macro F1 là **{float(blob['python']['macro_f1']):.6f}/{float(blob['fiji']['macro_f1']):.6f}** (Python/Fiji), trong khi micro F1 là **{float(blob['python']['micro_f1']):.6f}/{float(blob['fiji']['micro_f1']):.6f}**. Macro đặt mỗi ảnh cùng trọng số, nên bốn ảnh tổng hợp hoàn hảo có ảnh hưởng lớn. Micro gộp đối tượng, phản ánh rõ hơn ảnh tế bào có 276 nhãn so với chỉ 16 đối tượng tổng hợp. Cần báo cáo cả hai, không chọn riêng điểm cao.", "",
              "Việc ghép blob là một-một, có cả cổng khoảng cách tâm và sai số bán kính; 15 vùng ignore được áp trước khi tính FP. Lưới vẫn đúng 7 sigma; detector hiện bỏ hai đầu scale. GT ngoài dải kích thước/cực trị hợp lệ có thể làm giảm recall. Đây là giới hạn cấu hình/phương pháp, không phải lý do loại nhãn khó khỏi báo cáo.", "",
              "## 5. Thời gian chạy — đo mới trên cùng máy", "",
              "Đo lại **357 case** cùng ảnh/lệnh/scale của phạm vi macro hiện tại, loại 12 case edge legacy không thuộc phạm vi này. Mỗi nguồn có 357 × (1 warm-up + 5 lần giữ lại) = **2142 mẫu**, tổng **4284 mẫu**. Mỗi case dùng median 5 mẫu sau bỏ warm-up; lưu tất cả mẫu để kiểm tra dao động.", "",
              "Nguồn Java là **ImageJ 1.53k / ImageScience 3.0.0**, gọi API headless trên JVM cục bộ; không phải phép đo GUI macro. Python dùng NumPy tính float64, ImageScience dùng độ chính xác nội tại của thư viện. Đọc PNG, chuyển kiểu, clone input Java và ghi ảnh đều ngoài vùng đo. Các lệnh gradient/edge là gradient hoặc gradient+NMS, không bao gồm Canny hysteresis, Frangi hay pipeline chấm GT.", "",
              "| Lệnh | Case | Median Python (ms) | Median engine (ms) | Median tỷ số từng case Python/engine |",
              "| --- | ---: | ---: | ---: | ---: |"]
    lines += [f"| {r['command']} | {r['n_cases']} | {r['python_median']:.3f} | {r['fiji_engine_median']:.3f} | {r['ratio_median']:.3f} |" for r in rt_table]
    lines += ["", f"Median tỷ số Python/engine trên toàn bộ 357 case là **{float(np.median(ratios)):.3f}**. Tỷ số >1 nghĩa là Python mất nhiều thời gian hơn ở case đó; <1 nghĩa là ngược lại. Không gọi đây là tốc độ chung cho mọi ảnh/máy hoặc mọi lệnh. Median tỷ số từng case khác với tỷ số hai median và không được tráo hai phép tổng hợp.", "",
              "Biểu đồ theo sigma giữ cùng 5 ảnh Tầng 1, tránh thay đổi số ảnh/kích thước khi tăng sigma. Python tích chập hữu hạn theo support tăng với sigma; xu hướng thời gian còn phụ thuộc số phép tích chập của từng toán tử, bộ nhớ, JVM JIT và nhiễu hệ thống. Không dùng một lần chạy để suy ra độ phức tạp tiệm cận.", "",
              "Thanh IQR ở biểu đồ theo lệnh là phân bố **giữa các median case**, không phải khoảng tin cậy hay sai số chuẩn của 5 lần lặp. IQR/min/max của 5 lần đo từng case được lưu riêng. Java đo trước, Python đo sau, trong một phiên trên một máy; không kiểm soát hoàn toàn tải nền/tần số CPU. Hồ sơ môi trường và SHA-256 hai JAR nằm trong `runtime/runtime_environment.json`.", "",
              "## 6. Kết luận có thể dùng trong báo cáo", "",
              "Trên tập thực nghiệm nội bộ, hai nguồn tạo kết quả phát hiện khá gần nhau khi dùng chung detector/tham số. Gaussian đối chuẩn tốt; các đạo hàm và toán tử bậc cao vẫn có sai số biên độ vượt chuẩn gốc ở nhiều trường hợp dù tương quan cao. Do đó, chưa thể tuyên bố toàn bộ cài đặt tương đương số học FeatureJ.", "",
              "Scale trung gian cho kết quả cạnh tốt hơn trong dãy đã khảo sát. Ridge đạt precision cao hơn recall trong protocol này. LoG hoạt động tốt trên blob tổng hợp nhưng còn hạn chế ở ảnh tế bào; micro F1 cung cấp góc nhìn thận trọng hơn macro F1. Đo thời gian cho phép mô tả đánh đổi thực thi trên máy hiện tại, không tách riêng được ảnh hưởng ngôn ngữ, precision và rời rạc hóa.", "",
              "Cần phối hợp nhóm kiểm chứng kernel/chuẩn hóa bằng hiệu chuẩn trước khi chấp nhận ngưỡng nới, và dùng tập tách biệt nếu muốn đánh giá khả năng khái quát. Chưa có số liệu noise/crop mới, nên phần này không kết luận độ bền với nhiễu hay thay đổi kích thước. Các phân tích cơ chế ở trên được nêu như giả thuyết, không thay cho thí nghiệm bổ sung.", "",
              "## 7. Danh mục hình để đưa vào báo cáo/slide", ""]
    for item in catalog:
        lines += [f"### {item['stem']}: {item['title']}", "", f"![{item['title']}](figures/{item['stem']}.png)", "", item["caption"], ""]
    (TASK5 / "PHAN_TICH_KET_QUA.md").write_text("\n".join(lines), encoding="utf-8")


def write_gallery(catalog):
    cards = []
    for r in catalog:
        stem, title, caption = r["stem"], html.escape(r["title"]), html.escape(r["caption"])
        cards.append(f'<article><h2>{title}</h2><a href="figures/{stem}.png"><img loading="lazy" src="figures/{stem}.png" alt="{title}"></a><p>{caption}</p><p><a href="figures/{stem}.png">PNG 300 DPI</a> · <a href="figures/{stem}.svg">SVG</a> · <a href="figures/{stem}.pdf">PDF</a></p></article>')
    page = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Đức — Công việc 5: Biểu đồ thực nghiệm</title><style>
body{font:16px/1.6 system-ui,sans-serif;background:#f3f5f7;color:#162e3b;margin:0}main{max-width:1100px;margin:auto;padding:28px}header,article{background:white;border:1px solid #dce4e9;border-radius:12px;padding:24px;margin:0 0 24px}h1{font-size:28px}h2{font-size:21px}a{color:#007c91}img{max-width:100%;height:auto;display:block}p{max-width:95ch}.note{border-left:4px solid #b04a45;padding-left:16px}</style><main>
<header><h1>Biểu đồ &amp; phân tích — Đức — 08/11/2026</h1><p>STT 24 · 25 ảnh · Hai nguồn · 10 hình, xuất PNG 300 DPI / SVG / PDF.</p>
<p class="note">Tầng 1: 35/220 PASS, 185 chưa đạt ngưỡng gốc. F1 gần nhau không thay cho tương đương số học. Thời gian Java là lõi ImageScience headless, không gồm GUI hay đọc/ghi ảnh.</p>
<p><a href="PHAN_TICH_KET_QUA.md">Phân tích chi tiết (Markdown)</a> · <a href="tables/tier1_operator_summary.csv">Bảng đối chuẩn</a> · <a href="tables/edge_by_sigma.csv">F1 theo σ</a> · <a href="runtime/runtime_paired.csv">Thời gian từng case</a> · <a href="analysis_manifest.json">Hồ sơ phiên chạy</a></p></header>'''
    (TASK5 / "index.html").write_text(page + "".join(cards) + "</main></html>", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remeasure-runtime", action="store_true")
    parser.add_argument("--imagej-dir", type=Path)
    args = parser.parse_args()
    TASK5.mkdir(parents=True, exist_ok=True)
    manifest_path = TASK5 / "analysis_manifest.json"
    state = dict(status="RUNNING", task=24, started_at_utc=datetime.now(timezone.utc).isoformat())
    def save():
        manifest_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    save()
    try:
        source_manifest = verify_metric_delivery()
        cfg = strict_config()
        if args.remeasure_runtime or not (TASK5 / "runtime/runtime_environment.json").is_file():
            measure_runtime(TASK5, args.imagej_dir)
        runtime, paired, environment = validate_runtime(TASK5 / "runtime", cfg)
        t1, border, t2, summary, native = [read_csv(RESULTS / n) for n in (
            "tier1_report.csv", "tier1_border_report.csv", "tier2_results_both.csv", "tier2_summary.csv", "featurej_edge_reference.csv")]
        edge = edge_summary(t2, native)
        write_csv(TASK5 / "tables/tier1_operator_summary.csv", tier1_summary(t1))
        write_csv(TASK5 / "tables/edge_by_sigma.csv", edge)
        write_csv(TASK5 / "tables/tier2_summary.csv", summary)
        catalog, rt_table = draw_figures(t1, border, t2, summary, edge, runtime, paired)
        write_csv(TASK5 / "figure_catalog.csv", catalog)
        write_analysis(t1, t2, summary, edge, rt_table, paired, catalog)
        write_gallery(catalog)
        verify_metric_delivery()
        code_paths = [Path(__file__), ROOT / "src/eval/task5_runtime.py", ROOT / "src/fiji/BenchmarkRuntimeDuc.java", ROOT / "src/eval/benchmark_runtime.py"]
        state.update(status="COMPLETE", finished_at_utc=datetime.now(timezone.utc).isoformat(),
                     metric_manifest_sha256=sha256(RESULTS / "run_manifest.json"),
                     source_metrics=source_manifest["outputs"], task23_inputs_unchanged=True,
                     code_sha256={str(p.relative_to(ROOT)):sha256(p) for p in code_paths},
                     matplotlib_version=matplotlib.__version__, figures=10, formats=["png_300dpi","svg","pdf"],
                     runtime_cases=len(paired), runtime_samples=2*len(paired)*6,
                     runtime_engine=environment["engine"],
                     outputs={str(p.relative_to(TASK5)):sha256(p) for p in sorted(TASK5.rglob("*")) if p.is_file() and p != manifest_path})
        save()
        print(f"COMPLETE: 10 figures (PNG/SVG/PDF), analysis and {len(paired)} paired runtime cases.\n{TASK5 / 'index.html'}", flush=True)
    except Exception as exc:
        state.update(status="ERROR", error=f"{type(exc).__name__}: {exc}")
        save()
        raise


if __name__ == "__main__":
    main()
