"""Module tính toán các đạo hàm Gaussian đa tỷ lệ (Linear Scale-space Derivatives).

Cung cấp:
- Gaussian smoothing (bậc 0).
- Đạo hàm bậc 1: Lx, Ly.
- Gradient magnitude: ||∇L|| = sqrt(Lx^2 + Ly^2).
- Đạo hàm bậc 2: Lxx, Lyy, Lxy.
- Laplacian of Gaussian: ∇^2 L = Lxx + Lyy.

Quy ước trục:
- Trục x là cột (horizontal / axis=1).
- Trục y là hàng (vertical / axis=0).
"""

from typing import Optional, Tuple
import numpy as np
from src.config import get_kernel_k
from src.core.convolution import separable_convolve_2d
from src.core.kernel import get_gaussian_kernel_1d


def gaussian_smooth(
    img: np.ndarray,
    sigma: float,
    k: Optional[float] = None,
    mode: Optional[str] = None,
) -> np.ndarray:
  """Làm mịn ảnh bằng bộ lọc Gaussian tách rời 2D (bậc 0 theo x và bậc 0 theo y)."""
  k0 = k if k is not None else get_kernel_k(0)
  g0 = get_gaussian_kernel_1d(sigma, order=0, k=k0)
  return separable_convolve_2d(img, kernel_x=g0, kernel_y=g0, mode=mode)


def compute_derivatives_1st(
    img: np.ndarray,
    sigma: float,
    k: Optional[float] = None,
    mode: Optional[str] = None,
) -> Tuple[np.ndarray, np.ndarray]:
  """Tính đạo hàm Gaussian bậc 1: (Lx, Ly).

  - Lx: g1 (bậc 1) theo chiều ngang (axis=1), g0 (bậc 0) theo chiều dọc (axis=0).
  - Ly: g0 (bậc 0) theo chiều ngang (axis=1), g1 (bậc 1) theo chiều dọc (axis=0).
  """
  k0 = k if k is not None else get_kernel_k(0)
  k1 = k if k is not None else get_kernel_k(1)
  g0 = get_gaussian_kernel_1d(sigma, order=0, k=k0)
  g1 = get_gaussian_kernel_1d(sigma, order=1, k=k1)

  lx = separable_convolve_2d(img, kernel_x=g1, kernel_y=g0, mode=mode)
  ly = separable_convolve_2d(img, kernel_x=g0, kernel_y=g1, mode=mode)
  return lx, ly


def compute_gradient_magnitude(lx: np.ndarray, ly: np.ndarray) -> np.ndarray:
  """Tính độ lớn Gradient: ||∇L|| = sqrt(Lx^2 + Ly^2)."""
  return np.sqrt(lx * lx + ly * ly)


def compute_derivatives_2nd(
    img: np.ndarray,
    sigma: float,
    k: Optional[float] = None,
    mode: Optional[str] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
  """Tính đạo hàm Gaussian bậc 2: (Lxx, Lyy, Lxy).

  - Lxx: g2 (bậc 2) theo chiều ngang (axis=1), g0 (bậc 0) theo chiều dọc (axis=0).
  - Lyy: g0 (bậc 0) theo chiều ngang (axis=1), g2 (bậc 2) theo chiều dọc (axis=0).
  - Lxy: g1 (bậc 1) theo chiều ngang (axis=1), g1 (bậc 1) theo chiều dọc (axis=0).
  """
  k0 = k if k is not None else get_kernel_k(0)
  k1 = k if k is not None else get_kernel_k(1)
  k2 = k if k is not None else get_kernel_k(2)
  g0 = get_gaussian_kernel_1d(sigma, order=0, k=k0)
  g1 = get_gaussian_kernel_1d(sigma, order=1, k=k1)
  g2 = get_gaussian_kernel_1d(sigma, order=2, k=k2)

  lxx = separable_convolve_2d(img, kernel_x=g2, kernel_y=g0, mode=mode)
  lyy = separable_convolve_2d(img, kernel_x=g0, kernel_y=g2, mode=mode)
  lxy = separable_convolve_2d(img, kernel_x=g1, kernel_y=g1, mode=mode)
  return lxx, lyy, lxy


def compute_laplacian(
    img: np.ndarray,
    sigma: float,
    k: Optional[float] = None,
    mode: Optional[str] = None,
) -> np.ndarray:
  """Tính toán tử Laplacian of Gaussian (LoG): ∇^2 L = Lxx + Lyy."""
  lxx, lyy, _ = compute_derivatives_2nd(img, sigma=sigma, k=k, mode=mode)
  return lxx + lyy
