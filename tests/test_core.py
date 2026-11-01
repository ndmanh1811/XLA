"""Unit test suite kiểm thử toàn diện module src.core:

1. Kernel Gaussian 1D: bảo toàn moment giải tích cho bậc 0, 1, 2.
2. Tích chập tách rời 2D: so sánh đối chuẩn với scipy.ndimage (sai số < 1e-14).
3. Kiểm chứng giải tích trên ảnh đa thức:
   - Ảnh dốc I = x: Lx = 1.0, Ly = 0.0.
   - Ảnh parabol I = x^2/2: Lxx = 1.0, Lyy = 0.0, Lxy = 0.0.
   - Ảnh yên ngựa I = x^2/2 - y^2: Hessian diag(1, -2).
4. Structure Tensor: Trị riêng mu1, mu2 và Coherence.
5. Các hàm dò: Canny, Frangi, Blob.
"""

import numpy as np
from src.core.convolution import convolve_1d, separable_convolve_2d
from src.core.derivatives import (
    compute_derivatives_1st,
    compute_derivatives_2nd,
    compute_gradient_magnitude,
    compute_laplacian,
    gaussian_smooth,
)
from src.core.detectors import detect_blob, detect_canny, detect_ridge
from src.core.hessian import (
    compute_hessian_determinant,
    compute_hessian_eigenvalues,
)
from src.core.kernel import get_gaussian_kernel_1d
from src.core.structure_tensor import (
    compute_structure_coherence,
    compute_structure_tensor,
    compute_structure_tensor_eigenvalues,
)


def test_kernel_moments():
  """Kiểm tra tính chất bảo toàn moment giải tích của kernel 1D."""
  for sigma in [1.0, 2.0, 4.0]:
    # Bậc 0: tổng bằng 1.0
    g0 = get_gaussian_kernel_1d(sigma, order=0)
    assert np.isclose(np.sum(g0), 1.0, atol=1e-14)

    # Bậc 1: sum(x * g1) = -1.0 và sum(g1) = 0.0
    g1 = get_gaussian_kernel_1d(sigma, order=1)
    r = len(g1) // 2
    x = np.arange(-r, r + 1, dtype=np.float64)
    assert np.isclose(np.sum(g1), 0.0, atol=1e-14)
    assert np.isclose(np.sum(x * g1), -1.0, atol=1e-14)

    # Bậc 2: sum(x^2 * g2) = 2.0 và sum(g2) = 0.0
    g2 = get_gaussian_kernel_1d(sigma, order=2)
    r2 = len(g2) // 2
    x2 = np.arange(-r2, r2 + 1, dtype=np.float64)
    assert np.isclose(np.sum(g2), 0.0, atol=1e-14)
    assert np.isclose(np.sum((x2**2) * g2), 2.0, atol=1e-14)


def test_convolution_vs_scipy():
  """So sánh tích chập tự cài đặt với scipy.ndimage.convolve1d (đảm bảo sai số < 1e-14)."""
  import scipy.ndimage as ndi

  np.random.seed(42)
  img = np.random.randn(64, 64)
  kernel = np.array([0.05, 0.25, 0.4, 0.25, 0.05])

  for mode in ["reflect", "mirror"]:
    for axis in [0, 1]:
      res_custom = convolve_1d(img, kernel, axis=axis, mode=mode)
      res_scipy = ndi.convolve1d(img, kernel, axis=axis, mode=mode)
      diff = np.max(np.abs(res_custom - res_scipy))
      assert diff < 1e-14, (
          f"Lệch với SciPy tại mode={mode}, axis={axis}: diff={diff}"
      )


def test_analytical_polynomials():
  """Kiểm chứng giải tích trên ảnh dốc I = x, parabol I = x^2/2 và yên ngựa I = x^2/2 - y^2."""
  n = 256
  coords = np.arange(-n // 2, n // 2, dtype=np.float64)
  x, y = np.meshgrid(coords, coords)  # x: axis=1 (cột), y: axis=0 (hàng)

  sigma = 2.0
  r = int(np.ceil(4.0 * sigma))

  # 1. Ảnh dốc I = x
  lx, ly = compute_derivatives_1st(x, sigma=sigma)
  core_lx = lx[r:-r, r:-r]
  core_ly = ly[r:-r, r:-r]
  assert np.allclose(core_lx, 1.0, atol=1e-12)
  assert np.allclose(core_ly, 0.0, atol=1e-12)

  # 2. Ảnh parabol I = x^2 / 2
  i_parabol = (x**2) / 2.0
  lxx, lyy, lxy = compute_derivatives_2nd(i_parabol, sigma=sigma)
  core_lxx = lxx[r:-r, r:-r]
  core_lyy = lyy[r:-r, r:-r]
  core_lxy = lxy[r:-r, r:-r]
  assert np.allclose(core_lxx, 1.0, atol=1e-12)
  assert np.allclose(core_lyy, 0.0, atol=1e-12)
  assert np.allclose(core_lxy, 0.0, atol=1e-12)

  # 3. Ảnh yên ngựa I = x^2 / 2 - y^2 (Hessian diag(1, -2))
  i_saddle = (x**2) / 2.0 - (y**2)
  s_lxx, s_lyy, s_lxy = compute_derivatives_2nd(i_saddle, sigma=sigma)
  core_s_lxx = s_lxx[r:-r, r:-r]
  core_s_lyy = s_lyy[r:-r, r:-r]
  core_s_lxy = s_lxy[r:-r, r:-r]
  assert np.allclose(core_s_lxx, 1.0, atol=1e-12)
  assert np.allclose(core_s_lyy, -2.0, atol=1e-12)
  assert np.allclose(core_s_lxy, 0.0, atol=1e-12)

  # Kiểm tra sắp xếp trị riêng
  # (a) algebraic: lambda_1 >= lambda_2 -> lambda_1 = +1.0, lambda_2 = -2.0
  l1_alg, l2_alg = compute_hessian_eigenvalues(
      core_s_lxx, core_s_lyy, core_s_lxy, sort_order="algebraic"
  )
  assert np.allclose(l1_alg, 1.0, atol=1e-12)
  assert np.allclose(l2_alg, -2.0, atol=1e-12)

  # (b) absolute: |lambda_1| >= |lambda_2| -> lambda_1 = -2.0, lambda_2 = +1.0
  l1_abs, l2_abs = compute_hessian_eigenvalues(
      core_s_lxx, core_s_lyy, core_s_lxy, sort_order="absolute"
  )
  assert np.allclose(l1_abs, -2.0, atol=1e-12)
  assert np.allclose(l2_abs, 1.0, atol=1e-12)


def test_structure_tensor():
  """Kiểm tra Structure Tensor trên trường gradient không đổi."""
  n = 128
  coords = np.arange(-n // 2, n // 2, dtype=np.float64)
  x, y = np.meshgrid(coords, coords)
  # Ảnh dốc góc 45 độ: I = 3*x + 4*y -> Lx = 3, Ly = 4 -> ||grad||^2 = 25
  img = 3.0 * x + 4.0 * y

  j11, j22, j12 = compute_structure_tensor(img, sigma_d=1.0, sigma_i=3.0)
  mu1, mu2 = compute_structure_tensor_eigenvalues(j11, j22, j12)
  coherence = compute_structure_coherence(mu1, mu2)

  # Trong vùng lõi
  core_mu1 = mu1[20:-20, 20:-20]
  core_mu2 = mu2[20:-20, 20:-20]
  core_coh = coherence[20:-20, 20:-20]

  assert np.allclose(core_mu1, 25.0, atol=1e-10)
  assert np.allclose(core_mu2, 0.0, atol=1e-10)
  assert np.allclose(core_coh, 1.0, atol=1e-6)


def test_detectors_smoke():
  """Smoke test cho 3 hàm dò mức cao (Canny, Frangi, Blob)."""
  # 1. Canny
  lx = np.zeros((50, 50))
  ly = np.zeros((50, 50))
  lx[:, 25] = 100.0  # Cạnh dọc ở cột 25
  edge = detect_canny(lx, ly, p_low=50.0, p_high=80.0)
  assert edge[25, 25] == 255

  # 2. Ridge (Frangi)
  l1 = np.full((30, 30), 2.0)
  l2 = np.full((30, 30), 0.05)
  vesselness = detect_ridge(l1, l2, polarity="dark")
  assert np.all(vesselness > 0.5)

  # 3. Blob LoG
  sigmas = [1.0, 1.4, 2.0, 2.8, 4.0]
  stack = np.zeros((5, 40, 40))
  # Tạo cực tiểu LoG (đốm sáng) tại scale 2 (sigma=2.0) ở tâm (20, 20)
  stack[2, 20, 20] = -10.0
  blobs = detect_blob(stack, sigmas, polarity="bright", threshold=1.0)
  assert len(blobs) >= 1
  assert blobs[0][0] == 20 and blobs[0][1] == 20
  assert np.isclose(blobs[0][2], 2.0)
