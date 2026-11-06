# PHẢN HỒI KỸ THUẬT & GÓP Ý QUY ƯỚC (COMMITS 05/11 CỦA LỘC)
**Người gửi:** Nguyễn Đức Mạnh (Trưởng nhóm / Role 2 - Lead Developer)  
**Người nhận:** Phạm Bảo Lộc (Role 3 - Fiji / FeatureJ)  
**Thời gian đánh giá:** 22:50 - Ngày 05/11/2026  
**Mục tiêu:** Nhận xét đợt nộp STT 16, đối chiếu quy ước chung và chuẩn bị cho STT 18 (ImageJ Macro)  

---

## 1. Đánh giá chung & Ghi nhận nỗ lực (Khen ngợi)
- **Tiến độ:** Nộp rất đúng hạn (Commit `23a1f9e` lúc 22:22 và `d79ad4b` lúc 22:35 ngày 05/11/2026, đúng deadline STT 16).
- **Chất lượng tài liệu `WORKFLOW_EDGE_RIDGE.docx`:** 
  - Trình bày bài bản, ảnh chụp màn hình từng hộp thoại tham số trong Fiji rất rõ ràng.
  - Nắm đúng cơ chế của FeatureJ: Bật `Suppress non-maximum gradients` để làm mảnh biên, và đặc biệt đã **tắt `Absolute eigenvalue comparison`** để giữ trật tự đại số ($\lambda_1 \ge \lambda_2$) đúng theo cấu hình nhóm đã chốt.
  - Toàn bộ nội dung mô tả thao tác và hình ảnh này là tư liệu rất quý để Hưng đưa vào **Chương 3 của Báo cáo khoa học IEEE**.

---

## 2. Các điểm lệch quy chuẩn cần khắc phục ngay

Nhóm trưởng đã chạy kiểm tra ma trận số học giữa 12 file TIFF Lộc nộp với bộ kiểm chuẩn của nhóm và phát hiện **3 điểm lệch kỹ thuật** sau:

### ⚠️ Lỗi 1: Sai nguồn ảnh đầu vào (Nghiêm trọng nhất – Gây lệch số liệu)
* **Thao tác hiện tại của Lộc:**
  - Lộc mở ảnh màu thô từ `data/sources/drive/images/21_training.tif` rồi dùng lệnh `Image -> Type -> 8-bit` trong Fiji.
* **Tại sao thao tác này sai về mặt khoa học?**
  - Khi bấm `Type -> 8-bit`, ImageJ tự động tính trung bình có trọng số cả 3 kênh: $0.299R + 0.587G + 0.114B$.
  - Trong ảnh võng mạc y tế (DRIVE), huyết sắc tố hemoglobin trong máu **hấp thụ ánh sáng mạnh nhất ở bước sóng xanh lá (Green)**. Kênh Green cho độ tương phản mạch máu cực đại, trong khi kênh Red bị chói lóa (overexposed) và kênh Blue rất tối/nhiễu. Gộp 3 kênh lại làm mạch máu bị mờ đục và mất các mao mạch mảnh.
* **Hậu quả đo đạc thực tế:**
  - Bản đồ Hessian Lộc xuất ra bị lệch trung bình **13.62 mức xám** so với ảnh chuẩn.
  - Hệ số tương quan Pearson giữa file Lộc nộp (phiên bản 05/11, chưa sửa prefix và nguồn ảnh) và file chuẩn của nhóm chỉ đạt **$r = 0.9156$** — đây là số liệu lịch sử từ đợt nộp cũ, không phản ánh bản nộp cuối cùng đã đọc từ `data/raw/` với tiền tố `fiji_`.
* **Giải pháp bắt buộc:**
  - **Không mở ảnh ở thư mục `sources/`**.
  - **Bắt buộc mở ảnh từ thư mục `data/raw/*.png`** (Bùi Trung Đức đã tiền xử lý chuẩn: DRIVE lấy riêng kênh Green lossless, BSDS chuyển theo chuẩn BT.601).

---

### ⚠️ Lỗi 2: Sai quy ước đặt tên file (File Naming Convention)
Hệ thống đánh giá tự động (`verify_tier1.py` và `benchmark_tier2.py`) quét kết quả dựa trên mẫu tên thống nhất. Tên file của Lộc đang bị lệch:

| Thành phần | Lộc đang đặt | Quy ước nhóm (`quyuoc.md`) | Cách sửa |
| :--- | :--- | :--- | :--- |
| **Tiền tố nguồn** | `fiji_...` | `fiji_...` (theo quyuoc.md, INSTRUCTIONS.md) | Đã đúng, KHÔNG cần đổi |
| **Tên ảnh** | Dùng ID gốc: `100075`, `21_training` | Dùng mã chuẩn: `bsds_01`, `drive_01` | Dùng mã nhóm (`bsds_01`, `drive_01`...) |
| **Toán tử** | `edge`, `hess-l1`, `hess-l2` | `edge`, `hess-l1`, `hess-l2` |  Đã đúng |
| **Ký hiệu $\sigma$** | `_s1.tif`, `_s2.tif` | `_s1.0.tif`, `_s2.0.tif` | Thêm số thập phân `.0` (dạng float) |

**Ví dụ cụ thể (đã đúng quy ước `fiji_`):**
- File của Lộc: `outputs/fiji/fiji_100075_edge_s1.tif`  
  👉 Tên ảnh cần đổi sang mã chuẩn: `outputs/fiji/fiji_bsds_01_edge_s1.0.tif`
- File của Lộc: `outputs/fiji/fiji_21_training_hess-l1_s1.tif`  
  👉 Tên ảnh cần đổi sang mã chuẩn: `outputs/fiji/fiji_drive_01_hess-l1_s1.0.tif`

---

### ⚠️ Lỗi 3: Chưa có kịch bản Macro tự động hóa (.ijm)
* Ở commit này Lộc mới làm chuột thủ công bằng tay (GUI) trên 2 ảnh đại diện được 12 file.
* Bộ kiểm chuẩn Tầng 1 gồm **5 ảnh** (`bsds_01`, `bsds_02`, `drive_01`, `blob_01`, `blob_02`), gồm **10 toán tử vi phân** qua **4 mức scale** (200 bản đồ) cộng **Structure Tensor 2 cặp × 2 thành phần** (20 bản đồ), tổng cộng **220 bản đồ TIFF 32-bit**.
* Làm tay 220 bản đồ sẽ rất mất thời gian và dễ nhầm lẫn. Lộc cần hoàn thành kịch bản Macro tự động hóa `.ijm` cho nhiệm vụ **STT 18 (Hạn 08/11/2026)**.

---

## 3. Mã Macro ImageJ (.ijm) chuẩn mẫu để Lộc tham khảo

Để Lộc không phải viết từ đầu, nhóm trưởng chia sẻ cấu trúc mã mẫu Macro ImageJ tự động hóa chuẩn cho toàn bộ dataset. Lộc có thể dùng hoặc tinh chỉnh lại:

```javascript
// batch_process.ijm - IMAGEJ MACRO TỰ ĐỘNG HÓA FEATUREJ (TIER 1 BENCHMARK)
run("Close All");
setBatchMode(true); // Ẩn GUI để chạy siêu tốc trong nền

images = newArray("bsds_01", "bsds_02", "drive_01", "blob_01", "blob_02");
sigmas = newArray(1.0, 2.0, 4.0, 8.0);

csv_path = "outputs/metrics/fiji_runtime.csv";
File.makeDirectory("outputs/metrics");
File.makeDirectory("outputs/fiji");
File.saveString("image,operator,sigma,runtime_ms\n", csv_path);

for (i = 0; i < images.length; i++) {
    img_name = images[i];
    raw_path = "data/raw/" + img_name + ".png"; // Luôn mở từ data/raw/
    print("-> Đang xử lý: " + img_name);
    
    open(raw_path);
    // BẮT BUỘC: Đặt scale pixel ngay sau khi mở ảnh
    run("Set Scale...", "distance=0 known=0 pixel=1 unit=pixel");
    orig_title = getTitle();
    
    for (s_idx = 0; s_idx < sigmas.length; s_idx++) {
        s = sigmas[s_idx];
        s_str = d2s(s, 1); // Định dạng 1 chữ số thập phân (1.0, 2.0...)
        
        // 1. Hessian L1 và L2
        selectWindow(orig_title);
        t0 = getTime();
        run("FeatureJ Hessian", "smoothing=" + s + " largest smallest");
        t1 = getTime();
        
        // Lưu L1 (Largest)
        selectWindow(orig_title + " Hessian largest eigenvalues");
        saveAs("Tiff", "outputs/fiji/fiji_" + img_name + "_hess-l1_s" + s_str + ".tif");
        close();
        
        // Lưu L2 (Smallest)
        selectWindow(orig_title + " Hessian smallest eigenvalues");
        saveAs("Tiff", "outputs/fiji/fiji_" + img_name + "_hess-l2_s" + s_str + ".tif");
        close();
        
        File.append(img_name + ",hessian," + s_str + "," + (t1 - t0) + "\n", csv_path);
    }
    
    selectWindow(orig_title);
    close();
}
print("=== HOÀN TẤT XUẤT TOÀN BỘ BẢN ĐỒ ===");
```

---

## 4. Kế hoạch tiếp theo cho Lộc (Từ nay đến 09/11)

1. **Hạn 07/11 (STT 17):** Dựng workflow tương tự cho **Blob (FeatureJ Laplacian)** và **Structure Tensor (FeatureJ Structure)**. Bổ sung ảnh chụp màn hình vào file báo cáo.
2. **Hạn 08/11 (STT 18):** Hoàn thiện file script `src/fiji/batch_process.ijm` chạy tự động quét toàn bộ 5 ảnh của Tầng 1.
3. **Hạn 09/11 (STT 19):** Chạy macro xuất toàn bộ 220 file TIFF đúng chuẩn tên `fiji_*` vào `outputs/fiji/` và file đo thời gian `outputs/metrics/fiji_runtime.csv`.
4. **Phối hợp viết Báo cáo:** Phối hợp cùng Hưng để chuyển nội dung từ file `.docx` sang **Chương 3 (Khảo sát FeatureJ & Workflow Fiji)** trong file LaTeX `docs/report_template/main.tex` (~6 trang).

*Chúc Lộc hoàn thành tốt các mốc tiếp theo! Nhóm đang làm rất mượt và đi trước tiến độ.*
