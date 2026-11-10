"""Demo with freshly computed per-image metrics, using frozen thresholds.

python demo.py bsds --no-show
python demo.py drive --no-show
"""
import argparse
from pathlib import Path
import time
import numpy as np
from PIL import Image
from src.core.derivatives import compute_derivatives_1st, compute_derivatives_2nd
from src.core.hessian import compute_hessian_eigenvalues
from src.core.detectors import detect_canny, detect_ridge
from src.eval.bsds_threshold_grid import load_bsds_items, evaluate_prediction
from src.eval.metric_utils import ROOT, RESULTS, strict_config, normalize_scale, erode_square, scores
from src.eval.task5_runtime import read_csv
from src.eval.analyze_task5 import verify_metric_delivery


def run_quick_demo(choice="drive", show=True, out_dir=None, sigma=None):
    verify_metric_delivery()
    cfg = strict_config()
    image = "bsds_01" if choice == "bsds" else "drive_01"
    raw = np.asarray(Image.open(ROOT/f"data/raw/{image}.png"), dtype=np.float64)
    selected = [r for r in read_csv(RESULTS/"tier2_results_python.csv") if r["image"] == image]
    started = time.perf_counter()
    if choice == "bsds":
        sigma = float(sigma if sigma is not None else cfg["sigmas"][min(1,len(cfg["sigmas"])-1)])
        row = next((r for r in selected if float(r["sigma"]) == sigma), None)
        if row is None:
            raise ValueError(f"Sigma {sigma} not in the completed protocol")
        lx, ly = compute_derivatives_1st(raw,sigma)
        lx = normalize_scale(lx,sigma,1,"python","derivatives",cfg)
        ly = normalize_scale(ly,sigma,1,"python","derivatives",cfg)
        prediction = detect_canny(lx,ly,float(row["p_low"]),float(row["p_high"]),return_binary=False)
        item = next(i for i in load_bsds_items(ROOT/"data/raw",ROOT/"data/gt",10) if i.stem == image)
        measured = evaluate_prediction(prediction,item)
        precision, recall, f1 = [measured[k] for k in ("precision","recall","f1")]
        truth, response = item.union_gt,np.hypot(lx,ly)
        description = f"Canny một ảnh, sigma={sigma:g}; p={float(row['p_low']):g}/{float(row['p_high']):g}"
    else:
        threshold = float(selected[0]["threshold"])
        fov = np.asarray(Image.open(ROOT/f"data/gt/drive/{image}_fov.png")) > 0
        truth = np.asarray(Image.open(ROOT/f"data/gt/drive/{image}_vessels.png")) > 0
        radii = {s:int(np.ceil(max(cfg["kernel_k"].values())*s)) for s in cfg["sigmas"]}
        valid = erode_square(fov,max(radii.values()))
        responses = []
        for s in cfg["sigmas"]:
            xx, yy, xy = compute_derivatives_2nd(raw,s)
            a,b = compute_hessian_eigenvalues(xx,yy,xy,cfg["eigen_order"])
            a = normalize_scale(a,s,2,"python","hessian",cfg)
            b = normalize_scale(b,s,2,"python","hessian",cfg)
            response = detect_ridge(a,b,sigma=s,beta=.5,polarity="dark")
            response[~erode_square(fov,radii[s])] = 0
            responses.append(response)
        response = np.maximum.reduce(responses)
        prediction, truth = (response >= threshold) & valid,truth & valid
        precision,recall,f1 = scores(int((prediction & truth).sum()),int(prediction.sum()),int(truth.sum()))
        description = f"Frangi {cfg['sigmas']}; FOV={max(radii.values())}px; threshold={threshold:g}"
    elapsed = 1000*(time.perf_counter()-started)
    print(f"{image}: {description}")
    print(f"P={precision:.6f}; R={recall:.6f}; F1={f1:.6f}; compute+GT={elapsed:.2f} ms")
    print("Metric vừa tính cho một ảnh; không phải macro F1 toàn dataset. Threshold lấy từ phiên metric đã đóng băng.")
    import matplotlib
    if not show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    overlay = np.repeat((raw/255.)[...,None],3,axis=2)
    overlay[truth] = .35*overlay[truth]+.65*np.array([1.,.2,.2])
    overlay[prediction] = .35*overlay[prediction]+.65*np.array([0.,1.,1.])
    fig,axes = plt.subplots(1,4,figsize=(15,4),layout="constrained")
    for ax,data,title,cmap in zip(axes,[raw,response,prediction,overlay],
        [image,"Đáp ứng","Dự đoán",f"GT đỏ / dự đoán cyan; F1={f1:.4f}"],["gray","inferno","gray",None]):
        ax.imshow(data,cmap=cmap); ax.set_title(title,fontsize=10); ax.axis("off")
    fig.suptitle(description,fontsize=11)
    folder = Path(out_dir or ROOT/"docs/slides")
    folder.mkdir(parents=True,exist_ok=True)
    path = folder/f"demo_{choice}_output.png"
    fig.savefig(path,dpi=200)
    if show:
        plt.show()
    plt.close(fig)
    return dict(image=image,precision=precision,recall=recall,f1=f1,output=str(path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("choice",choices=["bsds","drive"],nargs="?",default="drive")
    parser.add_argument("--no-show",action="store_true")
    parser.add_argument("--sigma",type=float)
    args = parser.parse_args()
    run_quick_demo(args.choice,show=not args.no_show,sigma=args.sigma)
