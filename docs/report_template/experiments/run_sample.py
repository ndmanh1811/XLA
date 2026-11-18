"""Run three sample images using the repo core; compare genuine Fiji TIFFs if present.

No ground-truth F1 is produced here. The 25-image detector tables remain group results.
"""
import argparse
import csv
import importlib
import math
from pathlib import Path
import sys

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--figures", action="store_true")
    parser.add_argument("--run-name", default="sample_local")
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not (repo / "src/core/derivatives.py").is_file():
        parser.error("Repo is missing src/core/derivatives.py; clone/download the selected branch first.")
    sys.path.insert(0, str(repo))
    try:
        import numpy as np
        from PIL import Image
        import tifffile
        core = importlib.import_module("src.core.derivatives")
        config_module = importlib.import_module("src.config")
    except ImportError as exc:
        parser.exit(2, f"Missing dependency: {exc}. Install the repo requirements first.\n")
    cfg = config_module.load_config()
    def check_values(value):
        if value is None:
            parser.error("config.yaml contains null; complete calibration first.")
        if isinstance(value, dict):
            for item in value.values(): check_values(item)
        if isinstance(value, list):
            for item in value: check_values(item)
    check_values(cfg)
    sigmas = tuple(float(value) for value in cfg["sigmas"])
    kernel_k = {n: config_module.get_kernel_k(n, strict=True) for n in (0,1,2)}
    config_module.get_border_mode(strict=True)
    if Path(args.run_name).name != args.run_name or args.run_name in (".",".."):
        parser.error("--run-name must be a directory name, not a path.")
    out = repo / "experiments" / args.run_name
    py_dir = out / "python"
    py_dir.mkdir(parents=True, exist_ok=True)
    fiji_dir = out / "fiji"
    rows = []
    names = ["bsds_01", "drive_01", "blob_01"]
    for name in names:
        source = repo / "data/raw" / f"{name}.png"
        if not source.is_file():
            parser.error(f"Missing input image: {source}")
        with Image.open(source) as image:
            if image.mode != "L":
                parser.error(f"Input must already be 8-bit grayscale: {source} ({image.mode})")
            img = np.asarray(image, dtype=np.float64)
        for sigma in sigmas:
            lx, ly = core.compute_derivatives_1st(img, sigma)
            lxx, lyy, lxy = core.compute_derivatives_2nd(img, sigma)
            maps = {"gauss": core.gaussian_smooth(img, sigma),
                    "lx": lx, "ly": ly, "lxx": lxx, "lxy": lxy, "lyy": lyy}
            paired = {}
            for operator, value in maps.items():
                suffix = f"{name}_{operator}_s{sigma:.1f}.tif"
                # Compare the stored float32 output, like exchanged Fiji TIFFs.
                value = value.astype(np.float32)
                tifffile.imwrite(py_dir / f"py_{suffix}", value, compression=None)
                target = fiji_dir / f"fiji_{suffix}"
                row = dict(image=name, operator=operator, sigma=sigma,
                           crop=math.ceil(max(kernel_k[0], kernel_k[
                               0 if operator=="gauss" else 1 if operator in ("lx","ly","lxy") else 2
                           ]) * sigma),
                           mae="", rmse="", max_error="", relative_max_error="",
                           pearson="", status="MISSING_FIJI")
                if target.is_file():
                    ref = tifffile.imread(target)
                    if ref.shape != value.shape or ref.dtype != np.float32:
                        row["status"] = "SHAPE_OR_DTYPE_MISMATCH"
                    elif not np.isfinite(ref).all():
                        row["status"] = "NONFINITE_REFERENCE"
                    else:
                        r = row["crop"]
                        if min(ref.shape) <= 2*r:
                            row["status"] = "CROP_EMPTY"
                        else:
                            p = value[r:-r, r:-r].astype(np.float64)
                            f = ref[r:-r, r:-r].astype(np.float64)
                            d = p-f
                            maximum = float(np.max(np.abs(d)))
                            relative = maximum/(float(np.max(np.abs(f)))+1e-12)
                            pearson = (float(np.corrcoef(p.ravel(), f.ravel())[0,1])
                                       if np.std(p)>1e-12 and np.std(f)>1e-12 else float("nan"))
                            status = "CONSTANT_UNCLASSIFIED"
                            if np.isfinite(pearson):
                                status = ("PASS_STRICT" if relative < 1e-4 and pearson > .9999
                                          else "PASS_RELAXED" if relative < 1e-2 and pearson > .9999
                                          else "REVIEW")
                            row.update(mae=float(np.mean(np.abs(d))),
                                       rmse=float(np.sqrt(np.mean(d*d))),
                                       max_error=maximum, relative_max_error=relative,
                                       pearson=pearson, status=status)
                            paired[operator] = ref
                rows.append(row)
            if args.figures and sigma == 2.0 and len(paired) == len(maps):
                import matplotlib
                matplotlib.use("Agg")
                import matplotlib.pyplot as plt
                fig, axes = plt.subplots(3, 6, figsize=(18, 9), constrained_layout=True)
                for j, (op, value) in enumerate(maps.items()):
                    ref = paired[op]
                    limit = max(float(np.max(np.abs(value))), float(np.max(np.abs(ref))), 1e-12)
                    for i, data in enumerate((value, ref)):
                        axes[i,j].imshow(data, cmap="gray" if op=="gauss" else "RdBu_r",
                                         vmin=0 if op=="gauss" else -limit, vmax=limit)
                        axes[i,j].set_title(("Python " if i==0 else "Fiji ")+op)
                    delta=value-ref
                    lim=max(float(np.max(np.abs(delta))),1e-12)
                    im=axes[2,j].imshow(delta,cmap="RdBu_r",vmin=-lim,vmax=lim)
                    axes[2,j].set_title("Python - Fiji")
                    fig.colorbar(im,ax=axes[2,j],shrink=.65)
                for ax in axes.flat: ax.axis("off")
                fig.suptitle(f"{name}, sigma=2.0; raw maps; metrics exclude boundary")
                fig.savefig(out/f"sample_{name}_sigma2.png",dpi=200)
                plt.close(fig)
    with (out/"sample_comparison.csv").open("w",encoding="utf-8-sig",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    missing=sum(row["status"]=="MISSING_FIJI" for row in rows)
    print(f"Python maps written: {len(rows)}. Missing Fiji maps: {missing}.")
    print(f"New sample results: {out}")
    print("These are sample-map metrics, not a reproduction of the 25-image F1 benchmark.")

if __name__=="__main__":
    main()
