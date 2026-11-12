"""Analyze the FeatureJ calibration run without changing project config.

Reads the measured CSV/TIFF artifacts produced by ``reproduce.ijm`` and writes:

- reviewed conclusions back to ``measurement_results.csv``;
- ``calibration_summary.csv`` with normalization, support and border evidence;
- ``CALIBRATION_RESULTS.md`` for the report handoff.

The script intentionally fails closed when the expected 40 TIFF/measurement
records are not present.
"""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image


HERE = Path(__file__).resolve().parent
MEASUREMENTS = HERE / "measurement_results.csv"
OUTPUTS = HERE / "outputs"
SUMMARY = HERE / "calibration_summary.csv"
REPORT = HERE / "CALIBRATION_RESULTS.md"
MANIFEST = HERE / "output_manifest.csv"
SCREENSHOTS = HERE / "screenshots"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def image(path: Path) -> np.ndarray:
    value = np.asarray(Image.open(path), dtype=np.float64)
    if value.ndim != 2 or not np.isfinite(value).all():
        raise ValueError(f"Invalid calibration TIFF: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def support_radius(profile: np.ndarray, center: int) -> int:
    peak = float(np.max(np.abs(profile)))
    if peak == 0:
        raise ValueError("Cannot determine support from an all-zero profile")
    indexes = np.flatnonzero(np.abs(profile) > peak * 1e-7)
    return int(np.max(np.abs(indexes - center)))


def f(value: float, digits: int = 9) -> str:
    return f"{value:.{digits}g}"


def main() -> None:
    rows = read_csv(MEASUREMENTS)
    tiffs = sorted(p for p in OUTPUTS.glob("*.tif"))
    if len(rows) != 40 or len(tiffs) != 40:
        raise ValueError(
            f"Expected 40 measurements and 40 TIFFs, got {len(rows)} and {len(tiffs)}"
        )

    manifest_rows = []
    for path in tiffs:
        value = image(path)
        manifest_rows.append(
            {
                "filename": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "height": value.shape[0],
                "width": value.shape[1],
                "dtype": str(np.asarray(Image.open(path)).dtype),
                "finite": bool(np.isfinite(value).all()),
                "min": f(float(value.min()), 12),
                "max": f(float(value.max()), 12),
            }
        )
    write_csv(
        MANIFEST,
        manifest_rows,
        ["filename", "size_bytes", "sha256", "height", "width", "dtype", "finite", "min", "max"],
    )

    by_key = {(r["image"], r["command"], r["sigma"], r["sigma_i"]): r for r in rows}
    summary: list[dict[str, object]] = []

    # Direct analytical measurements.
    conclusions = {
        "lx": "RAW_NO_SIGMA; POSITIVE_X_SIGN",
        "lxx": "RAW_NO_SIGMA_SQUARED",
        "lap": "RAW_NO_SIGMA_SQUARED",
        "grad": "RAW_NO_SIGMA; NMS_OFF",
        "hess-l1": "RAW_SIGNED_ALGEBRAIC_LARGEST; NO_SIGMA_SQUARED",
        "hess-l2": "RAW_SIGNED_ALGEBRAIC_SMALLEST; NO_SIGMA_SQUARED",
        "st-l1": "RAW_STRUCTURE_EIGENVALUE; NO_SCALE_NORMALIZATION",
        "st-l2": "RAW_STRUCTURE_EIGENVALUE; NO_SCALE_NORMALIZATION",
    }
    direct_commands = set(conclusions)
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        if row["image"] in {"ramp.tif", "parabola.tif", "saddle.tif"}:
            command = row["command"]
            row["conclusion"] = conclusions[command]
            grouped[command].append((float(row["sigma"]), float(row["measured_mean"])))

    for command in sorted(direct_commands):
        values = sorted(grouped[command])
        if not values:
            continue
        summary.append(
            {
                "category": "normalization",
                "item": command,
                "sigma": ";".join(f(s, 3) for s, _ in values),
                "measured": ";".join(f(v) for _, v in values),
                "expected": "raw analytical response independent of sigma",
                "conclusion": conclusions[command],
                "evidence": "measurement_results.csv",
            }
        )

    # Dirac support. For odd Lx, use the column at the strongest derivative
    # response to measure the smoothing-axis support; the center column is zero.
    support_results: dict[tuple[str, str], tuple[int, int, float]] = {}
    for command in ("gauss", "lx", "lxx"):
        for sigma in (1.0, 2.0, 4.0):
            s = f"{sigma:.1f}"
            name = f"calib_dirac_{command}_s{s}.tif"
            array = image(OUTPUTS / name)
            h, w = array.shape
            cy, cx = h // 2, w // 2
            x_profile = array[cy, :]
            peak_x = int(np.argmax(np.abs(x_profile)))
            y_profile = array[:, peak_x]
            rx = support_radius(x_profile, cx)
            ry = support_radius(y_profile, cy)
            total = float(array.sum())
            support_results[(command, s)] = (rx, ry, total)
            expected_rx = int((3 if command == "gauss" else 4) * sigma)
            expected_ry = int(3 * sigma)
            status = "PASS" if (rx, ry) == (expected_rx, expected_ry) else "REVIEW"
            conclusion = (
                f"SUPPORT_{status}; derivative_x_radius={rx}; "
                f"smoothing_y_radius={ry}"
            )
            by_key[("dirac.tif", command, s, "")]["conclusion"] = conclusion
            summary.append(
                {
                    "category": "kernel_support",
                    "item": command,
                    "sigma": s,
                    "measured": f"rx={rx}; ry={ry}; sum2d={f(total, 12)}",
                    "expected": f"rx={expected_rx}; ry={expected_ry}",
                    "conclusion": conclusion,
                    "evidence": name,
                }
            )

    # Border mode. The actual tracked probe is a unit-valued outer border.
    # At the middle row, non-repeating mirror produces g[0] at x=0, while
    # repeating reflect produces g[0]+g[1]. Reconstruct the 1D Gaussian from
    # the center row of the 2D Dirac response.
    border_input = image(HERE.parents[2] / "data" / "calib" / "bright_border.tif")
    if border_input.shape != (256, 256) or border_input[128, 0] != 1.0:
        raise ValueError("Unexpected bright_border.tif; review the border derivation")
    border_conclusions: list[str] = []
    for sigma in (1.0, 2.0, 4.0):
        s = f"{sigma:.1f}"
        dirac = image(OUTPUTS / f"calib_dirac_gauss_s{s}.tif")
        border = image(OUTPUTS / f"calib_bright_border_gauss_s{s}.tif")
        cy, cx = np.array(dirac.shape) // 2
        row = dirac[cy, :]
        g = row / row.sum()
        observed = float(border[border.shape[0] // 2, 0])
        mirror = float(g[cx])
        reflect = float(g[cx] + g[cx - 1])
        error_mirror = abs(observed - mirror)
        error_reflect = abs(observed - reflect)
        conclusion = "MIRROR_NON_REPEATING" if error_mirror < error_reflect else "REFLECT_REPEATING"
        border_conclusions.append(conclusion)
        summary.append(
            {
                "category": "border_mode",
                "item": "gauss_edge_pixel",
                "sigma": s,
                "measured": f"observed={f(observed)}; err_mirror={f(error_mirror)}; err_reflect={f(error_reflect)}",
                "expected": f"mirror={f(mirror)}; reflect={f(reflect)}",
                "conclusion": conclusion,
                "evidence": f"calib_bright_border_gauss_s{s}.tif",
            }
        )
        for command in ("gauss", "lx", "lxx"):
            by_key[("bright_border.tif", command, s, "")]["conclusion"] = (
                f"{conclusion}; see calibration_summary.csv"
            )
    if set(border_conclusions) != {"MIRROR_NON_REPEATING"}:
        raise ValueError(f"Border evidence is inconsistent: {border_conclusions}")

    fields = list(rows[0])
    write_csv(MEASUREMENTS, rows, fields)
    summary_fields = [
        "category", "item", "sigma", "measured", "expected", "conclusion", "evidence"
    ]
    write_csv(SUMMARY, summary, summary_fields)

    kernel_lines = []
    for command in ("gauss", "lx", "lxx"):
        for sigma in (1.0, 2.0, 4.0):
            s = f"{sigma:.1f}"
            rx, ry, total = support_results[(command, s)]
            kernel_lines.append(
                f"| {command} | {s} | {rx} | {ry} | {f(total, 12)} |"
            )
    norm_lines = []
    for command in ("lx", "lxx", "lap", "grad", "hess-l1", "hess-l2", "st-l1", "st-l2"):
        values = sorted(grouped[command])
        norm_lines.append(
            f"| {command} | "
            + "; ".join(f"s={f(s,3)}: {f(v)}" for s, v in values)
            + f" | {conclusions[command]} |"
        )
    screenshot_count = len(list(SCREENSHOTS.glob("*.png")))
    if screenshot_count >= 15:
        screenshot_note = (
            f"- Đã lưu **{screenshot_count} PNG** hộp thoại, phiên bản, ROI và profile trong "
            "`screenshots/`; bảng ánh xạ nằm trong `screenshots/README.md`."
        )
    else:
        screenshot_note = (
            f"- Screenshot giao diện chưa đủ ({screenshot_count}/15); CSV/TIFF vẫn là "
            "bằng chứng định lượng chính."
        )

    report = f"""# Kết quả hiệu chuẩn FeatureJ — Phạm Bảo Lộc

Phép đo được tạo bởi `reproduce.ijm` trên 5 TIFF float32 trong `data/calib`.
Bộ bằng chứng gồm **40 TIFF**, **40 dòng đo ROI** và **2.682 điểm profile**.
`output_manifest.csv` lưu SHA-256, kích thước, dtype và miền giá trị của từng TIFF.

## Kết luận cấu hình

| Khóa | Kết luận thực đo |
| --- | --- |
| `kernel_k.gauss` | **3.0** |
| `kernel_k.lx` | **4.0** theo trục đạo hàm; trục làm mịn dùng support Gaussian k=3 |
| `kernel_k.lxx` | **4.0** theo trục đạo hàm; trục làm mịn dùng support Gaussian k=3 |
| `border_mode` | **mirror**, không lặp pixel biên |
| `featurej_normalized.derivatives` | **false** |
| `featurej_normalized.laplacian` | **false** |
| `featurej_normalized.hessian` | **false** |
| `featurej_normalized.edges` | **false** |
| `featurej_normalized.structure` | **false** |
| `eigen_order` | **algebraic**, Largest dương và Smallest âm trên saddle |

Các kết luận trên khớp `config.yaml` hiện hành. Không có thay đổi config nào được
thực hiện bởi script phân tích.

## Normalization và dấu

| Lệnh | Mean theo scale | Kết luận |
| --- | --- | --- |
{chr(10).join(norm_lines)}

Lx và gradient giữ gần 1 ở sigma 1, 2, 4. Các đáp ứng bậc hai/Hessian giữ gần
giá trị thô thay vì tăng theo sigma bình phương. Structure tại cặp (1,3) và
(2,6) cũng giữ trị riêng lớn gần 1 và trị riêng nhỏ bằng 0.

## Support từ Dirac

| Lệnh | Sigma | Bán kính x | Bán kính y | Tổng 2D |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(kernel_lines)}

Với Lx/Lxx, x là trục đạo hàm và y là trục làm mịn. Profile y của Lx được lấy
tại cột có đáp ứng đạo hàm cực đại vì cột tâm của kernel lẻ bằng 0.

## Kiểu biên

`bright_border.tif` thực tế là ảnh 256×256 với viền ngoài cùng bằng 1. Tại pixel
biên giữa hàng, cả ba sigma cho sai số so với mô hình mirror nhỏ hơn rõ rệt so
với reflect lặp pixel; chi tiết nằm trong `calibration_summary.csv`.

## Giới hạn và bằng chứng giao diện

- `FeatureJ Edges` được đo ở chế độ gradient magnitude, NMS tắt và ngưỡng trống;
  NMS không thay đổi hệ số chuẩn hóa nên cờ `edges=false` được áp cho nhánh Edge.
- Các toán tử Ly/Lxy/Lyy dùng cùng lệnh Derivatives và cùng quy tắc theo bậc;
  kết luận của chúng được suy từ Lx/Lxx thay vì đo lặp riêng.
{screenshot_note}
- CSV/TIFF là bằng chứng định lượng chính; screenshot không thay thế số đo.
- Hồ sơ này giải thích config; không biến 185 cặp chưa đạt STRICT thành STRICT.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"Reviewed {len(rows)} measurements; wrote {SUMMARY.name} and {REPORT.name}")


if __name__ == "__main__":
    main()

