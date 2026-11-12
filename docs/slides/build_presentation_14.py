"""Build a separate, light/black 14-slide presentation from verified project data.

python docs/slides/build_presentation_14.py
Leaves the canonical 10-slide builder and presentation unchanged.
"""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import tifffile
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
from src.eval.analyze_task5 import verify_metric_delivery, validate_runtime
from src.eval.metric_utils import RESULTS, sha256, strict_config
from src.eval.task5_runtime import TASK5, read_csv

OUT = Path(__file__).resolve().parent
ASSETS = OUT / 'thuyet_trinh_14/assets'
FILE = OUT / 'BTL_XLA_ThuyetTrinh_14_Slide.pptx'
FONT = 'Arial'
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
LIGHT = (246, 246, 246)
LINE = (210, 210, 210)
W, H = 13.333333, 7.5
NOTES = []
INPUTS = set()


def tracked(path):
    path = Path(path)
    INPUTS.add(path)
    return path


def csv(path):
    return read_csv(tracked(path))


def raw(name):
    return np.asarray(Image.open(tracked(ROOT / f'data/raw/{name}.png')))


def response(name, op, sigma):
    return tifffile.imread(tracked(ROOT / f'outputs/python/py_{name}_{op}_s{float(sigma)}.tif'))


def finish_plot(fig, name):
    path = ASSETS / f'{name}.png'
    fig.savefig(path, dpi=200, facecolor='white', bbox_inches='tight', pad_inches=.12)
    plt.close(fig)
    return path


def make_assets(edge, t1, summary, runtime, cfg):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 13,
                         'text.color': 'black', 'axes.labelcolor': 'black',
                         'xtick.color': 'black', 'ytick.color': 'black',
                         'axes.spines.top': False, 'axes.spines.right': False})
    assets = {}
    fig, ax = plt.subplots(figsize=(4.1, 3.2))
    x = np.linspace(-9, 9, 400)
    for sigma, color, style in [(1, 'black', '-'), (2, '.4', '--'), (4, '.65', ':')]:
        ax.plot(x, np.exp(-x*x/(2*sigma*sigma))/(np.sqrt(2*np.pi)*sigma),
                color=color, linestyle=style, linewidth=2.3, label=f'σ = {sigma}')
    ax.set(xlabel='Khoảng cách x', ylabel='Gσ(x)')
    ax.legend(frameon=False)
    assets['cover'] = finish_plot(fig, '01_gaussian_kernel')

    fig, axes = plt.subplots(1, 4, figsize=(12, 3.15))
    for ax, sigma in zip(axes, cfg['sigmas']):
        ax.imshow(response('bsds_01', 'gauss', sigma), cmap='gray', vmin=0, vmax=255)
        ax.set_title(f'σ = {sigma:g}', fontsize=17, pad=10)
        ax.axis('off')
    assets['scale'] = finish_plot(fig, '03_scale_space')

    fig, axes = plt.subplots(1, 3, figsize=(11.8, 3.1))
    for ax, op, label in zip(axes, ['gauss', 'grad', 'lxx'], ['Ảnh làm mịn L', 'Độ lớn gradient |∇L|', 'Đạo hàm bậc 2 Lxx']):
        a = response('bsds_01', op, 2)
        if op == 'lxx':
            peak = np.percentile(np.abs(a), 99.5)
            ax.imshow(a, cmap='gray', vmin=-peak, vmax=peak)
        else:
            ax.imshow(a, cmap='gray')
        ax.set_title(label, fontsize=16, pad=10)
        ax.axis('off')
    assets['derivatives'] = finish_plot(fig, '04_derivative_maps')

    fig, ax = plt.subplots(figsize=(6.3, .54))
    ax.axis('off')
    ax.text(.01,.5,r'$D_{\mathrm{norm}}^{(n)} = \sigma^{n\gamma} D^{(n)},\quad \gamma=1$',
            fontsize=24,va='center',color='black')
    assets['normalization'] = finish_plot(fig, '04_normalization_formula')

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
    for ax, image, label in zip(axes, ['bsds_01', 'drive_01', 'blob_05'], ['BSDS500 — cạnh', 'DRIVE — mạch máu', 'Blob — tế bào']):
        ax.imshow(raw(image), cmap='gray', vmin=0, vmax=255)
        ax.set_title(label, fontsize=17, pad=10)
        ax.axis('off')
    assets['dataset'] = finish_plot(fig, '02_dataset_examples')

    ops = list(dict.fromkeys(r['operator'] for r in t1))
    ratios = [100 * sum(r['status']=='PASS' for r in t1 if r['operator']==op)/sum(r['operator']==op for r in t1) for op in ops]
    fig, ax = plt.subplots(figsize=(7.2, 3.75))
    ax.bar(range(len(ops)), ratios, color='.25', width=.65)
    ax.set_xticks(range(len(ops)), ['G' if op=='gauss' else op for op in ops], rotation=35, ha='right')
    ax.set(ylim=(0, 115), ylabel='% cặp đạt STRICT')
    for i, v in enumerate(ratios):
        ax.text(i, v+3, f'{v:g}', ha='center', fontsize=12)
    ax.grid(axis='y', color='.9')
    ax.set_axisbelow(True)
    assets['t1'] = finish_plot(fig, '10_strict_by_operator')

    fig, ax = plt.subplots(figsize=(7.2, 3.75))
    scales = [float(r['sigma']) for r in edge]
    for key, label, style, marker, color in [('python_f1','Python','-','o','black'),('fiji_f1','Fiji + cùng Canny','--','s','.5')]:
        ax.plot(scales, [float(r[key]) for r in edge], linestyle=style, marker=marker,
                color=color, linewidth=2.4, markersize=8, label=label, markerfacecolor='white' if key=='fiji_f1' else color)
    ax.set(xlabel='Tỷ lệ σ', ylabel='Mean F1 trên 10 ảnh', xticks=scales, ylim=(.3,.53))
    ax.grid(color='.9')
    ax.legend(frameon=False, fontsize=12, loc='lower left')
    assets['edge'] = finish_plot(fig, '11_edge_f1')

    lookup = {(r['source'],r['task']):r for r in summary if r['task']!='edge_bsds'}
    fig, ax = plt.subplots(figsize=(7.15, 3.65))
    categories = ['DRIVE\nMacro F1', 'Blob\nMacro F1', 'Blob\nMicro F1']
    pos = np.arange(3)
    for source, dx, color, hatch in [('python',-.18,'.22',''),('fiji',.18,'.82','//')]:
        vals = [float(lookup[source,'ridge_drive']['macro_f1']),float(lookup[source,'blob_log']['macro_f1']),float(lookup[source,'blob_log']['micro_f1'])]
        ax.bar(pos+dx, vals, width=.34, color=color, edgecolor='black', hatch=hatch, label='Python' if source=='python' else 'Fiji')
        for x0, value in zip(pos+dx, vals):
            ax.text(x0,value+.025,f'{value:.3f}',ha='center',fontsize=12)
    ax.set(xticks=pos,xticklabels=categories,ylim=(0,1.18),ylabel='F1')
    ax.grid(axis='y',color='.9')
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc='upper center', ncol=2)
    assets['ridge_blob'] = finish_plot(fig,'12_ridge_blob_scores')

    fig, ax = plt.subplots(figsize=(7.0, 3.65))
    groups = list(dict.fromkeys(r['command'] for r in runtime))
    groups.sort()
    # Runtime column names come from the canonical paired table.
    for source, dx, color, hatch in [('python',-.18,'.22',''),('fiji_engine',.18,'.82','//')]:
        vals = [np.median([float(r[f'{source}_median_ms']) for r in runtime if r['command']==op]) for op in groups]
        ax.bar(np.arange(len(groups))+dx, vals, width=.35, label='Python' if source=='python' else 'ImageScience', color=color, edgecolor='black', hatch=hatch)
    ax.set_xticks(np.arange(len(groups)),groups,rotation=35,ha='right')
    ax.set_ylabel('Median thời gian / case (ms)')
    ax.grid(axis='y',color='.9'); ax.set_axisbelow(True)
    ax.legend(frameon=False)
    assets['runtime'] = finish_plot(fig,'13_runtime')
    return assets


def rect(slide,x,y,w,h,fill=LIGHT,line=None,radius=False):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                  Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid(); shape.fill.fore_color.rgb=RGBColor(*fill)
    if line:
        shape.line.color.rgb=RGBColor(*line);shape.line.width=Pt(.8)
    else:
        shape.line.fill.background()
    return shape


def text(slide,x,y,w,h,content,size=20,bold=False,align=PP_ALIGN.LEFT):
    shape=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    tf=shape.text_frame
    tf.clear();tf.word_wrap=True
    tf.margin_left=0;tf.margin_right=0;tf.margin_top=0;tf.margin_bottom=0
    for i,line in enumerate(content.split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.text=line;p.alignment=align;p.font.name=FONT;p.font.size=Pt(size)
        p.font.bold=bold;p.font.color.rgb=RGBColor(*BLACK)
        p.space_after=Pt(7);p.line_spacing=1.12
    return shape


def picture(slide,path,x,y,w,h):
    with Image.open(path) as img:
        aspect=img.width/img.height
    width=min(w,h*aspect);height=width/aspect
    slide.shapes.add_picture(str(path), Inches(x+(w-width)/2), Inches(y+(h-height)/2),width=Inches(width),height=Inches(height))


def bullet_list(slide,x,y,w,items,size=21,gap=.76):
    for i,item in enumerate(items):
        text(slide,x,y+i*gap,.18,.4,'•',size)
        text(slide,x+.3,y+i*gap,w-.3,gap-.07,item,size)


def card(slide,x,y,w,h,title,body,size=20):
    rect(slide,x,y,w,h)
    text(slide,x+.22,y+.18,w-.44,.58,title,23,True)
    text(slide,x+.22,y+.95,w-.44,h-1.1,body,size)


def new_slide(prs,section,title,takeaway,notes):
    slide=prs.slides.add_slide(prs.slide_layouts[6]);i=len(prs.slides)
    slide.background.fill.solid();slide.background.fill.fore_color.rgb=RGBColor(*WHITE)
    text(slide,.55,.23,11.5,.3,section.upper(),12,True)
    if title:
        text(slide,.55,.75,12.25,.66,title,30,True)
        rect(slide,.55,1.53,12.23,.012,fill=BLACK)
    if takeaway:
        rect(slide,.55,6.35,12.23,.56)
        text(slide,.73,6.47,11.85,.38,takeaway,16,True)
    text(slide,.55,7.13,11.6,.2,'GAUSSIAN ĐA TỶ LỆ  |  FEATUREJ × NUMPY',10)
    text(slide,12.0,7.08,.78,.3,f'{i:02d} / 14',12)
    slide.notes_slide.notes_text_frame.text=notes
    NOTES.append((title,section,notes))
    return slide


def build():
    ASSETS.mkdir(parents=True,exist_ok=True)
    tracked(Path(__file__).resolve())
    verify_metric_delivery()
    cfg=strict_config()
    validate_runtime(TASK5/'runtime',cfg)
    am=json.loads(tracked(TASK5/'analysis_manifest.json').read_text(encoding='utf-8'))
    check=am['status']=='COMPLETE' and am['metric_manifest_sha256']==sha256(RESULTS/'run_manifest.json')
    if not check: raise ValueError('Complete current analysis before building presentation')
    tracked(RESULTS/'run_manifest.json');tracked(ROOT/'config.yaml')
    for name,digest in am['outputs'].items():
        if sha256(TASK5/name)!=digest: raise ValueError(f'Analysis output changed: {name}')
    edge=csv(TASK5/'tables/edge_by_sigma.csv')
    summary=csv(RESULTS/'tier2_summary.csv');rows=csv(RESULTS/'tier2_results_both.csv')
    t1=csv(RESULTS/'tier1_report.csv');runtime=csv(TASK5/'runtime/runtime_paired.csv')
    best=max(edge,key=lambda r:float(r['python_f1']))
    lookup={(r['source'],r['task']):r for r in summary if r['task']!='edge_bsds'}
    cells={r['source']:r for r in rows if r['image']=='blob_05'}
    ann=json.loads(tracked(ROOT/'data/gt/blob/blob_05.json').read_text(encoding='utf-8'))
    t1_counts=Counter(r['status'] for r in t1)
    ratio=float(np.median([float(r['ratio_python_over_engine']) for r in runtime]))
    assets=make_assets(edge,t1,summary,runtime,cfg)
    prs=Presentation();prs.slide_width=Inches(W);prs.slide_height=Inches(H)
    prs.core_properties.title='Phát hiện đặc trưng ảnh đa tỷ lệ bằng đạo hàm Gaussian'
    prs.core_properties.subject='Thuyết trình 14 slide — FeatureJ và Python NumPy'
    prs.core_properties.author='Nguyễn Tiến Hưng; Nguyễn Đức Mạnh; Phạm Bảo Lộc; Bùi Trung Đức'

    s=new_slide(prs,'Bài tập lớn · Xử lý ảnh số','',None,
        'Giới thiệu đề tài và bốn thành viên. Nêu mục tiêu: cùng một nền tảng đạo hàm Gaussian để phân tích cạnh, gờ và đốm ở nhiều kích thước. Python tự cài, FeatureJ là nguồn tham chiếu. Dành khoảng 40 giây.')
    text(s,.62,.87,8.0,2.35,'Phát hiện đặc trưng ảnh\nđa tỷ lệ bằng\nđạo hàm Gaussian',36,True)
    text(s,.65,3.55,7.5,.9,'Từ mô hình toán học đến cài đặt,\nđối chuẩn và đánh giá thực nghiệm',23)
    text(s,.65,5.0,7.8,.9,'Nguyễn Tiến Hưng · Nguyễn Đức Mạnh\nPhạm Bảo Lộc · Bùi Trung Đức',20)
    text(s,.65,6.4,8,.4,'FeatureJ / Fiji  •  Python / NumPy  •  25 ảnh thực nghiệm',16)
    picture(s,assets['cover'],8.65,1.35,4.1,4.7)

    s=new_slide(prs,'01 · Giới thiệu','Bài toán và mục tiêu',
        'Cùng một ảnh, thay đổi tỷ lệ σ sẽ làm nổi bật các cấu trúc khác nhau.',
        'Mở đầu bằng ba loại đặc trưng. Cạnh là chuyển mức sáng; ridge là cấu trúc dài mảnh; blob là vùng đậm/sáng cục bộ. Mục tiêu thứ nhất là tự cài đúng, thứ hai so bản đồ với FeatureJ, thứ ba chấm phát hiện với GT. Dẫn vào lộ trình lý thuyết → cài đặt → thực nghiệm → kết luận.')
    card(s,.6,1.9,3.85,2.65,'CẠNH · EDGE','Biên vật thể và vùng\nchuyển mức sáng.\nVí dụ: ảnh tự nhiên.')
    card(s,4.74,1.9,3.85,2.65,'GỜ · RIDGE','Cấu trúc dài, mảnh.\nVí dụ: hệ mạch máu\ntrên ảnh võng mạc.')
    card(s,8.88,1.9,3.85,2.65,'ĐỐM · BLOB','Cấu trúc cục bộ\nvới nhiều kích thước.\nVí dụ: nhân tế bào.')
    text(s,.72,5.05,12,.9,'Tự cài NumPy  →  Đối chuẩn FeatureJ  →  Đánh giá bằng Ground Truth',23,True)

    s=new_slide(prs,'02 · Cơ sở lý thuyết','Gaussian smoothing và scale-space',
        'σ nhỏ giữ chi tiết; σ lớn ưu tiên cấu trúc lớn và giảm chi tiết nhỏ.',
        'Giải thích L=Gσ*I và tính tách trục. Ảnh minh họa đọc từ TIFF Python đã tính, cùng bsds_01 ở bốn sigma. Không so sáng từng ảnh bằng chuẩn hóa riêng: dải hiển thị 0–255 được giữ chung. Scale-space là họ ảnh theo sigma, không phải chỉ phóng to/thu nhỏ ảnh. Nguồn lý thuyết: Lindeberg, Scale-Space Theory in Computer Vision (1994).')
    text(s,.7,1.85,11.9,.6,'L(x, y; σ) = Gσ * I     ·     Gσ(x, y) = gσ(x) gσ(y)',26,True)
    picture(s,assets['scale'],.58,2.65,12.2,3.05)
    text(s,.72,5.8,11.9,.35,'Tích chập tách trục: lọc theo hàng rồi cột để giảm chi phí tính toán.',18)

    s=new_slide(prs,'02 · Cơ sở lý thuyết','Đạo hàm Gaussian, gradient và chuẩn hóa',
        'Với γ = 1: bậc 1 nhân σ; bậc 2, Laplacian và Hessian nhân σ².',
        'Lx, Ly được tạo bằng tích chập với đạo hàm Gaussian; gradient biểu diễn độ biến thiên và hướng. Laplacian là tổng Lxx+Lyy. Phân biệt chuẩn hóa tỷ lệ ở tầng detector và giữ bản đồ thô khi đối chuẩn. Không gọi bậc 2 là gamma=2. Ba ảnh cùng sigma=2, Lxx dùng thang xám có tâm 0; dải hiển thị khác nhau nên không suy biên độ từ độ sáng giữa các panel. Nguồn: Lindeberg (1998), Feature Detection with Automatic Scale Selection.')
    text(s,.72,1.85,12,.55,'∇L = (Lx, Ly)      |∇L| = √(Lx² + Ly²)      ∇²L = Lxx + Lyy',25,True)
    picture(s,assets['normalization'],.72,2.43,5.8,.59)
    text(s,6.65,2.56,6.0,.45,'Hướng gradient: atan2(Ly, Lx)',21)
    picture(s,assets['derivatives'],.6,3.08,12.15,2.92)

    s=new_slide(prs,'02 · Cơ sở lý thuyết','Hessian và Structure Tensor',
        'Hessian mô tả độ cong cục bộ; Structure Tensor mô tả hướng và tính kết hợp.',
        'Hessian dùng đạo hàm bậc hai, trị riêng cho biết độ cong theo các hướng chính. Ridge chọn cấu trúc một hướng cong mạnh; blob có độ cong ở nhiều hướng. Structure Tensor lấy tích các đạo hàm bậc một rồi làm mịn ở scale tích phân; coherence phản ánh tính trội của một hướng. Hessian có dấu; tensor cấu trúc lý tưởng bán xác định dương. Bộ đối chuẩn giữ thứ tự algebraic; Frangi tự xếp trị riêng theo độ lớn. Không đồng nhất hai ma trận này.')
    card(s,.65,1.9,5.85,3.95,'HESSIAN · ĐẠO HÀM BẬC 2','H = [[Lxx, Lxy], [Lxy, Lyy]]\n\nTrị riêng λ₁, λ₂ mô tả độ cong.\nỨng dụng: ridge và blob.\nLaplacian = trace(H).',21)
    card(s,6.83,1.9,5.85,3.95,'STRUCTURE TENSOR · HƯỚNG','J = Gσᵢ * (∇Lσᵈ ∇Lσᵈᵀ)\n\nHai tỷ lệ: vi phân và tích phân.\nCoherence = (μ₁ − μ₂)/(μ₁ + μ₂ + ε).\nỨng dụng: phân tích cấu trúc.',21)

    s=new_slide(prs,'03 · Phương pháp','Từ đạo hàm đến ba bộ phát hiện',
        'FeatureJ Edges dùng Canny; không phải zero-crossing của Laplacian.',
        'Đi lần lượt ba nhánh. Canny từ gradient qua NMS và hysteresis. Python dùng 4 sector NMS và liên thông 8 lân cận; FeatureJ có nội suy riêng nên native Edges chỉ là tham chiếu riêng. Frangi dùng Hessian chuẩn hóa, giữ tín hiệu ridge phù hợp dấu và lấy cực đại các scale. Blob tìm cực trị không gian–tỷ lệ của LoG chuẩn hóa; blob sáng tìm cực tiểu. Bán kính xấp xỉ sqrt(2)*sigma. Tham khảo Canny (1986), Frangi et al. (1998), Lindeberg (1998).')
    card(s,.6,1.95,3.85,3.8,'EDGE · CANNY','Lx, Ly → gradient\n↓\nNMS theo hướng\n↓\nNgưỡng kép + hysteresis',21)
    card(s,4.74,1.95,3.85,3.8,'RIDGE · FRANGI','Hessian chuẩn hóa σ²\n↓\nTrị riêng → vesselness\n↓\nLấy max qua các scale',21)
    card(s,8.88,1.95,3.85,3.8,'BLOB · LoG','σ²(Lxx + Lyy)\n↓\nCực trị 3D: x, y, σ\n↓\nTâm và bán kính đốm',21)

    s=new_slide(prs,'04 · Thực hiện','Dữ liệu thực nghiệm và Ground Truth',
        '25 ảnh; nhãn BSDS/DRIVE từ bộ dữ liệu, nhãn tế bào do nhóm rà soát.',
        f'BSDS có 10 ảnh, tổng 56 bộ nhãn ranh giới; DRIVE có 10 ảnh, vessel mask và FOV. Blob gồm 4 ảnh tổng hợp và 1 ảnh tế bào blob_05: {len(ann["objects"])} đối tượng, {len(ann["ignore_regions"])} vùng ignore. Tất cả raw uint8 xám lossless. BSDS theo BT.601, DRIVE lấy green. Không gọi nhãn blob_05 là nhãn chuyên gia của nhà cung cấp. Nguồn: data/SOURCES.md, data/manifest.json và data/gt.')
    picture(s,assets['dataset'],.65,1.78,12.0,2.9)
    for x0,title,body in [(.7,'10 BSDS500','56 bộ nhãn ranh giới'),(4.88,'10 DRIVE','Vessel mask + FOV'),(9.05,'5 BLOB',f'4 tổng hợp + {len(ann["objects"])} tế bào\n{len(ann["ignore_regions"])} vùng loại trừ')]:
        text(s,x0,4.87,3.7,.45,title,23,True)
        text(s,x0,5.38,3.7,.89,body,19)

    s=new_slide(prs,'04 · Thực hiện','Triển khai hai nguồn trên cùng cấu hình',
        'Đọc raw/GT một lần theo quy ước; giữ nguyên tham số để so sánh hai nguồn.',
        'Giải thích hai nguồn bản đồ: Python tự cài từ kernel đến tích chập, đạo hàm và trị riêng; Fiji xuất từ FeatureJ/ImageScience. Hai nguồn cùng downstream detector. Nội bộ Python float64, lưu TIFF float32 không nén. Config chứa k theo lệnh, mirror, cờ normalization và dãy sigma; không tự đoán fallback. Hiệu chuẩn đã có 40 TIFF và số đo định lượng, còn ảnh giao diện cần Lộc bổ sung. SHA-256 xác minh toàn vẹn file của từng nguồn, không chứng minh Python byte-identical Fiji.')
    card(s,.65,1.88,5.8,2.15,'PYTHON · NUMPY TỰ CÀI','Kernel 1D → tích chập tách trục\nĐạo hàm → gradient / Hessian / tensor',21)
    card(s,6.85,1.88,5.8,2.15,'FIJI · FEATUREJ','Đo hiệu chuẩn → config.yaml\nMacro → bản đồ đáp ứng tham chiếu',21)
    rect(s,.65,4.35,12.0,1.45)
    text(s,.85,4.55,11.6,.45,'TIFF float32 không nén  →  Cùng detector  →  Cùng protocol chấm',23,True)
    scales=', '.join(f'{v:g}' for v in cfg['sigmas'])
    text(s,.85,5.15,11.6,.4,f'σ chính: {scales}  |  Blob: {len(cfg["sigmas_blob"])} scale  |  Biên: {cfg["border_mode"]}',19)

    s=new_slide(prs,'04 · Thiết kế thực nghiệm','Hai tầng đánh giá: độ khớp và độ chính xác',
        'Ngưỡng chọn trên Python, áp nguyên cho Fiji; đây là đánh giá trên tập nội bộ.',
        'Tầng 1 crop vùng lõi theo support từ config rồi so bản đồ thô: MSE, RMSE, relative max error, Pearson; PSNR MAX255 chỉ cho Gaussian. Tiêu chuẩn gốc đồng thời relative error<1e-4 và r>.9999. Tầng 2 chấm P/R/F1; BSDS dung sai Euclidean2px, precision any annotator, recall mean annotator; DRIVE giao FOV hợp lệ qua mọi scale (32px support hiện tại); blob matching maximum-cardinality một–một, tâm<=2px bán kính<=20%, áp ignore trước FP. Chọn và chấm cùng tập nên không gọi là test độc lập.')
    card(s,.65,1.9,5.82,3.95,'TẦNG 1 · BẢN ĐỒ LIÊN TỤC','220 cặp / 5 ảnh đại diện\nCrop lõi theo support của config\n\nMSE, RMSE, relative error, Pearson\nPSNR: chỉ áp dụng Gaussian',21)
    card(s,6.82,1.9,5.82,3.95,'TẦNG 2 · SO VỚI GROUND TRUTH','P = TP / (TP + FP)\nR = TP / (TP + FN)\nF1 = 2PR / (P + R)\n\nBlob: khớp một–một + ignore',21)

    s=new_slide(prs,'05 · Kết quả','Đối chuẩn số học: Gaussian khớp tốt nhất',
        'Pearson cao không đủ chứng minh cùng biên độ; giữ nguyên số đo không đạt.',
        f'Tầng 1 có {t1_counts["PASS"]} PASS STRICT trong {len(t1)} cặp; {t1_counts["FAIL"]} chưa đạt ngưỡng gốc. Gaussian20/20; đạo hàm bậc cao và tensor còn sai số hệ thống. Các cặp này đạt ngưỡng mở rộng 1e-2 theo phân tích cũ nhưng không được gọi đạt STRICT. Đáp ứng xung/hiệu chuẩn giúp kiểm tra cách rời rạc hóa, support và chuẩn hóa; chưa khẳng định nguyên nhân duy nhất. Biểu đồ tính từ tier1_report.csv của phiên hiện hành.')
    picture(s,assets['t1'],.62,1.85,7.6,4.28)
    text(s,8.65,2.0,3.7,.7,f'{t1_counts["PASS"]} / {len(t1)}',39,True)
    text(s,8.65,2.85,3.8,.55,'cặp đạt STRICT',23,True)
    text(s,8.65,3.65,3.75,1.1,'Relative error < 10⁻⁴\nvà Pearson r > 0,9999',21)
    text(s,8.65,5.1,3.8,.85,f'{t1_counts["FAIL"]} cặp còn vượt\nngưỡng gốc.',21)

    s=new_slide(prs,'05 · Kết quả','Cạnh: tỷ lệ trung gian cho F1 tốt hơn',
        'Trong dãy đã khảo sát, σ = 2 cho mean F1 cao nhất; không suy rộng mọi ảnh.',
        f'F1 trung bình Python cao nhất trong lưới là {float(best["python_f1"]):.6f} tại sigma={float(best["sigma"]):g}; Fiji cùng Canny {float(best["fiji_f1"]):.6f}. Hai đường gần trùng, marker rỗng giúp phân biệt. Đây là mean trên10ảnh, không phải F1 của một ảnh demo. Khi sigma tăng quá lớn, chi tiết/cạnh yếu có thể mất; đó là diễn giải xu hướng nội bộ. Native FeatureJ Edges không nằm trong hai đường vì NMS/ngưỡng khác. Nguồn edge_by_sigma.csv.')
    picture(s,assets['edge'],.62,1.85,7.55,4.3)
    text(s,8.65,2.03,3.65,.7,f'{float(best["python_f1"]):.4f}',39,True)
    text(s,8.65,2.9,3.7,.98,f'Mean F1 Python\ntại σ = {float(best["sigma"]):g}',23,True)
    text(s,8.65,4.12,3.65,1.95,'Cùng ngưỡng cho Fiji.\nDung sai cạnh: 2 px.\nĐường F1 gần trùng\ntrên tập đang khảo sát.',21)

    s=new_slide(prs,'05 · Kết quả','Ridge và blob: cần đọc cả macro lẫn micro',
        'Blob tổng hợp dễ hơn tế bào thật; macro F1 cao chưa phản ánh hết độ khó.',
        f'DRIVE macro F1 Python/Fiji={float(lookup["python","ridge_drive"]["macro_f1"]):.6f}/{float(lookup["fiji","ridge_drive"]["macro_f1"]):.6f}. Python precision={float(lookup["python","ridge_drive"]["macro_precision"]):.6f}, recall={float(lookup["python","ridge_drive"]["macro_recall"]):.6f}: còn bỏ sót. Blob macro/micro như biểu đồ. Bốn ảnh tổng hợp F1=1 nhưng blob_05 chỉ {float(cells["python"]["f1"]):.6f}/{float(cells["fiji"]["f1"]):.6f}; micro gộp số đối tượng nên phản ánh ảnh276nhãn nhiều hơn. Matching một–một và15ignore đã được dùng. Nguồn tier2_summary.csv và tier2_results_both.csv.')
    picture(s,assets['ridge_blob'],.62,1.83,7.55,4.3)
    text(s,8.65,1.98,3.6,.5,'DRIVE',24,True)
    text(s,8.65,2.63,3.65,1.1,f'P = {float(lookup["python","ridge_drive"]["macro_precision"]):.3f}\nR = {float(lookup["python","ridge_drive"]["macro_recall"]):.3f}  (Python)',22)
    text(s,8.65,4.0,3.6,.5,'TẾ BÀO THẬT',24,True)
    text(s,8.65,4.65,3.65,1.25,f'F1: {float(cells["python"]["f1"]):.3f} / {float(cells["fiji"]["f1"]):.3f}\nPython / Fiji\n{len(ann["objects"])} nhãn + {len(ann["ignore_regions"])} vùng ignore',20)

    s=new_slide(prs,'05 · Kết quả','Thời gian chạy và đánh đổi thực thi',
        'Số đo trên một máy/phiên; không kết luận tốc độ chung cho mọi môi trường.',
        f'{len(runtime)} case mỗi nguồn,1warmup+5lượt giữ lại; dùng median5mẫu mỗi case. Biểu đồ là median giữa các median case theo lệnh, không phải tổng thời gian. Median tỷ số từng case Python/engine={ratio:.3f}, khác tỷ số hai median. API Java ImageScience headless, loại I/O; đo nguồn Java trước, Python sau. Pythonfloat64 và precision nội tại engine khác nhau. Các lệnhedge chỉ gradient+NMS, không phải toàn bộ pipeline Canny/GT. Độ phức tạp tích chập tách trục giúp giảm chi phí so với2D trực tiếp nhưng không đồng nghĩa Python nhanh hơn engineJava. Nguồn runtime_paired.csv và runtime_environment.json.')
    picture(s,assets['runtime'],.62,1.85,7.55,4.3)
    text(s,8.65,2.0,3.7,.6,f'{len(runtime)} case',30,True)
    text(s,8.65,2.85,3.65,1.0,'1 warm-up + 5 lượt\nLấy median từng case',21)
    text(s,8.65,4.12,3.7,.65,f'{ratio:.2f}×',36,True)
    text(s,8.65,4.95,3.65,1.0,'Median tỷ số\nPython / ImageScience',20)

    s=new_slide(prs,'06 · Kết luận','Kết luận và hướng phát triển',
        'Cảm ơn thầy và các bạn đã lắng nghe.  •  Trao đổi và câu hỏi',
        'Tổng kết ba đóng góp: lõi tự cài; pipeline hai nguồn, có dữ liệu/GT/manifest; số liệu và biểu đồ có thể tái hiện. Nêu giới hạn thẳng thắn:185cặp chưaSTRICT; nhãn tế bào nội bộ; chọn ngưỡng và chấm cùng tập; chưa thí nghiệm nhiễu/resize. Hướng phát triển: tách tập chọn ngưỡng/đánh giá, mở rộng dải kích thước và ảnh thật, hoàn thiện đối chiếu kernel/hiệu chuẩn. Nguồn nền tảng: Lindeberg1994/1998; Canny1986; Frangi1998; FeatureJ/ImageScience và quy ước dự án. Bộ slide phản ánh kết quả hiện có, không tuyên bố mọi tiêu chí nghiệm thu đã đạt.')
    card(s,.65,1.9,5.82,3.85,'ĐÃ THỰC HIỆN','• Gaussian và đạo hàm đa tỷ lệ\n• Edge / Ridge / Blob / Structure\n• Đối chuẩn và đánh giá bằng GT\n• Số liệu, biểu đồ có truy vết',20)
    card(s,6.82,1.9,5.82,3.85,'GIỚI HẠN & PHÁT TRIỂN','• Chưa đạt toàn bộ ngưỡng STRICT\n• Tách tập chọn ngưỡng và test\n• Mở rộng ảnh tế bào, dải scale\n• Kiểm tra nhiễu và kích thước',20)
    text(s,.7,5.94,12,.26,'Nền tảng: Lindeberg (1994, 1998) · Canny (1986) · Frangi (1998) · FeatureJ / ImageScience',12)

    prs.save(FILE)
    validate(prs)
    guide=['# Thuyết trình 14 slide — nền sáng, chữ đen','',
           'Mở **BTL_XLA_ThuyetTrinh_14_Slide.pptx** bằng PowerPoint; nhấn F5 để trình chiếu. File tự chứa toàn bộ ảnh, không cần mở Python.','',
           'Bản PDF xem nhanh: **BTL_XLA_ThuyetTrinh_14_Slide.pdf**. Ảnh preview từng trang và nhật ký kiểm tra khung chữ nằm trong `thuyet_trinh_14/`.','',
           'Tỷ lệ 16:9; nội dung và biểu đồ lấy từ phiên metric/timing hiện hành. Gợi ý thời lượng 12–16 phút. Nội dung nói có sẵn trong Notes dưới từng slide.','',
           'Bộ 10 slide cũ và builder `build_slides.py` được giữ nguyên. Khi cần cập nhật bộ 14 slide, từ gốc dự án chạy `python docs/slides/build_presentation_14.py`.','',
           'Nếu máy có PowerPoint và cần xuất lại PDF/preview sau khi dựng mới: `cscript //Nologo docs/slides/render_presentation_14.vbs`. Script chỉ đóng bài do nó mở, không đóng các bài đang mở khác.','',
           '## Nội dung và gợi ý nói','']
    for i,(title,section,note) in enumerate(NOTES,1):
        guide += [f'### Slide {i:02d} — {title or "Giới thiệu đề tài"}', '', note, '']
    guide += ['## Nguồn số liệu','',
              '- `outputs/metrics/duc_10_11/`: MSE/PSNR/Pearson, P/R/F1, matching audit.',
              '- `outputs/analysis/duc_task5_10_11/`: F1 theo sigma, timing và manifest.',
              '- `outputs/python/`: TIFF dùng làm ảnh minh họa scale-space và đạo hàm.',
              '- `data/raw/`, `data/gt/`: ảnh đầu vào và số nhãn.',
              '- Lý thuyết: các mục Lindeberg/Canny/Frangi đã có trong `docs/report_template/references.bib`.','',
              'Không diễn giải 35/220 STRICT thành tất cả đều đạt. Không gọi điểm trên tập dùng chọn ngưỡng là điểm test độc lập. Nội dung slide không thay thế việc Lộc bổ sung screenshot hoặc Hưng nghiệm thu PDF báo cáo.','']
    (OUT/'HUONG_DAN_THUYET_TRINH_14_SLIDE.md').write_text('\n'.join(guide),encoding='utf-8')
    evidence=dict(status='PASS',built_at_utc=datetime.now(timezone.utc).isoformat(),slides=14,
                  file=FILE.name,pptx_sha256=sha256(FILE),all_native_text_black=True,
                  embedded_images=True,style='white/light gray background; black Arial text; 16:9',
                  input_sha256={str(p.relative_to(ROOT)):sha256(p) for p in sorted(INPUTS)},
                  metric_manifest_sha256=sha256(RESULTS/'run_manifest.json'),
                  analysis_manifest_sha256=sha256(TASK5/'analysis_manifest.json'))
    (OUT/'thuyet_trinh_14/BUILD_MANIFEST.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Built and structurally checked: {FILE} (14 slides)')


def validate(prs):
    if len(prs.slides)!=14: raise ValueError('Expected 14 slides')
    for i,slide in enumerate(prs.slides,1):
        if slide.background.fill.fore_color.rgb!=RGBColor(*WHITE): raise ValueError(f'Background {i}')
        if not slide.notes_slide.notes_text_frame.text.strip(): raise ValueError(f'Notes missing {i}')
        for shape in slide.shapes:
            if min(shape.left,shape.top)<0 or shape.left+shape.width>prs.slide_width+2 or shape.top+shape.height>prs.slide_height+2:
                raise ValueError(f'Shape exceeds slide boundary: slide {i}')
            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    if p.text and p.font.color.rgb!=RGBColor(*BLACK): raise ValueError(f'Nonblack text {i}')


if __name__=='__main__':
    build()
