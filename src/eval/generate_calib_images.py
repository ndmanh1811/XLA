"""Script tạo sẵn bộ ảnh hiệu chuẩn (Calibration Images) lưu vào data/calib/

Bao gồm:
1. ramp.tif: Ảnh dốc I(x, y) = x (256x256, gốc tại tâm [-128, 127], TIFF 32-bit float).
   Dùng để kiểm tra: cờ tự nhân sigma của Derivatives (Lx = 1 hay sigma) và dấu trục (+1).
2. parabol.tif: Ảnh parabol I(x, y) = x^2 / 2 (256x256, gốc tại tâm, TIFF 32-bit float).
   Dùng để kiểm tra: cờ tự nhân sigma^2 của Laplacian và Hessian (Lxx = 1 hay sigma^2).
3. saddle.tif: Ảnh yên ngựa I(x, y) = x^2 / 2 - y^2 (256x256, gốc tại tâm, TIFF 32-bit float).
   Dùng để phân biệt: thứ tự trị riêng Hessian là đại số (1, -2) hay trị tuyệt đối (-2, 1).
4. dirac.tif: Ảnh xung Dirac delta (101x101, pixel tâm = 1.0, TIFF 32-bit float).
   Dùng để đo bán kính cắt k = r/sigma và so sánh profile trọng số kernel với Gaussian giải tích.
5. bright_border.tif: Ảnh có viền sáng (101x101, TIFF 32-bit float).
   Dùng để đo kiểu xử lý biên: lặp pixel (reflect) hay không lặp (mirror).
"""

from pathlib import Path
import sys
import numpy as np
import tifffile

sys.stdout.reconfigure(encoding="utf-8")

CALIB_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "calib"


def generate_all_calib_images():
  CALIB_DIR.mkdir(parents=True, exist_ok=True)
  print(f"Bắt đầu tạo ảnh hiệu chuẩn tại: {CALIB_DIR}")

  # 1. Ảnh đa thức kích thước 256x256, gốc tọa độ đặt tại tâm
  n = 256
  coords = np.arange(-n // 2, n // 2, dtype=np.float32)
  x, y = np.meshgrid(coords, coords)  # x: cột (axis=1), y: hàng (axis=0)

  # (a) Ramp: I = x
  ramp = x.astype(np.float32)
  tifffile.imwrite(CALIB_DIR / "ramp.tif", ramp)
  print("[OK] Tạo data/calib/ramp.tif (256x256, float32)")

  # (b) Parabol: I = x^2 / 2
  parabol = ((x**2) / 2.0).astype(np.float32)
  tifffile.imwrite(CALIB_DIR / "parabol.tif", parabol)
  print("[OK] Tạo data/calib/parabol.tif (256x256, float32)")

  # (c) Saddle: I = x^2 / 2 - y^2
  saddle = ((x**2) / 2.0 - (y**2)).astype(np.float32)
  tifffile.imwrite(CALIB_DIR / "saddle.tif", saddle)
  print("[OK] Tạo data/calib/saddle.tif (256x256, float32)")

  # 2. Ảnh xung Dirac delta 101x101
  n_dirac = 101
  dirac = np.zeros((n_dirac, n_dirac), dtype=np.float32)
  dirac[n_dirac // 2, n_dirac // 2] = 1.0
  tifffile.imwrite(CALIB_DIR / "dirac.tif", dirac)
  print("[OK] Tạo data/calib/dirac.tif (101x101, pixel tâm = 1.0)")

  # 3. Ảnh có viền sáng 101x101 (để đo phản xạ biên reflect vs mirror)
  border_img = np.zeros((n_dirac, n_dirac), dtype=np.float32)
  # Đặt viền ngoài cùng bằng 100.0, các pixel bên trong giảm dần
  border_img[0, :] = 100.0
  border_img[-1, :] = 100.0
  border_img[:, 0] = 100.0
  border_img[:, -1] = 100.0
  border_img[1, 1:-1] = 50.0
  border_img[-2, 1:-1] = 50.0
  border_img[1:-1, 1] = 50.0
  border_img[1:-1, -2] = 50.0
  tifffile.imwrite(CALIB_DIR / "bright_border.tif", border_img)
  print("[OK] Tạo data/calib/bright_border.tif (101x101)")

  print("=" * 60)
  print("HOÀN TẤT TẠO 5 ẢNH HIỆU CHUẨN TRONG data/calib/!")
  print("=" * 60)


if __name__ == "__main__":
  generate_all_calib_images()
