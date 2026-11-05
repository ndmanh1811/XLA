"""
generate_albatross_comparison.py - Tạo ảnh đối chiếu chuyên sâu cho ảnh chim hải âu (bsds_09)
so sánh kết quả dò biên Canny (Python Core from scratch) với Ground Truth (8 người gán nhãn BSDS500).
"""

import sys
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from scipy.ndimage import binary_dilation

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.core.derivatives import compute_derivatives_1st, compute_gradient_magnitude
from src.core.detectors import detect_canny

def run_albatross_comparison():
    img_path = ROOT / "data" / "raw" / "bsds_09.png"
    gt_path = ROOT / "data" / "gt" / "bsds_09_boundaries.npy"

    if not img_path.exists() or not gt_path.exists():
        print("[!] Không tìm thấy dữ liệu ảnh hoặc GT của bsds_09!")
        return

    # 1. Đọc ảnh và Ground Truth
    img_gray = np.array(Image.open(img_path).convert("L"), dtype=np.float64) / 255.0
    gt_all = np.load(gt_path) # shape: (8, H, W)
    num_annotators = gt_all.shape[0]

    # Bản đồ xác suất biên (tỉ lệ người đồng thuận vẽ đường biên đó)
    gt_prob = np.mean(gt_all > 0, axis=0)
    union_gt = np.any(gt_all > 0, axis=0)

    # 2. Chạy thuật toán Canny của nhóm (sigma = 2.0, chuẩn hóa Lindeberg gamma=1)
    sigma = 2.0
    lx, ly = compute_derivatives_1st(img_gray, sigma=sigma)
    lx_norm = (sigma ** 1.0) * lx
    ly_norm = (sigma ** 1.0) * ly
    grad_mag = compute_gradient_magnitude(lx_norm, ly_norm)

    # Dò biên Canny với phân vị p_low=55, p_high=85
    pred_edges = detect_canny(lx_norm, ly_norm, p_low=55.0, p_high=85.0, return_binary=False)

    # 3. Tính toán các chỉ số định lượng (Precision, Recall, F1 với dung sai 2px)
    struct_2px = np.ones((5, 5), dtype=bool)
    dilated_union_gt = binary_dilation(union_gt, structure=struct_2px)

    pred_pos = np.sum(pred_edges)
    tp = np.sum(pred_edges & dilated_union_gt)
    precision = float(tp / pred_pos) if pred_pos > 0 else 0.0

    dilated_pred = binary_dilation(pred_edges, structure=struct_2px)
    recs = [np.sum((gt_all[i] > 0) & dilated_pred) / np.sum(gt_all[i] > 0) for i in range(num_annotators)]
    recall = float(np.mean(recs))
    f1 = float((2 * precision * recall) / (precision + recall + 1e-10))

    print(f"=== ĐÁNH GIÁ SỐ HỌC ẢNH HẢI ÂU (bsds_09) ===")
    print(f"-> Độ chính xác (Precision): {precision * 100:.2f}%")
    print(f"-> Độ bao phủ (Recall):      {recall * 100:.2f}%")
    print(f"-> Điểm hài hòa (F1-Score):  {f1:.3f}")

    # 4. Vẽ bảng ảnh ghép đối chiếu 2x3 (300 DPI)
    fig, axes = plt.subplots(2, 3, figsize=(16, 10), dpi=300)
    plt.subplots_adjust(wspace=0.08, hspace=0.18)

    # (a) Ảnh gốc
    axes[0, 0].imshow(img_gray, cmap="gray")
    axes[0, 0].set_title("(a) Ảnh gốc BSDS500 (bsds_09.png)\nKích thước: 481 x 321 px", fontsize=11, fontweight="bold")
    axes[0, 0].axis("off")

    # (b) Độ lớn Gradient
    im1 = axes[0, 1].imshow(grad_mag, cmap="inferno")
    axes[0, 1].set_title(r"(b) Độ lớn Gradient $\sqrt{L_x^2 + L_y^2}$" + f"\n(Lindeberg $\sigma={sigma:.1f}$)", fontsize=11, fontweight="bold")
    axes[0, 1].axis("off")
    fig.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)

    # (c) Ground Truth (Đồng thuận 8 người gán nhãn)
    im2 = axes[0, 2].imshow(gt_prob, cmap="jet")
    axes[0, 2].set_title(f"(c) Ground Truth chuẩn (BSDS500)\nĐồng thuận từ {num_annotators} chuyên gia vẽ tay", fontsize=11, fontweight="bold")
    axes[0, 2].axis("off")
    cbar2 = fig.colorbar(im2, ax=axes[0, 2], fraction=0.046, pad=0.04)
    cbar2.set_label("Tỉ lệ đồng thuận (0.0 -> 1.0)", fontsize=9)

    # (d) Biên Canny phát hiện
    axes[1, 0].imshow(pred_edges, cmap="gray")
    axes[1, 0].set_title(f"(d) Biên Canny tự động (NumPy Core)\n{pred_pos} pixels biên sau NMS & Hysteresis", fontsize=11, fontweight="bold")
    axes[1, 0].axis("off")

    # (e) Ảnh phủ màu trực quan (Overlay)
    overlay_rgb = np.stack([img_gray, img_gray, img_gray], axis=-1)
    # Tô màu xanh lá dạ quang cho biên Canny
    overlay_rgb[pred_edges] = [0.0, 1.0, 0.2]
    axes[1, 1].imshow(overlay_rgb)
    axes[1, 1].set_title(f"(e) Phủ màu trực quan (Overlay)\nBiên Canny xanh lá ôm khít thân chim", fontsize=11, fontweight="bold")
    axes[1, 1].axis("off")

    # (f) Bản đồ đối chiếu sai số chi tiết (Error Analysis Map)
    # Nền xám
    err_rgb = np.stack([img_gray * 0.4, img_gray * 0.4, img_gray * 0.4], axis=-1)
    # True Positives: Màu Xanh lá (Khớp Ground Truth)
    matched_mask = pred_edges & dilated_union_gt
    # False Positives: Màu Đỏ (Biên nền cỏ/lông chim)
    fp_mask = pred_edges & ~dilated_union_gt
    # False Negatives: Màu Cyan (Ground Truth mà máy chưa bắt)
    fn_mask = union_gt & ~dilated_pred

    err_rgb[fn_mask] = [0.0, 0.6, 1.0]     # Xanh dương: GT người vẽ
    err_rgb[fp_mask] = [1.0, 0.2, 0.2]     # Đỏ: False Positive
    err_rgb[matched_mask] = [0.0, 1.0, 0.0] # Xanh lá: Khớp chính xác (True Positive)

    axes[1, 2].imshow(err_rgb)
    axes[1, 2].set_title(f"(f) Bản đồ đối chiếu định lượng\nPrec={precision*100:.1f}%, Rec={recall*100:.1f}% => F1={f1:.3f}", fontsize=11, fontweight="bold")
    axes[1, 2].axis("off")

    # Chú thích góc dưới
    plt.suptitle("KẾT QUẢ THỰC NGHIỆM ĐỐI CHUẨN: CANNY EDGE DETECTION vs GROUND TRUTH (BSDS500)", fontsize=14, fontweight="bold", y=0.98)
    
    out_file = ROOT / "outputs" / "bsds09_albatross_groundtruth_comparison.png"
    plt.savefig(out_file, bbox_inches="tight")
    plt.close()
    print(f"[OK] Đã tạo thành công ảnh ghép đối chiếu: {out_file.name}")

if __name__ == "__main__":
    run_albatross_comparison()
