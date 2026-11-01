"""Module tính toán ma trận Hessian và nghiệm đóng trị riêng (Eigenvalues) 2D.

Ma trận Hessian đối xứng:
H = [[Lxx, Lxy],
     [Lxy, Lyy]]

Nghiệm đóng giải tích không cần lặp ma trận (cực nhanh và chính xác):
Tr(H) = Lxx + Lyy
Det(H) = Lxx * Lyy - Lxy^2
R = sqrt((Lxx - Lyy)^2 + 4 * Lxy^2)

lambda_plus = 0.5 * (Tr(H) + R)
lambda_minus = 0.5 * (Tr(H) - R)

Hỗ trợ 2 chế độ sắp xếp dựa theo config:
- 'algebraic': lambda_1 >= lambda_2 (theo đại số có dấu).
- 'absolute':  |lambda_1| >= |lambda_2| (theo độ lớn tuyệt đối).
"""

from typing import Optional, Tuple
import numpy as np
from src.config import get_eigen_order
from src.core.derivatives import compute_derivatives_2nd


def compute_hessian_matrix(
    img: np.ndarray,
    sigma: float,
    k: Optional[float] = None,
    mode: Optional[str] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
  """Tính 3 thành phần của ma trận Hessian 2D: (Lxx, Lyy, Lxy)."""
  return compute_derivatives_2nd(img, sigma=sigma, k=k, mode=mode)


def compute_hessian_eigenvalues(
    lxx: np.ndarray,
    lyy: np.ndarray,
    lxy: np.ndarray,
    sort_order: Optional[str] = None,
) -> Tuple[np.ndarray, np.ndarray]:
  """Tính 2 trị riêng của ma trận Hessian theo công thức giải tích nghiệm đóng.

  Args:
      lxx, lyy, lxy: Các thành phần đạo hàm bậc 2.
      sort_order: 'algebraic' (đại số: l1 >= l2) hoặc 'absolute' (độ lớn tuyệt
        đối: |l1| >= |l2|). Nếu None, đọc từ config.yaml.

  Returns:
      (lambda_1, lambda_2): Hai mảng trị riêng cùng kích thước với lxx.
  """
  if sort_order is None:
    sort_order = get_eigen_order(strict=False)
  sort_order = sort_order.lower().strip()

  trace = lxx + lyy
  # Biệt thức delta = (lxx - lyy)^2 + 4*lxy^2 >= 0 luôn không âm
  radius = np.sqrt((lxx - lyy) ** 2 + 4.0 * (lxy**2))

  lambda_plus = 0.5 * (trace + radius)
  lambda_minus = 0.5 * (trace - radius)

  if sort_order == "algebraic":
    # lambda_plus >= lambda_minus
    return lambda_plus, lambda_minus
  elif sort_order == "absolute":
    # |lambda_1| >= |lambda_2|
    mask = np.abs(lambda_minus) > np.abs(lambda_plus)
    lambda_1 = np.where(mask, lambda_minus, lambda_plus)
    lambda_2 = np.where(mask, lambda_plus, lambda_minus)
    return lambda_1, lambda_2
  else:
    raise ValueError(
        f"Chế độ sắp xếp trị riêng không hỗ trợ: {sort_order}. Chỉ hỗ trợ"
        " 'algebraic' hoặc 'absolute'."
    )


def compute_hessian_determinant(lxx: np.ndarray, lyy: np.ndarray, lxy: np.ndarray) -> np.ndarray:
  """Tính định thức ma trận Hessian (Determinant of Hessian - DoH).

  DoH = Lxx * Lyy - Lxy^2
  Dùng trong phát hiện đốm/blob đa tỷ lệ.
  """
  return lxx * lyy - (lxy**2)
