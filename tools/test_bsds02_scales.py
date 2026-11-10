"""
test_bsds02_scales.py - Thử nghiệm đa tỷ lệ (Multi-scale Canny) trên ảnh bsds_02 (Con vật trên khúc cây)
Mục đích: Chứng minh khi tăng sigma (kính lúp lớn hơn), các vết sần sùi của vỏ cây
          sẽ bị triệt tiêu hoàn toàn, làm nổi bật đường viền thân con vật và cành cây
          giống hệt như cách con người nhìn nhận.
"""

import sys
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.derivatives import compute_derivatives_1st
from src.core.detectors import detect_canny

def main():
    print("=" * 65)
    print("  THỬ NGHIỆM ĐA TỶ LỆ CANNY TRÊN ẢNH BSDS_02 (CON VẬT TRÊN CÀNH CÂY)")
    print("=" * 65)
    
    img_path = ROOT / "data/raw/bsds_02.png"
    gt_path = ROOT / "data/gt/bsds_02_boundaries.npy"
    
    img_raw = np.array(Image.open(img_path))
    img_float = img_raw.astype(np.float64) / 255.0
    gt_boundaries = np.load(gt_path)
    gt_union = np.any(gt_boundaries > 0, axis=0)
    
    # Thử 3 mức scale: nhỏ (chi tiết), vừa, và lớn (khung hình chính)
    scales = [1.2, 2.5, 4.0]
    results = []
    
    for s in scales:
        print(f"-> Đang chạy Canny ở sigma = {s:.1f}...")
        lx, ly = compute_derivatives_1st(img_float, sigma=s)
        # Chuẩn hóa gamma=1 (nhân s^1)
        edge = detect_canny(s * lx, s * ly, p_low=55.0, p_high=82.0)
        results.append((s, edge))
        
    # Tạo bảng hiển thị 2 hàng x 3 cột
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle("MINH HỨNG SỨC MẠNH CỦA KHÔNG GIAN TỶ LỆ (SCALE-SPACE): TĂNG SIGMA ĐỂ LỌC VỎ CÂY SẦN SÙI", 
                 fontsize=14, fontweight='bold')
    
    # Ô 1: Ảnh gốc
    axes[0, 0].imshow(img_raw, cmap='gray')
    axes[0, 0].set_title("1. Ảnh gốc bsds_02\n(Con chuột/sóc trên khúc cây sần sùi)", fontsize=11, fontweight='bold', color='navy')
    axes[0, 0].axis('off')
    
    # Ô 2: Canny sigma = 1.2 (cũ)
    axes[0, 1].imshow(results[0][1], cmap='gray')
    axes[0, 1].set_title("2. Canny ở σ = 1.2 (Kính lúp nhỏ)\n(Bắt cả vết nứt nẻ sần sùi của vỏ cây)", fontsize=11, fontweight='bold', color='darkorange')
    axes[0, 1].axis('off')
    
    # Ô 3: Canny sigma = 2.5 (vừa)
    axes[0, 2].imshow(results[1][1], cmap='gray')
    axes[0, 2].set_title("3. Canny ở σ = 2.5 (Làm mịn vỏ cây)\n(Vỏ cây biến mất dần, hiện rõ dáng con vật)", fontsize=11, fontweight='bold', color='darkblue')
    axes[0, 2].axis('off')
    
    # Ô 4: Canny sigma = 4.0 (lớn)
    axes[1, 0].imshow(results[2][1], cmap='gray')
    axes[1, 0].set_title("4. Canny ở σ = 4.0 (Kính lúp lớn)\n(Lọc sạch vỏ cây! Hiện viền thân chuột & cành cây)", fontsize=11, fontweight='bold', color='darkred')
    axes[1, 0].axis('off')
    
    # Ô 5: Đáp án chuyên gia con người
    axes[1, 1].imshow(gt_union, cmap='gray')
    axes[1, 1].set_title("5. Đáp án chuẩn Ground Truth\n(Con người chỉ vẽ khung con vật và cành cây)", fontsize=11, fontweight='bold', color='darkgreen')
    axes[1, 1].axis('off')
    
    # Ô 6: Ghép nét Canny (sigma=4.0) màu đỏ đè lên ảnh gốc
    overlay = np.stack([img_raw, img_raw, img_raw], axis=-1)
    mask_edges = results[2][1] > 0
    overlay[mask_edges, 0] = 255
    overlay[mask_edges, 1] = 0
    overlay[mask_edges, 2] = 0
    axes[1, 2].imshow(overlay)
    axes[1, 2].set_title("6. Nét viền đỏ (σ = 4.0) ôm khít trên ảnh gốc\n(Thấy rõ đường viền sống lưng, đầu chuột & cành)", fontsize=11, fontweight='bold', color='purple')
    axes[1, 2].axis('off')
    
    plt.tight_layout()
    out_file = ROOT / "outputs" / "bsds02_multiscale_comparison.png"
    plt.savefig(out_file, dpi=200, bbox_inches='tight')
    plt.close()
    
    print(f"\n=> [THÀNH CÔNG] Đã lưu kết quả thử nghiệm tại: {out_file}")
    print("=" * 65)

if __name__ == "__main__":
    main()
