# Nguồn số liệu trong gói báo cáo

## Snapshot canonical dùng cho báo cáo hiện tại

Thư mục `canonical_58bdfd8/` chứa protocol và CSV Tier 2 lấy từ repo `ndmanh1811/XLA`, nhánh `dev/NguyenDucManh`, commit `58bdfd8dde8b3ea443750a021852f2d0444b82a1`. Dùng `PROTOCOL.md`, `tier2_results.csv` (Python chính thức), `tier2_results_both.csv` (so sánh Python--Fiji), `tier2_bsds_thresholds.csv` và `optimization_benchmark.csv` làm nguồn cho các số liệu hiện hành trong báo cáo. Tier 1 vẫn là 35 STRICT / 185 RELAXED / 0 FAIL.

## Snapshot lịch sử

Thư mục `duc_08_11/` là snapshot trước khi sửa dung sai BSDS, dùng ô vuông 5×5 thay cho đĩa Euclidean bán kính 2 px. Không dùng các số liệu trong thư mục này làm kết quả hiện hành. `ARCHIVED_HISTORICAL.md` ghi rõ trạng thái của snapshot.

Các CSV ở cấp gốc `metrics/` cũng được giữ để truy nguyên lần chạy trước; không dùng chúng làm nguồn số liệu canonical hiện tại.

- `repo_update_verification_950d47f.json` ghi nhận lần đối chiếu lịch sử ở commit 950d47f; trạng thái hiện tại ghi trong `repo_update_verification.json`.

## Tái chạy mẫu cục bộ

`sample_comparison.csv`, `fiji_api_sample_log.csv`, `fiji_api_run.txt`, `local_build_provenance.json` và `java_runtime.txt` là minh chứng cho lần so sánh 72 bản đồ bằng ImageScience API. Phép chạy đó dùng nhân NumPy tại commit 58e28e7; không dùng để thay số liệu Tier 2 chuẩn và không phải ảnh chụp thao tác GUI bằng tay.
