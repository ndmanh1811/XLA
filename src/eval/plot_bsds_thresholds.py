"""plot_bsds_thresholds.py - Vẽ các biểu đồ điều khiển cho Tier 2 BSDS.

Sinh ra 4 hình ảnh trong ``outputs/figures/``:

1. ``tier2_bsds_pr_curves.png`` — Đường cong Precision-Recall trung bình theo
   từng sigma (điểm p_low/p_high đã chọn, vẽ theo độ cao F1).
2. ``tier2_bsds_f1_vs_sigma.png`` — F1 trung bình vs sigma cho Python, Fiji và
   tham chiếu FeatureJ Edges.
3. ``tier2_bsds_f1_heatmap.png`` — Bản đồ nhiệt F1 trung bình theo lưới
   (p_low, p_high) của Python cho sigma tiêu biểu (2.0).
4. ``tier2_runtime_comparison.png`` — So sánh thời gian chạy Python vs Fiji theo
   từng loại phép toán (command).

Tất cả dữ liệu đọc từ CSV đã lưu trong ``outputs/metrics/``, giữ nguyên NumPy/
SciPy; chỉ dùng matplotlib để vẽ.
"""

from dataclasses import dataclass
from pathlib import Path
import csv
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

METRICS_DIR = ROOT / "outputs" / "metrics"
FIG_DIR = ROOT / "outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

SIGMAS = [1.0, 2.0, 4.0, 8.0]


def read_csv(path: Path):
    """Đọc CSV UTF-8-SIG, trả về danh sách dict (rỗng nếu file không có)."""
    if not path.exists():
        print(f"   [!] Bỏ qua {path}: chưa có file.")
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def float_or_none(value):
    if value in (None, "", "N/A"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def select_fair_rows(rows):
    """Lấy dòng đã chọn (selected == '1') cho nhánh fair, theo source và sigma."""
    selected = {}
    for row in rows:
        if row.get("selected", "0") != "1":
            continue
        sigma = float(row["sigma"])
        source = row["source"]
        selected[(source, sigma)] = row
    return selected


def plot_pr_curves(rows):
    """Đường cong P-R theo từng sigma (điểm đã chọn, màu nhãn theo F1)."""
    selected = select_fair_rows(rows)
    if not selected:
        return

    plt.figure(figsize=(7.2, 5.2), dpi=200)
    colors = {1.0: "#1f77b4", 2.0: "#ff7f0e", 4.0: "#2ca02c", 8.0: "#d62728"}
    handles = []
    for sigma in SIGMAS:
        for source, marker in (("python", "o"), ("fiji", "^")):
            row = selected.get((source, sigma))
            if row is None:
                continue
            p = float(row["mean_precision"])
            r = float(row["mean_recall"])
            f1 = float(row["mean_f1"])
            scatter = plt.scatter(
                [r],
                [p],
                s=120,
                color=colors[sigma],
                marker=marker,
                edgecolors="black",
                linewidths=0.7,
                zorder=5,
            )
            handles.append(
                plt.Line2D(
                    [0], [0], marker=marker, color="w", label=(
                        f"σ={sigma:.1f} ({'Python' if source == 'python' else 'Fiji'})"
                        f" — F1={f1:.4f}"
                    ),
                    markerfacecolor=colors[sigma],
                    markeredgecolor="black",
                    markersize=9,
                )
            )
    plt.xlabel("Recall (trung bình qua 10 annotator)", fontsize=10)
    plt.ylabel("Precision", fontsize=10)
    plt.title(
        "Precision–Recall tại bộ ngưỡng đã chọn, từng σ (nhánh fair Canny)",
        fontsize=11,
    )
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.grid(True, alpha=0.3)
    plt.legend(handles=handles, loc="lower left", fontsize=8.5, framealpha=0.9)
    plt.tight_layout()
    out = FIG_DIR / "tier2_bsds_pr_curves.png"
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"   -> Đã lưu: {out}")


def plot_f1_vs_sigma(rows):
    """F1 trung bình vs σ cho Python, Fiji và FeatureJ Edges."""
    by_sigma = read_csv(METRICS_DIR / "tier2_bsds_by_sigma.csv")
    if not by_sigma:
        return
    sigmas = []
    py_f1, fj_f1, edge_f1 = [], [], []
    for row in by_sigma:
        sigma = float(row["sigma"])
        sigmas.append(sigma)
        py_f1.append(float_or_none(row["python_mean_f1"]))
        fj_f1.append(float_or_none(row["fiji_mean_f1"]))
        edge_f1.append(float_or_none(row["edge_reference_mean_f1"]))

    plt.figure(figsize=(7.2, 5.2), dpi=200)
    plt.plot(
        sigmas,
        py_f1,
        marker="o",
        color="#1f77b4",
        linewidth=2,
        label="Python (fair Canny, ngưỡng đóng băng)",
    )
    plt.plot(
        sigmas,
        fj_f1,
        marker="^",
        color="#ff7f0e",
        linewidth=2,
        label="Fiji (lx/ly × σ + detect_canny)",
    )
    plt.plot(
        sigmas,
        edge_f1,
        marker="s",
        color="#d62728",
        linewidth=2,
        linestyle="--",
        label="FeatureJ Edges (tham chiếu, ngưỡng tuyệt đối)",
    )
    for x, y1, y2 in zip(sigmas, py_f1, fj_f1):
        plt.annotate(
            f"{y1:.4f}",
            (x, y1),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8,
            color="#1f77b4",
        )
        plt.annotate(
            f"{y2:.4f}",
            (x, y2),
            textcoords="offset points",
            xytext=(0, -14),
            ha="center",
            fontsize=8,
            color="#ff7f0e",
        )
    plt.xlabel("σ (tỷ lệ Gaussian)", fontsize=10)
    plt.ylabel("F1 trung bình (10 ảnh BSDS)", fontsize=10)
    plt.title("F1 trung bình vs σ — Python so với Fiji và tham chiếu FeatureJ",
              fontsize=11)
    plt.xscale("log", base=2)
    plt.xticks(sigmas, [f"{s:.1f}" for s in sigmas])
    plt.grid(True, alpha=0.3, which="both")
    plt.legend(fontsize=9)
    plt.tight_layout()
    out = FIG_DIR / "tier2_bsds_f1_vs_sigma.png"
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"   -> Đã lưu: {out}")


def plot_f1_heatmap(rows):
    """Bản đồ nhiệt F1 trung bình của Python theo lưới (p_low, p_high) tại σ=2.0."""
    heat_rows = [
        r for r in rows
        if r["source"] == "python"
        and float(r["sigma"]) == 2.0
        and r["selection_stage"] == "coarse"
    ]
    if not heat_rows:
        return
    plow_vals = sorted({float(r["p_low"]) for r in heat_rows})
    phigh_vals = sorted({float(r["p_high"]) for r in heat_rows})
    matrix = np.full((len(plow_vals), len(phigh_vals)), np.nan)
    for r in heat_rows:
        i = plow_vals.index(float(r["p_low"]))
        j = phigh_vals.index(float(r["p_high"]))
        matrix[i, j] = float(r["mean_f1"])

    plt.figure(figsize=(7.6, 5.6), dpi=200)
    im = plt.imshow(
        matrix,
        aspect="auto",
        origin="lower",
        cmap="viridis",
        vmin=np.nanmin(matrix),
        vmax=np.nanmax(matrix),
    )
    plt.xticks(
        range(len(phigh_vals)),
        [f"{v:.0f}" for v in phigh_vals],
        rotation=45,
        ha="right",
    )
    plt.yticks(range(len(plow_vals)), [f"{v:.0f}" for v in plow_vals])
    plt.xlabel("p_high (phân vị trên)", fontsize=10)
    plt.ylabel("p_low (phân vị dưới)", fontsize=10)
    plt.title(
        "F1 trung bình của Python trên lưới ngưỡng, σ = 2.0",
        fontsize=11,
    )
    cbar = plt.colorbar(im, fraction=0.046, pad=0.04)
    cbar.set_label("F1 trung bình", fontsize=9)
    plt.tight_layout()
    out = FIG_DIR / "tier2_bsds_f1_heatmap.png"
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"   -> Đã lưu: {out}")


def plot_runtime_comparison():
    """So sánh thời gian chạy trung vị Python vs Fiji theo command."""
    fj_rows = read_csv(METRICS_DIR / "fiji_runtime.csv")
    py_rows = read_csv(METRICS_DIR / "python_runtime.csv")
    if not fj_rows or not py_rows:
        return

    fj_med = defaultdict(list)
    for r in fj_rows:
        fj_med[r["command"]].append(float(r["runtime_ms"]))
    py_med = defaultdict(list)
    for r in py_rows:
        py_med[r["command"]].append(float(r["runtime_ms"]))

    commands = sorted(set(fj_med) | set(py_med))
    fj_vals = [float(np.median(fj_med[c])) if c in fj_med else np.nan
               for c in commands]
    py_vals = [float(np.median(py_med[c])) if c in py_med else np.nan
               for c in commands]

    x = np.arange(len(commands))
    width = 0.38
    plt.figure(figsize=(9.2, 5.2), dpi=200)
    plt.bar(x - width / 2, fj_vals, width, label="Fiji (ImageJ Macro)",
            color="#ff7f0e", alpha=0.85)
    plt.bar(x + width / 2, py_vals, width, label="Python Core (NumPy)",
            color="#1f77b4", alpha=0.85)
    for i, (a, b) in enumerate(zip(fj_vals, py_vals)):
        if not np.isnan(a):
            plt.text(i - width / 2, a, f"{a:.0f}", ha="center", va="bottom",
                     fontsize=7.5, color="#8a3d0d")
        if not np.isnan(b):
            plt.text(i + width / 2, b, f"{b:.0f}", ha="center", va="bottom",
                     fontsize=7.5, color="#0d4a8a")
    plt.xticks(x, commands, rotation=35, ha="right")
    plt.ylabel("Thời gian chạy trung vị (ms)", fontsize=10)
    plt.title("So sánh thời gian chạy Python vs Fiji theo loại phép toán",
              fontsize=11)
    plt.grid(True, axis="y", alpha=0.3)
    plt.legend(fontsize=9)
    plt.tight_layout()
    out = FIG_DIR / "tier2_runtime_comparison.png"
    plt.savefig(out, bbox_inches="tight")
    plt.close()
    print(f"   -> Đã lưu: {out}")


def main():
    rows = read_csv(METRICS_DIR / "tier2_bsds_sigma_grid.csv")
    print(f"   Đọc {len(rows)} dòng lưới ngưỡng.")
    plot_pr_curves(rows)
    plot_f1_vs_sigma(rows)
    plot_f1_heatmap(rows)
    plot_runtime_comparison()
    print("\n-> Tất cả biểu đồ đã sinh ra tại:", FIG_DIR)


if __name__ == "__main__":
    main()
