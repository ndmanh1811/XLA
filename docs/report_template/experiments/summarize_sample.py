"""Create report tables and figures from genuine local sample artifacts."""
from pathlib import Path
import argparse, csv, collections, json, platform, shutil
import numpy as np
import tifffile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repo",required=True,type=Path)
args=parser.parse_args()
report=Path(__file__).resolve().parent.parent
sample=args.repo/"experiments/sample_local"
rows=list(csv.DictReader((sample/"sample_comparison.csv").open(encoding="utf-8-sig")))
assert len(rows)==72 and all(r["relative_max_error"] and r["pearson"] for r in rows)
for name in ("sample_comparison.csv","fiji_api_sample_log.csv","fiji_api_run.txt","java_runtime.txt"):
    shutil.copy2(sample/name,report/"metrics"/name)
build=json.loads((report.parent/".xla_review_tmp/build_provenance.json").read_text(encoding="utf-8"))
build[0]["source_tree"]="e57c3f3e6d74727a3690f441b34c54a00aa115ff"
build[1]["source_tree"]="9c47659ea7ca773548f667d01ee7e35d16341f79"
(report/"metrics/local_build_provenance.json").write_text(json.dumps(build,indent=2),encoding="utf-8")
operators=("gauss","lx","ly","lxx","lxy","lyy")
labels={"gauss":"Gauss","lx":r"$L_x$","ly":r"$L_y$","lxx":r"$L_{xx}$","lxy":r"$L_{xy}$","lyy":r"$L_{yy}$"}
states=collections.Counter(r["status"] for r in rows)
minimum=min(float(r["pearson"]) for r in rows)
maximum=max(float(r["relative_max_error"]) for r in rows)
mean=float(np.mean([float(r["pearson"]) for r in rows]))
text=r"""\subsection{Kết quả tái chạy mẫu tại máy biên tập}
Ngoài các bảng nhóm được giữ nguyên nguồn, một lần chạy mới được thực hiện trên ba ảnh
\texttt{bsds\_01}, \texttt{drive\_01}, \texttt{blob\_01}, bốn mức tỷ lệ từ config
và sáu toán tử $L,L_x,L_y,L_{xx},L_{xy},L_{yy}$. Nhân NumPy được lấy nguyên từ
repo tại commit \texttt{58e28e7}; đầu ra tham chiếu được tính thực sự bằng
ImageScience API với các thư viện của Fiji. Mỗi nhánh xuất 72 TIFF float32 không nén.

ImageJ dùng trong lần chạy là 1.54p, ImageScience là 3.1.0; Java là Temurin
21.0.12.1. FeatureJ được cài bằng bản build cục bộ từ nguồn chính thức
(\texttt{2.0.1-SNAPSHOT-local}). Lần xuất TIFF này gọi API ImageScience trực tiếp,
không đi qua hộp thoại plugin và không tạo ảnh chụp GUI. Vì khác nguồn và phiên bản
so với snapshot nhóm, các kết quả mới được báo cáo trong bảng riêng.

Python chạy ở phiên bản """+platform.python_version()+r""", NumPy """+np.__version__+r"""
và tifffile """+tifffile.__version__+r""". Các tham số $\sigma$, bán kính kernel và
kiểu biên đọc từ config.yaml; bản đồ thô được so khớp sau khi loại dải biên.
Không dùng các PNG minh họa để tính sai số.

"""
text+=f"Có đủ 72 cặp hợp lệ, {states.get('PASS_STRICT',0)} cặp đạt STRICT và {states.get('PASS_RELAXED',0)} cặp đạt RELAXED. "
text+=("Pearson nhỏ nhất là $%.8f$, trung bình $%.8f$; sai số cực đại tương đối lớn nhất là $%.4f\\%%$.\n"%(minimum,mean,100*maximum))
text+=r"""
\begin{table*}[t]
\centering
\caption{Đối chiếu 72 bản đồ tính mới qua ImageScience API và nhân NumPy; relative error theo công thức~\eqref{eq:relmax}}
\begin{tabular}{lrrrrrr}
\toprule
Toán tử & $N$ & STRICT & RELAXED & Rel TB & Rel lớn nhất & Pearson nhỏ nhất\\
\midrule
"""
for op in operators:
    sub=[r for r in rows if r["operator"]==op]
    c=collections.Counter(r["status"] for r in sub)
    vals=[float(r["relative_max_error"]) for r in sub]
    text+=f"{labels[op]} & {len(sub)} & {c['PASS_STRICT']} & {c['PASS_RELAXED']} & {np.mean(vals):.3e} & {max(vals):.3e} & {min(float(r['pearson']) for r in sub):.8f} "+r"\\"+"\n"
text+=r"""\bottomrule
\end{tabular}
\label{tab:local_sample}
\end{table*}

Các con số cho thấy phép đối chiếu mới tái hiện mức tương đồng cao trên tập mẫu:
Gaussian và một số đạo hàm bậc nhất đạt tiêu chí nghiêm ngặt, còn các bản đồ khác
có sai số hệ thống nằm dưới ngưỡng nới lỏng. Kết luận giới hạn trong 72 cặp đã đo;
không suy ra lại F1/IoU trên 25 ảnh từ lần chạy này. Thời gian trong log API là
thời gian của phép lọc đơn lẻ, chưa có quy trình lặp và loại warm-up, nên chưa
được dùng để công bố một hệ số tăng tốc Python--Fiji.

Các hình sau dùng chung thang màu cho cặp Python và ImageScience của từng toán tử.
Hàng sai khác có thanh màu riêng để nhìn vị trí sai số; độ đậm của hàng này phải
đọc cùng trị số trên colorbar. Hình hiển thị toàn ảnh, trong khi CSV tính điểm sau crop.
"""
for name in ("bsds_01","drive_01","blob_01"):
    fig,axes=plt.subplots(3,3,figsize=(11,10),constrained_layout=True)
    for j,op in enumerate(("gauss","lx","lxx")):
        p=tifffile.imread(sample/"python"/f"py_{name}_{op}_s2.0.tif").astype(float)
        f=tifffile.imread(sample/"fiji"/f"fiji_{name}_{op}_s2.0.tif").astype(float)
        lo=min(float(p.min()),float(f.min())) if op=="gauss" else -max(np.abs(p).max(),np.abs(f).max())
        hi=max(float(p.max()),float(f.max())) if op=="gauss" else -lo
        for i,a in enumerate((p,f)):
            im=axes[i,j].imshow(a,cmap="gray" if op=="gauss" else "RdBu_r",vmin=lo,vmax=hi)
            axes[i,j].set_title(("Python" if i==0 else "ImageScience API")+" / "+op,fontsize=12)
        fig.colorbar(im,ax=list(axes[:2,j]),shrink=.65)
        d=p-f
        limit=max(float(np.abs(d).max()),1e-12)
        im=axes[2,j].imshow(d,cmap="RdBu_r",vmin=-limit,vmax=limit)
        axes[2,j].set_title("Python - ImageScience",fontsize=12)
        fig.colorbar(im,ax=axes[2,j],shrink=.65)
    for ax in axes.flat: ax.axis("off")
    fig.suptitle(f"{name}, sigma = 2.0; fresh local sample",fontsize=15)
    fig.savefig(report/"figures"/f"local_{name}_comparison.png",dpi=300)
    plt.close(fig)
    text+=r"\begin{figure*}[p]"+"\n"+r"\centering"+"\n"
    text+=r"\includegraphics[width=0.94\textwidth]{figures/local_"+name+r"_comparison.png}"+"\n"
    text+=r"\caption{Đối chiếu mẫu "+name.replace("_",r"\_")+r" tại $\sigma=2$: cột Gaussian, $L_x$, $L_{xx}$; hàng Python, ImageScience API và sai khác. Đây là dữ liệu tính mới, không phải ảnh chụp giao diện Fiji.}"+"\n"
    text+=r"\label{fig:local_"+name+"}\n"+r"\end{figure*}"+"\n\n"
(report/"sections/sample_results.tex").write_text(text,encoding="utf-8")
appendix=r"""\appendices
\section{Hồ Sơ và Cách Tái Lập Lần Chạy Mẫu}
Mã chạy kèm báo cáo gồm \texttt{SampleFeatureJ.java}, \texttt{run\_fiji\_api\_sample.py},
\texttt{run\_sample.py} và \texttt{sample\_featurej.ijm}.
Hai chương trình đầu tạo bản đồ qua API ImageScience; chương trình Python dùng
nhân repo để tính và chấm; macro dành cho thực hành qua lệnh plugin trong GUI.
Hướng dẫn thao tác và lệnh đầy đủ nằm trong tệp \texttt{HUONG\_DAN\_THUC\_NGHIEM.md}.

Repo tại máy biên tập là bản shallow/sparse đúng commit gốc, gồm mã nguồn,
25 ảnh raw và CSV cần thiết. Các bộ TIFF, archive lớn và phần ground truth ngoài
phạm vi mẫu chưa được tải đầy đủ. Vì thế không coi lần chạy mẫu là một lần
tái lập benchmark toàn bộ 25 ảnh; các bảng F1 tổng hợp vẫn có nguồn là CSV nhóm.

\subsection{Các bước thực hiện}
\begin{enumerate}
\item Kiểm tra commit, config.yaml và ba PNG gốc; không chuyển màu lần nữa.
\item Chạy exporter API với ImageScience được cài trong Fiji; lưu TIFF và log nguồn.
\item Chạy chương trình Python với cùng repo, tỷ lệ và toán tử.
\item Kiểm tra đủ 72 cặp, float32, kích thước, giá trị hữu hạn và dải crop.
\item Lưu CSV và tạo hình từ chính TIFF; giữ các file nhóm trong outputs riêng.
\end{enumerate}

\subsection{Minh chứng GUI bổ sung}
Lần chạy API đã hoàn thành nhưng chưa chụp ảnh thao tác hộp thoại FeatureJ.
Để bổ sung minh chứng này, mở Fiji, đặt đơn vị pixel và 32-bit sau mỗi lần mở ảnh,
chạy Derivatives hoặc Hessian với tham số nhìn thấy trong hộp thoại, rồi lưu ảnh
chụp cùng TIFF. Macro GUI ghi sang \texttt{experiments/sample\_gui\_local}, tách
khỏi thư mục API \texttt{experiments/sample\_local}. Đối chiếu GUI bằng
\texttt{run\_sample.py} với tùy chọn \texttt{--run-name sample\_gui\_local}.

\subsection{Nguồn và phiên bản thư viện}
Các JAR cục bộ được biên dịch từ nguồn chính thức ImageScience/FeatureJ, không
chỉnh sửa thuật toán vi phân. Tệp \texttt{metrics/local\_build\_provenance.json}
ghi phiên bản, mã băm nguồn và SHA256 JAR. Bản build này phục vụ thí nghiệm tại chỗ;
không được diễn giải như cùng tệp nhị phân với bộ tham chiếu nhóm.

\section{Sai Số Chi Tiết của 72 Cặp Mẫu}
Các bảng sau ghi sai số từng bản đồ mới. MAE, RMSE và sai số tương đối được
tính sau crop; cột R/S lần lượt chỉ RELAXED/STRICT. Các hàng chưa làm tròn trong
CSV là nguồn để tính các giá trị tổng hợp.
"""
for name in ("bsds_01","drive_01","blob_01"):
    appendix+=r"\begin{table*}[p]"+"\n"+r"\centering"+"\n"
    appendix+=r"\caption{Sai số mẫu "+name.replace("_",r"\_")+r" (24 bản đồ)}"+"\n"
    appendix+=r"\begin{tabular}{lrrrrrr}"+"\n"+r"\toprule"+"\n"
    appendix+=r"Toán tử & $\sigma$ & MAE & RMSE & Rel max & Pearson & Loại\\"+"\n"+r"\midrule"+"\n"
    for r in [r for r in rows if r["image"]==name]:
        state="S" if r["status"]=="PASS_STRICT" else "R" if r["status"]=="PASS_RELAXED" else "!"
        appendix+=f"{labels[r['operator']]} & {float(r['sigma']):g} & {float(r['mae']):.3e} & {float(r['rmse']):.3e} & {float(r['relative_max_error']):.3e} & {float(r['pearson']):.8f} & {state} "+r"\\"+"\n"
    appendix+=r"\bottomrule"+"\n"+r"\end{tabular}"+"\n"+r"\end{table*}"+"\n\n"
(report/"sections/reproduction.tex").write_text(appendix,encoding="utf-8")
print("Created measured sample tables, three figures and the detailed reproduction appendix.")
