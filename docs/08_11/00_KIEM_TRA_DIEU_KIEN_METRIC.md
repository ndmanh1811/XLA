# Kiểm tra công việc 4 của Đức sau lần cập nhật source

> **Hồ sơ kiểm tra trước khi triển khai.** Công việc metric sau đó đã được
> thực hiện trong [bộ bàn giao của Đức](../../README_DUC_08_11.md).
> Xem [kiểm tra bàn giao](02_KIEM_TRA_BAN_GIAO.md) và
> [kết quả tính lại](../../outputs/metrics/duc_08_11/KET_QUA_METRIC.md).
> Những điểm "cần làm" bên dưới mô tả trạng thái trước khi viết pipeline mới.

Ngày kiểm tra: **08/11/2026**. Công việc **STT 23 — Tính metric định lượng**, hạn
12/11 trong bảng phân công. Phạm vi lần này: đọc tài liệu, kiểm tra dữ liệu và
code, chạy kiểm thử có sẵn và smoke test trong bộ nhớ; chưa triển khai lại
pipeline metric, chưa sinh lại các bảng kết quả hoặc làm công việc vẽ biểu đồ.

## Kết luận

**Đủ dữ liệu và code để Đức thực hiện công việc 4 ngay. Không còn phải chờ bổ
sung các loại bản đồ Fiji như kết luận ngày 06/11.** Tuy nhiên, pipeline chấm
hiện tại còn điểm cần sửa; chưa thể dùng nguyên các CSV đã pull để kết luận
công việc 4 đã hoàn thành đúng toàn bộ ràng buộc.

Thiếu thư mục `outputs/python/` trên máy hiện tại là bước cần chạy để tạo lại
đầu ra, không phải thiếu code của người phụ trách Python. Batch mới đã có cả
Tầng 1 và Tầng 2. Tầng 2 hiện tính nhánh Python trực tiếp từ raw nên không cần
thư mục này để chạy, nhưng Tầng 1 cần các TIFF Python để ghép cặp.

## Tài liệu đã đối chiếu

- Bảng [Phân công XLA (1).xlsx](../../Phân%20công%20XLA%20(1).xlsx) trong dự án
  và bảng Excel gốc ở thư mục cha: STT 23 cùng yêu cầu Fiji/Python
  (MSE/PSNR/tương quan), Precision/Recall/F1 với ground truth.
- Bốn tài liệu hiện tại ở gốc dự án: [INSTRUCTIONS.md](../../INSTRUCTIONS.md),
  [yeucau.md](../../yeucau.md), [debai.md](../../debai.md),
  [quyuoc.md](../../quyuoc.md), cùng [config.yaml](../../config.yaml).
- Hồ sơ dữ liệu/thí nghiệm ngày 02/11, ground truth ngày 05/11, hai workflow
  DOCX Fiji, README mới và [nhận xét ngày 07/11](../../nhanxet7/11.md).
- Code core, batch Python, macro Fiji, Java exporter, hai pipeline đánh giá,
  bộ kiểm thử và các TIFF/CSV/ZIP hiện có.

Các bản `docs/references/INSTRUCTIONS.md` và `docs/report_template/quyuoc.md`
không giống hoàn toàn bản ở gốc dự án. Kiểm tra lần này đối chiếu với **bản ở
gốc sau lần pull mới**; báo cáo 06/11 chỉ phản ánh trạng thái cũ.

## Những phần đã đủ — kiểm tra trực tiếp

| Thành phần | Kết quả trên máy hiện tại |
| --- | --- |
| Dataset | 25 ảnh raw, grayscale uint8; checksum khớp inventory |
| Ground truth | 25/25 READY; toàn bộ file nhãn và input khớp SHA-256 trong manifest |
| Nhãn blob_05 của Đức | 276 đối tượng, 15 vùng bỏ qua, không còn gợi ý chờ duyệt |
| Fiji macro | 435/435 TIFF qua validator; đúng bộ kỳ vọng, manifest và runtime; mọi ảnh float32, một trang, không nén, hữu hạn |
| Fiji Tầng 1 | Đủ 220/220 bản đồ chuẩn trong `outputs/fiji/` |
| Fiji Tầng 2 | Đã có lx/ly cho BSDS, Hessian cho DRIVE, lap lưới dày cho 5 blob |
| Tham chiếu Java | ZIP có 220 TIFF; kiểm tra trực tiếp trong ZIP, đủ và khớp kích thước/SHA-256 của manifest, float32 và hữu hạn |
| Batch Python | Có `--tier1`, `--tier2`; xuất các loại bản đồ cần dùng |
| Pipeline Tầng 2 | Đã có `--source both`, quét ngưỡng theo sigma, đóng băng ngưỡng từ Python sang Fiji và xuất CSV |
| CSV Tầng 2 đã pull | 110 dòng = 55 mỗi nguồn: 40 BSDS (10 ảnh × 4 sigma), 10 DRIVE, 5 blob; bảng đối sánh 55 dòng |
| Kiểm thử hiện có | `run_tests.py`: 5/5; unittest discovery: 22/22 |

`outputs/python/` và `outputs/fiji_java/` chưa tồn tại sau pull này.
`outputs/fiji_java_tier1.zip` có đủ bộ Java nên không cần nhờ xuất lại bộ này;
`verify_tier1.py` có chức năng giải nén tự động. Lần kiểm tra này đọc trực tiếp
ZIP, không giải nén hoặc ghi đè TIFF/CSV.

## Những điểm còn cần hoàn thiện để bàn giao metric

| Phần | Hiện trạng và việc cần làm | Phối hợp |
| --- | --- | --- |
| Đầu ra Python Tầng 1 | Chạy batch để tạo lại 220 TIFF từ cùng raw/config; kiểm tra định dạng và đủ cặp | Đức chạy code Mạnh đã bàn giao |
| Metric Tầng 1 | Có MAE, RMSE, Max Error, Relative Error, Pearson, PSNR cho Gaussian; chưa có cột **MSE**, chưa có bảng sai số vùng biên, chưa xuất đúng `outputs/metrics/tier1_report.csv` | Đức |
| Cách nghiệm thu Tầng 1 | Có `PASS_RELAXED` với rel < 1e-2, trong khi INSTRUCTIONS/quyuoc vẫn quy định rel < 1e-4 và r > 0.9999; phải tách rõ đạt chuẩn gốc và kết quả theo ngưỡng nới, ghi căn cứ/thống nhất của nhóm khi dùng ngưỡng nới | Đức + Mạnh; người viết báo cáo ghi đúng |
| Trường hợp đặc biệt Tầng 1 | Bản đồ hằng đang có thể được gán r=1; mẫu số 0 được cộng epsilon; crop rỗng dùng lại toàn ảnh. Cần trạng thái không xác định/không hợp lệ phù hợp, không tự coi đạt | Đức |
| Chuẩn hóa Tầng 2/config | Đang nhân sigma/sigma² rải rác, chưa có hàm chung đọc `featurej_normalized`; nhiều getter còn fallback. Cần kiểm tra config nghiêm ngặt và chuẩn hóa theo cờ từng lệnh | Đức, phối hợp Mạnh ở giao diện config |
| Blob — ghép đối tượng | Vòng lặp hiện cho một phát hiện khớp nhiều GT; cần ghép **một-một** theo cả khoảng cách tâm ≤2 px và sai số bán kính ≤20% | Đức |
| Blob — nhãn đã duyệt | Chưa áp dụng 15 `ignore_regions`, chưa chặn nhãn chưa READY và chưa kiểm tra hash lúc benchmark | Đức; không cần Đức gán nhãn lại |
| Blob — sigma | Chạy `--source both --blob-sigmas config` dùng đúng 7 sigma; chế độ Python mặc định vẫn có thể thêm 11.3. Bản bàn giao chuẩn phải dùng đúng config | Đức |
| DRIVE | Đã xói mòn từng scale, nhưng k=4 và FOV đánh giá cuối ở sigma=2 vẫn gõ cứng. Cần đọc k từ config và quy định rõ vùng hợp lệ khi gộp nhiều scale | Đức |
| BSDS | Đã có đủ annotator và quét ngưỡng riêng từng sigma. Mask dung sai vẫn là hình vuông 5×5: cần ghi rõ dùng khoảng cách nào; nếu là Euclidean 2 px thì phải sửa mask | Đức |
| Ràng buộc thư viện | `benchmark_tier2.py` và `bsds_threshold_grid.py` còn dùng `scipy.ndimage` cho morphology/label trong pipeline chính; tài liệu chỉ cho module này trong kiểm thử độc lập và benchmark thời gian | Đức, phối hợp Mạnh nếu thay phần hysteresis tăng tốc |

Java exporter vẫn gõ cứng danh sách ảnh, sigma, cặp ST và lựa chọn trị riêng;
hiện các giá trị trùng config. Nếu dùng exporter để tái sinh về sau, cần đồng
bộ cách đọc config. Bộ TIFF đã có đủ nên đây không phải thiếu đầu vào để Đức
bắt đầu. `smoke_test_analytical.py` còn tìm `parabol.tif` trong khi ảnh đã bàn
giao là `parabola.tif`; cần sửa tên nếu sử dụng script này.

Theo **tài liệu mới**, PSNR dùng MAX=255 được chốt cho **Gaussian smoothing**;
các bản đồ đạo hàm dùng bộ sai số/tương quan tương ứng. Không cần chờ chốt lại
phạm vi PSNR như ghi chú cũ ngày 06/11. MSE có thể tính trực tiếp từ bình
phương sai số; việc đã có RMSE không thay cho cột MSE trong đầu ra được yêu cầu.

## Smoke test thực sự trên code và raw hiện tại

Tính lại trong bộ nhớ từ `data/raw/bsds_01.png`, sigma=2; so với TIFF macro
hiện tại và TIFF Java trong ZIP. Crop 8 px theo config. Kết quả hai nguồn
tham chiếu giống nhau ở các phép so sánh này:

| Toán tử | max\|delta\| / max\|ref\| | Pearson r | Đạt cả hai ngưỡng gốc? |
| --- | ---: | ---: | --- |
| lx | 0.000364464297 | xấp xỉ 1.0 | Không |
| ly | 0.000364504544 | xấp xỉ 1.0 | Không |
| lxx | 0.00404235386 | 0.9999955971 | Không |

Điều này **không cản việc tính metric và báo cáo sai số thực**, nhưng chưa đủ
để tuyên bố khóa lõi theo smoke test chuẩn gốc. Không sửa lõi hoặc nới ngưỡng
chỉ để ép PASS. Cần đối chiếu phép đo/kernel/cách chuẩn hóa và ghi rõ lý do
nếu nhóm quyết định dùng ngưỡng khác.

CSV Tầng 1 đã pull có **35 PASS_STRICT + 185 PASS_RELAXED**. Đếm lại từ cột
rel_error/Pearson đúng là chỉ 35/220 dòng thỏa cả hai ngưỡng gốc. Đây là kiểm
tra bảng có sẵn, **chưa phải tái đo đủ 220 cặp** trên máy này.

Sáu TIFF ở `outputs/smoke_test_tier1/` cũng đã có, nhưng bản Fiji trong bộ này
không trùng các bản đồ Fiji hiện tại và có tương quan thấp với đầu ra tính
từ raw/code hiện tại. Chưa xác minh nguồn gốc sai khác; phải tạo lại smoke
test từ bộ raw/config hiện tại trước khi dùng làm bằng chứng.

## Trình tự công việc 4 tiếp theo

1. Hoàn thiện cách kiểm tra/chấm, ghép một-một và vùng bỏ qua; giữ nguyên raw
   và ground truth đã được Đức duyệt.
2. Sinh lại TIFF Python; chọn rõ tham chiếu macro hay Java, lưu nguồn vào
   báo cáo; chạy lại smoke test và đủ 220 cặp với tiêu chuẩn gốc.
3. Đánh giá cả hai nguồn trên 25 ảnh, đúng 7 sigma blob, cùng detector/tham số;
   sinh lại CSV sau các sửa đổi. Các CSV pull về chỉ là kết quả tham khảo
   của phiên bản pipeline hiện có.
4. Bàn giao bảng MSE/MAE/RMSE/Max/Relative Error/Pearson, PSNR cho Gaussian,
   bảng sai số biên và Precision/Recall/F1 theo ảnh/nguồn/sigma thích hợp.
   Vẽ biểu đồ và phân tích tổng hợp là STT 24, tách khỏi lần kiểm tra này.
