"""Module quản lý và kiểm tra cấu hình tập trung cho toàn bộ dự án.

Đọc các thông số đo đạc thực nghiệm từ `config.yaml`.
Nếu các giá trị đo từ FeatureJ chưa được điền (còn null), module hỗ trợ:
1. Chế độ nghiêm ngặt (strict=True): Báo lỗi AssertionError yêu cầu chạy đo calib trước.
2. Chế độ kiểm thử/mặc định (strict=False): Sử dụng giá trị dự phòng chuẩn lý thuyết (k=4.0, mode='reflect')
   để Người phụ trách Lập trình Python có thể code và unit test độc lập ngay từ hôm nay.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config() -> Dict[str, Any]:
  """Đọc toàn bộ file config.yaml."""
  if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"Không tìm thấy file cấu hình tại {CONFIG_PATH}")
  with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)
  return cfg or {}


def get_kernel_k(order: int = 0, strict: bool = True) -> float:
  """Lấy hệ số bán kính cắt kernel k = r / sigma cho từng bậc đạo hàm.

  Args:
      order: Bậc đạo hàm (0: gauss, 1: lx/ly, 2: lxx/lyy/lxy).
      strict: Nếu True, bắt buộc giá trị trong config.yaml không được null.

  Returns:
      Hệ số k (float).
  """
  cfg = load_config()
  k_map = cfg.get("kernel_k", {})
  key = {0: "gauss", 1: "lx", 2: "lxx"}.get(order, "gauss")
  val = k_map.get(key)

  if val is None:
    if strict:
      raise AssertionError(
          f"Thông số kernel_k['{key}'] trong config.yaml còn 'null'. "
          "Người phụ trách Fiji cần hoàn tất đo calib trước khi khóa code!"
      )
    # Giá trị mặc định lý thuyết trong lúc code độc lập:
    return 4.0
  return float(val)


def get_border_mode(strict: bool = True) -> str:
  """Lấy kiểu xử lý biên ('reflect' hoặc 'mirror' theo định nghĩa SciPy)."""
  cfg = load_config()
  mode = cfg.get("border_mode")
  if mode is None:
    if strict:
      raise AssertionError(
          "Thông số border_mode trong config.yaml còn 'null'. "
          "Người phụ trách Fiji cần xác định kiểu biên trên ảnh viền sáng!"
      )
    return "reflect"
  return str(mode).strip().lower()


def is_featurej_normalized(command: str, strict: bool = True) -> bool:
  """Kiểm tra xem lệnh FeatureJ tương ứng đã tự động nhân sigma^n hay chưa.

  Args:
      command: Tên lệnh ('derivatives', 'laplacian', 'hessian', 'edges',
        'structure').
  """
  cfg = load_config()
  norm_map = cfg.get("featurej_normalized", {})
  val = norm_map.get(command.lower())
  if val is None:
    if strict:
      raise AssertionError(
          f"Cờ featurej_normalized['{command}'] trong config.yaml còn 'null'. "
          "Cần đo giải tích trên ảnh dốc/parabol trước!"
      )
    return False
  return bool(val)


def get_eigen_order(strict: bool = True) -> str:
  """Lấy quy tắc sắp xếp trị riêng Hessian: 'algebraic' hay 'absolute'."""
  cfg = load_config()
  order = cfg.get("eigen_order")
  if order is None:
    if strict:
      raise AssertionError(
          "Thông số eigen_order trong config.yaml còn 'null'. "
          "Cần đo trên ảnh yên ngựa I = x^2/2 - y^2 trước!"
      )
    return "absolute"
  return str(order).strip().lower()


def get_sigmas() -> List[float]:
  """Lấy danh sách sigma tổng quát: [1.0, 2.0, 4.0, 8.0]."""
  cfg = load_config()
  return [float(s) for s in cfg.get("sigmas", [1.0, 2.0, 4.0, 8.0])]


def get_blob_sigmas() -> List[float]:
  """Lấy lưới sigma dày cho blob: [1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0]."""
  cfg = load_config()
  return [
      float(s)
      for s in cfg.get(
          "sigmas_blob", [1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0]
      )
  ]


def get_structure_pairs() -> List[Tuple[float, float]]:
  """Lấy các cặp tỷ lệ Structure Tensor: [(1.0, 3.0), (2.0, 6.0)]."""
  cfg = load_config()
  pairs = cfg.get("structure_pairs", [[1.0, 3.0], [2.0, 6.0]])
  return [(float(p[0]), float(p[1])) for p in pairs]


def get_tier1_images() -> List[str]:
  """Lấy danh sách 5 ảnh đại diện dùng cho Tầng 1."""
  cfg = load_config()
  return cfg.get(
      "tier1_images",
      ["bsds_01", "bsds_02", "drive_01", "blob_01", "blob_02"],
  )
