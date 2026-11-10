"""Package Python TIFFs as flat independent ZIPs containing only .tif files.

Use --replace to rebuild the generated handoff archives. Originals stay intact.
"""
import argparse
import csv
import hashlib
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.eval.metric_utils import RESULTS, sha256, validate_inputs, strict_config, read_map
from src.eval.run_metrics import expected_source_files

OUT = ROOT / "outputs/archives/duc_08_11"
SOFT_LIMIT = 90 * 1024 * 1024
HARD_LIMIT = 95 * 1024 * 1024


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    cfg = strict_config()
    gt, _ = validate_inputs()
    files = sorted((ROOT / "outputs/python").glob("*.tif"))
    required = {p.name for p in expected_source_files(cfg, gt, "python")}
    if not files or not required <= {p.name for p in files}:
        raise ValueError("Missing Python maps; run CHAY_METRIC_DUC_08_11.cmd first")
    shapes = {r["image"]:r["shape"] for r in gt}
    with (RESULTS / "map_manifest.csv").open(encoding="utf-8-sig", newline="") as f:
        metric_hashes = {Path(r["path"].replace("\\", "/")).name:r["sha256"] for r in csv.DictReader(f) if r["source"] == "python"}
    hashes = {}
    for p in files:
        image = "_".join(p.stem.split("_")[1:3])
        read_map(p, shapes[image])
        hashes[p.name] = sha256(p)
        if p.name in metric_hashes and hashes[p.name] != metric_hashes[p.name]:
            raise ValueError(f"Map differs from the completed metric run: {p.name}")
    OUT.mkdir(parents=True, exist_ok=True)
    assert OUT.resolve().is_relative_to(ROOT.resolve())
    old = set(OUT.glob("python_maps_duc_08_11_part*.zip"))
    if old and not args.replace:
        raise FileExistsError("Packages already exist; use --replace to rebuild")
    parts = []
    archive = None
    try:
        for i, p in enumerate(files, 1):
            if archive is None or archive.fp.tell() + p.stat().st_size*1.01 + 8192 > SOFT_LIMIT:
                if archive is not None:
                    archive.close()
                destination = OUT / f"python_maps_duc_08_11_part{len(parts)+1:02d}.zip"
                temporary = destination.with_suffix(".zip.tmp")
                if temporary.exists():
                    raise FileExistsError(f"Unfinished package exists: {temporary}")
                archive = ZipFile(temporary, "w", ZIP_DEFLATED, compresslevel=6)
                parts.append(dict(final=destination, temporary=temporary, names=[]))
            # Flat layout: opening a ZIP shows TIFFs, not folders or metadata.
            archive.write(p, p.name)
            parts[-1]["names"].append(p.name)
            if i % 50 == 0:
                print(f"Packaged {i}/{len(files)} TIFFs", flush=True)
        archive.close()
        archive = None
    finally:
        if archive is not None:
            archive.close()
    seen = set()
    for part in parts:
        p = part["temporary"]
        if p.stat().st_size >= HARD_LIMIT:
            raise ValueError(f"Package too large: {p.name}")
        with ZipFile(p) as z:
            names = z.namelist()
            if names != part["names"] or z.testzip() is not None:
                raise ValueError(f"ZIP content/CRC mismatch: {p.name}")
            for name in names:
                if name != Path(name).name or not name.endswith(".tif") or name in seen:
                    raise ValueError(f"Unexpected entry: {name}")
                if hashlib.sha256(z.read(name)).hexdigest() != hashes[name]:
                    raise ValueError(f"TIFF bytes changed: {name}")
                seen.add(name)
    if seen != set(hashes):
        raise ValueError("ZIP union does not match all source TIFFs")
    for p in files:
        if sha256(p) != hashes[p.name]:
            raise ValueError(f"Source changed during packaging: {p.name}")
    validate_inputs()
    # Only replace the handoff archives after all parts passed verification.
    for part in parts:
        assert part["final"].resolve().parent == OUT.resolve()
        part["temporary"].replace(part["final"])
    obsolete = old - {p["final"] for p in parts}
    for p in obsolete:
        assert p.resolve().parent == OUT.resolve()
        p.unlink()
    # These were created by the previous package version, not source data.
    for name in ("TIFF_MANIFEST.csv", "PACKAGE_MANIFEST.json", "SHA256SUMS.txt", ".gitattributes"):
        p = OUT / name
        assert p.resolve().parent == OUT.resolve()
        if p.exists():
            p.unlink()
    lines = ["# Bàn giao ảnh TIFF Python", "", f"Đủ **{len(files)} ảnh TIFF**, chia thành {len(parts)} ZIP.", "",
             "Mỗi ZIP chỉ chứa các file `.tif` ngay khi mở: không thư mục lồng, không file phụ.", "",
             "| ZIP | Số TIFF | Dung lượng |", "| --- | ---: | ---: |"]
    for part in parts:
        p = part["final"]
        lines.append(f"| [{p.name}]({p.name}) | {len(part['names'])} | {p.stat().st_size/1024**2:.2f} MiB |")
        print(f"Verified {p.name}: {len(part['names'])} TIFFs", flush=True)
    lines += ["", "**Bàn giao cả ba ZIP.** Giải nén đủ các ZIP vào **cùng thư mục `outputs/python/`** nếu dùng với code dự án. Có thể giải nén vào thư mục trống khác để mở xem bằng Fiji/ImageJ.", "",
              "Đã kiểm tra CRC và SHA-256 từng ảnh trong ZIP; giữ nguyên toàn bộ ảnh gốc. Đây là bản đồ đầu ra Python, không phải ground truth.", ""]
    (OUT / "README_BAN_GIAO.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"COMPLETE: {len(files)} TIFFs; handoff folder contains {len(parts)} ZIPs and one short README.", flush=True)


if __name__ == "__main__":
    main()
