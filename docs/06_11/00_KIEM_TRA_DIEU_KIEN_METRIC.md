# Kiểm tra điều kiện làm công việc 4 — Tính metric định lượng

> **Bản lịch sử ngày 06/11.** Sau lần pull mới, xem
> [kiểm tra cập nhật ngày 08/11](../08_11/00_KIEM_TRA_DIEU_KIEN_METRIC.md).
> Các số lượng file và danh sách thiếu bên dưới phản ánh phiên bản cũ.

Ngày kiểm tra: 06/11/2026. Vai trò: Bùi Trung Đức — Dữ liệu & Đánh giá.
Phạm vi lần này: đọc, đối chiếu và kiểm tra mức sẵn sàng; chưa sửa thuật toán,
chạy batch hay sinh kết quả metric mới.

## Kết luận

Đã có đủ nền tảng để Đức bắt đầu hoàn thiện pipeline đánh giá. Chưa đủ bản đồ
đầu ra và chưa có pipeline chấm tuân thủ đầy đủ quy ước để chạy toàn bộ kết quả
so sánh Python/Fiji hoặc kết luận nghiệm thu.

## Căn cứ đã đọc

- [INSTRUCTIONS.md](../references/INSTRUCTIONS.md), yêu cầu vai trò Dữ liệu & Đánh giá.
- [yeucau.md](../references/yeucau.md), yêu cầu chung của giảng viên.
- [debai.md](../report_template/debai.md), bản đề bài mới có trong code nhận về.
- [quyuoc.md](../report_template/quyuoc.md), quy chuẩn kỹ thuật mới có trong code nhận về.
- Tài liệu ngày 02/11, 05/11, manifest dataset và ground truth hiện có.
- [WORKFLOW_EDGE_RIDGE.docx](../fiji/WORKFLOW_EDGE_RIDGE.docx), macro của Lộc,
  code Python, các script đánh giá và kết quả đầu ra hiện có.

Quy ước chi tiết xác định Tầng 1 dùng MAE, RMSE, Max Error, Pearson trên bản đồ
liên tục; không dùng PSNR cho bản đồ đạo hàm có dấu. Tiêu chuẩn vẫn là cả hai
điều kiện `max|delta|/max|ref| < 1e-4` và `r > 0.9999`, sau khi crop đúng biên.

## Phần đã sẵn sàng

| Thành phần | Kiểm tra thực tế |
| --- | --- |
| Dataset | 25 input; checksum vẫn khớp bảng kiểm kê |
| Ground truth | 25/25 READY; file và checksum khớp manifest |
| Tế bào blob_05 | Giữ nhãn Đức đã rà soát: 276 đối tượng và 15 vùng bỏ qua |
| Python core | Có kernel, tích chập, đạo hàm, Hessian, Structure Tensor, ba detector; `run_tests.py` đạt 5/5 |
| Batch Python | Đã đọc ảnh/sigma/Structure/eigen_order từ config; lỗi cố định thứ tự trị riêng trước đây đã được xử lý |
| Cấu hình | Hiện `eigen_order=algebraic`, khớp lựa chọn trong macro Fiji mới; các ô đo không còn null |
| Fiji Edge/Ridge | 164 TIFF đều là một trang, float32 không nén, hữu hạn và đúng kích thước ảnh raw tương ứng |
| Phân loại Fiji | 52 Edge + 56 hess-l1 + 56 hess-l2 |
| Runtime Fiji | Có 108 bản ghi: 52 Edge + 56 Hessian |

5/5 unit test xác nhận các kiểm tra lõi hiện có; chưa thay thế đối chuẩn với
FeatureJ. Cấu hình có giá trị cũng chưa thay thế hồ sơ hiệu chuẩn.

## Đầu ra còn thiếu

| Đầu ra | Hiện có | Yêu cầu để chạy |
| --- | ---: | --- |
| Python — 5 ảnh Tầng 1, bản đồ chuẩn | 0/220 | Chạy batch Python để tạo 220 bản đồ chuẩn |
| Fiji — 5 ảnh Tầng 1, bản đồ chuẩn | 40/220 | Đã có Hessian; bổ sung 180 bản đồ Gaussian/đạo hàm/gradient/Laplacian/Structure |
| Smoke Test `bsds_01`, sigma=2, lx/ly/lxx | 0/3 mỗi nguồn | Cần đủ 3 TIFF Python và 3 TIFF Fiji |
| Laplacian Fiji lưới dày cho 5 ảnh blob | 0/35 | Xuất lap tại đúng 7 sigma trong config cho cả 5 ảnh |
| Fiji lx/ly cho nhánh Canny công bằng | Chưa có | Xuất lx/ly cho 10 ảnh BSDS ở các sigma chuẩn |
| Python phục vụ toàn bộ Tầng 2 | Chưa có file | Batch hiện chỉ xử lý 5 ảnh Tầng 1; cần mở rộng đầu ra phục vụ 20 ảnh còn lại và lap lưới dày |

220 là 5 ảnh × (10 bản đồ × 4 sigma + 2 trị riêng Structure × 2 cặp scale).
Laplacian lưới dày của hai ảnh blob Tầng 1 còn cần các mức ngoài sigma chuẩn;
không được coi 220 là toàn bộ đầu ra cần cho cả hai tầng.

Macro [batch_process.ijm](../../src/fiji/batch_process.ijm) hiện chỉ làm Edge và
Hessian, đúng phạm vi tài liệu Edge/Ridge của Lộc. Đây là bàn giao một phần;
phần Derivatives/Laplacian/Structure cần được bổ sung bởi phần Fiji tương ứng.
`edge` có NMS, không thể dùng thay cho `lx`, `ly` hoặc `grad` thô.

## Các script đánh giá cần hoàn thiện

### Tầng 1 — verify_tier1.py

- Dòng 67/118 tìm prefix `fj_`, trong khi quy ước và file hiện có dùng `fiji_`.
- Dòng 100 chỉ phân loại PASS theo Pearson, chưa dùng ngưỡng sai số tương đối.
  Structure tại dòng 144 còn dùng Pearson >=0.9990, thấp hơn quy định.
- Dòng 98/142 đổi Pearson NaN thành 1.0; bản đồ hằng không được tự coi là đạt.
- Thiếu file thì bỏ qua, dễ tạo tổng kết trên một tập con mà không báo thiếu
  đủ số lượng bắt buộc. Chưa có RMSE và bảng sai số biên riêng theo yêu cầu.
- Crop Structure đang lấy ceil của tổng thay vì cộng hai ceil; xử lý vùng lõi
  rỗng cũng cần báo lỗi thay vì dùng lại toàn ảnh.

CSV sẵn có ở `docs/report_template/metrics/tier1_verification_summary.csv` có
220 dòng được gắn PASS. Khi áp dụng lại **cả hai ngưỡng quy định trên số liệu
trong CSV**, chỉ 35 dòng thỏa mãn. Đây là kiểm tra tính nhất quán của CSV cũ,
không phải tái đo trên các TIFF hiện tại; hiện chưa có đủ các TIFF đó để tái
kiểm chứng. Cần sửa cách chấm và đo lại, không tự nới ngưỡng hoặc sửa lõi để ép PASS.

### Tầng 2 — benchmark_tier2.py

- Hiện tự tính từ raw bằng nhánh Python; chưa chạy cùng detector trên bản đồ
  Fiji, chưa so sánh hai nguồn và chưa dùng chung hàm chuẩn hóa theo cờ từng lệnh.
- `main` chỉ gọi 5 BSDS + 5 DRIVE + 5 blob, chưa đủ 25 ảnh.
- Edge chỉ dùng một sigma và cặp ngưỡng cố định 60/85, chưa quét ngưỡng/chấm
  theo từng sigma. Cần chốt hình học dung sai 2 px; hiện mask 5×5 bao cả đường
  chéo có khoảng cách Euclidean lớn hơn 2 px.
- DRIVE xói mòn FOV bằng cấu trúc 9×9 cố định, chưa theo support `ceil(k*sigma)`.
- Blob tự thêm sigma=11.3 ngoài config; cần giữ đúng lưới đã chốt.
- Ghép blob chưa đảm bảo một phát hiện chỉ khớp một GT; có thể đếm trùng TP.
- Chưa áp dụng 15 vùng bỏ qua của blob_05 và chưa kiểm tra trạng thái nhãn READY.
- Hiện in console, chưa xuất các bảng CSV metric phục vụ bàn giao/báo cáo.
- Script đang dùng `scipy.ndimage` cho morphology. Quy tắc chung giới hạn module
  này vào kiểm thử độc lập/benchmark thời gian, vì vậy cần xử lý phù hợp khi
  hoàn thiện pipeline thay vì tự mở rộng ngoại lệ trong tài liệu.

### Các điểm tích hợp khác

- `src/config.py` vẫn có chế độ mặc định/fallback; pipeline nghiệm thu phải
  kiểm tra nghiêm ngặt config, báo lỗi nếu thiếu/null, không nhận fallback.
- `smoke_test_analytical.py` tìm `parabol.tif`, trong khi file đã bàn giao là
  `parabola.tif`; cần thống nhất tên trước khi chạy script đó.
- Canny core đang lấy phân vị trên phần NMS khác 0; tài liệu nói phân vị độ lớn
  gradient trong ảnh. Đức và Mạnh cần thống nhất định nghĩa trước khi quét ngưỡng.
- Comment config vẫn nói bán kính floor(k*sigma)+1, kernel dùng ceil(k*sigma).
  Cần đối chiếu phép đo đã bàn giao, không tự đổi thông số đo để giảm sai số.

## Thứ tự triển khai tiếp theo

1. **Đức:** hoàn thiện kiểm tra đầu vào và cách chấm Tầng 1, giữ tiêu chuẩn gốc;
   chuẩn bị metric Tầng 2 theo đúng nhãn hiện có và quy ước.
2. **Python:** tạo đầu ra chuẩn từ cùng `data/raw` và config; bổ sung phạm vi
   batch cần cho Tầng 2. Có thể chạy code đã có tại máy Đức sau khi kiểm tra.
3. **Fiji:** bổ sung Derivatives/Laplacian/Structure còn thiếu; ưu tiên 3 file
   Smoke Test trước. Nhánh Hessian hiện có đã đủ ảnh DRIVE ở 4 sigma.
4. Chạy Smoke Test thật → ghi nhận sai số, xử lý theo quy tắc nếu không đạt →
   đánh giá 5 ảnh Tầng 1 → chạy đủ 25 ảnh Tầng 2 và xuất CSV.

Không cần chờ tất cả đầu ra mới bắt đầu viết pipeline. Kết luận định lượng
cuối cùng cần đủ đầu ra hai nguồn, đúng cấu hình và đúng cách chấm.
