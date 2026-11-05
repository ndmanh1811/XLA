"""Script chạy Bước 1 của Smoke Test: Kiểm chứng giải tích trên các ảnh data/calib/.

Đọc các file TIFF 32-bit float từ data/calib/ và kiểm tra:
1. data/calib/ramp.tif: Lx = +1.0, Ly = 0.0 (kiểm tra dấu trục và đạo hàm bậc 1).
2. data/calib/parabol.tif: Lxx = +1.0, Lyy = 0.0, Lxy = 0.0 (kiểm tra đạo hàm bậc 2).
3. data/calib/saddle.tif: Lxx = +1.0, Lyy = -2.0, kiểm tra thứ tự trị riêng Hessian.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import tifffile

sys.stdout.reconfigure(encoding="utf-8")

from src.core.derivatives import (
    compute_derivatives_1st,
    compute_derivatives_2nd,
)
from src.core.hessian import compute_hessian_eigenvalues

CALIB_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "calib"


def run_smoke_test_analytical(sigma: float = 2.0, k: float = 4.0):
  print("=" * 65)
  print(f"BƯỚC 1: KIỂM CHỨNG GIẢI TÍCH TRÊN data/calib/ (sigma={sigma}, k={k})")
  print("=" * 65)

  r = int(np.ceil(k * sigma))

  # 1. Kiểm tra trên ramp.tif
  ramp_path = CALIB_DIR / "ramp.tif"
  if not ramp_path.exists():
    raise FileNotFoundError(f"Chưa có file {ramp_path}")
  ramp = tifffile.imread(ramp_path).astype(np.float64)

  lx, ly = compute_derivatives_1st(ramp, sigma=sigma, k=k)
  core_lx = lx[r:-r, r:-r]
  core_ly = ly[r:-r, r:-r]

  err_lx = np.max(np.abs(core_lx - 1.0))
  err_ly = np.max(np.abs(core_ly - 0.0))
  print(
      f"1. Ảnh dốc ramp.tif (I = x):"
      f"\n   - Mean Lx vùng lõi: {np.mean(core_lx):.10f} (kỳ vọng: +1.0)"
      f"\n   - Sai số cực đại Lx: {err_lx:.2e}"
      f"\n   - Sai số cực đại Ly: {err_ly:.2e}"
  )
  assert err_lx < 1e-10, f"Lx sai lệch quá lớn: {err_lx}"
  assert err_ly < 1e-10, f"Ly sai lệch quá lớn: {err_ly}"
  print("   -> [PASS] Đạo hàm bậc 1 và dấu trục x hoàn toàn chính xác!")

  # 2. Kiểm tra trên parabol.tif
  parabol_path = CALIB_DIR / "parabol.tif"
  parabol = tifffile.imread(parabol_path).astype(np.float64)

  lxx, lyy, lxy = compute_derivatives_2nd(parabol, sigma=sigma, k=k)
  core_lxx = lxx[r:-r, r:-r]
  core_lyy = lyy[r:-r, r:-r]
  core_lxy = lxy[r:-r, r:-r]

  err_lxx = np.max(np.abs(core_lxx - 1.0))
  err_lyy = np.max(np.abs(core_lyy - 0.0))
  err_lxy = np.max(np.abs(core_lxy - 0.0))
  print(
      f"\n2. Ảnh parabol.tif (I = x^2 / 2):"
      f"\n   - Mean Lxx vùng lõi: {np.mean(core_lxx):.10f} (kỳ vọng: +1.0)"
      f"\n   - Sai số cực đại Lxx: {err_lxx:.2e}"
      f"\n   - Sai số cực đại Lyy: {err_lyy:.2e}"
      f"\n   - Sai số cực đại Lxy: {err_lxy:.2e}"
  )
  assert err_lxx < 1e-10, f"Lxx sai lệch: {err_lxx}"
  assert err_lyy < 1e-10, f"Lyy sai lệch: {err_lyy}"
  assert err_lxy < 1e-10, f"Lxy sai lệch: {err_lxy}"
  print("   -> [PASS] Đạo hàm bậc 2 Lxx, Lyy, Lxy hoàn toàn chính xác!")

  # 3. Kiểm tra trên saddle.tif
  saddle_path = CALIB_DIR / "saddle.tif"
  saddle = tifffile.imread(saddle_path).astype(np.float64)

  s_lxx, s_lyy, s_lxy = compute_derivatives_2nd(saddle, sigma=sigma, k=k)
  core_s_lxx = s_lxx[r:-r, r:-r]
  core_s_lyy = s_lyy[r:-r, r:-r]
  core_s_lxy = s_lxy[r:-r, r:-r]

  l1_alg, l2_alg = compute_hessian_eigenvalues(
      core_s_lxx, core_s_lyy, core_s_lxy, sort_order="algebraic"
  )
  l1_abs, l2_abs = compute_hessian_eigenvalues(
      core_s_lxx, core_s_lyy, core_s_lxy, sort_order="absolute"
  )

  print(
      f"\n3. Ảnh yên ngựa saddle.tif (I = x^2 / 2 - y^2):"
      f"\n   - Kỳ vọng Hessian lý thuyết: Lxx = +1.0, Lyy = -2.0, Lxy = 0.0"
      f"\n   - Mean Lxx đo được: {np.mean(core_s_lxx):.10f}"
      f"\n   - Mean Lyy đo được: {np.mean(core_s_lyy):.10f}"
      f"\n   - Chế độ 'algebraic': lambda_1 = {np.mean(l1_alg):.4f}, lambda_2 ="
      f" {np.mean(l2_alg):.4f}"
      f"\n   - Chế độ 'absolute':  lambda_1 = {np.mean(l1_abs):.4f}, lambda_2 ="
      f" {np.mean(l2_abs):.4f}"
  )
  assert np.isclose(np.mean(l1_alg), 1.0) and np.isclose(np.mean(l2_alg), -2.0)
  assert np.isclose(np.mean(l1_abs), -2.0) and np.isclose(np.mean(l2_abs), 1.0)
  print("   -> [PASS] Cả 2 chế độ sắp xếp trị riêng Hessian hoạt động hoàn hảo!")

  print("=" * 65)
  print("KẾT LUẬN: BƯỚC 1 SMOKE TEST GIẢI TÍCH ĐẠT 100%!")
  print("=" * 65)


if __name__ == "__main__":
  run_smoke_test_analytical()
