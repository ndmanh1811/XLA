"""Module tính toán Structure Tensor (Second-moment matrix) 2 tỷ lệ.

Structure Tensor J_rho được định nghĩa:
1. Đạo hàm vi phân ở tỷ lệ sigma_d:
   Lx = I * (dG_{sigma_d} / dx)
   Ly = I * (dG_{sigma_d} / dy)
2. Tích ngoài gradient:
   J0 = [[Lx^2, Lx*Ly],
         [Lx*Ly, Ly^2]]
3. Làm trơn tích phân ở tỷ lệ sigma_i:
   J11 = G_{sigma_i} * (Lx^2)
   J22 = G_{sigma_i} * (Ly^2)
   J12 = G_{sigma_i} * (Lx * Ly)

Do ma trận Structure Tensor nửa xác định dương (Positive Semi-Definite),
2 trị riêng luôn thỏa mãn: mu1 >= mu2 >= 0.

Độ kết hợp cấu trúc (Coherence):
Coherence = (mu1 - mu2) / (mu1 + mu2 + epsilon) với epsilon = 1e-6.
"""

from typing import Optional, Tuple
import numpy as np
from src.core.derivatives import compute_derivatives_1st, gaussian_smooth


def compute_structure_tensor(
    img: np.ndarray,
    sigma_d: float,
    sigma_i: float,
    k: Optional[float] = None,
    mode: Optional[str] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
  """Tính 3 thành phần của ma trận Structure Tensor 2D: (J11, J22, J12).

  Args:
      img: Mảng ảnh 2D (float64).
      sigma_d: Differentiation scale (tỷ lệ đạo hàm vi phân).
      sigma_i: Integration scale (tỷ lệ làm trơn tích phân).
      k: Hệ số cắt kernel.
      mode: Chế độ xử lý biên ('reflect' hoặc 'mirror').

  Returns:
      (J11, J22, J12): Ba mảng thành phần tensor sau làm mịn.
  """
  # 1. Đạo hàm ở thang sigma_d
  lx, ly = compute_derivatives_1st(img, sigma=sigma_d, k=k, mode=mode)

  # 2. Tích ngoài gradient
  lx2 = lx * lx
  ly2 = ly * ly
  lxy = lx * ly

  # 3. Làm mịn ở thang sigma_i
  j11 = gaussian_smooth(lx2, sigma=sigma_i, k=k, mode=mode)
  j22 = gaussian_smooth(ly2, sigma=sigma_i, k=k, mode=mode)
  j12 = gaussian_smooth(lxy, sigma=sigma_i, k=k, mode=mode)

  return j11, j22, j12


def compute_structure_tensor_eigenvalues(
    j11: np.ndarray, j22: np.ndarray, j12: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
  """Tính 2 trị riêng của Structure Tensor: (mu_1, mu_2).

  Luôn đảm bảo mu_1 >= mu_2 >= 0 theo tính chất nửa xác định dương.
  """
  trace = j11 + j22
  radius = np.sqrt((j11 - j22) ** 2 + 4.0 * (j12**2))

  mu_1 = 0.5 * (trace + radius)
  mu_2 = 0.5 * (trace - radius)

  # Cắt giá trị âm cực nhỏ do sai số làm tròn số thực
  mu_1 = np.maximum(mu_1, 0.0)
  mu_2 = np.maximum(mu_2, 0.0)

  return mu_1, mu_2


def compute_structure_coherence(
    mu_1: np.ndarray, mu_2: np.ndarray, epsilon: float = 1e-6
) -> np.ndarray:
  """Tính độ kết hợp cấu trúc (Coherence) trong khoảng [0, 1].

  Coherence = (mu_1 - mu_2) / (mu_1 + mu_2 + epsilon).
  """
  return (mu_1 - mu_2) / (mu_1 + mu_2 + epsilon)
