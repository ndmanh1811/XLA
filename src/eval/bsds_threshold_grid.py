"""Công cụ quét lưới ngưỡng BSDS theo từng sigma.

Mục tiêu là triển khai đúng yêu cầu tại ``INSTRUCTIONS.md:128``:

- NMS chỉ được tính một lần cho mỗi ảnh và mỗi sigma.
- Ngưỡng của nhánh fair là phân vị của ``nms[nms > 0]``.
- Lưới ``(p_low, p_high)`` được quét riêng cho từng sigma.
- Bộ ngưỡng tối ưu được chọn trên Python theo F1 trung bình, sau đó đóng băng
  và áp nguyên vẹn cho Fiji.
- Nhánh tham chiếu FeatureJ Edges dùng ngưỡng tuyệt đối (đơn vị đầu ra của
  plugin), không dùng chung lưới phân vị với nhánh fair.

Phần lõi toán học vẫn nằm trong ``src/core`` và chỉ dùng NumPy. Toàn bộ xử lý
hình thái học (dilation, gán nhãn thành phần liên thông) trong module này cũng
đã được viết lại bằng thuần NumPy, không dùng ``scipy.ndimage``, tuân thủ
ràng buộc tại ``INSTRUCTIONS.md:25``.
"""

from dataclasses import dataclass
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image

# Toàn bộ xử lý hình thái học trong module này dùng thuần NumPy (không dùng
# scipy.ndimage) theo ràng buộc tại INSTRUCTIONS.md:25 (SciPy chỉ được phép trong
# unit test / benchmark thời gian).

_STRUCT_DISK_R2 = np.zeros((5, 5), dtype=bool)
_dy_disk, _dx_disk = np.mgrid[-2:3, -2:3]
_STRUCT_DISK_R2[_dx_disk**2 + _dy_disk**2 <= 4] = True

# Các tọa độ sai dịch của phần tử cấu trúc đĩa bán kính 2 px (13 pixel), dùng
# cho phép dilation vectơ hóa.
_DISK_OFFSETS = [
    (dy, int(dx))
    for dy in range(-2, 3)
    for dx in range(-2, 3)
    if _STRUCT_DISK_R2[dy + 2, dx + 2]
]

STRUCT_2PX = _STRUCT_DISK_R2
STRUCT_8 = np.ones((3, 3), dtype=bool)


def _find(label_val: int, parent: Dict[int, int]) -> int:
    """Tìm đại diện của tập hợp với nén đường dẫn (union-find)."""
    root = label_val
    while parent[root] != root:
        root = parent[root]
    while parent[label_val] != root:
        nxt = parent[label_val]
        parent[label_val] = root
        label_val = nxt
    return root


def binary_dilation(image: np.ndarray, structure: np.ndarray) -> np.ndarray:
    """Phãn nở nhị phân vectơ hóa với phần tử cấu trúc arbitrary (kernel_bool).

    Thay thế trực tiếp ``scipy.ndimage.binary_dilation``. Chỉ xử lý mảng bool 2D
    và phần tử cấu trúc bool 2D; pixel ngoài biên được coi là False (không wrap).
    """
    h, w = image.shape
    out = np.zeros((h, w), dtype=bool)
    sh, sw = structure.shape
    cy, cx = sh // 2, sw // 2
    for dy in range(-cy, cy + 1):
        for dx in range(-cx, cx + 1):
            if not structure[dy + cy, dx + cx]:
                continue
            ys = max(0, -dy)
            ye = min(h, h - dy)
            xs = max(0, -dx)
            xe = min(w, w - dx)
            if ys >= ye or xs >= xe:
                continue
            out[ys + dy : ye + dy, xs + dx : xe + dx] |= image[ys:ye, xs:xe]
    return out


def label(image: np.ndarray, structure: np.ndarray | None = None) -> Tuple[np.ndarray, int]:
    """Gán nhãn thành phần liên thông 8-láng giềng (union-find thuần NumPy).

    Thay thế trực tiếp ``scipy.ndimage.label`` với ``structure`` 3x3 toàn 1.
    Trả về ``(labels, num_labels)`` trong đó ``labels`` có kiểu int64, giá trị 0
    là nền, các thành phần được đánh số từ 1 đến ``num_labels``.

    Chỉ duyệt qua các pixel nền (foreground), nên nhanh với bản đồ biên thưa.
    """
    h, w = image.shape
    if structure is None:
        structure = STRUCT_8

    labels = np.zeros((h, w), dtype=np.int64)
    parent: Dict[int, int] = {}
    next_label = 1

    # Các láng giềng đã duyệt trước theo thứ tự quét (trên, trên-trái, trên-phải, trái)
    prev_offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1)]

    ys, xs = np.where(image)
    for y, x in zip(ys.tolist(), xs.tolist()):
        neighbor_labels: List[int] = []
        for dy, dx in prev_offsets:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                nl = int(labels[ny, nx])
                if nl > 0:
                    neighbor_labels.append(nl)

        if not neighbor_labels:
            labels[y, x] = next_label
            parent[next_label] = next_label
            next_label += 1
        else:
            m = min(neighbor_labels)
            labels[y, x] = m
            root_m = _find(m, parent)
            for nl in neighbor_labels:
                root_nl = _find(nl, parent)
                if root_m != root_nl:
                    parent[root_nl] = root_m
                    root_m = _find(m, parent)

    # Duyệt qua lần hai: làm cháng labels về đại diện cùng lúc nén đường dẫn.
    for y, x in zip(ys.tolist(), xs.tolist()):
        lv = int(labels[y, x])
        if lv > 0:
            labels[y, x] = _find(lv, parent)

    # Giọp nhãn lại thành dãy liên tiếp từ 1.
    unique = np.unique(labels)
    unique = unique[unique > 0]
    num_labels = int(unique.size)
    if num_labels > 0:
        remap = np.zeros(int(unique.max()) + 1, dtype=np.int64)
        remap[unique] = np.arange(1, num_labels + 1, dtype=np.int64)
        labels = remap[labels]

    return labels, num_labels


@dataclass
class BsdsItem:
    """Một ảnh BSDS cùng toàn bộ mặt nạ Ground Truth đa annotator."""

    stem: str
    image: np.ndarray
    gt_boundaries: np.ndarray  # bool, shape (num_annotators, H, W)
    union_gt: np.ndarray  # bool, shape (H, W)
    dilated_union_gt: np.ndarray  # bool, shape (H, W)
    annotator_positives: np.ndarray  # int, shape (num_annotators,)


def load_bsds_items(raw_dir: Path, gt_dir: Path, sample_limit: int = 10) -> List[BsdsItem]:
    """Đọc ảnh BSDS và Ground Truth theo đúng quy ước của benchmark Tầng 2."""
    items: List[BsdsItem] = []
    bsds_files = sorted(list(Path(raw_dir).glob("bsds_*.png")))[:sample_limit]
    for img_path in bsds_files:
        stem = img_path.stem
        annotator_files = sorted(
            list((Path(gt_dir) / "bsds" / stem).glob("annotator_*_boundaries.png"))
        )
        if annotator_files:
            gt_boundaries = np.stack(
                [np.array(Image.open(f)) > 0 for f in annotator_files], axis=0
            )
        elif (Path(gt_dir) / f"{stem}_boundaries.npy").exists():
            gt_boundaries = np.load(Path(gt_dir) / f"{stem}_boundaries.npy") > 0
        else:
            continue

        if gt_boundaries.ndim == 2:
            gt_boundaries = gt_boundaries[None, :, :]

        img = np.array(Image.open(img_path), dtype=np.float64)
        union_gt = np.any(gt_boundaries > 0, axis=0)
        items.append(
            BsdsItem(
                stem=stem,
                image=img,
                gt_boundaries=gt_boundaries,
                union_gt=union_gt,
                dilated_union_gt=binary_dilation(union_gt, structure=STRUCT_2PX),
                annotator_positives=np.sum(gt_boundaries > 0, axis=(1, 2)),
            )
        )
    return items


def hysteresis_absolute(
    nms: np.ndarray, t_low: float, t_high: float
) -> np.ndarray:
    """Ngưỡng trễ với hai ngưỡng tuyệt đối trên edge strength đã NMS.

    Hàm dùng thành phần liên thông 8-láng giềng: giữ toàn bộ thành phần
    ``nms >= t_low`` có chứa ít nhất một pixel ``nms >= t_high``. Cách này cho
    cùng kết quả với BFS 8-láng giềng trong ``src.core.detectors`` nhưng nhanh
    hơn nhiều khi quét lưới.
    """
    if t_high < t_low:
        raise ValueError("t_high phải lớn hơn hoặc bằng t_low")

    candidate = (nms >= t_low) & (nms > 0)
    strong = (nms >= t_high) & (nms > 0)
    out = np.zeros(nms.shape, dtype=bool)
    if not strong.any():
        return out

    labels, num_labels = label(candidate, structure=STRUCT_8)
    if num_labels == 0:
        return out

    keep = np.zeros(num_labels + 1, dtype=bool)
    keep[np.unique(labels[strong])] = True
    keep[0] = False
    return keep[labels]


def hysteresis_percentile_fast(
    nms: np.ndarray, p_low: float, p_high: float
) -> np.ndarray:
    """Ngưỡng trễ phân vị, dùng cho kiểm tra chéo và các lần chạy lẻ."""
    nonzero = nms[nms > 0]
    if len(nonzero) == 0:
        return np.zeros(nms.shape, dtype=bool)
    t_high = float(np.percentile(nonzero, p_high))
    t_low = float(np.percentile(nonzero, p_low))
    return hysteresis_absolute(nms, t_low=t_low, t_high=t_high)


def evaluate_prediction(pred: np.ndarray, item: BsdsItem) -> Dict[str, float]:
    """Tính Precision/Recall/F1 với dung sai biên 2 px và Recall đa annotator."""
    pred_positive = int(np.sum(pred))
    if pred_positive > 0:
        true_positives = int(np.sum(pred & item.dilated_union_gt))
        precision = true_positives / pred_positive
    else:
        true_positives = 0
        precision = 0.0

    dilated_pred = binary_dilation(pred, structure=STRUCT_2PX)
    recalls: List[float] = []
    for a_idx in range(item.gt_boundaries.shape[0]):
        human_boundary = item.gt_boundaries[a_idx] > 0
        human_positives = int(item.annotator_positives[a_idx])
        if human_positives > 0:
            recalls.append(
                float(np.sum(human_boundary & dilated_pred) / human_positives)
            )
    recall = float(np.mean(recalls)) if recalls else 0.0
    f1 = (2.0 * precision * recall) / (precision + recall + 1e-10)
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "true_positives": float(true_positives),
        "predicted_count": float(pred_positive),
    }


def _valid_pairs(
    grid_low: Sequence[float], grid_high: Sequence[float]
) -> List[Tuple[float, float]]:
    lows = sorted({round(float(v), 6) for v in grid_low})
    highs = sorted({round(float(v), 6) for v in grid_high})
    return [(lo, hi) for lo in lows for hi in highs if lo < hi]


def evaluate_percentile_grid(
    nms_by_stem: Dict[str, np.ndarray],
    items: Sequence[BsdsItem],
    grid_low: Sequence[float],
    grid_high: Sequence[float],
) -> List[Dict[str, float]]:
    """Quét lưới phân vị trên nhiều ảnh và trả về Precision/Recall/F1 trung bình.

    Với mỗi ảnh, mỗi ``p_low`` chỉ cần dựng nhãn liên thông một lần; các
    ``p_high`` dùng lại nhãn đó. Đây là điểm quyết định tốc độ của toàn bộ grid.
    """
    pairs = _valid_pairs(grid_low, grid_high)
    if not pairs:
        return []

    accum = {
        pair: {"precision": 0.0, "recall": 0.0, "f1": 0.0, "count": 0}
        for pair in pairs
    }

    for item in items:
        nms = nms_by_stem.get(item.stem)
        if nms is None:
            continue
        nonzero = nms[nms > 0]
        if len(nonzero) == 0:
            # Ảnh không có cạnh nào sau NMS: vẫn tính vào mẫu số với F1 = 0
            # (không được loại bỏ như hiện tại, gây bias mean F1 lên cao).
            for (lo, hi) in pairs:
                acc = accum[(lo, hi)]
                acc["precision"] += 0.0
                acc["recall"] += 0.0
                acc["f1"] += 0.0
                acc["count"] += 1
            continue

        t_lows = {round(lo, 6): float(np.percentile(nonzero, lo)) for lo, _ in pairs}
        t_highs = {round(hi, 6): float(np.percentile(nonzero, hi)) for _, hi in pairs}

        # Gom các p_low cần dựng nhãn; mỗi p_low dựng label đúng một lần.
        lows_needed = sorted({lo for lo, _ in pairs})
        for lo in lows_needed:
            candidate = nms >= t_lows[round(lo, 6)]
            labels, num_labels = label(candidate, structure=STRUCT_8)
            if num_labels == 0:
                continue
            highs_needed = [hi for l, hi in pairs if l == lo]
            for hi in highs_needed:
                strong = nms >= t_highs[round(hi, 6)]
                if not strong.any():
                    pred = np.zeros(nms.shape, dtype=bool)
                else:
                    keep = np.zeros(num_labels + 1, dtype=bool)
                    keep[np.unique(labels[strong])] = True
                    keep[0] = False
                    pred = keep[labels]
                metrics = evaluate_prediction(pred, item)
                acc = accum[(lo, hi)]
                acc["precision"] += metrics["precision"]
                acc["recall"] += metrics["recall"]
                acc["f1"] += metrics["f1"]
                acc["count"] += 1

    rows: List[Dict[str, float]] = []
    for (lo, hi), acc in sorted(accum.items()):
        n = acc["count"]
        if n == 0:
            continue
        rows.append(
            {
                "p_low": float(lo),
                "p_high": float(hi),
                "mean_precision": acc["precision"] / n,
                "mean_recall": acc["recall"] / n,
                "mean_f1": acc["f1"] / n,
                "n_images": int(n),
            }
        )
    return rows


def evaluate_absolute_grid(
    edge_maps_by_stem: Dict[str, np.ndarray],
    items: Sequence[BsdsItem],
    grid_low: Sequence[float],
    grid_high: Sequence[float],
) -> List[Dict[str, float]]:
    """Quét lưới ngưỡng tuyệt đối cho nhánh tham chiếu FeatureJ Edges.

    ``grid_low``/``grid_high`` nằm trong đơn vị edge strength của plugin, không
    phải phân vị. Mỗi cặp ngưỡng được áp cho toàn bộ 10 ảnh ở cùng sigma.
    """
    pairs = _valid_pairs(grid_low, grid_high)
    if not pairs:
        return []

    accum = {
        pair: {"precision": 0.0, "recall": 0.0, "f1": 0.0, "count": 0}
        for pair in pairs
    }

    for item in items:
        nms = edge_maps_by_stem.get(item.stem)
        if nms is None:
            continue
        if not np.any(nms > 0):
            # Ảnh không có pixel cạnh nào: vẫn tính vào mẫu số với F1 = 0.
            for (lo, hi) in pairs:
                acc = accum[(lo, hi)]
                acc["precision"] += 0.0
                acc["recall"] += 0.0
                acc["f1"] += 0.0
                acc["count"] += 1
            continue

        # Gom các t_low duy nhất; tính nhãn liên thông đúng 1 lần cho mỗi t_low
        # thay vì gọi lại hysteresis_absolute (và label) cho từng cặp (lo, hi).
        lows_needed = sorted({lo for lo, _ in pairs})
        t_low_candidates: Dict[float, Tuple[np.ndarray, int]] = {}
        for lo in lows_needed:
            candidate = (nms >= lo) & (nms > 0)
            labels, num_labels = label(candidate, structure=STRUCT_8)
            if num_labels == 0:
                continue
            t_low_candidates[lo] = (labels, num_labels)

        highs_by_low: Dict[float, List[float]] = {}
        for lo, hi in pairs:
            highs_by_low.setdefault(lo, []).append(hi)

        for lo, highs in highs_by_low.items():
            if lo not in t_low_candidates:
                continue
            labels, num_labels = t_low_candidates[lo]
            for hi in highs:
                strong = (nms >= hi) & (nms > 0)
                if not strong.any():
                    pred = np.zeros(nms.shape, dtype=bool)
                else:
                    keep = np.zeros(num_labels + 1, dtype=bool)
                    keep[np.unique(labels[strong])] = True
                    keep[0] = False
                    pred = keep[labels]
                metrics = evaluate_prediction(pred, item)
                acc = accum[(lo, hi)]
                acc["precision"] += metrics["precision"]
                acc["recall"] += metrics["recall"]
                acc["f1"] += metrics["f1"]
                acc["count"] += 1

    rows: List[Dict[str, float]] = []
    for (lo, hi), acc in sorted(accum.items()):
        n = acc["count"]
        if n == 0:
            continue
        rows.append(
            {
                "t_low": float(lo),
                "t_high": float(hi),
                "mean_precision": acc["precision"] / n,
                "mean_recall": acc["recall"] / n,
                "mean_f1": acc["f1"] / n,
                "n_images": int(n),
            }
        )
    return rows


def select_best_row(rows: Sequence[Dict[str, float]]) -> Optional[Dict[str, float]]:
    """Chọn dòng có F1 trung bình cao nhất.

    Tie-break: ưu tiên Precision cao hơn, sau đó ưu tiên ngưỡng cao hơn
    (bộ ngưỡng bảo thủ hơn, ít biên giả hơn).
    """
    if not rows:
        return None

    def key(row: Dict[str, float]):
        return (
            float(row["mean_f1"]),
            float(row["mean_precision"]),
            float(row.get("p_low", row.get("t_low", 0.0))),
            float(row.get("p_high", row.get("t_high", 0.0))),
        )

    return max(rows, key=key)


def make_refine_grid(
    center_low: float,
    center_high: float,
    radius: float = 2.0,
    step: float = 1.0,
) -> Tuple[List[float], List[float]]:
    """Tạo lưới tinh quanh một cặp ngưỡng, giới hạn trong [0, 100]."""
    if step <= 0:
        return [], []
    lows = np.arange(
        max(0.0, center_low - radius),
        min(100.0, center_low + radius) + step * 0.5,
        step,
    )
    highs = np.arange(
        max(0.0, center_high - radius),
        min(100.0, center_high + radius) + step * 0.5,
        step,
    )
    return (
        [round(float(v), 4) for v in np.unique(lows)],
        [round(float(v), 4) for v in np.unique(highs)],
    )


def write_csv(
    rows: Sequence[Dict[str, object]],
    path: Path,
    fieldnames: Optional[Sequence[str]] = None,
) -> None:
    """Ghi danh sách dict ra CSV UTF-8-SIG, bỏ các khóa nội bộ bắt đầu bằng ``_``."""
    if not rows:
        print(f"   [!] Không có dòng nào để ghi vào {path}")
        return
    fields = fieldnames or [k for k in rows[0].keys() if not str(k).startswith("_")]
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"   -> Đã ghi: {out_path} ({len(rows)} dòng)")


def write_thresholds_csv(selected_rows: Sequence[Dict[str, object]], path: Path) -> None:
    """Ghi bảng ngưỡng tối ưu theo sigma để tái sử dụng cho Fiji."""
    rows = []
    for row in selected_rows:
        rows.append(
            {
                "sigma": f"{float(row['sigma']):.1f}",
                "p_low": f"{float(row['p_low']):.4f}",
                "p_high": f"{float(row['p_high']):.4f}",
                "mean_f1_python": f"{float(row['mean_f1']):.6f}",
                "mean_precision_python": f"{float(row['mean_precision']):.6f}",
                "mean_recall_python": f"{float(row['mean_recall']):.6f}",
                "n_images": int(row["n_images"]),
                "selection_method": "grid_python_f1_coarse_to_fine",
                "frozen_for_fiji": 1,
                "notes": "Chọn trên Python; áp nguyên vẹn cho Fiji",
            }
        )
    write_csv(rows, path)


def load_thresholds_csv(path: Path) -> Dict[float, Tuple[float, float]]:
    """Đọc bảng ngưỡng đã chọn; trả về ``{sigma: (p_low, p_high)}``."""
    out: Dict[float, Tuple[float, float]] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            sigma = float(row["sigma"])
            out[sigma] = (float(row["p_low"]), float(row["p_high"]))
    return out


def write_by_sigma_csv(
    fair_rows: Sequence[Dict[str, object]],
    edge_rows: Sequence[Dict[str, object]],
    path: Path,
) -> None:
    """Tổng hợp bảng F1 theo sigma cho báo cáo.

    ``fair_rows`` là các dòng đã chọn của Python/Fiji (mỗi sigma một dòng mỗi
    nguồn). ``edge_rows`` là các dòng tham chiếu FeatureJ Edges tại ngưỡng
    tuyệt đối tốt nhất của từng sigma.
    """
    def _find(source: str, sigma: float):
        for row in fair_rows:
            if row["source"] == source and abs(float(row["sigma"]) - sigma) < 1e-9:
                return row
        return None

    edge_by_sigma = {
        float(row["sigma"]): row for row in edge_rows
    }
    sigmas = sorted(
        {
            float(row["sigma"])
            for row in fair_rows
            if row.get("source") == "python" and float(row.get("selected", 1)) == 1
        }
    )
    out = []
    for sigma in sigmas:
        py = _find("python", sigma)
        fj = _find("fiji", sigma)
        edge = edge_by_sigma.get(sigma)
        py_f1 = float(py["mean_f1"]) if py else None
        fj_f1 = float(fj["mean_f1"]) if fj else None
        out.append(
            {
                "sigma": f"{sigma:.1f}",
                "python_p_low": f"{float(py['p_low']):.4f}" if py else "N/A",
                "python_p_high": f"{float(py['p_high']):.4f}" if py else "N/A",
                "python_mean_precision": f"{float(py['mean_precision']):.6f}" if py else "N/A",
                "python_mean_recall": f"{float(py['mean_recall']):.6f}" if py else "N/A",
                "python_mean_f1": f"{py_f1:.6f}" if py_f1 is not None else "N/A",
                "fiji_p_low": f"{float(fj['p_low']):.4f}" if fj else "N/A",
                "fiji_p_high": f"{float(fj['p_high']):.4f}" if fj else "N/A",
                "fiji_mean_precision": f"{float(fj['mean_precision']):.6f}" if fj else "N/A",
                "fiji_mean_recall": f"{float(fj['mean_recall']):.6f}" if fj else "N/A",
                "fiji_mean_f1": f"{fj_f1:.6f}" if fj_f1 is not None else "N/A",
                "delta_f1": (
                    f"{fj_f1 - py_f1:+.6f}"
                    if py_f1 is not None and fj_f1 is not None
                    else "N/A"
                ),
                "edge_reference_t_low": f"{float(edge['t_low']):.6f}" if edge else "N/A",
                "edge_reference_t_high": f"{float(edge['t_high']):.6f}" if edge else "N/A",
                "edge_reference_mean_precision": f"{float(edge['mean_precision']):.6f}" if edge else "N/A",
                "edge_reference_mean_recall": f"{float(edge['mean_recall']):.6f}" if edge else "N/A",
                "edge_reference_mean_f1": f"{float(edge['mean_f1']):.6f}" if edge else "N/A",
                "n_images": int(py["n_images"]) if py else 0,
            }
        )
    write_csv(out, path)


def edge_maps_for_sigma(
    fiji_dir: Path, items: Sequence[BsdsItem], sigma: float
) -> Dict[str, np.ndarray]:
    """Đọc các bản đồ ``fiji_*_edge_s{sigma}.tif`` cho toàn bộ ảnh BSDS."""
    import tifffile

    out: Dict[str, np.ndarray] = {}
    for item in items:
        path = Path(fiji_dir) / f"fiji_{item.stem}_edge_s{sigma:.1f}.tif"
        if path.exists():
            out[item.stem] = np.asarray(tifffile.imread(path), dtype=np.float64)
    return out
