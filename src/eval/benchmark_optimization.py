"""benchmark_optimization.py - Đo thời gian chập 2D trực tiếp vs tách chập 1D.

Ví dụ démon nêu rõ: phép chập 2D kích thước Kx x Ky tốn O(Kx*Ky*HW), còn tách
chập thành hai phép chập 1D nối tiếp tốn O((Kx + Ky)*HW). Thực nghiệm này
chỉ dùng để đo thời gian, KHÔNG đưa vào src/core.

Output: outputs/metrics/optimization_benchmark.csv
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Callable

import numpy as np

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.core.convolution import separable_convolve_2d
from src.core.kernel import get_gaussian_kernel_1d
from src.config import get_border_mode

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_CSV = ROOT / "outputs" / "metrics" / "optimization_benchmark.csv"

# Cảnh báo: đây là hàm chập 2D trực tiếp để đo thời gian, không dùng trong src/core.
def naive_convolve_2d(
    img: np.ndarray,
    kx: np.ndarray,
    ky: np.ndarray,
    mode: str,
) -> np.ndarray:
    """Phép chập 2D trực tiếp (baseline cho mục đích đo thời gian).

    Tương đương với (I * Kx * Ky) nhưng tính bằng kernel 2D đầy đủ:
    out = sum_{m,n} k2[m,n] * padded[i+m, j+n]

    Không đưa vào src/core vì có chi phí O(Kx*Ky*HW).
    """
    np_mode = "symmetric" if mode == "reflect" else "reflect"
    ry, rx = len(ky) // 2, len(kx) // 2
    padded = np.pad(img, ((ry, ry), (rx, rx)), mode=np_mode)

    k2 = np.outer(ky[::-1], kx[::-1])
    h, w = img.shape
    out = np.zeros_like(img, dtype=np.float64)
    for m in range(k2.shape[0]):
        row = padded[m : m + h, :]
        for n in range(k2.shape[1]):
            out += k2[m, n] * row[:, n : n + w]
    return out


def measure(fn: Callable[[], float | None], reps: int = 5, min_total_s: float = 0.2) -> float:
    """Median thời gian (ms) sau 1 lần warm-up, lặp ít nhất `reps` lần."""
    fn()  # warm-up
    times = []
    total = 0.0
    for _ in range(max(reps, 3)):
        t0 = time.perf_counter()
        fn()
        dt = time.perf_counter() - t0
        times.append(dt)
        total += dt
        if len(times) >= 3 and total >= min_total_s:
            break
    return float(np.median(times)) * 1000.0


def main() -> None:
    images = ["bsds_01", "drive_01", "blob_01"]
    sigmas = [1.0, 2.0, 4.0, 8.0]
    ops = [
        ("gauss", (0, 0)),
        ("lx", (1, 0)),
        ("lxx", (2, 0)),
    ]
    mode = get_border_mode()

    rows = []
    for image in images:
        img_path = ROOT / "data" / "raw" / f"{image}.png"
        img = np.array(__import__("PIL.Image", fromlist=["Image"]).open(img_path), dtype=np.float64)

        for sigma in sigmas:
            for name, (ox, oy) in ops:
                kx = get_gaussian_kernel_1d(sigma, order=ox)
                ky = get_gaussian_kernel_1d(sigma, order=oy)

                separable_fn = lambda: separable_convolve_2d(img, kernel_x=kx, kernel_y=ky, mode=mode)
                naive_fn = lambda: naive_convolve_2d(img, kx, ky, mode)

                # Kiểm tra đúng đắn trước khi đo
                ref = separable_convolve_2d(img, kernel_x=kx, kernel_y=ky, mode=mode)
                got = naive_convolve_2d(img, kx, ky, mode)
                max_diff = float(np.max(np.abs(ref - got)))

                sep_ms = measure(separable_fn)
                naive_ms = measure(naive_fn)

                kx_len = int(kx.shape[0])
                ky_len = int(ky.shape[0])
                theory_speedup = (kx_len * ky_len) / (kx_len + ky_len)
                speedup = naive_ms / sep_ms if sep_ms > 0 else float("nan")

                rows.append(
                    {
                        "operator": name,
                        "image": image,
                        "sigma": sigma,
                        "kx_len": kx_len,
                        "ky_len": ky_len,
                        "naive_ms": round(naive_ms, 6),
                        "separable_ms": round(sep_ms, 6),
                        "speedup": round(speedup, 6),
                        "theory_speedup": round(theory_speedup, 4),
                        "max_abs_diff": f"{max_diff:.3e}",
                    }
                )

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "operator", "image", "sigma", "kx_len", "ky_len",
        "naive_ms", "separable_ms", "speedup", "theory_speedup", "max_abs_diff",
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows -> {OUTPUT_CSV}")
    print(f"Fieldnames: {fieldnames}")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
