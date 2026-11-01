"""Module cài đặt tích chập tách rời 2D (Separable Convolution) thuần NumPy (From Scratch).

Tuyệt đối không dùng scipy.ndimage.convolve trong luồng tính toán cốt lõi.
Ánh xạ chính xác điều kiện biên theo định nghĩa SciPy:
- 'reflect': Pixel biên bị lặp lại (d c b a | a b c d | d c b a) -> ánh xạ sang np.pad(mode='symmetric').
- 'mirror':  Pixel biên không lặp lại (d c b | a b c d | c b a) -> ánh xạ sang np.pad(mode='reflect').
"""

from typing import Optional
import numpy as np
from src.config import get_border_mode


def convolve_1d(
    img: np.ndarray,
    kernel: np.ndarray,
    axis: int = 0,
    mode: Optional[str] = None,
) -> np.ndarray:
  """Tích chập 1D trên mảng 2D dọc theo một trục xác định.

  Args:
      img: Mảng ảnh 2D (float64).
      kernel: Mảng kernel 1D độ dài lẻ (float64).
      axis: 0 (dọc - theo hàng) hoặc 1 (ngang - theo cột).
      mode: 'reflect' hoặc 'mirror' theo định nghĩa SciPy. Nếu None, đọc từ
        config.

  Returns:
      Mảng ảnh 2D sau tích chập, cùng kích thước với img.
  """
  if img.ndim != 2:
    raise ValueError(f"convolve_1d chỉ hỗ trợ ảnh 2D, nhận được ndim={img.ndim}")
  if kernel.ndim != 1:
    raise ValueError(
        f"kernel phải là mảng 1D, nhận được ndim={kernel.ndim}"
    )
  if len(kernel) % 2 == 0:
    raise ValueError(f"Độ dài kernel phải là số lẻ, nhận được len={len(kernel)}")

  if mode is None:
    mode = get_border_mode(strict=False)
  mode = mode.lower().strip()

  # Ánh xạ thuật ngữ SciPy sang chế độ np.pad của NumPy
  if mode == "reflect":
    np_mode = "symmetric"  # Pixel biên bị lặp
  elif mode == "mirror":
    np_mode = "reflect"  # Pixel biên không bị lặp
  else:
    raise ValueError(
        f"Chế độ biên không hỗ trợ: {mode}. Chỉ hỗ trợ 'reflect' hoặc 'mirror'."
    )

  r = len(kernel) // 2
  pad_width = ((r, r), (0, 0)) if axis == 0 else ((0, 0), (r, r))
  padded = np.pad(img, pad_width, mode=np_mode)

  # Định nghĩa tích chập: (I * K)(i) = sum_j I(i - j) * K(j) = sum_j I(i + j) * K(-j)
  kernel_flipped = kernel[::-1]
  out = np.zeros_like(img, dtype=np.float64)
  h, w = img.shape

  if axis == 0:
    for m in range(len(kernel)):
      out += kernel_flipped[m] * padded[m : m + h, :]
  else:
    for m in range(len(kernel)):
      out += kernel_flipped[m] * padded[:, m : m + w]

  return out


def separable_convolve_2d(
    img: np.ndarray,
    kernel_x: np.ndarray,
    kernel_y: np.ndarray,
    mode: Optional[str] = None,
) -> np.ndarray:
  """Tích chập tách rời 2D: kernel_x theo chiều ngang (axis=1), kernel_y theo chiều dọc (axis=0).

  Lưu ý:
  - kernel_x tác động dọc theo các cột (horizontal / x / axis=1).
  - kernel_y tác động dọc theo các hàng (vertical / y / axis=0).
  """
  # Tích chập theo hàng (axis=1) với kernel_x
  temp = convolve_1d(img, kernel_x, axis=1, mode=mode)
  # Tích chập theo cột (axis=0) với kernel_y
  result = convolve_1d(temp, kernel_y, axis=0, mode=mode)
  return result
