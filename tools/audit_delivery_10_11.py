"""Audit current local deliverables without regenerating project outputs."""
from collections import Counter, defaultdict
from contextlib import redirect_stdout
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/10_11/kiem_tra_toan_bo_nhom"
sys.path.insert(0, str(ROOT))
import audit_team_delivery as previous


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_manifest(path, groups):
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    result = []
    for key, base in groups.items():
        for name, expected in doc.get(key, {}).items():
            target = base / name
            state = "MISSING" if not target.is_file() else "MATCH" if digest(target) == expected else "CHANGED"
            result.append(dict(manifest=str(path.relative_to(ROOT)), group=key, path=name, status=state))
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    previous.OUT = OUT
    with redirect_stdout(io.StringIO()):
        previous.main()
    facts = json.loads((OUT / "AUDIT_FACTS.json").read_text(encoding="utf-8"))
    results = {}
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "MPLBACKEND": "Agg"}
    for name, args in {
        "UNITTEST": ["-m", "unittest", "discover", "-s", "tests", "-v"],
        "CORE_TEST": ["run_tests.py"],
        "FIJI_VALIDATION": ["src/eval/validate_fiji_outputs.py"],
        "ANALYTICAL_SMOKE": ["src/eval/smoke_test_analytical.py"],
    }.items():
        try:
            p = subprocess.run([sys.executable, "-B", "-X", "utf8", *args], cwd=ROOT,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               env=env, timeout=90)
            log = p.stdout.decode("utf-8", errors="replace")
            results[name] = dict(returncode=p.returncode, tail=log.splitlines()[-6:])
        except subprocess.TimeoutExpired as exc:
            log = (exc.stdout or b"").decode("utf-8", errors="replace")
            results[name] = dict(returncode="TIMEOUT")
        (OUT / f"{name}_LOG.txt").write_text(log, encoding="utf-8")

    metric = ROOT / "outputs/metrics/duc_08_11"
    analysis = ROOT / "outputs/analysis/duc_task5_08_11"
    checks = compare_manifest(metric / "run_manifest.json", {"outputs": metric, "code_config_sha256": ROOT})
    checks += compare_manifest(analysis / "analysis_manifest.json", {"outputs": analysis, "source_metrics": metric, "code_sha256": ROOT})
    with (OUT / "MANIFEST_INTEGRITY.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["manifest", "group", "path", "status"])
        w.writeheader(); w.writerows(checks)
    results["manifest_integrity"] = dict(Counter(r["status"] for r in checks))

    raw = rows(metric / "tier2_results_both.csv")
    diff = []
    for r in rows(metric / "tier2_summary.csv"):
        group = [x for x in raw if all(x[k] == r[k] for k in ("source", "task", "sigma"))]
        for key in ("precision", "recall", "f1"):
            mean = sum(float(x[key]) for x in group) / len(group)
            stored = float(r[f"macro_{key}"])
            if abs(mean - stored) > 1e-8:
                diff.append(dict(source=r["source"], task=r["task"], sigma=r["sigma"], metric=key, raw=mean, summary=stored))
    dump("ARCHIVED_SUMMARY_VS_RAW.json", diff)
    results["archived_summary_mismatches_at_1e_8"] = len(diff)
    results["archived_manifest_status"] = json.loads((metric / "run_manifest.json").read_text(encoding="utf-8"))["status"]

    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    deck = ROOT / "docs/slides/BTL_XLA_Nhom_BaoCao.pptx"
    slides = []
    with ZipFile(deck) as z:
        names = sorted([n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)],
                       key=lambda n: int(re.search(r"slide(\d+)", n).group(1)))
        for name in names:
            doc = ET.fromstring(z.read(name))
            slides.append(dict(slide=name, text="\n".join(x.text or "" for x in doc.findall(".//a:t", ns))))
        results["pptx"] = dict(slides=len(slides), images=sum(n.startswith("ppt/media/") for n in z.namelist()), corrupt_entry=z.testzip())
    dump("SLIDE_TEXT.json", slides)
    html = (ROOT / "bai_trinh_trinh_xla.html").read_text(encoding="utf-8-sig")
    images = re.findall(r'<img[^>]+src=["\']([^"\']+)', html)
    results["html_slides"] = dict(slides=len(re.findall(r"<section(?:\s|>)", html)),
                                    missing_local_images=[x for x in images if not x.startswith(("http", "data:")) and not (ROOT / x).is_file()])
    results["report_figures_missing"] = facts["report"]["missing_figures"]
    dump("CURRENT_CHECKS.json", results)
    print(json.dumps(results, ensure_ascii=True, indent=2), flush=True)


if __name__ == "__main__":
    main()
