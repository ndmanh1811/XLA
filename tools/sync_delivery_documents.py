"""Publish report tables and handoff notes from verified canonical CSVs.

No manual score replacement: the generated Chapter 5/6 is reproducible.
The previous main.tex and slide source are preserved in the repair ZIP.
"""
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.eval.metric_utils import RESULTS,sha256
from src.eval.analyze_task5 import verify_metric_delivery
from src.eval.task5_runtime import TASK5,read_csv


def main():
    verify_metric_delivery()
    analysis=json.loads((TASK5/'analysis_manifest.json').read_text(encoding='utf-8'))
    if analysis['status']!='COMPLETE' or analysis['metric_manifest_sha256']!=sha256(RESULTS/'run_manifest.json'):
        raise ValueError('Current analysis is missing or does not use the current metric run')
    summary=read_csv(RESULTS/'tier2_summary.csv')
    cells=[r for r in read_csv(RESULTS/'tier2_results_both.csv') if r['image']=='blob_05']
    thresholds=read_csv(RESULTS/'bsds_selected_thresholds.csv')
    edge=read_csv(TASK5/'tables/edge_by_sigma.csv')
    status=dict(Counter(r['status'] for r in read_csv(RESULTS/'tier1_report.csv')))
    table=['| Nguồn | Bài toán | Sigma | Macro P | Macro R | Macro F1 | Micro F1 |',
           '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for r in summary:
        micro=f"{float(r['micro_f1']):.6f}" if r['micro_f1'] else '—'
        table.append(f"| {r['source']} | {r['task']} | {r['sigma']} | {float(r['macro_precision']):.6f} | {float(r['macro_recall']):.6f} | {float(r['macro_f1']):.6f} | {micro} |")
    out=ROOT/'docs/10_11/sau_sua_loi'
    out.mkdir(parents=True,exist_ok=True)
    data=dict(protocol='duc_10_11_v1',metric_directory=str(RESULTS.relative_to(ROOT)),
              analysis_directory=str(TASK5.relative_to(ROOT)),tier1=status,summary=summary,cells=cells,
              metric_manifest_sha256=sha256(RESULTS/'run_manifest.json'),
              analysis_manifest_sha256=sha256(TASK5/'analysis_manifest.json'))
    (out/'SO_LIEU_BAN_GIAO.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Bàn giao sau sửa lỗi — phiên 10/11/2026','',
           '## Nguồn số liệu chính','',
           '- Metric: `outputs/metrics/duc_10_11`; manifest phải là COMPLETE và checksum phải hợp lệ.',
           '- Biểu đồ, nhận xét, timing: `outputs/analysis/duc_task5_10_11`.',
           '- Các bộ duc_08_11/pre_fix_10_11 là lịch sử. Không trộn ngưỡng/FOV/sigma giữa các phiên.','',
           '## Đã xử lý','',
           '- Chỉ một pipeline thực hiện chấm điểm; benchmark_tier2.py là lối gọi tương thích, không còn bộ chấm độc lập.',
           '- Blob khớp một–một theo maximum cardinality, loại ignore trước khi đếm FP; có test ở đúng hàm chấm hai nguồn.',
           '- DRIVE dùng giao FOV hợp lệ theo support lớn nhất suy ra từ config; hình thái học NumPy.',
           '- Chuẩn hóa qua một hàm, xét featurej_normalized cho Fiji; hai nguồn dùng cùng 7 sigma blob.',
           '- BSDS đĩa Euclidean 2px; tìm ngưỡng thô/tinh trên Python, đóng băng cho Fiji.',
           '- Đã sinh lại metric, biểu đồ và timing. Launcher công việc 5 đọc phiên hiện hành.',
           '- Slide dùng gamma=1 cho cả hai bậc, mô tả đúng FeatureJ Edges/Canny; checksum chỉ nói toàn vẹn dữ liệu.',
           '- Demo tính P/R/F1 thật cho một ảnh; số trong slide/báo cáo lấy từ cùng CSV.','',
           '## Kết quả','',f"Tầng 1 theo ngưỡng gốc: {status}. 185 cặp vẫn không đạt ngưỡng gốc; có thể ghi RELAXED theo ngưỡng mở rộng của nhóm, không gọi đạt STRICT.",'']+table
    lines+=['','### Ảnh tế bào','', '| Nguồn | TP | Dự đoán sau ignore | GT | Bỏ qua | F1 |','| --- | ---: | ---: | ---: | ---: | ---: |']
    lines += [f"| {r['source']} | {r['tp']} | {r['predicted_count']} | {r['gt_count']} | {r['ignored_predictions']} | {float(r['f1']):.6f} |" for r in cells]
    lines+=['','Điểm DRIVE khác số ~0.681 của phiên cũ vì vùng FOV và cách chọn ngưỡng đã đổi. Điểm blob khác vì matching/ignore/ngưỡng đã được chốt lại; đây không phải các phép đo có thể trộn với phiên cũ.',
            'Phép thử giữ ngưỡng cũ 7.65 cho blob_05 từng cho F1 0.493827/0.488576. Phiên bàn giao chọn ngưỡng trong lưới đã công bố, nên không thay F1 hiện tại bằng các số kiểm chứng đó.','',
            '## Còn cần nhóm hoàn thiện','',
            '- Hưng mở rộng lý thuyết, rà nguồn/trích dẫn, biên dịch và nghiệm thu PDF ~30 trang. Mã LaTeX cập nhật chưa đồng nghĩa đã có PDF cuối.',
            '- Lộc đã bổ sung hồ sơ đo định lượng k/border/normalization ngày 11/11; còn ảnh chụp phiên bản, hộp thoại và profile của đúng phiên đo trong `docs/fiji/calibration/screenshots`.',
            '- Cả nhóm kiểm tra trình chiếu, chuẩn bị câu hỏi bảo vệ và xác minh quyền link LMS trước nộp.',
            '- Baseline 25 ảnh; chưa kết luận về nhiễu/đổi kích thước khi chưa có thí nghiệm bổ sung.','']
    (out/'BAN_GIAO_SAU_SUA.md').write_text('\n'.join(lines),encoding='utf-8')

    # Generate one complete report section from the canonical run; no old
    # protocol values survive inside the experimental results/conclusion.
    report=ROOT/'docs/report_template/main.tex'
    text=report.read_text(encoding='utf-8-sig')
    text=text.replace('5 ảnh hiệu chuẩn','5 ảnh đại diện')
    text=text.replace('Triệt tiêu không cực đại 8 hướng (NMS)','Triệt tiêu không cực đại theo 4 sector hướng (NMS)')
    text=text.replace('triệt tiêu không cực đại 8 hướng','triệt tiêu không cực đại theo 4 sector hướng')
    text=text.replace('Chất lượng đường biên trơn tru, liền mạch vượt trội so với các bộ lọc rời rạc thông thường.',
                      'Kết quả được đánh giá bằng sai số số học và nhãn đối chứng; các khác biệt được báo cáo theo từng protocol.')
    text=text.replace('và chứng minh tính ưu việt của điều kiện bảo toàn moment','và kiểm tra điều kiện bảo toàn moment')
    text=text.replace('hoàn toàn không phải lỗi giải thuật','cần được kiểm chứng bằng phép đo hiệu chuẩn để xác định nguyên nhân')
    chapters=list(re.finditer(r'\\section\{Chương [56]:[^}]+\}',text))
    if len(chapters)!=2:
        raise ValueError('Expected one Chapter 5 and one Chapter 6 in main.tex')
    trailer=text[text.index('\\bibliographystyle'):]
    bsds_table='\n'.join(f"{float(r['sigma']):g} & {float(r['python_f1']):.6f} & {float(r['fiji_f1']):.6f} & {float(r['delta_f1_fiji_minus_python']):+.8f} "+r'\\' for r in edge)
    summary_table='\n'.join(f"{r['source']} / {r['task'].replace('_',chr(92)+'_')} & {float(r['macro_precision']):.6f} & {float(r['macro_recall']):.6f} & {float(r['macro_f1']):.6f} "+r'\\' for r in summary if r['task']!='edge_bsds')
    cell_table='\n'.join(f"{r['source']} & {r['tp']} & {r['predicted_count']} & {r['ignored_predictions']} & {float(r['f1']):.6f} "+r'\\' for r in cells)
    blob_summary={r['source']:r for r in summary if r['task']=='blob_log'}
    micro_text='; '.join(f"{source}: macro F1={float(r['macro_f1']):.6f}, micro F1={float(r['micro_f1']):.6f}" for source,r in blob_summary.items())
    generated=r'''
\section{Chương 5: Thực Nghiệm, Đánh Giá Định Lượng và Phân Tích}
\subsection{Dữ liệu và protocol có thể tái lập}
Bộ dữ liệu gồm 25 ảnh xám uint8: 10 BSDS500 với 56 bộ nhãn đa annotator, 10 DRIVE có vessel mask/FOV, 4 ảnh blob tổng hợp và ảnh tế bào \texttt{blob\_05}. Ảnh tế bào có 276 đối tượng và 15 vùng loại trừ, được nhóm xây dựng và Đức rà soát; không coi là nhãn chuyên gia độc lập.
Nguồn chính của chương này là \texttt{outputs/metrics/duc\_10\_11} và \texttt{outputs/analysis/duc\_task5\_10\_11}, kèm manifest SHA-256. Checksum xác minh toàn vẹn từng bộ, không chứng minh Python và Fiji có cùng byte hoặc cùng giá trị số.

\subsection{Tầng 1: đối chuẩn bản đồ liên tục}
Đối chiếu 220 cặp TIFF trên năm ảnh đại diện, crop theo support của từng toán tử. Ngưỡng gốc yêu cầu đồng thời relative max error $<10^{-4}$ và Pearson $r>0.9999$. Có 35 cặp đạt ngưỡng gốc và 185 cặp chưa đạt. Nếu nhóm dùng ngưỡng mở rộng $10^{-2}$, cần ghi rõ 185 cặp là RELAXED, không phải STRICT. PSNR với MAX=255 chỉ áp dụng Gaussian; đạo hàm có dấu dùng MAE/RMSE/relative error/Pearson. Tương quan cao không đủ chứng minh tương đương biên độ. Khác biệt rời rạc hóa là giả thuyết cần đối chiếu hồ sơ hiệu chuẩn.

\subsection{Tầng 2: biên BSDS500}
Dung sai là đĩa Euclidean bán kính 2 px. Precision xét biên của ít nhất một annotator; recall trung bình các annotator. Ngưỡng phân vị tính trên NMS khác 0, chọn lưới thô/tinh riêng từng sigma trên Python rồi đóng băng cho Fiji. Ảnh NMS rỗng vẫn được tính vào mẫu số. FeatureJ Edges dùng Canny với NMS nội suy và hysteresis, là nhánh tham chiếu riêng, không phải zero-crossing Laplacian.
\begin{table}[htbp]\centering
\caption{F1 trung bình trên 10 ảnh BSDS; cùng ngưỡng cho hai nguồn}\label{tab:duc10_bsds}
\begin{tabular}{rrrr}\toprule
$\sigma$ & Python & Fiji & Fiji--Python \\\midrule
__BSDS__
\bottomrule\end{tabular}\end{table}

\subsection{Tầng 2: ridge và blob}
DRIVE lấy cực đại Frangi qua các scale đã chuẩn hóa. Vùng đánh giá là giao các FOV hợp lệ qua scale, với support lấy từ config (hiện 32 px); ngưỡng tuyệt đối được chọn trong lưới đã công bố trên Python và dùng chung cho Fiji. Vì khác vùng FOV/ngưỡng, không so trực tiếp điểm này với phiên cũ dùng FOV 8 px hoặc phân vị p85.
Blob dùng đúng 7 sigma config cho cả hai nguồn, ghép một--một theo maximum cardinality với tâm lệch $\le2$ px và bán kính sai $\le20\%$. Bỏ dự đoán có tâm trong vùng ignore trước khi tính FP.
\begin{table}[htbp]\centering\small
\caption{Macro Precision/Recall/F1 của ridge và blob}\label{tab:duc10_accuracy}
\begin{tabular}{lrrr}\toprule
Nguồn / bài toán & P & R & F1 \\\midrule
__SUMMARY__
\bottomrule\end{tabular}\end{table}
\begin{table}[htbp]\centering
\caption{Ảnh tế bào: GT=276; dự đoán sau ignore; số bỏ qua}\label{tab:duc10_cells}
\begin{tabular}{lrrrr}\toprule
Nguồn & TP & Dự đoán & Ignore & F1 \\\midrule
__CELLS__
\bottomrule\end{tabular}\end{table}
Macro đặt mỗi ảnh cùng trọng số; micro gộp số đối tượng. Bốn ảnh tổng hợp dễ có ảnh hưởng lớn đến macro nên cần báo cáo cả hai. __MICRO__. Audit từng cặp được lưu đầy đủ trong CSV/JSON của phiên chạy.

\subsection{Biểu đồ và thời gian thực thi}
357 trường hợp mỗi nguồn được đo một warm-up và năm lượt đo, lấy median, giữ mẫu thô và fingerprint code/config/raw. Java đo API ImageScience headless, không gồm GUI hay đọc/ghi TIFF; không tuyên bố hai engine có precision nội bộ giống nhau hoặc ưu thế tốc độ trên mọi máy.
__FIGURES__

\subsection{Giới hạn}
Ngưỡng được chọn và đánh giá trên cùng tập nội bộ, không phải điểm test độc lập của benchmark chính thức. Chưa chạy biến thể nhiễu/kích thước; không kết luận độ bền với nhiễu. Nhãn tế bào do nhóm rà soát; trường hợp dính/cắt biên được loại theo vùng ignore. Detector LoG hiện bỏ hai đầu lưới scale, nên đối tượng ngoài dải vẫn có thể làm giảm recall.

\section{Chương 6: Kết Luận và Hướng Phát Triển}
Nhóm đã hiện thực Gaussian, đạo hàm bậc 1/2, gradient, Hessian, Canny, Frangi, LoG và Structure Tensor bằng NumPy; kiểm thử và đánh giá trên hai nguồn bản đồ cùng hậu xử lý. Kết quả số học chưa đạt ngưỡng gốc cho mọi cặp; giữ rõ STRICT và RELAXED. Đánh giá GT áp dụng matching một--một, ignore và cùng cấu hình cho hai nguồn. Công việc tiếp theo là kiểm chứng hiệu chuẩn, mở rộng dữ liệu/tập tách biệt và thực nghiệm nhiễu trước khi đưa ra kết luận khái quát.

'''
    figures=[]
    for stem,caption in [('04_f1_theo_sigma','F1 theo sigma trên cùng protocol.'),('08_blob_macro_micro','Macro/micro F1 trên tập blob.'),('09_thoi_gian_theo_lenh','Median thời gian theo lệnh; API headless, không gồm I/O.')]:
        name=f'duc10_{stem}.png'
        shutil.copyfile(TASK5/'figures'/f'{stem}.png',report.parent/'figures'/name)
        figures.append(r'\begin{figure}[htbp]\centering\includegraphics[width=\linewidth]{figures/'+name+'}\\caption{'+caption+r'}\end{figure}')
    generated=generated.replace('__BSDS__',bsds_table).replace('__SUMMARY__',summary_table).replace('__CELLS__',cell_table).replace('__FIGURES__','\n'.join(figures)).replace('__MICRO__',micro_text)
    chapter6=generated.index('\\section{Chương 6:')
    parts={'CH5':generated[:chapter6], 'CH6':generated[chapter6:]}
    marked={key:f'% BEGIN AUTO_{key}\n{value.strip()}\n% END AUTO_{key}' for key,value in parts.items()}
    if all(f'% BEGIN AUTO_{key}' in text for key in parts):
        for key,value in marked.items():
            text=re.sub(rf'(?ms)^% BEGIN AUTO_{key}\n.*?^% END AUTO_{key}',lambda m,v=value:v,text)
        report.write_text(text,encoding='utf-8')
    else:
        report.write_text(text[:chapters[0].start()]+'\n'+marked['CH5']+'\n\n'+marked['CH6']+'\n\n'+trailer,encoding='utf-8')
    print(f'Synchronized {report} and {out}')


if __name__=='__main__':
    main()
