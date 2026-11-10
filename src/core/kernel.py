"""Module tạo kernel Gaussian 1D giải tích cho bậc 0, bậc 1 và bậc 2.

Đặc điểm toán học:
- Tận dụng tính khả tách (Separability) của bộ lọc Gaussian 2D.
- Bán kính cắt kernel: r = ceil(k * sigma), độ dài kernel K = 2r + 1.
- Chuẩn hóa rời rạc theo Taylor moment để tái lập chính xác đạo hàm trên đa thức:
  + Bậc 0 (Làm mịn): sum(g0) = 1.0 (bảo toàn năng lượng/độ sáng DC).
  + Bậc 1 (Đạo hàm riêng): sum(x * g1) = -1.0 và sum(g1) = 0.0 (tái lập đạo hàm trên hàm dốc I = x).
  + Bậc 2 (Đạo hàm cấp 2): sum(x^2 * g2) = 2.0 và sum(g2) = 0.0 (tái lập đạo hàm trên parabol I = x^2/2).
"""

from typing import Optional
import numpy as np
from src.config import get_kernel_k


def get_gaussian_kernel_1d(
    sigma: float,
    order: int = 0,
    k: Optional[float] = None,
    normalize: bool = True,
) -> np.ndarray:
  """Tạo kernel Gaussian 1D rời rạc cho bậc 0, 1 hoặc 2.

  Args:
      sigma: Độ lệch chuẩn của hàm Gaussian (sigma > 0).
      order: Bậc đạo hàm (0: làm mịn, 1: đạo hàm bậc 1, 2: đạo hàm bậc 2).
      k: Hệ số bán kính cắt (r = ceil(k * sigma)). Nếu None, lấy từ config.
      normalize: Có chuẩn hóa moment rời rạc để triệt tiêu sai số sai phân hay
        không.

  Returns:
      Mảng numpy 1D kiểu float64 có độ dài lẻ K = 2r + 1.
  """
  if sigma <= 0:
    raise ValueError(f"Độ lệch chuẩn sigma phải > 0, nhận được: {sigma}")
  if order not in (0, 1, 2):
    raise ValueError(
        f"Chỉ hỗ trợ bậc đạo hàm order in (0, 1, 2), nhận được: {order}"
    )

  if k is None:
    k = get_kernel_k(order, strict=True)

  radius = int(np.ceil(k * sigma))
  x = np.arange(-radius, radius + 1, dtype=np.float64)

  variance = sigma * sigma
  # Hàm Gaussian cơ bản g0(x)
  g0 = np.exp(-0.5 * (x * x) / variance) / (np.sqrt(2.0 * np.pi) * sigma)

  if order == 0:
    if normalize:
      kernel = g0 / np.sum(g0)
    else:
      kernel = g0

  elif order == 1:
    # Đạo hàm bậc 1 liên tục: g1(x) = - (x / sigma^2) * g0(x)
    g1 = -(x / variance) * g0
    if normalize:
      # Moment chuẩn hóa: sum(x * g1) = -1.0
      moment1 = np.sum(x * g1)
      if abs(moment1) > 1e-15:
        kernel = g1 * (-1.0 / moment1)
      else:
        kernel = g1
    else:
      kernel = g1

  elif order == 2:
    # Đạo hàm bậc 2 liên tục: g2(x) = ((x^2 - sigma^2) / sigma^4) * g0(x)
    g2 = ((x * x - variance) / (variance * variance)) * g0
    if normalize:
      # Đảm bảo tổng bằng 0 tuyệt đối trên kernel rời rạc cắt cụt
      g2 = g2 - np.mean(g2)
      # Moment chuẩn hóa: sum(x^2 * g2) = 2.0
      moment2 = np.sum(x * x * g2)
      if abs(moment2) > 1e-15:
        kernel = g2 * (2.0 / moment2)
      else:
        kernel = g2
    else:
      kernel = g2

  return kernel
