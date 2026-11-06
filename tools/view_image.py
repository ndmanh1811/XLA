"""
view_image.py - CÔNG CỤ XEM ẢNH KHOA HỌC ĐA ĐỊNH DẠNG (.tif, .mat, .png)
Dành cho: Mọi thành viên trong nhóm và Trưởng nhóm

Cách dùng:
1. Xem một file cụ thể:
   python view_image.py outputs/python/py_drive_01_hess-l1_s4.0.tif
2. Chạy không kèm tham số (sẽ hiện cửa sổ chọn tệp):
   python view_image.py
"""

import sys
import os
from pathlib import Path
import numpy as np
import tifffile
import matplotlib.pyplot as plt
from PIL import Image

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def load_any_image(file_path: Path):
    """Đọc ảnh từ nhiều định dạng: TIFF 32-bit float, MAT, PNG, JPG."""
    ext = file_path.suffix.lower()
    
    if ext in [".tif", ".tiff"]:
        data = tifffile.imread(str(file_path))
        return data
    elif ext == ".mat":
        import scipy.io
        mat = scipy.io.loadmat(str(file_path))
        # Tìm mảng 2D đầu tiên có trong mat
        for k, v in mat.items():
            if isinstance(v, np.ndarray) and v.ndim == 2:
                return v
        # Nếu là groundTruth của BSDS500
        if 'groundTruth' in mat:
            gt_cell = mat['groundTruth']
            # Ghép tất cả biên của annotator lại
            boundaries = [gt_cell[0][a]['Boundaries'][0, 0] for a in range(len(gt_cell[0]))]
            return np.any(np.stack(boundaries, axis=0) > 0, axis=0).astype(np.float32)
        raise ValueError(f"Không tìm thấy mảng ảnh 2D trong tệp .mat: {file_path}")
    elif ext in [".png", ".jpg", ".jpeg", ".bmp"]:
        img = Image.open(file_path)
        return np.array(img)
    else:
        raise ValueError(f"Định dạng chưa được hỗ trợ: {ext}")

def display_image(file_path: Path):
    if not file_path.exists():
        print(f"[!] Không tìm thấy tệp: {file_path}")
        return
        
    data = load_any_image(file_path)
    
    print("\n" + "=" * 60)
    print(f"  THÔNG TIN TỆP: {file_path.name}")
    print("=" * 60)
    print(f"  - Đường dẫn: {file_path.resolve()}")
    print(f"  - Kích thước: {data.shape[1]} (rộng) x {data.shape[0]} (cao)")
    print(f"  - Kiểu dữ liệu: {data.dtype}")
    print(f"  - Giá trị nhỏ nhất (Min): {np.min(data):.4f}")
    print(f"  - Giá trị lớn nhất (Max): {np.max(data):.4f}")
    print(f"  - Giá trị trung bình (Mean): {np.mean(data):.4f}")
    print("=" * 60)
    
    # Chọn bảng màu thông minh:
    # Nếu có cả giá trị âm và dương (đạo hàm Lx, Lxx, trị riêng Hessian) -> dùng bảng màu phân kỳ coolwarm
    # Nếu chỉ có giá trị dương -> dùng inferno hoặc gray
    is_signed = (np.min(data) < -1e-5) and (np.max(data) > 1e-5)
    
    plt.figure(figsize=(9, 7))
    if is_signed:
        # Cân bằng dải màu quanh số 0
        v_abs_max = max(abs(np.min(data)), abs(np.max(data)))
        im = plt.imshow(data, cmap="coolwarm", vmin=-v_abs_max, vmax=v_abs_max)
        cbar = plt.colorbar(im)
        cbar.set_label("Biên độ vi phân (Xanh: Âm | Đỏ: Dương)", rotation=270, labelpad=15)
    else:
        im = plt.imshow(data, cmap="inferno" if data.ndim == 2 else None)
        if data.ndim == 2:
            cbar = plt.colorbar(im)
            cbar.set_label("Cường độ sáng", rotation=270, labelpad=15)
            
    plt.title(f"{file_path.name}\n(Min: {np.min(data):.3f}, Max: {np.max(data):.3f}, Kích thước: {data.shape[1]}x{data.shape[0]})", fontsize=11)
    plt.axis("off")
    plt.tight_layout()
    
    print("-> Đang mở cửa sổ hiển thị ảnh... (Đóng cửa sổ để kết thúc)")
    plt.show()

def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        display_image(path)
    else:
        # Nếu không truyền file, mở hộp thoại chọn tệp
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw() # Ẩn cửa sổ chính
        
        initial_dir = Path(__file__).resolve().parent / "outputs" / "python"
        if not initial_dir.exists():
            initial_dir = Path(__file__).resolve().parent
            
        file_selected = filedialog.askopenfilename(
            title="Chọn tệp ảnh cần xem (.tif, .mat, .png, .jpg)",
            initialdir=str(initial_dir),
            filetypes=[
                ("Tất cả định dạng hỗ trợ", "*.tif;*.tiff;*.mat;*.png;*.jpg"),
                ("Ảnh khoa học TIFF (.tif)", "*.tif;*.tiff"),
                ("Dữ liệu MATLAB (.mat)", "*.mat"),
                ("Ảnh thông thường (.png, .jpg)", "*.png;*.jpg"),
                ("Tất cả tệp", "*.*")
            ]
        )
        
        if file_selected:
            display_image(Path(file_selected))
        else:
            print("Chưa chọn tệp nào. Bạn có thể truyền trực tiếp đường dẫn, ví dụ:")
            print("python view_image.py outputs/python/py_drive_01_hess-l1_s4.0.tif")

if __name__ == "__main__":
    main()
