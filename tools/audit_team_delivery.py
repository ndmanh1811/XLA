"""Read-only checks of team deliverables; write evidence to docs/09_11."""
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from datetime import datetime, timedelta
from collections import Counter
import csv
import hashlib
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.eval.metric_utils import validate_inputs, strict_config
from src.eval.analyze_task5 import verify_metric_delivery, validate_runtime
from src.eval.task5_runtime import TASK5

OUT = ROOT / "docs/09_11/kiem_tra_toan_bo_nhom"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    facts = {}
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    tasks = []
    with ZipFile(next(ROOT.glob("*.xlsx"))) as z:
        ss = ["".join(e.itertext()) for e in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("s:si", ns)] if "xl/sharedStrings.xml" in z.namelist() else []
        for row in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).findall(".//s:row", ns):
            cells = {}
            for c in row.findall("s:c", ns):
                v = c.find("s:v", ns)
                text = v.text if v is not None else "".join(c.itertext())
                if c.get("t") == "s" and v is not None:
                    text = ss[int(v.text)]
                cells[re.sub(r"\d", "", c.get("r"))] = text
            if not (cells.get("A") or "").isdigit():
                continue
            n = int(cells["A"])
            owner = "Hung" if n <= 7 else "Manh" if n <= 14 else "Loc" if n <= 19 else "Duc" if n <= 24 else "Nhom / chua chi dinh"
            tasks.append(dict(stt=n, group=cells.get("B", ""), task=cells.get("C", ""), required=cells.get("D", ""), deadline=(datetime(1899, 12, 30)+timedelta(days=float(cells["E"]))).strftime("%Y-%m-%d"), assigned_in_sheet=cells.get("F", ""), role_for_review=owner, status_in_sheet=cells.get("G", "")))
    with (OUT / "TASKS_FROM_WORKBOOK.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(tasks[0])); w.writeheader(); w.writerows(tasks)
    facts["tasks"] = len(tasks)
    facts["role_counts"] = dict(Counter(r["role_for_review"] for r in tasks))
    try:
        gt, _ = validate_inputs()
        facts["ground_truth"] = dict(count=len(gt), statuses=dict(Counter(r["status"] for r in gt)))
    except Exception as e:
        facts["ground_truth"] = str(e)
    for name, fn in [("metric_integrity", verify_metric_delivery), ("runtime_integrity", lambda: validate_runtime(TASK5/"runtime", strict_config()))]:
        try:
            fn(); facts[name] = "PASS"
        except Exception as e:
            facts[name] = f"{type(e).__name__}: {e}"
    for filename in ["outputs/metrics/duc_08_11/tier1_report.csv", "outputs/metrics/optimization_benchmark.csv"]:
        with (ROOT/filename).open(encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        if "optimization" in filename:
            facts["optimization"] = dict(rows=len(rows), max_error=max(float(r["max_abs_diff"]) for r in rows), speedup_min=min(float(r["speedup"]) for r in rows), speedup_max=max(float(r["speedup"]) for r in rows))
        else:
            facts["tier1"] = dict(rows=len(rows), statuses=dict(Counter(r["status"] for r in rows)))
    path = ROOT/"docs/report_template/main.tex"
    tex = path.read_text(encoding="utf-8-sig")
    clean = re.sub(r"(?<!\\)%[^\n]*", "", tex)
    labels = re.findall(r"\\label\{([^}]+)\}", clean)
    refs = re.findall(r"\\(?:ref|eqref|autoref|cref)\{([^}]+)\}", clean)
    cites = {k.strip() for x in re.findall(r"\\cite\w*\{([^}]+)\}", clean) for k in x.split(",")}
    keys = set(re.findall(r"@\w+\{\s*([^,]+),", (path.parent/"references.bib").read_text(encoding="utf-8-sig")))
    figures = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", clean)
    sections = [(m.start(), m.group(1)) for m in re.finditer(r"\\section\{([^}]+)\}", clean)]
    lengths = {title:len(re.findall(r"\S+", clean[start:(sections[i+1][0] if i+1<len(sections) else len(clean))])) for i, (start, title) in enumerate(sections)}
    stack, errors = [], []
    for kind, env in re.findall(r"\\(begin|end)\{([^}]+)\}", clean):
        if kind == "begin": stack.append(env)
        elif not stack or stack[-1] != env: errors.append((kind, env))
        else: stack.pop()
    facts["report"] = dict(lines=len(tex.splitlines()), section_tokens=lengths, labels=len(labels), references=len(refs), undefined_refs=sorted(set(refs)-set(labels)), citation_keys=len(cites), bib_entries=len(keys), missing_citations=sorted(cites-keys), figures=len(figures), missing_figures=[x for x in figures if not (path.parent/x).exists()], environment_errors=errors, unclosed_environments=stack, ch4_included=bool(re.search(r"\\(?:input|include)\{ch4_content", clean)), compiler={n:shutil.which(n) for n in ["pdflatex", "xelatex", "lualatex", "latexmk"]})
    delivered = []
    for folder in [ROOT/"docs", ROOT/"outputs"]:
        for p in folder.rglob("*"):
            if p.is_file() and p.suffix.lower() in [".pptx", ".ppt", ".odp", ".pdf"]:
                delivered.append(p.relative_to(ROOT).as_posix())
    facts["pdf_and_slides"] = delivered
    facts["fiji_documents"] = []
    for p in sorted((ROOT/"docs/fiji").glob("*.docx")):
        with ZipFile(p) as z:
            text = "\n".join("".join(r.itertext()) for r in ET.fromstring(z.read("word/document.xml")).findall(".//w:p", {"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}))
            facts["fiji_documents"].append(dict(path=p.relative_to(ROOT).as_posix(), date_09_11=("09 " in text and "2026" in text), images=sum(n.startswith("word/media/") for n in z.namelist()), mentions435=("435" in text)))
    # Only the file naming/path test is evaluated; this does not run a script
    # that could regenerate calibration inputs or overwrite reports.
    facts["analytical_smoke_paths"] = {name:(ROOT/"data/calib"/name).exists() for name in ["parabol.tif", "parabola.tif"]}
    # Verify actual image bytes in the new flat handoff archives.
    source = {p.name:p for p in (ROOT/"outputs/python").glob("*.tif")}
    seen, packages = set(), []
    for p in sorted((ROOT/"outputs/archives/duc_08_11").glob("*.zip")):
        with ZipFile(p) as z:
            for name in z.namelist():
                if name != Path(name).name or not name.endswith(".tif") or name in seen:
                    raise ValueError(f"Unexpected package entry: {name}")
                if hashlib.sha256(z.read(name)).digest() != hashlib.sha256(source[name].read_bytes()).digest():
                    raise ValueError(f"Bad TIFF in {p.name}: {name}")
                seen.add(name)
            packages.append(dict(name=p.name, maps=len(z.namelist()), bytes=p.stat().st_size))
    facts["python_packages"] = dict(parts=packages, total_maps=len(seen), complete=(seen==set(source)))
    (OUT/"AUDIT_FACTS.json").write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(facts, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
