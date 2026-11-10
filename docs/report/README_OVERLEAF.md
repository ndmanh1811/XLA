# Biên dịch báo cáo IEEE

Trong gói ZIP, mở `main.tex` ở cấp gốc làm tài liệu chính và chọn XeLaTeX; giữ nguyên các thư mục `sections/`, `figures/` và `metrics/`. Tài liệu dùng BibTeX cho `references.bib`. Nguồn trong repo nằm ở `docs/report_hung/`; có thể biên dịch cục bộ bằng `compile_report.ps1` nếu đã cài XeLaTeX và BibTeX.

Báo cáo đối chiếu với snapshot canonical `58bdfd8dde8b3ea443750a021852f2d0444b82a1` của nhánh `dev/NguyenDucManh`. Hai commit mới nhất sửa dung sai BSDS thành đĩa Euclidean bán kính 2 px, tính hình thái học bằng NumPy thuần, quy định ảnh NMS rỗng có F1 bằng 0 và tái tạo metric Tier 2. Các tệp nguồn hiện hành được kèm trong `metrics/canonical_58bdfd8/`; `metrics/duc_08_11/` là snapshot lịch sử trước khi sửa dung sai. Bảng rà soát bốn nhánh và các con số mới nằm trong `sections/repo_update_39e4d02.tex` và `metrics/repo_update_verification.json`.

Nguồn hiện chưa có PDF đã biên dịch. `metrics/report_source_check.json` ghi nhận kiểm tra tĩnh của LaTeX; số trang và bố trí cuối cần được xác nhận sau khi biên dịch XeLaTeX.
