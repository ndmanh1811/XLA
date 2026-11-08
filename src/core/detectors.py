"""Module chứa 3 thuật toán phát hiện đặc trưng mức cao (High-level Feature Detectors):

1. detect_canny(lx, ly, p_low, p_high):
   - Nhận đạo hàm Lx, Ly.
   - Non-Maximum Suppression (NMS) theo hướng gradient (4 khu vực góc: 0, 45, 90, 135 độ).
   - Ngưỡng trễ Hysteresis dựa trên phân vị (percentile p_low, p_high) của độ lớn gradient.

2. detect_ridge(hess_l1, hess_l2, sigma, beta=0.5, c=None, polarity='dark'):
   - Nhận 2 trị riêng của Hessian.
   - TỰ ĐỘNG sắp xếp lại theo độ lớn tuyệt đối |l1| >= |l2| bên trong hàm để chống lỗi đảo thứ tự.
   - Bộ lọc Frangi Vesselness 2D:
     Rb = |l2 / l1|
     S = sqrt(l1^2 + l2^2)
     V = exp(-Rb^2 / (2*beta^2)) * (1 - exp(-S^2 / (2*c^2)))
   - Cực tính: 'dark' (mạch máu DRIVE tối hơn nền -> giữ l1 > 0), 'bright' (giữ l1 < 0).

3. detect_blob(laplacian_scale_stack, sigmas, polarity='bright', threshold=None):
   - Nhận chồng bản đồ Laplacian đã nhân chuẩn hóa sigma^2 qua các thang tỷ lệ (shape: [num_scales, H, W]).
   - Cực tính: 'bright' (đốm sáng là cực tiểu địa phương của sigma^2 * ∇^2 L), 'dark' (cực đại).
   - Tìm cực trị địa phương trong lân cận 3x3x3 không gian tỷ lệ (scale-space extrema).
"""

from typing import List, Optional, Tuple, Union
import numpy as np


def canny_nms(lx: np.ndarray, ly: np.ndarray) -> np.ndarray:
  """Tính edge strength sau Non-Maximum Suppression (NMS).

  NMS chỉ phụ thuộc vào ``lx`` và ``ly``, không phụ thuộc ngưỡng. Tách riêng
  bước này cho phép quét lưới ngưỡng trên cùng một lần tính NMS, thay vì tính
  lại NMS cho từng cặp ``(p_low, p_high)``.

  Args:
      lx: Mảng đạo hàm theo cột (axis=1).
      ly: Mảng đạo hàm theo hàng (axis=0).

  Returns:
      Mảng cùng kích thước với ``lx``; giá trị 0 tại pixel không phải cực đại
      địa phương theo hướng gradient.
  """
  magnitude = np.sqrt(lx * lx + ly * ly)
  h, w = magnitude.shape

  # Hướng gradient góc theta = arctan2(Ly, Lx) theo độ trong dải [0, 180)
  angle_rad = np.arctan2(ly, lx)
  angle_deg = np.rad2deg(angle_rad) % 180.0

  # 1. Non-Maximum Suppression (NMS)
  pad_m = np.pad(magnitude, 1, mode="constant", constant_values=0)

  # Phân vùng 4 hướng:
  # Sector 0 (ngang: [0, 22.5) hoặc [157.5, 180]) -> kiểm tra láng giềng trái-phải (cột)
  sec0 = ((angle_deg >= 0) & (angle_deg < 22.5)) | (
      (angle_deg >= 157.5) & (angle_deg <= 180.0)
  )
  # Sector 45 (đường chéo góc 45 độ) -> kiểm tra góc trên-phải (y-1, x+1) và dưới-trái (y+1, x-1)
  sec45 = (angle_deg >= 22.5) & (angle_deg < 67.5)
  # Sector 90 (dọc: [67.5, 112.5)) -> kiểm tra láng giềng trên-dưới (hàng)
  sec90 = (angle_deg >= 67.5) & (angle_deg < 112.5)
  # Sector 135 (đường chéo góc 135 độ) -> kiểm tra góc trên-trái (y-1, x-1) và dưới-phải (y+1, x+1)
  sec135 = (angle_deg >= 112.5) & (angle_deg < 157.5)

  # Lấy láng giềng từ pad_m (pad_m có kích thước H+2, W+2; tâm tương ứng [1:H+1, 1:W+1])
  n1_0 = pad_m[1 : h + 1, 2 : w + 2]
  n2_0 = pad_m[1 : h + 1, 0:w]

  # Sector 45: gradient hướng Down-Right (+y, +x) và Up-Left (-y, -x)
  n1_45 = pad_m[0:h, 0:w]
  n2_45 = pad_m[2 : h + 2, 2 : w + 2]

  n1_90 = pad_m[0:h, 1 : w + 1]
  n2_90 = pad_m[2 : h + 2, 1 : w + 1]

  # Sector 135: gradient hướng Down-Left (+y, -x) và Up-Right (-y, +x)
  n1_135 = pad_m[0:h, 2 : w + 2]
  n2_135 = pad_m[2 : h + 2, 0:w]

  cond0 = sec0 & (magnitude >= n1_0) & (magnitude >= n2_0)
  cond45 = sec45 & (magnitude >= n1_45) & (magnitude >= n2_45)
  cond90 = sec90 & (magnitude >= n1_90) & (magnitude >= n2_90)
  cond135 = sec135 & (magnitude >= n1_135) & (magnitude >= n2_135)

  return np.where(cond0 | cond45 | cond90 | cond135, magnitude, 0.0)


def hysteresis_from_nms(
    nms: np.ndarray,
    p_low: float = 50.0,
    p_high: float = 80.0,
    return_binary: bool = False,
) -> np.ndarray:
  """Áp ngưỡng trễ phân vị lên edge strength đã NMS.

  Args:
      nms: Edge strength sau NMS (giá trị 0 tại pixel bị loại).
      p_low: Phân vị ngưỡng dưới (0 đến 100).
      p_high: Phân vị ngưỡng trên (0 đến 100).
      return_binary: Nếu True, trả về mảng uint8 (0 và 255); False trả về bool.

  Returns:
      Mặt nạ biên nhị phân.
  """
  non_zero = nms[nms > 0]
  if len(non_zero) == 0:
    return (
        np.zeros_like(nms, dtype=np.uint8)
        if return_binary
        else np.zeros_like(nms, dtype=bool)
    )

  t_high = np.percentile(non_zero, p_high)
  t_low = np.percentile(non_zero, p_low)

  strong_mask = nms >= t_high
  candidate_mask = nms >= t_low

  # Kết nối 8-láng giềng từ các điểm strong đến các điểm candidate bằng thuật toán loang BFS thuần NumPy
  edge_bool = strong_mask.copy()
  queue = list(zip(*np.where(strong_mask)))
  visited = strong_mask.copy()

  h, w = nms.shape
  dys = [-1, -1, -1, 0, 0, 1, 1, 1]
  dxs = [-1, 0, 1, -1, 1, -1, 0, 1]

  while queue:
    cy, cx = queue.pop()
    for dy, dx in zip(dys, dxs):
      ny, nx = cy + dy, cx + dx
      if 0 <= ny < h and 0 <= nx < w:
        if candidate_mask[ny, nx] and not visited[ny, nx]:
          visited[ny, nx] = True
          edge_bool[ny, nx] = True
          queue.append((ny, nx))

  if return_binary:
    return np.where(edge_bool, 255, 0).astype(np.uint8)
  return edge_bool


def detect_canny(
    lx: np.ndarray,
    ly: np.ndarray,
    p_low: float = 50.0,
    p_high: float = 80.0,
    return_binary: bool = True,
) -> np.ndarray:
  """Thuật toán phát hiện biên Canny từ đạo hàm Lx, Ly.

  Args:
      lx: Mảng đạo hàm theo cột (axis=1).
      ly: Mảng đạo hàm theo hàng (axis=0).
      p_low: Phân vị ngưỡng dưới (0 đến 100), ví dụ 50.0.
      p_high: Phân vị ngưỡng trên (0 đến 100), ví dụ 80.0.
      return_binary: Nếu True, trả về mảng uint8 (0 và 255); False trả về bool.

  Returns:
      Mặt nạ biên nhị phân.
  """
  nms = canny_nms(lx, ly)
  return hysteresis_from_nms(
      nms, p_low=p_low, p_high=p_high, return_binary=return_binary
  )


def detect_ridge(
    hess_l1: np.ndarray,
    hess_l2: np.ndarray,
    sigma: Optional[float] = None,
    beta: float = 0.5,
    c: Optional[float] = None,
    polarity: str = "dark",
    threshold: Optional[float] = None,
    mask: Optional[np.ndarray] = None,
) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
  """Bộ lọc Frangi 2D phát hiện đường gờ / vân mạch máu (Ridge / Vesselness).

  TỰ ĐỘNG sắp xếp trị riêng theo độ lớn tuyệt đối |l1| >= |l2| bên trong hàm.

  Args:
      hess_l1, hess_l2: Hai mảng trị riêng của Hessian (đã chuẩn hóa sigma^2).
      sigma: Thang tỷ lệ (nếu cần tham chiếu).
      beta: Tham số nhạy cấu trúc dạng đường (mặc định 0.5).
      c: Tham số độ tương phản cấu trúc. Nếu None, lấy 0.5 * max(S) (hoặc phân vị 99.5% trong mask).
      polarity: 'dark' (mạch máu tối trên nền sáng như DRIVE) hoặc 'bright'.
      threshold: Nếu không None, trả về thêm ảnh nhị phân cắt theo threshold.
      mask: Mặt nạ vùng hợp lệ (ví dụ mặt nạ FOV xói mòn để triệt tiêu biên võng mạc).

  Returns:
      vesselness (mảng float trong khoảng [0, 1]) hoặc (vesselness, binary_mask).
  """
  # 1. Tự động sắp xếp lại trị riêng để |lambda_1| >= |lambda_2|
  mask_swap = np.abs(hess_l2) > np.abs(hess_l1)
  lambda_1 = np.where(mask_swap, hess_l2, hess_l1)
  lambda_2 = np.where(mask_swap, hess_l1, hess_l2)

  # 2. Tính tỉ số Blob-likeness Rb và chuẩn cấu trúc S
  # Rb = |lambda_2 / lambda_1| (càng gần 0 thì càng giống đường thẳng)
  rb = np.abs(lambda_2) / (np.abs(lambda_1) + 1e-10)
  s = np.sqrt(lambda_1**2 + lambda_2**2)

  if c is None:
    if mask is not None:
      s_valid = s[mask]
      max_s = np.percentile(s_valid, 99.5) if len(s_valid) > 0 else 1.0
    else:
      max_s = np.max(s)
    c = 0.5 * max_s if max_s > 1e-10 else 1.0

  term_rb = np.exp(-(rb**2) / (2.0 * (beta**2)))
  term_s = 1.0 - np.exp(-(s**2) / (2.0 * (c**2)))
  vesselness = term_rb * term_s

  # 3. Phân định cực tính (Polarity)
  if polarity.lower() == "dark":
    # Mạch máu tối hơn nền: mặt cắt ngang qua lòng mạch máu là rãnh lõm -> đạo hàm bậc 2 > 0
    vesselness = np.where(lambda_1 > 0, vesselness, 0.0)
  elif polarity.lower() == "bright":
    # Cấu trúc sáng hơn nền -> đạo hàm bậc 2 theo hướng pháp tuyến < 0
    vesselness = np.where(lambda_1 < 0, vesselness, 0.0)
  else:
    raise ValueError(
        f"polarity không hợp lệ: {polarity}. Chỉ hỗ trợ 'dark' hoặc 'bright'."
    )

  if mask is not None:
    vesselness = np.where(mask, vesselness, 0.0)

  if threshold is not None:
    binary_ridge = np.where(vesselness >= threshold, 255, 0).astype(np.uint8)
    return vesselness, binary_ridge

  return vesselness


def detect_blob(
    laplacian_scale_stack: np.ndarray,
    sigmas: List[float],
    polarity: str = "bright",
    threshold: Optional[float] = 0.01,
) -> List[Tuple[int, int, float, float, float]]:
  """Phát hiện đốm/blob bằng cực trị địa phương trong không gian tỷ lệ (Scale-space Extrema).

  Args:
      laplacian_scale_stack: Mảng 3D shape (num_scales, H, W) chứa sigma^2 * ∇^2
        L.
      sigmas: Danh sách các giá trị sigma tương ứng từng lát cắt.
      polarity: 'bright' (đốm sáng là cực tiểu của sigma^2 * ∇^2 L) hoặc 'dark'
        (cực đại).
      threshold: Ngưỡng loại bỏ đáp ứng yếu.

  Returns:
      Danh sách các blob: [(y, x, sigma, radius, response), ...], trong đó
      radius = sigma * sqrt(2).
  """
  if laplacian_scale_stack.ndim != 3:
    raise ValueError("laplacian_scale_stack phải là mảng 3D (num_scales, H, W)")
  num_scales, h, w = laplacian_scale_stack.shape
  if len(sigmas) != num_scales:
    raise ValueError(
        f"Số lượng sigma ({len(sigmas)}) không khớp số lát cắt ({num_scales})"
    )

  # Nếu polarity là 'bright', đốm sáng là cực tiểu của LoG.
  # Để thống nhất tìm cực đại, ta đổi dấu: response = - LoG nếu bright, response = LoG nếu dark.
  if polarity.lower() == "bright":
    response = -laplacian_scale_stack
  elif polarity.lower() == "dark":
    response = laplacian_scale_stack
  else:
    raise ValueError(
        f"polarity không hợp lệ: {polarity}. Chỉ hỗ trợ 'bright' hoặc 'dark'."
    )

  blobs = []

  # Duyệt qua các thang tỷ lệ bên trong (bỏ 2 thang biên scale 0 và num_scales-1)
  for s_idx in range(1, num_scales - 1):
    sigma = sigmas[s_idx]
    radius = sigma * np.sqrt(2.0)

    # Khối lân cận 3x3x3 xung quanh s_idx
    cube = response[s_idx - 1 : s_idx + 2, :, :]
    current_slice = response[s_idx, :, :]

    # Kiểm tra cực đại so với 26 láng giềng
    is_max = np.ones((h, w), dtype=bool)

    for ds in (0, 1, 2):
      for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
          if ds == 1 and dy == 0 and dx == 0:
            continue
          # Trích xuất mảng láng giềng dịch chuyển
          shifted = np.roll(np.roll(cube[ds], -dy, axis=0), -dx, axis=1)
          is_max &= current_slice > shifted

    # Loại bỏ viền ngoài mép ảnh
    border = 2
    is_max[:border, :] = False
    is_max[-border:, :] = False
    is_max[:, :border] = False
    is_max[:, -border:] = False

    if threshold is not None:
      is_max &= current_slice >= threshold

    ys, xs = np.where(is_max)
    for y, x in zip(ys, xs):
      resp_val = float(current_slice[y, x])
      blobs.append((int(y), int(x), float(sigma), float(radius), resp_val))

  return blobs
