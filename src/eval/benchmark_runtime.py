"""benchmark_runtime.py - Đo thời gian chạy Python Core theo cùng phạm vi Fiji.

Mục tiêu là tạo một bảng thời gian chạy có thể đặt cạnh
``outputs/metrics/fiji_runtime.csv`` mà không so sánh khập khiễng:

- Đọc từng dòng ``(image, command, sigma)`` của Fiji.
- Chạy đúng phép toán Python tương ứng trên cùng ảnh, cùng sigma.
- Bỏ lần chạy đầu tiên (warm-up), lặp nhiều lần và lấy trung vị.
- Ghi ra ``outputs/metrics/python_runtime.csv`` với schema 6 cột giống hệt:
  ``source,image,command,sigma,runtime_ms,output_files``.

Phép toán tương ứng:

===============  =========================================================
Fiji command     Python Core
===============  =========================================================
gauss            ``gaussian_smooth``
lx, ly           một phép tích chập tách rời với kernel đạo hàm bậc 1
lxx, lxy, lyy    một phép tích chập tách rời với kernel đạo hàm bậc 2
gradient         ``compute_derivatives_1st`` + độ lớn gradient
edge             ``compute_derivatives_1st`` + NMS (``canny_nms``)
laplacian        ``compute_laplacian``
hessian          ``compute_hessian_matrix`` + trị riêng giải tích
structure        ``compute_structure_tensor`` + trị riêng giải tích
===============  =========================================================

Thời gian chỉ đo phần tính toán trong bộ nhớ, không tính đọc/ghi TIFF, đúng
với cách macro Fiji đo ``getTime()`` trước ``saveAs``.
"""

import argparse
import csv
from pathlib import Path
import re
import statistics
import sys
import time

import numpy as np
from PIL import Image

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.config import get_border_mode, get_eigen_order, get_kernel_k
from src.core.convolution import separable_convolve_2d
from src.core.derivatives import (
    compute_derivatives_1st,
    compute_gradient_magnitude,
    compute_laplacian,
    gaussian_smooth,
)
from src.core.detectors import canny_nms
from src.core.hessian import (
    compute_hessian_eigenvalues,
    compute_hessian_matrix,
)
from src.core.kernel import get_gaussian_kernel_1d
from src.core.structure_tensor import (
    compute_structure_tensor,
    compute_structure_tensor_eigenvalues,
)

RAW_DIR = ROOT / "data" / "raw"
METRICS_DIR = ROOT / "outputs" / "metrics"

RUNTIME_FIELDS = [
    "source",
    "image",
    "command",
    "sigma",
    "runtime_ms",
    "output_files",
]

STRUCTURE_RE = re.compile(r"sd([0-9.]+)_si([0-9.]+)")


def read_csv(path: Path):
    """Đọc CSV UTF-8-SIG và trả về danh sách dict."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def single_derivative(
    img: np.ndarray, sigma: float, x_order: int, y_order: int
) -> np.ndarray:
    """Tính một bản đồ đạo hàm duy nhất, đúng quy ước của ``src.core``."""
    kx = get_kernel_k(x_order)
    ky = get_kernel_k(y_order)
    gx = get_gaussian_kernel_1d(sigma, order=x_order, k=kx)
    gy = get_gaussian_kernel_1d(sigma, order=y_order, k=ky)
    return separable_convolve_2d(
        img, kernel_x=gx, kernel_y=gy, mode=get_border_mode()
    )


def parse_sigma(sigma_text: str) -> float:
    """Đọc sigma số thực từ chuỗi của bảng runtime."""
    return float(str(sigma_text).strip())


def parse_structure_sigma(sigma_text: str):
    """Đọc cặp ``(sigma_d, sigma_i)`` từ chuỗi ``sd1.0_si3.0``."""
    match = STRUCTURE_RE.fullmatch(str(sigma_text).strip())
    if not match:
        raise ValueError(f"Không đọc được sigma structure: {sigma_text!r}")
    return float(match.group(1)), float(match.group(2))


def build_operation(command: str, img: np.ndarray, sigma_text: str):
    """Trả về hàm không tham số thực hiện đúng phép toán Python tương ứng."""
    if command == "gauss":
        sigma = parse_sigma(sigma_text)
        return lambda: gaussian_smooth(img, sigma=sigma)

    if command in ("lx", "ly", "lxx", "lxy", "lyy"):
        sigma = parse_sigma(sigma_text)
        orders = {
            "lx": (1, 0),
            "ly": (0, 1),
            "lxx": (2, 0),
            "lxy": (1, 1),
            "lyy": (0, 2),
        }[command]
        return lambda: single_derivative(img, sigma, orders[0], orders[1])

    if command == "gradient":
        sigma = parse_sigma(sigma_text)

        def _gradient():
            lx, ly = compute_derivatives_1st(img, sigma=sigma)
            return compute_gradient_magnitude(sigma * lx, sigma * ly)

        return _gradient

    if command == "edge":
        sigma = parse_sigma(sigma_text)

        def _edge():
            lx, ly = compute_derivatives_1st(img, sigma=sigma)
            return canny_nms(sigma * lx, sigma * ly)

        return _edge

    if command == "laplacian":
        sigma = parse_sigma(sigma_text)
        return lambda: compute_laplacian(img, sigma=sigma)

    if command == "hessian":
        sigma = parse_sigma(sigma_text)
        eigen_order = get_eigen_order()

        def _hessian():
            lxx, lyy, lxy = compute_hessian_matrix(img, sigma=sigma)
            return compute_hessian_eigenvalues(
                lxx, lyy, lxy, sort_order=eigen_order
            )

        return _hessian

    if command == "structure":
        sigma_d, sigma_i = parse_structure_sigma(sigma_text)

        def _structure():
            j11, j22, j12 = compute_structure_tensor(
                img, sigma_d=sigma_d, sigma_i=sigma_i
            )
            return compute_structure_tensor_eigenvalues(j11, j22, j12)

        return _structure

    raise ValueError(f"Không hỗ trợ command runtime: {command!r}")


def measure_operation(fn, min_time_s: float, max_reps: int):
    """Đo thời gian trung vị, bỏ lần chạy đầu tiên.

    Lặp cho đến khi đạt ``min_time_s`` hoặc ``max_reps``, nhưng luôn có ít nhất
    3 lần đo sau warm-up. Cách này ổn định với cả phép toán dưới 1 ms.
    """
    fn()  # Warm-up: bỏ lần chạy đầu tiên.
    samples = []
    total = 0.0
    while len(samples) < max_reps:
        start = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - start
        samples.append(elapsed)
        total += elapsed
        if len(samples) >= 3 and total >= min_time_s:
            break
    return statistics.median(samples) * 1000.0, len(samples)


def load_image(image_name: str, cache: dict) -> np.ndarray:
    """Đọc ảnh một lần cho mỗi tên và lưu vào cache."""
    if image_name not in cache:
        path = RAW_DIR / f"{image_name}.png"
        if not path.exists():
            raise FileNotFoundError(f"Thiếu ảnh đầu vào: {path}")
        cache[image_name] = np.array(Image.open(path), dtype=np.float64)
    return cache[image_name]


def selected_rows(rows, commands):
    """Lọc các dòng runtime theo danh sách command (rỗng = giữ tất cả)."""
    if not commands:
        return rows
    keep = {cmd.strip() for cmd in commands if cmd.strip()}
    return [row for row in rows if row["command"] in keep]


def summarize(rows, label):
    """In trung vị thời gian theo từng command."""
    print(f"\n  Tóm tắt {label}:")
    print(f"  {'Command':<12} {'n':>4} {'Trung vị (ms)':>15}")
    print("  " + "-" * 34)
    by_command = {}
    for row in rows:
        by_command.setdefault(row["command"], []).append(float(row["runtime_ms"]))
    for command in sorted(by_command):
        values = by_command[command]
        print(
            f"  {command:<12} {len(values):>4} "
            f"{statistics.median(values):>15.3f}"
        )


def write_runtime_csv(rows, path: Path):
    """Ghi bảng runtime Python với đúng schema của Fiji."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RUNTIME_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n-> Đã ghi: {path} ({len(rows)} dòng)")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Đo thời gian Python Core theo đúng bộ (image, command, sigma) "
            "của fiji_runtime.csv."
        )
    )
    parser.add_argument(
        "--fiji-runtime",
        type=str,
        default=str(METRICS_DIR / "fiji_runtime.csv"),
        help="CSV runtime Fiji cần mô phỏng (mặc định: outputs/metrics/fiji_runtime.csv)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(METRICS_DIR / "python_runtime.csv"),
        help="CSV runtime Python đầu ra (mặc định: outputs/metrics/python_runtime.csv)",
    )
    parser.add_argument(
        "--commands",
        type=str,
        default=None,
        help="Chỉ đo các command này, ví dụ 'gauss,lx,edge' (mặc định: tất cả)",
    )
    parser.add_argument(
        "--min-time",
        type=float,
        default=0.12,
        help="Thời gian đo tối thiểu cho mỗi dòng, giây (mặc định: 0.12)",
    )
    parser.add_argument(
        "--max-reps",
        type=int,
        default=30,
        help="Số lần đo tối đa sau warm-up (mặc định: 30)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Chỉ chạy N dòng đầu, dùng để kiểm tra nhanh",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    fiji_csv = Path(args.fiji_runtime)
    if not fiji_csv.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {fiji_csv}. Hãy chạy macro Fiji trước để có "
            "fiji_runtime.csv."
        )

    fiji_rows = read_csv(fiji_csv)
    commands = args.commands.split(",") if args.commands else None
    target_rows = selected_rows(fiji_rows, commands)
    if args.limit is not None:
        target_rows = target_rows[: args.limit]
    if not target_rows:
        raise RuntimeError("Không có dòng runtime nào để đo.")

    print("=" * 68)
    print("  ĐO THỜI GIAN PYTHON CORE THEO PHẠM VI RUNTIME FIJI")
    print(f"  Nguồn Fiji : {fiji_csv} ({len(fiji_rows)} dòng)")
    print(f"  Số dòng đo : {len(target_rows)}")
    print(
        f"  Chế độ đo  : bỏ warm-up, tối thiểu {args.min_time:.3f}s, "
        f"tối đa {args.max_reps} lần, lấy trung vị"
    )
    print("=" * 68)

    image_cache = {}
    output_rows = []
    start_all = time.perf_counter()

    for index, row in enumerate(target_rows, 1):
        image_name = row["image"]
        command = row["command"]
        sigma_text = row["sigma"]

        try:
            img = load_image(image_name, image_cache)
            operation = build_operation(command, img, sigma_text)
            runtime_ms, reps = measure_operation(
                operation, args.min_time, args.max_reps
            )
        except Exception as exc:  # pragma: no cover - báo lỗi rõ ràng
            print(f"   [!] Bỏ qua {image_name}/{command}/{sigma_text}: {exc}")
            continue

        output_rows.append(
            {
                "source": "python",
                "image": image_name,
                "command": command,
                "sigma": sigma_text,
                "runtime_ms": f"{runtime_ms:.3f}",
                "output_files": "in-memory",
            }
        )
        print(
            f"   [{index:>3}/{len(target_rows)}] {image_name:<10} "
            f"{command:<10} sigma={sigma_text:<12} "
            f"{runtime_ms:>9.3f} ms  ({reps} lần)"
        )

    elapsed = time.perf_counter() - start_all
    summarize(output_rows, "Python")
    print(f"\n  Tổng thời gian đo: {elapsed:.1f} s")
    write_runtime_csv(output_rows, Path(args.out))


if __name__ == "__main__":
    main()
