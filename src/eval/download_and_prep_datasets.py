"""
download_and_prep_datasets.py - Tự động thu thập và tiền xử lý 25 ảnh thực tế (Tier 2 Dataset)
Dành cho: Bùi Trung Đức (Role 1) & Trưởng nhóm nghiệm thu sớm

Bộ dữ liệu chuẩn gồm:
1. 10 ảnh BSDS500 (Berkeley Segmentation Dataset): Chuyển xám theo ITU-R BT.601, kèm Ground Truth đa annotator.
2. 10 ảnh DRIVE (Retinal Vessel Extraction): Trích xuất kênh Green 8-bit uint8, kèm Ground Truth mạch máu & mặt nạ FOV.
3. 5 ảnh Blob (Đốm đa tỷ lệ): Tổng hợp đốm Gaussian chính xác theo lưới tỷ lệ đề tài, kèm Ground Truth tọa độ và bán kính.
"""

import sys
import json
import io
from pathlib import Path
import numpy as np
import requests
import certifi
from PIL import Image
from huggingface_hub import hf_hub_download
import scipy.io

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / "data" / "raw"
GT_DIR = ROOT / "data" / "gt"

RAW_DIR.mkdir(parents=True, exist_ok=True)
GT_DIR.mkdir(parents=True, exist_ok=True)

# 10 ID ảnh BSDS500 tiêu biểu từ tập Test
BSDS_IDS = [
    "100007", "100039", "100099", "10081", "101027",
    "101084", "102062", "103006", "103029", "103078"
]

# 10 ID ảnh DRIVE từ tập Train (21 đến 30)
DRIVE_IDS = [f"{i}" for i in range(21, 31)]

def download_bsds500():
    print("\n--- 1. ĐANG TẢI & TIỀN XỬ LÝ 10 ẢNH BSDS500 (EDGE DETECTION) ---")
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for idx, img_id in enumerate(BSDS_IDS, start=1):
        name = f"bsds_{idx:02d}"
        img_out = RAW_DIR / f"{name}.png"
        gt_out = GT_DIR / f"{name}_gt.mat"
        
        print(f"[{idx}/10] Đang tải ảnh BSDS {img_id} -> {name}...")
        
        # 1. Tải ảnh gốc JPG từ GitHub BIDS mirror
        img_url = f"https://raw.githubusercontent.com/BIDS/BSDS500/master/BSDS500/data/images/test/{img_id}.jpg"
        r_img = requests.get(img_url, headers=headers, verify=certifi.where())
        if r_img.status_code != 200:
            print(f"   [LỖI] Không tải được ảnh {img_id}: HTTP {r_img.status_code}")
            continue
            
        # Tiền xử lý: chuyển sang xám 8-bit theo ITU-R BT.601: 0.299*R + 0.587*G + 0.114*B
        pil_img = Image.open(io.BytesIO(r_img.content)).convert("RGB")
        arr = np.array(pil_img)
        gray = np.round(0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]).astype(np.uint8)
        
        # Lưu lossless PNG 8-bit
        Image.fromarray(gray).save(img_out)
        
        # 2. Tải file Ground Truth .mat
        gt_url = f"https://raw.githubusercontent.com/BIDS/BSDS500/master/BSDS500/data/groundTruth/test/{img_id}.mat"
        r_gt = requests.get(gt_url, headers=headers, verify=certifi.where())
        if r_gt.status_code == 200:
            gt_out.write_bytes(r_gt.content)
            
            # Trích xuất thêm file npy chứa các mặt nạ biên của các người gán nhãn
            mat = scipy.io.loadmat(io.BytesIO(r_gt.content))
            gt_cell = mat['groundTruth']
            num_annotators = len(gt_cell[0])
            boundaries = [gt_cell[0][a]['Boundaries'][0, 0].astype(np.uint8) for a in range(num_annotators)]
            np.save(GT_DIR / f"{name}_boundaries.npy", np.stack(boundaries, axis=0))
            print(f"   -> Đã lưu {name}.png ({gray.shape[1]}x{gray.shape[0]}) kèm {num_annotators} bản gán nhãn biên.")
        else:
            print(f"   [CẢNH BÁO] Không tải được GT cho {img_id}")

def download_drive():
    print("\n--- 2. ĐANG TẢI & TIỀN XỬ LÝ 10 ẢNH DRIVE (RETINAL VESSEL EXTRACTION) ---")
    for idx, drive_id in enumerate(DRIVE_IDS, start=1):
        name = f"drive_{idx:02d}"
        img_out = RAW_DIR / f"{name}.png"
        vessel_out = GT_DIR / f"{name}_vessels.png"
        fov_out = GT_DIR / f"{name}_fov.png"
        
        print(f"[{idx}/10] Đang tải ảnh DRIVE {drive_id} -> {name}...")
        
        # 1. Tải ảnh gốc TIFF từ Hugging Face
        file_path = hf_hub_download(
            repo_id="Zomba/DRIVE-digital-retinal-images-for-vessel-extraction",
            filename=f"train/input/{drive_id}.tif",
            repo_type="dataset"
        )
        pil_img = Image.open(file_path).convert("RGB")
        arr = np.array(pil_img)
        
        # Trích xuất riêng kênh Green (kênh có độ tương phản mạch máu cao nhất)
        green_channel = arr[:, :, 1].astype(np.uint8)
        Image.fromarray(green_channel).save(img_out)
        
        # 2. Tải nhãn chuyên gia (Vessel Ground Truth)
        label_path = hf_hub_download(
            repo_id="Zomba/DRIVE-digital-retinal-images-for-vessel-extraction",
            filename=f"train/label/{drive_id}.png",
            repo_type="dataset"
        )
        vessel_mask = Image.open(label_path).convert("L")
        vessel_mask.save(vessel_out)
        
        # 3. Tạo mặt nạ FOV (Field Of View - vùng võng mạc tròn, loại bỏ viền đen)
        # Nền đen ngoài nhãn cầu có giá trị rất nhỏ (<= 10)
        fov_mask = ((arr[:, :, 0] > 10) | (arr[:, :, 1] > 10) | (arr[:, :, 2] > 10)).astype(np.uint8) * 255
        Image.fromarray(fov_mask).save(fov_out)
        
        print(f"   -> Đã lưu {name}.png ({green_channel.shape[1]}x{green_channel.shape[0]}), kênh Green uint8 + FOV mask.")

def generate_blobs():
    print("\n--- 3. ĐANG TẠO 5 ẢNH ĐỐM BLOB THEO ĐÚNG LƯỚI TỶ LỆ QUY ƯỚC ---")
    # Lưới tỷ lệ chuẩn: sigmas = [1.0, 1.4, 2.0, 2.8, 4.0, 5.7, 8.0]
    # Bán kính giải tích r = sigma * sqrt(2) ≈ [1.4, 2.0, 2.8, 4.0, 5.7, 8.0, 11.3]
    rng = np.random.default_rng(2026)
    size = 256
    y, x = np.mgrid[:size, :size]
    
    for idx in range(1, 6):
        name = f"blob_{idx:02d}"
        img_out = RAW_DIR / f"{name}.png"
        gt_out = GT_DIR / f"{name}_gt.json"
        
        canvas = np.zeros((size, size), dtype=np.float64)
        gt_blobs = []
        
        # Số lượng đốm mỗi ảnh: 6-10 đốm đa kích thước
        sigmas = [1.4, 2.0, 2.8, 4.0, 5.7, 8.0]
        # Tạo lưới các vị trí không đè lên nhau
        positions = [
            (50, 50), (50, 130), (50, 200),
            (130, 60), (130, 140), (130, 210),
            (200, 50), (200, 130), (200, 200)
        ]
        
        polarity = "bright" if idx <= 3 else "dark"
        base_val = 0.0 if polarity == "bright" else 1.0
        canvas.fill(base_val)
        
        for p_idx, (cy, cx) in enumerate(positions[:len(sigmas)]):
            s = sigmas[p_idx % len(sigmas)]
            r = s * np.sqrt(2.0)
            d2 = (x - cx)**2 + (y - cy)**2
            spot = np.exp(-d2 / (2.0 * s**2))
            
            if polarity == "bright":
                canvas += spot * 0.9
            else:
                canvas -= spot * 0.9
                
            gt_blobs.append({
                "y": int(cy),
                "x": int(cx),
                "sigma": float(s),
                "radius": float(r),
                "polarity": polarity
            })
            
        # Thêm nhiễu Gaussian nhẹ 1% mô phỏng tế bào
        canvas += rng.normal(0, 0.01, canvas.shape)
        canvas = np.clip(canvas, 0.0, 1.0)
        img_uint8 = (canvas * 255.0).round().astype(np.uint8)
        
        Image.fromarray(img_uint8).save(img_out)
        with open(gt_out, "w", encoding="utf-8") as f:
            json.dump({"blobs": gt_blobs, "polarity": polarity}, f, indent=2)
            
        print(f"   -> Đã tạo {name}.png ({polarity}, {len(gt_blobs)} đốm chuẩn, r={sigmas[0]*1.414:.1f}px -> {sigmas[-1]*1.414:.1f}px)")

def main():
    print("=" * 70)
    print("  KHỞI CHẠY THU THẬP BỘ DỮ LIỆU ĐẦY ĐỦ 25 ẢNH CHO ĐỀ TÀI (TIER 2)")
    print("=" * 70)
    
    download_bsds500()
    download_drive()
    generate_blobs()
    
    raw_files = list(RAW_DIR.glob("*.png"))
    gt_files = list(GT_DIR.glob("*"))
    print("\n" + "=" * 70)
    print(f"  TỔNG KẾT: Đã hoàn tất thu thập {len(raw_files)}/25 ảnh vào data/raw/")
    print(f"  Kèm {len(gt_files)} tệp nhãn Ground Truth tương ứng vào data/gt/")
    print("=" * 70)

if __name__ == "__main__":
    main()
