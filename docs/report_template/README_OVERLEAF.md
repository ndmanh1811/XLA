# Gói báo cáo IEEE

Để biên dịch trên Overleaf, tải ZIP bằng **New Project → Upload Project**. Tệp main.tex nằm ở cấp gốc; chọn **XeLaTeX** làm compiler và giữ nguyên references.bib, ch4_content.tex, figures/ và metrics/.

Báo cáo được đối chiếu theo protocol canonical duc_10_11_v1. Quy ước đầy đủ được kèm tại metrics/PROTOCOL.md. Các CSV và manifest nguồn được sao vào metrics/duc_10_11/; mẫu thời gian và môi trường đo nằm trong metrics/runtime_duc_task5_10_11/; phân tích tổng hợp nằm trong metrics/analysis_duc_task5_10_11/. Benchmark chập NumPy riêng nằm tại metrics/optimization_benchmark.csv.

Gói chứa mã LaTeX, hình và hồ sơ số liệu để tái lập/đối chiếu. Không có PDF biên dịch sẵn; sau khi tải lên Overleaf, biên dịch để tạo PDF.