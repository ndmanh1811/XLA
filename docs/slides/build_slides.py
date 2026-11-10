"""Build the PPTX and offline HTML from the completed canonical delivery.

Run from the project root: python docs/slides/build_slides.py
No F1 score is hard-coded; slides use the same tables as the report/charts.
"""
from pathlib import Path
import base64
import html
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from src.eval.metric_utils import RESULTS, sha256
from src.eval.analyze_task5 import verify_metric_delivery
from src.eval.task5_runtime import TASK5, read_csv


def slide_content():
    verify_metric_delivery()
    manifest = json.loads((TASK5/"analysis_manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "COMPLETE" or manifest["metric_manifest_sha256"] != sha256(RESULTS/"run_manifest.json"):
        raise ValueError("Complete the current analysis before publishing slides")
    edge = read_csv(TASK5/"tables/edge_by_sigma.csv")
    summary = read_csv(RESULTS/"tier2_summary.csv")
    rows = read_csv(RESULTS/"tier2_results_both.csv")
    t1 = read_csv(RESULTS/"tier1_report.csv")
    n_pass = sum(r["status"] == "PASS" for r in t1)
    best = max(edge,key=lambda r:float(r["python_f1"]))
    lookup = {(r["source"],r["task"]):r for r in summary if r["task"] != "edge_bsds"}
    cells = {r["source"]:r for r in rows if r["image"] == "blob_05"}
    runtime = read_csv(TASK5/"runtime/runtime_paired.csv")
    import numpy as np
    ratio = float(np.median([float(r["ratio_python_over_engine"]) for r in runtime]))
    def fig(name): return TASK5/"figures"/name
    return [
        ("Phát hiện đặc trưng ảnh đa tỷ lệ bằng đạo hàm Gaussian",[
            "Nguyễn Tiến Hưng · Nguyễn Đức Mạnh · Phạm Bảo Lộc · Bùi Trung Đức",
            "Tham chiếu FeatureJ/Fiji; lõi tự cài bằng NumPy; thực nghiệm hai nguồn cùng detector.",
            "Nguồn số liệu: outputs/metrics/duc_10_11 và outputs/analysis/duc_task5_10_11.",
            "Hạn chính thức theo đề: 19/11; mục tiêu nội bộ nộp trước 18/11."],None),
        ("Gaussian, scale-space và đạo hàm",[
            "L(x,y;σ) = Gσ * I; Gaussian 2D tách thành hai kernel 1D.",
            "D_norm^(n) = σ^(nγ) D^(n), với γ=1: bậc 1 nhân σ; bậc 2 nhân σ².",
            "Dãy scale đọc từ config.yaml; phép đối chuẩn tầng 1 giữ giá trị thô.",
            "k là hệ số bán kính cắt r=ceil(kσ), không phải bậc Taylor."],None),
        ("Gradient, Hessian và Structure Tensor",[
            "Gradient: (Lx,Ly), độ lớn sqrt(Lx²+Ly²), hướng atan2(Ly,Lx).",
            "Hessian = [[Lxx,Lxy],[Lxy,Lyy]]; hai trị riêng tính bằng nghiệm đóng.",
            "Canny: NMS 4 sector hướng; hysteresis liên thông 8 lân cận.",
            "Ridge: Frangi từ Hessian chuẩn hóa; blob: cực trị LoG 3D không gian–tỷ lệ.",
            "Structure Tensor: hai scale vi phân/tích phân; trị riêng và coherence."],None),
        ("Workflow FeatureJ và dữ liệu",[
            "FeatureJ Edges dùng Canny: gradient magnitude, NMS và threshold/hysteresis.",
            "NMS FeatureJ dùng nội suy tuyến tính; không phải tìm zero-crossing Laplacian.",
            "25 ảnh xám uint8; BSDS 10 ảnh/56 bộ nhãn; DRIVE 10 vessel mask và FOV.",
            "Blob: 4 ảnh tổng hợp và blob_05 gồm 276 tế bào + 15 vùng ignore, Đức rà soát.",
            "435 TIFF Fiji; 415 TIFF Python. SHA-256 xác minh toàn vẹn từng bộ, không chứng minh Python = Fiji."],None),
        ("Tầng 1: đối chuẩn số học",[
            f"220 cặp TIFF trên 5 ảnh đại diện: {n_pass} đạt ngưỡng gốc; {220-n_pass} chưa đạt ngưỡng gốc.",
            "STRICT: relative max error < 1e-4 và Pearson r > 0.9999.",
            "RELAXED 1e-2 là ngưỡng mở rộng, phải phân biệt với STRICT.",
            "PSNR MAX=255 chỉ cho Gaussian. Đạo hàm dùng MAE/RMSE/relative error/Pearson.",
            "Pearson cao không đủ để kết luận hai bản đồ có cùng biên độ."],fig("01_doi_chuan_tang1.png")),
        ("Tầng 2: Canny trên BSDS500",[
            f"Mean F1 Python tốt nhất trong lưới: {float(best['python_f1']):.6f}, σ={float(best['sigma']):g}.",
            f"Fiji dùng cùng ngưỡng: {float(best['fiji_f1']):.6f}; ΔF1={float(best['delta_f1_fiji_minus_python']):+.8f}.",
            "Dung sai đĩa Euclidean 2 px; P so ít nhất một annotator, R trung bình các annotator.",
            "Ngưỡng chọn trên Python rồi đóng băng cho Fiji. FeatureJ Edges là tham chiếu riêng.",
            "Chọn ngưỡng và chấm trên cùng tập nội bộ; không gọi đây là điểm test độc lập."],fig("04_f1_theo_sigma.png")),
        ("Tầng 2: DRIVE và blob",[
            f"DRIVE macro F1 Python/Fiji: {float(lookup['python','ridge_drive']['macro_f1']):.6f} / {float(lookup['fiji','ridge_drive']['macro_f1']):.6f}.",
            "DRIVE chấm trên giao FOV hợp lệ của các scale; support lấy từ config (hiện 32 px).",
            f"Blob macro F1: {float(lookup['python','blob_log']['macro_f1']):.6f} / {float(lookup['fiji','blob_log']['macro_f1']):.6f}.",
            f"Blob micro F1: {float(lookup['python','blob_log']['micro_f1']):.6f} / {float(lookup['fiji','blob_log']['micro_f1']):.6f}.",
            f"blob_05 F1: {float(cells['python']['f1']):.6f} / {float(cells['fiji']['f1']):.6f}; matching một–một và ignore.",
            "Hai nguồn dùng cùng 7 sigma, tâm ≤2 px và sai số bán kính ≤20%."],fig("08_blob_macro_micro.png")),
        ("Thời gian chạy và tối ưu",[
            f"{len(runtime)} trường hợp/nguồn, 1 warm-up + 5 lượt đo; lấy median.",
            f"Median tỷ số Python/Java engine giữa các case: {ratio:.3f}×, chỉ áp dụng phiên/máy này.",
            "Java: API ImageScience headless; không phải thao tác GUI, không gồm đọc/ghi ảnh.",
            "Python float64; không khẳng định hai engine giống hệt precision hoặc kernel.",
            "Benchmark tối ưu riêng so tích chập 2D trực tiếp với tách trục; không trộn với Python–Fiji."],fig("09_thoi_gian_theo_lenh.png")),
        ("Giới hạn và kiểm chứng",[
            "Unit test bổ sung ở đúng pipeline: một dự đoán không khớp hai GT; ignore; FOV; cờ normalization.",
            "GT tế bào do nhóm rà soát, không phải nhãn chuyên gia độc lập.",
            "Bốn ảnh blob tổng hợp không đại diện đầy đủ cho dữ liệu tế bào thật.",
            "Chưa chạy biến thể nhiễu/kích thước: không kết luận độ bền với nhiễu.",
            "Báo cáo số đo thực; kiểm chứng hiệu chuẩn trước khi giải thích nguyên nhân sai số."],None),
        ("Bàn giao và câu hỏi bảo vệ",[
            "Đức: dataset/GT, metric, biểu đồ; Mạnh: lõi/detector và kiểm thử/tối ưu.",
            "Lộc: workflow/macro, TIFF và hồ sơ đo FeatureJ; Hưng: lý thuyết và báo cáo cuối.",
            "Mở README_DUC_10_11.md; chạy CHAY_METRIC_DUC.cmd rồi CHAY_CONG_VIEC_5_DUC.cmd.",
            "Cần hoàn thiện PDF báo cáo ~30 trang và kiểm tra quyền link LMS trước nộp.",
            "Hỏi đáp: vì sao chuẩn hóa σ²; vì sao Pearson cao vẫn có sai số; vì sao macro/micro F1 khác nhau?"],None),
    ]


def create_presentation():
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from PIL import Image
    data = slide_content()
    prs = Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)
    cards=[]
    for i,(title,points,picture) in enumerate(data,1):
        slide=prs.slides.add_slide(prs.slide_layouts[6])
        slide.background.fill.solid(); slide.background.fill.fore_color.rgb=RGBColor(245,248,251)
        def box(x,y,w,h,text,size,color,bold=False):
            tf=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h)).text_frame
            tf.word_wrap=True
            for j,line in enumerate(text.split('\n')):
                p=tf.paragraphs[0] if j==0 else tf.add_paragraph()
                p.text=line; p.font.name='Arial'; p.font.size=Pt(size); p.font.bold=bold
                p.font.color.rgb=RGBColor(*color); p.space_after=Pt(13)
        box(.5,.25,12.2,.95,title,26,(15,51,70),True)
        text_width=6.0 if picture else 12.1
        box(.6,1.35,text_width,5.45,'\n'.join('• '+p for p in points),18 if picture else 21,(34,55,68))
        if picture:
            with Image.open(picture) as im: aspect=im.width/im.height
            w=min(6.0,4.8*aspect); h=w/aspect
            slide.shapes.add_picture(str(picture),Inches(6.8+(6-w)/2),Inches(1.4+(4.8-h)/2),width=Inches(w),height=Inches(h))
        box(.6,7.0,12,.3,f'Phiên duc_10_11 · Metric từ CSV đã kiểm chứng · {i}/{len(data)}',10,(70,93,104))
        img=''
        if picture:
            encoded=base64.b64encode(picture.read_bytes()).decode('ascii')
            img=f'<img alt="{html.escape(title)}" src="data:image/png;base64,{encoded}">'
        cards.append(f'<section><h1>{html.escape(title)}</h1><div class="body"><ul>'+''.join(f'<li>{html.escape(p)}</li>' for p in points)+f'</ul>{img}</div><footer>{i}/{len(data)} · duc_10_11</footer></section>')
    path=ROOT/'docs/slides/BTL_XLA_Nhom_BaoCao.pptx'; prs.save(path)
    css='body{margin:0;background:#eaf0f5;font:22px/1.55 Arial;color:#183748}section{box-sizing:border-box;min-height:100vh;padding:4vh 4vw;background:#f5f8fb;border-bottom:2px solid #ccd9e3}h1{font-size:34px}.body{display:flex;gap:3vw;align-items:center}.body ul{flex:1}li{margin:0 0 18px}.body img{width:48%;height:auto}footer{font-size:14px;color:#566b78} @media(max-width:800px){.body{display:block}.body img{width:100%}} @media print{section{break-after:page;min-height:95vh}}'
    page='<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BTL XLA — duc_10_11</title><style>'+css+'</style>'+''.join(cards)
    page+='<script>document.addEventListener("keydown",e=>{if(["ArrowRight","PageDown","ArrowLeft","PageUp"].includes(e.key)){e.preventDefault();window.scrollBy({top:(e.key==="ArrowLeft"||e.key==="PageUp"?-1:1)*innerHeight,behavior:"smooth"})}})</script></html>'
    (ROOT/'bai_trinh_trinh_xla.html').write_text(page,encoding='utf-8')
    print(f'Built {len(data)} slides: {path}')


if __name__=='__main__':
    create_presentation()
