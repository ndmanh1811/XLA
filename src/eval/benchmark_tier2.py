"""
benchmark_tier2.py - Đánh giá định lượng Tầng 2 (So sánh với Ground Truth thực tế)
Người thực hiện: Nguyễn Đức Mạnh (Role 2 — Lead Algorithm Developer)

Khung đánh giá định lượng Tầng 2 trên toàn bộ 25 ảnh so với Ground Truth thực tế:
- Bài toán 1 (Edge - BSDS500, 10 ảnh): Dò biên Canny đa tỷ lệ, so sánh dung sai 2px với đa annotator.
- Bài toán 2 (Ridge - DRIVE, 10 ảnh): Dò mạch máu Frangi qua Hessian, áp mặt nạ FOV xói mòn đa tỷ lệ, tính F1/IoU.
- Bài toán 3 (Blob - Đốm đa tỷ lệ, 5 ảnh): Dò cực trị LoG 3D scale-space, khớp tâm <= 2px & bán kính <= 20%.

Hỗ trợ 2 nguồn bản đồ (--source):
- python: tính toán trực tiếp từ nhân NumPy thuần (mặc định, kết quả chính thức).
- fiji:   đọc các bản đồ TIFF do ImageJ Macro của Lộc xuất tại outputs/fiji/.
- both:   chạy cả hai và xuất bảng đối sánh song song tier2_comparison.csv.

Nhánh BSDS của Fiji có 2 chế độ (--bsds-fiji-mode):
- canny: đọc fiji_*_lx/ly, chuẩn hóa sigma rồi gọi detect_canny (mặc định, fair).
- edge:  đọc fiji_*_edge (FeatureJ Edges) và áp hysteresis (tham chiếu riêng).

Từ bản cập nhật ngưỡng theo sigma:
- ``--bsds-threshold-mode grid`` (mặc định) quét lưới phân vị riêng cho từng
  sigma, chọn bộ tối ưu trên Python rồi đóng băng sang Fiji.
- ``--bsds-threshold-mode fixed`` giữ hành vi cũ: một cặp p_low/p_high tại
  sigma=2.0, dùng để tái lập kết quả lịch sử.
- Nhánh tham chiếu FeatureJ Edges có lưới ngưỡng tuyệt đối riêng (đơn vị đầu
  ra của plugin) và được ghi tách khỏi bảng fair.

Toàn bộ kết quả chi tiết và tổng hợp được lưu vào: outputs/metrics/tier2_results.csv
"""

import sys
import csv
import json
from pathlib import Path
import numpy as np
from PIL import Image
import tifffile
from scipy.ndimage import binary_dilation, binary_erosion

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.core.derivatives import compute_derivatives_1st, compute_laplacian
from src.core.hessian import compute_hessian_matrix, compute_hessian_eigenvalues
from src.core.detectors import (
    detect_canny,
    detect_ridge,
    detect_blob,
    canny_nms,
    hysteresis_from_nms,
)
from src.config import get_eigen_order, get_sigmas, get_blob_sigmas
from src.eval.bsds_threshold_grid import (
    BsdsItem,
    edge_maps_for_sigma,
    evaluate_absolute_grid,
    evaluate_percentile_grid,
    evaluate_prediction,
    hysteresis_absolute,
    load_bsds_items,
    make_refine_grid,
    select_best_row,
    write_by_sigma_csv,
    write_csv,
    write_thresholds_csv,
)

RAW_DIR = ROOT / "data" / "raw"
GT_DIR = ROOT / "data" / "gt"
METRICS_DIR = ROOT / "outputs" / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)

FIJI_DIR = ROOT / "outputs" / "fiji"

# Lưới phân vị mặc định cho nhánh fair. Bước 5% đủ dày để tìm vùng tối ưu,
# sau đó bước tinh 1% được chạy quanh điểm tốt nhất của từng sigma.
DEFAULT_BSDS_GRID_LOW = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85]
DEFAULT_BSDS_GRID_HIGH = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95]

GRID_FIELDS = [
    "source", "sigma", "p_low", "p_high",
    "mean_precision", "mean_recall", "mean_f1", "n_images",
    "selection_stage", "selected",
]
EDGE_GRID_FIELDS = [
    "source", "sigma", "t_low", "t_high",
    "mean_precision", "mean_recall", "mean_f1", "n_images",
    "selection_stage", "selected",
]


def _fiji_tif(name: str) -> np.ndarray:
    """Đọc một bản đồ 32-bit float do ImageJ Macro của Lộc xuất."""
    path = FIJI_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Thiếu bản đồ Fiji: {path}")
    return np.asarray(tifffile.imread(path), dtype=np.float64)


def get_fov_eroded_mask(fov_mask: np.ndarray, sigma: float, k: float = 4.0) -> np.ndarray:
    """Xói mòn mặt nạ FOV thích ứng theo tỷ lệ sigma: r = ceil(k * sigma)."""
    r = int(np.ceil(k * sigma))
    struct_size = 2 * r + 1
    struct = np.ones((struct_size, struct_size), dtype=bool)
    return binary_erosion(fov_mask, structure=struct)

def evaluate_bsds_edges(
    sample_limit=10,
    p_low=60.0,
    p_high=85.0,
    records=None,
    source="python",
    fiji_mode="canny",
    task_name="BSDS500_Canny_Edge",
    sigmas=None,
    thresholds_by_sigma=None,
    selection_method="grid_python_f1",
):
    """Đánh giá Canny Edge Detection trên BSDS500 với GT đa annotator.

    Hàm chạy lần lượt qua toàn bộ ``sigmas``. Với mỗi sigma, cặp ngưỡng được
    lấy từ ``thresholds_by_sigma`` (đã chọn trên Python) và áp nguyên vẹn cho
    cả Python lẫn Fiji. Nếu không truyền, hàm giữ hành vi cũ: một cặp
    ``p_low``/``p_high`` tại sigma mặc định.

    Nhánh Fiji:
    - fiji_mode="canny": đọc lx/ly của Macro, nhân sigma rồi chạy đúng
      ``detect_canny`` (cùng thuật toán với Python -> đối sánh công bằng).
    - fiji_mode="edge": đọc bản đồ FeatureJ Edges (đã NMS nội bộ) và chỉ áp
      ngưỡng trễ; đây là tham chiếu riêng, không dùng thay nhánh fair.

    Nhánh tham chiếu FeatureJ Edges với ngưỡng tuyệt đối được xử lý riêng bởi
    ``calibrate_edge_reference`` để không trộn với lưới phân vị fair.
    """
    if sigmas is None:
        sigmas = [2.0]
    sigmas = [float(s) for s in sigmas]
    if thresholds_by_sigma is None:
        thresholds_by_sigma = {
            sigma: (float(p_low), float(p_high)) for sigma in sigmas
        }

    print("\n" + "=" * 65)
    print("  1. BENCHMARK BÀI TOÁN DÒ BIÊN (BSDS500 - CANNY EDGE DETECTION)")
    fiji_note = f" | Fiji mode={fiji_mode}" if source == "fiji" else ""
    print(
        f"     Nguồn bản đồ: {source.upper()}{fiji_note} | "
        f"sigmas={', '.join(f'{s:.1f}' for s in sigmas)}"
    )
    print(f"     Cách chọn ngưỡng: {selection_method}")
    print("=" * 65)

    items = load_bsds_items(RAW_DIR, GT_DIR, sample_limit=sample_limit)
    if not items:
        print("   [!] Chưa tìm thấy ảnh bsds_*.png trong data/raw/")
        return 0.0

    results = []
    per_sigma = {sigma: [] for sigma in sigmas}
    for item in items:
        for sigma in sigmas:
            pl, ph = thresholds_by_sigma.get(sigma, (float(p_low), float(p_high)))

            if source == "fiji":
                if fiji_mode == "canny":
                    # Nhánh fair: dùng đạo hàm bậc 1 lx/ly của Fiji, chuẩn hóa
                    # sigma rồi chạy đúng detect_canny như nhánh Python.
                    lx = sigma * _fiji_tif(
                        f"fiji_{item.stem}_lx_s{sigma:.1f}.tif"
                    )
                    ly = sigma * _fiji_tif(
                        f"fiji_{item.stem}_ly_s{sigma:.1f}.tif"
                    )
                    nms = canny_nms(lx, ly)
                else:
                    # Tham chiếu riêng: FeatureJ Edge đã NMS nội bộ.
                    nms = _fiji_tif(
                        f"fiji_{item.stem}_edge_s{sigma:.1f}.tif"
                    )
            else:
                # Đạo hàm bậc 1 chuẩn hóa gamma=1 (Lindeberg)
                lx, ly = compute_derivatives_1st(item.image, sigma=sigma)
                nms = canny_nms(sigma * lx, sigma * ly)

            pred_edge = hysteresis_from_nms(
                nms, p_low=pl, p_high=ph, return_binary=False
            )
            metrics = evaluate_prediction(pred_edge, item)
            precision = metrics["precision"]
            recall = metrics["recall"]
            f1 = metrics["f1"]
            pred_positive = int(metrics["predicted_count"])
            true_positives = int(metrics["true_positives"])

            results.append((item.stem, sigma, precision, recall, f1))
            per_sigma[sigma].append(f1)

            if records is not None:
                records.append(
                    {
                        "source": source,
                        "task": task_name,
                        "image": item.stem,
                        "sigma": f"{sigma:.1f}",
                        "parameter": (
                            f"sigma={sigma:.1f}_plow={pl:.1f}_phigh={ph:.1f}"
                            f"_select={selection_method}"
                        ),
                        "precision": round(precision, 4),
                        "recall": round(recall, 4),
                        "f1": round(f1, 4),
                        "iou": "N/A",
                        "gt_count": int(item.union_gt.sum()),
                        "detected_count": pred_positive,
                        "matched_count": true_positives,
                        "_f1_raw": f1,
                    }
                )
            print(
                f"   Ảnh {item.stem} | sigma={sigma:.1f}: "
                f"Precision={precision:.3f}, Recall={recall:.3f} "
                f"=> F1={f1:.3f} (p_low={pl:.1f}, p_high={ph:.1f})"
            )

    for sigma in sigmas:
        values = per_sigma[sigma]
        if values:
            print(
                f"   => [BSDS500 sigma={sigma:.1f}] "
                f"F1 trung bình: {float(np.mean(values)):.6f}"
            )
    avg_f1 = float(np.mean([r[4] for r in results])) if results else 0.0
    print(f"   => [KẾT QUẢ BSDS500] F1 trung bình toàn bộ sigma: {avg_f1:.6f}")
    return avg_f1


def _nms_for_python(items, sigma):
    """Tính NMS một lần cho mỗi ảnh ở một sigma, phục vụ quét lưới."""
    nms_by_stem = {}
    for item in items:
        lx, ly = compute_derivatives_1st(item.image, sigma=sigma)
        nms_by_stem[item.stem] = canny_nms(sigma * lx, sigma * ly)
    return nms_by_stem


def _nms_for_fiji(items, sigma):
    """Đọc lx/ly của Fiji, chuẩn hóa sigma và tính NMS một lần."""
    nms_by_stem = {}
    for item in items:
        lx = sigma * _fiji_tif(f"fiji_{item.stem}_lx_s{sigma:.1f}.tif")
        ly = sigma * _fiji_tif(f"fiji_{item.stem}_ly_s{sigma:.1f}.tif")
        nms_by_stem[item.stem] = canny_nms(lx, ly)
    return nms_by_stem


def calibrate_fair_thresholds(
    sample_limit=10,
    sigmas=None,
    grid_low=None,
    grid_high=None,
    refine=True,
    refine_radius=2.0,
    refine_step=1.0,
    grid_out=None,
    thresholds_out=None,
):
    """Quét lưới phân vị riêng cho từng sigma và chọn ngưỡng trên Python.

    Quy trình:

    1. Với mỗi sigma, tính NMS Python một lần cho cả 10 ảnh.
    2. Quét lưới thô ``(p_low, p_high)``; chọn dòng có F1 trung bình cao nhất.
    3. Quét lưới tinh quanh điểm tốt nhất (mặc định ±2 điểm phần trăm, bước 1).
    4. Đóng băng cặp ngưỡng cuối cùng và áp nguyên vẹn cho Fiji.
    5. Ghi CSV lưới đầy đủ và CSV ngưỡng theo sigma.

    Returns:
        ``(thresholds_by_sigma, grid_rows, selected_rows)``.
    """
    if sigmas is None:
        sigmas = get_sigmas()
    sigmas = [float(s) for s in sigmas]
    grid_low = list(grid_low or DEFAULT_BSDS_GRID_LOW)
    grid_high = list(grid_high or DEFAULT_BSDS_GRID_HIGH)

    items = load_bsds_items(RAW_DIR, GT_DIR, sample_limit=sample_limit)
    if not items:
        raise RuntimeError("Không đọc được ảnh BSDS/GT để hiệu chuẩn ngưỡng.")

    grid_rows = []
    selected_rows = []
    thresholds_by_sigma = {}

    print("\n" + "=" * 65)
    print("  HIỆU CHUẨN NGƯỠNG BSDS THEO TỪNG SIGMA (CHỌN TRÊN PYTHON)")
    print(f"  Lưới thô: p_low={grid_low}")
    print(f"            p_high={grid_high}")
    print(
        f"  Lưới tinh: {'bật' if refine else 'tắt'} "
        f"(radius={refine_radius}, step={refine_step})"
    )
    print("=" * 65)

    for sigma in sigmas:
        print(f"\n   [sigma={sigma:.1f}] Đang tính NMS Python...")
        py_nms = _nms_for_python(items, sigma)

        print(f"   [sigma={sigma:.1f}] Quét lưới thô...")
        coarse = evaluate_percentile_grid(py_nms, items, grid_low, grid_high)
        for row in coarse:
            row.update(
                {
                    "source": "python",
                    "sigma": sigma,
                    "selection_stage": "coarse",
                    "selected": 0,
                }
            )
        combined = {
            (round(float(r["p_low"]), 6), round(float(r["p_high"]), 6)): r
            for r in coarse
        }
        best_coarse = select_best_row(coarse)
        if best_coarse is None:
            print(f"   [!] sigma={sigma:.1f}: không có tổ hợp ngưỡng hợp lệ.")
            continue

        if refine:
            refine_low, refine_high = make_refine_grid(
                best_coarse["p_low"],
                best_coarse["p_high"],
                radius=refine_radius,
                step=refine_step,
            )
            refine_rows = evaluate_percentile_grid(
                py_nms, items, refine_low, refine_high
            )
            for row in refine_rows:
                row.update(
                    {
                        "source": "python",
                        "sigma": sigma,
                        "selection_stage": "refine",
                        "selected": 0,
                    }
                )
                key = (
                    round(float(row["p_low"]), 6),
                    round(float(row["p_high"]), 6),
                )
                if key not in combined:
                    combined[key] = row

        best_python = select_best_row(list(combined.values()))
        if best_python is None:
            continue
        best_key = (
            round(float(best_python["p_low"]), 6),
            round(float(best_python["p_high"]), 6),
        )
        for row in combined.values():
            row["selected"] = 0
        combined[best_key]["selected"] = 1
        thresholds_by_sigma[sigma] = (
            float(best_python["p_low"]),
            float(best_python["p_high"]),
        )
        selected_rows.append(dict(combined[best_key]))
        grid_rows.extend(combined.values())
        print(
            f"   [sigma={sigma:.1f}] Python tối ưu: "
            f"p_low={best_python['p_low']:.2f}, "
            f"p_high={best_python['p_high']:.2f}, "
            f"F1={best_python['mean_f1']:.6f}"
        )

        print(f"   [sigma={sigma:.1f}] Đang tính NMS Fiji và lưới đối chứng...")
        try:
            fj_nms = _nms_for_fiji(items, sigma)
        except FileNotFoundError as exc:
            print(f"   [!] Bỏ qua lưới Fiji tại sigma={sigma:.1f}: {exc}")
            continue
        fj_coarse = evaluate_percentile_grid(fj_nms, items, grid_low, grid_high)
        fj_combined = {}
        for row in fj_coarse:
            row.update(
                {
                    "source": "fiji",
                    "sigma": sigma,
                    "selection_stage": "coarse_frozen",
                    "selected": 0,
                }
            )
            fj_combined[
                (round(float(row["p_low"]), 6), round(float(row["p_high"]), 6))
            ] = row

        # Bổ sung đúng cặp ngưỡng Python đã chọn (có thể nằm ngoài lưới thô).
        fj_selected = evaluate_percentile_grid(
            fj_nms, items, [best_python["p_low"]], [best_python["p_high"]]
        )
        for row in fj_selected:
            row.update(
                {
                    "source": "fiji",
                    "sigma": sigma,
                    "selection_stage": "selected_frozen",
                    "selected": 0,
                }
            )
            key = (
                round(float(row["p_low"]), 6),
                round(float(row["p_high"]), 6),
            )
            if key not in fj_combined:
                fj_combined[key] = row

        for row in fj_combined.values():
            row["selected"] = 0
        fj_best_key = (
            round(float(best_python["p_low"]), 6),
            round(float(best_python["p_high"]), 6),
        )
        if fj_best_key in fj_combined:
            fj_combined[fj_best_key]["selected"] = 1
            selected_rows.append(dict(fj_combined[fj_best_key]))
            print(
                f"   [sigma={sigma:.1f}] Fiji (đóng băng): "
                f"F1={fj_combined[fj_best_key]['mean_f1']:.6f}, "
                f"ΔF1={fj_combined[fj_best_key]['mean_f1'] - best_python['mean_f1']:+.6f}"
            )
        grid_rows.extend(fj_combined.values())

    if grid_out:
        write_csv(grid_rows, grid_out, fieldnames=GRID_FIELDS)
    if thresholds_out:
        write_thresholds_csv(
            [r for r in selected_rows if r["source"] == "python"],
            thresholds_out,
        )
    return thresholds_by_sigma, grid_rows, selected_rows


def calibrate_edge_reference(
    sample_limit=10,
    sigmas=None,
    grid_out=None,
    by_sigma_out=None,
):
    """Quét lưới ngưỡng tuyệt đối cho nhánh tham chiếu FeatureJ Edges.

    Khác với nhánh fair, ngưỡng ở đây là giá trị tuyệt đối trong đơn vị edge
    strength do plugin xuất ra, không phải phân vị. Mỗi sigma có một lưới riêng
    và một cặp ngưỡng tốt nhất; kết quả chỉ dùng làm tham chiếu, không dùng để
    kết luận công bằng giữa Python và Fiji.
    """
    if sigmas is None:
        sigmas = get_sigmas()
    sigmas = [float(s) for s in sigmas]

    items = load_bsds_items(RAW_DIR, GT_DIR, sample_limit=sample_limit)
    if not items:
        raise RuntimeError("Không đọc được ảnh BSDS/GT cho tham chiếu FeatureJ Edges.")

    grid_rows = []
    summary_rows = []
    per_image_records = []

    print("\n" + "=" * 65)
    print("  HIỆU CHUẨN THAM CHIẾU FeatureJ EDGES (NGƯỠNG TUYỆT ĐỐI)")
    print("  Nhánh này chỉ dùng tham chiếu; không trộn với bảng fair.")
    print("=" * 65)

    for sigma in sigmas:
        edge_maps = edge_maps_for_sigma(FIJI_DIR, items, sigma)
        if not edge_maps:
            print(f"   [!] sigma={sigma:.1f}: không có bản đồ edge Fiji.")
            continue

        values = np.concatenate(
            [m[m > 0].ravel() for m in edge_maps.values() if np.any(m > 0)]
        )
        if len(values) == 0:
            continue
        vmax = float(np.percentile(values, 99.5))
        if vmax <= 0:
            vmax = float(np.max(values))

        grid_high = np.linspace(0.05 * vmax, 0.80 * vmax, 16)
        grid_low = np.linspace(0.01 * vmax, 0.50 * vmax, 12)
        print(
            f"\n   [sigma={sigma:.1f}] vmax(p99.5)={vmax:.4f} | "
            f"t_low=[{grid_low[0]:.4f}, {grid_low[-1]:.4f}] | "
            f"t_high=[{grid_high[0]:.4f}, {grid_high[-1]:.4f}]"
        )

        coarse = evaluate_absolute_grid(edge_maps, items, grid_low, grid_high)
        for row in coarse:
            row.update(
                {
                    "source": "fiji_edge_reference",
                    "sigma": sigma,
                    "selection_stage": "coarse_absolute",
                    "selected": 0,
                }
            )
        combined = {
            (round(float(r["t_low"]), 9), round(float(r["t_high"]), 9)): r
            for r in coarse
        }
        best_coarse = select_best_row(coarse)
        if best_coarse is None:
            continue

        span = max(0.05 * vmax, 1e-9)
        refine_low = np.linspace(
            max(0.0, best_coarse["t_low"] - span),
            best_coarse["t_low"] + span,
            5,
        )
        refine_high = np.linspace(
            max(0.0, best_coarse["t_high"] - span),
            best_coarse["t_high"] + span,
            5,
        )
        refine = evaluate_absolute_grid(edge_maps, items, refine_low, refine_high)
        for row in refine:
            row.update(
                {
                    "source": "fiji_edge_reference",
                    "sigma": sigma,
                    "selection_stage": "refine_absolute",
                    "selected": 0,
                }
            )
            key = (round(float(row["t_low"]), 9), round(float(row["t_high"]), 9))
            if key not in combined:
                combined[key] = row

        best = select_best_row(list(combined.values()))
        if best is None:
            continue
        best_key = (round(float(best["t_low"]), 9), round(float(best["t_high"]), 9))
        for row in combined.values():
            row["selected"] = 0
        combined[best_key]["selected"] = 1
        grid_rows.extend(combined.values())

        summary_rows.append(
            {
                "sigma": f"{sigma:.1f}",
                "t_low": f"{float(best['t_low']):.9f}",
                "t_high": f"{float(best['t_high']):.9f}",
                "mean_precision": f"{float(best['mean_precision']):.6f}",
                "mean_recall": f"{float(best['mean_recall']):.6f}",
                "mean_f1": f"{float(best['mean_f1']):.6f}",
                "n_images": int(best["n_images"]),
                "selection_stage": "coarse_to_fine_absolute",
                "selected": 1,
            }
        )
        print(
            f"   [sigma={sigma:.1f}] FeatureJ Edges tốt nhất: "
            f"t_low={best['t_low']:.6f}, t_high={best['t_high']:.6f}, "
            f"F1={best['mean_f1']:.6f}"
        )

        for item in items:
            nms = edge_maps.get(item.stem)
            if nms is None:
                continue
            pred = hysteresis_absolute(
                nms, t_low=float(best["t_low"]), t_high=float(best["t_high"])
            )
            metrics = evaluate_prediction(pred, item)
            per_image_records.append(
                {
                    "source": "fiji",
                    "task": "BSDS500_FeatureJ_Edges_Reference",
                    "image": item.stem,
                    "sigma": f"{sigma:.1f}",
                    "parameter": (
                        f"sigma={sigma:.1f}_tlow={float(best['t_low']):.6f}"
                        f"_thigh={float(best['t_high']):.6f}"
                    ),
                    "precision": round(metrics["precision"], 4),
                    "recall": round(metrics["recall"], 4),
                    "f1": round(metrics["f1"], 4),
                    "iou": "N/A",
                    "gt_count": int(item.union_gt.sum()),
                    "detected_count": int(metrics["predicted_count"]),
                    "matched_count": int(metrics["true_positives"]),
                    "_f1_raw": metrics["f1"],
                }
            )

    if grid_out:
        write_csv(grid_rows, grid_out, fieldnames=EDGE_GRID_FIELDS)
    if by_sigma_out:
        write_csv(summary_rows, by_sigma_out)

    return per_image_records, summary_rows, grid_rows


def evaluate_drive_vessels(sample_limit=10, records=None, source="python"):
    """Đánh giá Frangi Vesselness trên ảnh võng mạc DRIVE với mặt nạ FOV xói mòn đa tỷ lệ."""
    print("\n" + "=" * 65)
    print("  2. BENCHMARK BÀI TOÁN DÒ MẠCH MÁU (DRIVE - FRANGI VESSELNESS)")
    print(f"     Nguồn bản đồ: {source.upper()}")
    print("     Mặt nạ FOV: Xói mòn thích ứng theo từng sigma r = ceil(k * sigma)")
    print("=" * 65)
    
    results = []
    drive_files = sorted(list(RAW_DIR.glob("drive_*.png")))[:sample_limit]
    if not drive_files:
        print("   [!] Chưa tìm thấy ảnh drive_*.png trong data/raw/")
        return 0.0, 0.0
        
    sigmas = get_sigmas()
    eigen_order = get_eigen_order()
    
    for img_path in drive_files:
        stem = img_path.stem
        vessel_gt_path = GT_DIR / "drive" / f"{stem}_vessels.png"
        if not vessel_gt_path.exists():
            vessel_gt_path = GT_DIR / f"{stem}_vessels.png"
            
        fov_mask_path = GT_DIR / "drive" / f"{stem}_fov.png"
        if not fov_mask_path.exists():
            fov_mask_path = GT_DIR / f"{stem}_fov.png"
        
        if not vessel_gt_path.exists() or not fov_mask_path.exists():
            continue
            
        gt_vessels = np.array(Image.open(vessel_gt_path)) > 128
        fov_mask = np.array(Image.open(fov_mask_path)) > 128
        img = np.array(Image.open(img_path), dtype=np.float64)
        
        # Mặt nạ FOV đánh giá tổng thể (sigma=2.0, k=4.0 -> r=8px, struct 17x17)
        eval_fov = get_fov_eroded_mask(fov_mask, sigma=2.0, k=4.0)
        
        # Chạy Frangi đa tỷ lệ với FOV scale-aware
        max_vesselness = np.zeros_like(img)
        for s in sigmas:
            # Triệt tiêu gờ biên giả cho từng tỷ lệ sigma riêng biệt
            fov_s = get_fov_eroded_mask(fov_mask, sigma=s, k=4.0)
            
            if source == "fiji":
                # FeatureJ xuất trị riêng Hessian thô (chưa nhân sigma^2) -> chuẩn hóa tại đây
                l1 = (s ** 2.0) * _fiji_tif(f"fiji_{stem}_hess-l1_s{s:.1f}.tif")
                l2 = (s ** 2.0) * _fiji_tif(f"fiji_{stem}_hess-l2_s{s:.1f}.tif")
            else:
                lxx, lyy, lxy = compute_hessian_matrix(img, sigma=s)
                lxx_norm = (s ** 2.0) * lxx
                lyy_norm = (s ** 2.0) * lyy
                lxy_norm = (s ** 2.0) * lxy
                l1, l2 = compute_hessian_eigenvalues(lxx_norm, lyy_norm, lxy_norm, sort_order=eigen_order)
            
            # Mạch máu trong kênh Green là rãnh tối -> polarity='dark'
            v = detect_ridge(l1, l2, sigma=s, beta=0.5, polarity="dark")
            v[~fov_s] = 0.0  # Cắt biên thích ứng tỷ lệ
            max_vesselness = np.maximum(max_vesselness, v)
            
        # Áp dụng ngưỡng phân vị trên vùng FOV xói mòn
        fov_vals = max_vesselness[eval_fov]
        thresh = np.percentile(fov_vals, 85.0) if len(fov_vals) > 0 else 0.5
        pred_vessels = (max_vesselness >= thresh) & eval_fov
        gt_valid = gt_vessels & eval_fov
        
        intersection = int(np.sum(pred_vessels & gt_valid))
        union = int(np.sum(pred_vessels | gt_valid))
        iou = intersection / (union + 1e-10)
        
        pred_cnt = int(np.sum(pred_vessels))
        gt_cnt = int(np.sum(gt_valid))
        prec = intersection / (pred_cnt + 1e-10)
        rec = intersection / (gt_cnt + 1e-10)
        f1 = (2 * prec * rec) / (prec + rec + 1e-10)
        
        results.append((stem, prec, rec, f1, iou))
        
        if records is not None:
            records.append({
                "source": source,
                "task": "DRIVE_Frangi_Ridge",
                "image": stem,
                "sigma": "multiscale",
                "parameter": "multiscale_sigmas=[1,2,4,8]_thresh=p85_FOVscale",
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "iou": round(iou, 4),
                "gt_count": gt_cnt,
                "detected_count": pred_cnt,
                "matched_count": intersection,
                "_f1_raw": f1,
                "_iou_raw": iou,
            })
        print(f"   Ảnh {stem}: Precision={prec:.3f}, Recall={rec:.3f} => F1={f1:.3f}, IoU={iou:.3f}")
        
    avg_f1 = float(np.mean([r[3] for r in results])) if results else 0.0
    avg_iou = float(np.mean([r[4] for r in results])) if results else 0.0
    print(f"   => [KẾT QUẢ DRIVE] F1 trung bình: {avg_f1:.3f}, IoU trung bình: {avg_iou:.3f}")
    return avg_f1, avg_iou

def evaluate_blobs(sample_limit=5, records=None, source="python", blob_sigmas="extended"):
    """Đánh giá LoG Scale-Space Blob Detection so với Ground Truth."""
    print("\n" + "=" * 65)
    print("  3. BENCHMARK BÀI TOÁN DÒ ĐỐM (BLOBS - LOG SCALE-SPACE)")
    print(f"     Nguồn bản đồ: {source.upper()}")
    print("=" * 65)
    
    blob_files = sorted(list(RAW_DIR.glob("blob_*.png")))[:sample_limit]
    if not blob_files:
        print("   [!] Chưa tìm thấy ảnh blob_*.png trong data/raw/")
        return 0.0
        
    sigmas_blob = get_blob_sigmas()
    if source == "python" and blob_sigmas == "extended":
        if 11.3 not in sigmas_blob:
            sigmas_blob.append(11.3)
    elif source == "fiji" and blob_sigmas == "extended":
        print("   [!] Fiji không có Laplacian tại sigma=11.3 -> dùng 7 sigma cấu hình.")
    print(f"     Thang đo Blob: {len(sigmas_blob)} sigma = {sigmas_blob}")
        
    total_matched = 0
    total_gt = 0
    total_pred = 0
    
    for img_path in blob_files:
        stem = img_path.stem
        gt_json_path = GT_DIR / "blob" / f"{stem}.json"
        if not gt_json_path.exists():
            gt_json_path = GT_DIR / f"{stem}_gt.json"
            
        if not gt_json_path.exists():
            continue
            
        with open(gt_json_path, "r", encoding="utf-8") as f:
            gt_data = json.load(f)
            
        gt_blobs = gt_data.get("objects", gt_data.get("blobs", []))
        polarity = gt_data.get("polarity", "bright")
        img = np.array(Image.open(img_path), dtype=np.float64)
        
        # Chồng bản đồ LoG đã chuẩn hóa sigma^2
        lap_stack = []
        for s in sigmas_blob:
            if source == "fiji":
                # Fiji xuất Laplacian thô (chưa nhân sigma^2) -> chuẩn hóa tại đây
                lap = _fiji_tif(f"fiji_{stem}_lap_s{s:.1f}.tif")
            else:
                lap = compute_laplacian(img, sigma=s)
            lap_norm = (s ** 2.0) * lap
            lap_stack.append(lap_norm)
        lap_stack = np.stack(lap_stack, axis=0)
        
        # Dò cực trị không gian tỷ lệ (ngưỡng 0.03 * 255)
        detected = detect_blob(lap_stack, sigmas=sigmas_blob, polarity=polarity, threshold=0.03 * 255.0)
        
        # Tiêu chuẩn khớp đúng: tâm lệch <= 2px và bán kính sai lệch <= 20%
        matched_gt = 0
        for g in gt_blobs:
            gx, gy, gr = g["x"], g["y"], g["radius"]
            found = False
            for d in detected:
                dy, dx, ds, dr, resp = d
                dist = np.sqrt((gx - dx)**2 + (gy - dy)**2)
                r_err = abs(gr - dr) / gr
                if dist <= 2.0 and r_err <= 0.20:
                    found = True
                    break
            if found:
                matched_gt += 1
                
        prec = matched_gt / (len(detected) + 1e-10)
        rec = matched_gt / (len(gt_blobs) + 1e-10)
        f1 = (2 * prec * rec) / (prec + rec + 1e-10)
        
        total_matched += matched_gt
        total_gt += len(gt_blobs)
        total_pred += len(detected)
        
        if records is not None:
            records.append({
                "source": source,
                "task": "Blobs_LoG_ScaleSpace",
                "image": stem,
                "sigma": "multiscale",
                "parameter": f"polarity={polarity}_thresh=0.03_nsigmas={len(sigmas_blob)}",
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
                "iou": "N/A",
                "gt_count": len(gt_blobs),
                "detected_count": len(detected),
                "matched_count": matched_gt,
                "_f1_raw": f1,
            })
        print(f"   Ảnh {stem} ({polarity}): GT={len(gt_blobs)}, Tìm thấy={len(detected)}, Khớp={matched_gt} => F1={f1:.3f}")
        
    overall_f1 = (2 * total_matched) / (total_gt + total_pred + 1e-10)
    print(f"   => [KẾT QUẢ ĐỐM] Tỉ lệ phát hiện trúng đích tổng thể (F1): {overall_f1:.3f}")
    return overall_f1

def write_records(records, out_path):
    """Ghi danh sách bản ghi kết quả định lượng ra CSV (bỏ các khóa nội bộ)."""
    if not records:
        print(f"   [!] Không có bản ghi nào để ghi vào {out_path}")
        return
    fields = [key for key in records[0].keys() if not key.startswith("_")]
    clean = [{key: rec[key] for key in fields} for rec in records]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(clean)
    print(f"\n-> ĐÃ XUẤT KẾT QUẢ RA: {out_path}")


def write_comparison(records, out_path):
    """Tổng hợp bảng đối sánh Python vs Fiji theo ảnh, bài toán và sigma."""
    grouped = {}
    for rec in records:
        key = (rec["task"], rec["image"], rec.get("sigma", "multiscale"))
        grouped.setdefault(key, {})[rec["source"]] = rec

    def _num(value):
        if value in ("N/A", "", None):
            return None
        return float(value)

    rows = []
    for (task, image, sigma), pair in grouped.items():
        if "python" not in pair or "fiji" not in pair:
            continue
        py, fj = pair["python"], pair["fiji"]
        py_iou, fj_iou = _num(py["iou"]), _num(fj["iou"])
        py_f1_raw = float(py.get("_f1_raw", py["f1"]))
        fj_f1_raw = float(fj.get("_f1_raw", fj["f1"]))
        py_iou_raw = py.get("_iou_raw", py_iou)
        fj_iou_raw = fj.get("_iou_raw", fj_iou)
        rows.append({
            "task": task,
            "image": image,
            "sigma": sigma,
            "python_parameter": py["parameter"],
            "fiji_parameter": fj["parameter"],
            "python_precision": py["precision"],
            "python_recall": py["recall"],
            "python_f1": py["f1"],
            "python_iou": py["iou"],
            "fiji_precision": fj["precision"],
            "fiji_recall": fj["recall"],
            "fiji_f1": fj["f1"],
            "fiji_iou": fj["iou"],
            "delta_f1": round(fj_f1_raw - py_f1_raw, 6),
            "delta_iou": (
                round(float(fj_iou_raw) - float(py_iou_raw), 6)
                if py_iou_raw is not None and fj_iou_raw is not None
                else "N/A"
            ),
            "_python_f1_raw": py_f1_raw,
            "_fiji_f1_raw": fj_f1_raw,
        })

    rows.sort(key=lambda r: (r["task"], r["sigma"], r["image"]))
    fields = [
        "task", "image", "sigma", "python_parameter", "fiji_parameter",
        "python_precision", "python_recall", "python_f1", "python_iou",
        "fiji_precision", "fiji_recall", "fiji_f1", "fiji_iou",
        "delta_f1", "delta_iou",
    ]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n-> ĐÃ XUẤT BẢNG ĐỐI SÁNH PYTHON vs FIJI RA: {out_path}")
    by_task = {}
    for row in rows:
        by_task.setdefault((row["task"], row["sigma"]), []).append(row)
    print(
        f"   {'Bài toán':<28} {'Sigma':>8} {'Python F1':>10} "
        f"{'Fiji F1':>10} {'ΔF1':>10}"
    )
    print("   " + "-" * 74)
    for (task, sigma), group in sorted(by_task.items()):
        py_f1 = float(np.mean([r["_python_f1_raw"] for r in group]))
        fj_f1 = float(np.mean([r["_fiji_f1_raw"] for r in group]))
        print(
            f"   {task:<28} {sigma:>8} {py_f1:>10.6f} "
            f"{fj_f1:>10.6f} {fj_f1 - py_f1:>+10.6f}"
        )
    return rows


def parse_float_list(spec, default):
    """Đọc danh sách số thực từ chuỗi ``1,2,4,8`` hoặc trả về mặc định."""
    if spec is None:
        return list(default)
    if isinstance(spec, (list, tuple)):
        return [float(v) for v in spec]
    text = str(spec).strip()
    if text == "" or text.lower() in ("config", "default"):
        return list(default)
    return [
        float(part)
        for part in text.replace(";", ",").split(",")
        if part.strip() != ""
    ]


def parse_args():
    """Hỗ trợ tham số ngưỡng, lưới sigma, số lượng mẫu và nguồn bản đồ."""
    import argparse
    parser = argparse.ArgumentParser(
        description="Khung đánh giá định lượng Tầng 2 (Ground Truth Benchmark)"
    )
    parser.add_argument(
        "--p-low", type=float, default=60.0,
        help="Phân vị ngưỡng dưới Canny cho chế độ fixed (mặc định: 60.0)"
    )
    parser.add_argument(
        "--p-high", type=float, default=85.0,
        help="Phân vị ngưỡng trên Canny cho chế độ fixed (mặc định: 85.0)"
    )
    parser.add_argument(
        "--bsds-threshold-mode", choices=["grid", "fixed"], default="grid",
        help="grid = quét lưới phân vị riêng cho từng sigma (mặc định, đúng INSTRUCTIONS.md:128); "
             "fixed = giữ một cặp p_low/p_high tại sigma=2.0 để tái lập kết quả lịch sử"
    )
    parser.add_argument(
        "--bsds-sigmas", type=str, default="config",
        help="Danh sách sigma cho BSDS: 'config' hoặc chuỗi '1,2,4,8' (mặc định: config)"
    )
    parser.add_argument(
        "--bsds-grid-low", type=str, default=None,
        help="Danh sách phân vị dưới, ví dụ '5,10,...,85' (mặc định: lưới 5%% đến 85%%)"
    )
    parser.add_argument(
        "--bsds-grid-high", type=str, default=None,
        help="Danh sách phân vị trên, ví dụ '50,55,...,95' (mặc định: lưới 50%% đến 95%%)"
    )
    parser.add_argument(
        "--bsds-refine", dest="bsds_refine", action="store_true", default=True,
        help="Bật lưới tinh quanh điểm tốt nhất (mặc định: bật)"
    )
    parser.add_argument(
        "--no-bsds-refine", dest="bsds_refine", action="store_false",
        help="Tắt lưới tinh, chỉ dùng lưới thô"
    )
    parser.add_argument(
        "--bsds-refine-radius", type=float, default=2.0,
        help="Bán kính lưới tinh quanh điểm tốt nhất, đơn vị phân vị (mặc định: 2.0)"
    )
    parser.add_argument(
        "--bsds-refine-step", type=float, default=1.0,
        help="Bước lưới tinh, đơn vị phân vị (mặc định: 1.0)"
    )
    parser.add_argument(
        "--bsds-grid-out", type=str, default=None,
        help="CSV lưới đầy đủ (mặc định: outputs/metrics/tier2_bsds_sigma_grid.csv)"
    )
    parser.add_argument(
        "--bsds-thresholds-out", type=str, default=None,
        help="CSV ngưỡng tối ưu theo sigma (mặc định: outputs/metrics/tier2_bsds_thresholds.csv)"
    )
    parser.add_argument(
        "--bsds-by-sigma-out", type=str, default=None,
        help="CSV tổng hợp F1 theo sigma (mặc định: outputs/metrics/tier2_bsds_by_sigma.csv)"
    )
    parser.add_argument(
        "--edge-reference-grid-out", type=str, default=None,
        help="CSV lưới ngưỡng tuyệt đối FeatureJ Edges (mặc định: outputs/metrics/tier2_bsds_edge_reference_grid.csv)"
    )
    parser.add_argument(
        "--edge-reference-sigma-out", type=str, default=None,
        help="CSV tổng hợp tham chiếu FeatureJ Edges theo sigma (mặc định: outputs/metrics/tier2_bsds_edge_reference_by_sigma.csv)"
    )
    parser.add_argument("--bsds-samples", type=int, default=10, help="Số lượng ảnh BSDS500 (mặc định: 10)")
    parser.add_argument("--drive-samples", type=int, default=10, help="Số lượng ảnh DRIVE (mặc định: 10)")
    parser.add_argument("--blob-samples", type=int, default=5, help="Số lượng ảnh Blob (mặc định: 5)")
    parser.add_argument(
        "--source", choices=["python", "fiji", "both"], default="python",
        help="Nguồn bản đồ: python (mặc định), fiji (các TIFF của Lộc), hoặc both (đối sánh song song)"
    )
    parser.add_argument(
        "--bsds-fiji-mode", choices=["canny", "edge"], default="canny",
        help="Nhánh BSDS của Fiji: canny = lx/ly + detect_canny (mặc định, fair); "
             "edge = FeatureJ Edges + hysteresis (tham chiếu riêng)"
    )
    parser.add_argument(
        "--edge-reference-out", type=str, default=None,
        help="CSV tham chiếu FeatureJ Edges cho BSDS (mặc định: outputs/metrics/tier2_bsds_edge_reference.csv)"
    )
    parser.add_argument(
        "--blob-sigmas", choices=["config", "extended"], default=None,
        help="Thang đo Blob: config = 7 sigma [1,1.4,2,2.8,4,5.7,8]; extended = thêm 11.3 (chỉ Python). "
             "Mặc định: extended khi chỉ chạy Python, config khi chạy Fiji/both."
    )
    parser.add_argument("--out", type=str, default=None, help="Đường dẫn CSV kết quả chi tiết (tùy chọn)")
    parser.add_argument("--comparison-out", type=str, default=None, help="Đường dẫn CSV đối sánh Python vs Fiji (chỉ dùng với --source both)")
    return parser.parse_known_args()[0]

def main():
    args = parse_args()
    blob_mode = args.blob_sigmas or ("extended" if args.source == "python" else "config")
    sources = ["python", "fiji"] if args.source == "both" else [args.source]

    if args.bsds_threshold_mode == "grid":
        sigmas = parse_float_list(args.bsds_sigmas, get_sigmas())
    else:
        sigmas = [2.0]

    print("=" * 65)
    print("  KHỞI CHẠY KHUNG ĐÁNH GIÁ ĐỊNH LƯỢNG TẦNG 2 (BENCHMARK)")
    print(f"  Nguồn bản đồ: {args.source.upper()}")
    print(f"  Chế độ ngưỡng BSDS: {args.bsds_threshold_mode.upper()}")
    if args.bsds_threshold_mode == "grid":
        print(f"  Sigma BSDS: {', '.join(f'{s:.1f}' for s in sigmas)}")
        print(
            "  Lưới phân vị: "
            f"p_low={parse_float_list(args.bsds_grid_low, DEFAULT_BSDS_GRID_LOW)} | "
            f"p_high={parse_float_list(args.bsds_grid_high, DEFAULT_BSDS_GRID_HIGH)}"
        )
        print(
            f"  Lưới tinh: {'bật' if args.bsds_refine else 'tắt'} "
            f"(radius={args.bsds_refine_radius}, step={args.bsds_refine_step})"
        )
    else:
        print(
            f"  Canny cố định: p_low={args.p_low:.1f}, p_high={args.p_high:.1f} "
            f"tại sigma=2.0"
        )
        print("  [!] Chế độ fixed chỉ dùng để tái lập kết quả lịch sử;")
        print("      không đáp ứng yêu cầu quét lưới riêng cho từng sigma.")
    print(f"  Nhánh BSDS của Fiji: {args.bsds_fiji_mode}")
    print(f"  Thang đo Blob: {blob_mode} ({7 if blob_mode == 'config' else 8} sigma)")
    print("=" * 65)

    thresholds_by_sigma = {
        float(s): (float(args.p_low), float(args.p_high)) for s in sigmas
    }
    selected_rows = []
    grid_rows = []

    if args.bsds_threshold_mode == "grid":
        grid_out = (
            Path(args.bsds_grid_out)
            if args.bsds_grid_out
            else METRICS_DIR / "tier2_bsds_sigma_grid.csv"
        )
        thresholds_out = (
            Path(args.bsds_thresholds_out)
            if args.bsds_thresholds_out
            else METRICS_DIR / "tier2_bsds_thresholds.csv"
        )
        thresholds_by_sigma, grid_rows, selected_rows = calibrate_fair_thresholds(
            sample_limit=args.bsds_samples,
            sigmas=sigmas,
            grid_low=parse_float_list(args.bsds_grid_low, DEFAULT_BSDS_GRID_LOW),
            grid_high=parse_float_list(args.bsds_grid_high, DEFAULT_BSDS_GRID_HIGH),
            refine=args.bsds_refine,
            refine_radius=args.bsds_refine_radius,
            refine_step=args.bsds_refine_step,
            grid_out=grid_out,
            thresholds_out=thresholds_out,
        )
        print("\n  BẢNG NGƯỠNG TỐI ƯU THEO SIGMA (CHỌN TRÊN PYTHON)")
        print(f"  {'Sigma':>6} {'p_low':>8} {'p_high':>8} {'F1 Python':>12}")
        print("  " + "-" * 40)
        for sigma in sigmas:
            pl, ph = thresholds_by_sigma[sigma]
            py_row = next(
                (
                    r
                    for r in selected_rows
                    if r["source"] == "python"
                    and abs(float(r["sigma"]) - sigma) < 1e-9
                ),
                None,
            )
            f1 = float(py_row["mean_f1"]) if py_row else 0.0
            print(f"  {sigma:>6.1f} {pl:>8.2f} {ph:>8.2f} {f1:>12.6f}")

    all_records = []

    # Chạy đủ 25 ảnh: 10 BSDS + 10 DRIVE + 5 Blob (theo spec Tầng 2)
    for source in sources:
        task_name = "BSDS500_Canny_Edge"
        if source == "fiji" and args.bsds_fiji_mode == "edge":
            task_name = "BSDS500_FeatureJ_Edges_Reference"
        evaluate_bsds_edges(
            sample_limit=args.bsds_samples,
            p_low=args.p_low,
            p_high=args.p_high,
            records=all_records,
            source=source,
            fiji_mode=args.bsds_fiji_mode,
            task_name=task_name,
            sigmas=sigmas,
            thresholds_by_sigma=thresholds_by_sigma,
            selection_method=(
                "grid_python_f1_frozen_for_fiji"
                if args.bsds_threshold_mode == "grid"
                else "fixed_p_low_p_high"
            ),
        )
        evaluate_drive_vessels(
            sample_limit=args.drive_samples, records=all_records, source=source
        )
        evaluate_blobs(
            sample_limit=args.blob_samples,
            records=all_records,
            source=source,
            blob_sigmas=blob_mode,
        )

    edge_ref_records = []
    edge_summary_rows = []
    edge_grid_rows = []

    # Tham chiếu riêng FeatureJ Edges: chỉ ghi khi bảng chính dùng nhánh fair canny.
    if args.source == "both" and args.bsds_fiji_mode == "canny":
        edge_ref_csv = (
            Path(args.edge_reference_out)
            if args.edge_reference_out
            else METRICS_DIR / "tier2_bsds_edge_reference.csv"
        )
        if args.bsds_threshold_mode == "grid":
            edge_grid_csv = (
                Path(args.edge_reference_grid_out)
                if args.edge_reference_grid_out
                else METRICS_DIR / "tier2_bsds_edge_reference_grid.csv"
            )
            edge_sigma_csv = (
                Path(args.edge_reference_sigma_out)
                if args.edge_reference_sigma_out
                else METRICS_DIR / "tier2_bsds_edge_reference_by_sigma.csv"
            )
            edge_ref_records, edge_summary_rows, edge_grid_rows = (
                calibrate_edge_reference(
                    sample_limit=args.bsds_samples,
                    sigmas=sigmas,
                    grid_out=edge_grid_csv,
                    by_sigma_out=edge_sigma_csv,
                )
            )
        else:
            evaluate_bsds_edges(
                sample_limit=args.bsds_samples,
                p_low=args.p_low,
                p_high=args.p_high,
                records=edge_ref_records,
                source="fiji",
                fiji_mode="edge",
                task_name="BSDS500_FeatureJ_Edges_Reference",
                sigmas=[2.0],
                thresholds_by_sigma={2.0: (args.p_low, args.p_high)},
                selection_method="fixed_percentile_reference",
            )
        write_records(edge_ref_records, edge_ref_csv)

    # Lưu toàn bộ kết quả định lượng ra outputs/metrics/tier2_results.csv
    if args.out:
        out_csv = Path(args.out)
    else:
        default_names = {
            "python": "tier2_results.csv",
            "fiji": "tier2_results_fiji.csv",
            "both": "tier2_results_both.csv",
        }
        out_csv = METRICS_DIR / default_names[args.source]

    write_records(all_records, out_csv)

    if args.source == "both":
        comp_csv = (
            Path(args.comparison_out)
            if args.comparison_out
            else METRICS_DIR / "tier2_comparison.csv"
        )
        write_comparison(all_records, comp_csv)

    if args.bsds_threshold_mode == "grid":
        by_sigma_csv = (
            Path(args.bsds_by_sigma_out)
            if args.bsds_by_sigma_out
            else METRICS_DIR / "tier2_bsds_by_sigma.csv"
        )
        write_by_sigma_csv(selected_rows, edge_summary_rows, by_sigma_csv)

    print("\n" + "=" * 65)
    print("  HOÀN TẤT ĐÁNH GIÁ ĐỊNH LƯỢNG TẦNG 2!")
    print("=" * 65)

if __name__ == "__main__":
    main()
