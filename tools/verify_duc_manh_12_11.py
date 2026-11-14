"""Verify the 12/11 completion against manifests and the pre-change backup.

Run verify_delivery_10_11.py --run-tests first. This tool preserves report text
and calibration files. --refresh-handoff updates only JSON manifest references,
after checking that all saved metric rows are identical to the current CSV.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.eval.analyze_task5 import verify_metric_delivery, validate_runtime
from src.eval.metric_utils import strict_config, sha256

OUT = ROOT / 'docs/12_11/sau_hoan_thien_duc_manh'
METRIC = ROOT / 'outputs/metrics/duc_10_11'
ANALYSIS = ROOT / 'outputs/analysis/duc_task5_10_11'


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def check(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-handoff', action='store_true')
    args = parser.parse_args()
    proof = dict(status='RUNNING', checked_at_utc=datetime.now(timezone.utc).isoformat())
    try:
        verify_metric_delivery()
        _, paired, _ = validate_runtime(ANALYSIS / 'runtime', strict_config())
        check(len(paired) == 357, 'Unexpected runtime case count')
        proof['metric_and_runtime_gate'] = 'PASS'
        proof['runtime_cases_per_source'] = len(paired)
        proof['runtime_samples_including_warmup'] = len(paired) * 2 * 6

        delivery_dir = ROOT / 'docs/10_11/sau_sua_loi'
        delivery = read_json(delivery_dir / 'KIEM_TRA_SAU_SUA.json')
        check(delivery['status'] == 'PASS', 'Full delivery verification not PASS')
        for key in ('UNITTEST', 'CORE', 'FIJI', 'ANALYTICAL'):
            check(delivery.get(key) == 'PASS', f'Missing {key} validation')
        log = (delivery_dir / 'UNITTEST_LOG.txt').read_text(encoding='utf-8')
        count = re.search(r'Ran (\d+) tests', log)
        expected_count = unittest.defaultTestLoader.discover(str(ROOT / 'tests')).countTestCases()
        check(count and int(count[1]) == expected_count and re.search(r'^OK\s*$', log, re.M), 'Expected the complete current unittest suite to pass')
        proof['full_delivery'] = delivery
        proof['unittest_count'] = int(count[1])
        proof['validation_evidence_sha256'] = {
            p.name: sha256(p) for p in [delivery_dir / 'KIEM_TRA_SAU_SUA.json', *sorted(delivery_dir.glob('*_LOG.txt'))]
        }

        protected = read_csv(OUT / 'PROTECTED_FILES_BEFORE.csv')
        changed = [row['path'] for row in protected if sha256(ROOT / row['path']).lower() != row['sha256'].lower()]
        check(not changed, f'Protected files changed: {changed}')
        proof['protected_files_checked'] = len(protected)
        proof['protected_files_changed'] = changed

        backup = ROOT / 'outputs/archives/maintenance_12_11/truoc_hoan_thien_duc_manh.zip'
        identical = []
        with ZipFile(backup) as z:
            for name in ('tier1_report.csv', 'tier2_results_both.csv', 'tier2_summary.csv', 'bsds_selected_thresholds.csv'):
                target = f'outputs/metrics/duc_10_11/{name}'
                entries = [p for p in z.namelist() if p.replace('\\', '/') == target]
                check(len(entries) == 1, f'Missing unique backup entry: {target}')
                check(hashlib.sha256(z.read(entries[0])).hexdigest() == sha256(METRIC / name), f'Metric CSV changed: {name}')
                identical.append(target)
        proof['metric_csv_identical_to_backup'] = identical

        reference = ROOT / 'outputs/benchmarks/reference_comparison'
        manifest = read_json(reference / 'comparison_manifest.json')
        check(manifest['status'] == 'COMPLETE', 'Reference comparison incomplete')
        for section in ('input_code_sha256', 'outputs'):
            for name, digest in manifest[section].items():
                check(sha256(ROOT / name) == digest, f'Reference comparison changed: {name}')
        check(len(read_csv(reference / 'continuous_comparison.csv')) == manifest['continuous_pairs'] == 16, 'Expected 16 continuous comparisons')
        check(len(read_csv(reference / 'canny_mask_agreement.csv')) == manifest['mask_pairs'] == 2, 'Expected 2 mask comparisons')
        proof['reference_comparison'] = dict(status='PASS', continuous_pairs=16, mask_pairs=2,
                                            manifest_sha256=sha256(reference / 'comparison_manifest.json'))

        handoff_path = delivery_dir / 'SO_LIEU_BAN_GIAO.json'
        handoff = read_json(handoff_path)
        check(handoff['summary'] == read_csv(METRIC / 'tier2_summary.csv'), 'Handoff summary differs from CSV')
        check(handoff['cells'] == [r for r in read_csv(METRIC / 'tier2_results_both.csv') if r['image'] == 'blob_05'], 'Handoff cell rows differ from CSV')
        fingerprints = dict(metric_manifest_sha256=sha256(METRIC / 'run_manifest.json'),
                            analysis_manifest_sha256=sha256(ANALYSIS / 'analysis_manifest.json'))
        if args.refresh_handoff:
            handoff.update(fingerprints)
            handoff_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding='utf-8')
        check(all(handoff[key] == digest for key, digest in fingerprints.items()), 'Handoff manifest references stale; use --refresh-handoff after confirming CSV equality')
        proof.update(fingerprints)
        proof['handoff_metadata'] = 'PASS'

        rows = read_csv(ROOT / 'docs/12_11/kiem_tra_toan_bo_nhom/CHECKLIST_29_CONG_VIEC.csv')
        check(len(rows) == 29 and {int(r['stt']) for r in rows} == set(range(1, 30)), 'Invalid task checklist')
        updates = {
            13: ('Đã sửa và đo lại; 16 cặp liên tục + 2 cấu hình Canny', 'Không gõ cứng Pearson/PASS; đọc scope của bảng thư viện, không dùng IoU Canny minh họa làm điểm GT'),
            22: ('Protocol giữ nguyên; phiên đã khớp config hiện hành', 'Chạy lại metric/timing khi code/config/raw đổi; chưa kết luận độ bền nhiễu/kích thước ngoài baseline'),
            23: ('Đã chạy lại; metric gate PASS', '35 STRICT; 185 chưa đạt ngưỡng gốc. CSV P/R/F1 không đổi; không gọi toàn bộ đạt STRICT'),
            24: ('Đã đo lại timing; analysis/runtime gate PASS', '10 hình PNG/SVG/PDF; 357 case/nguồn; warm-up + 5 lượt; Hưng dùng biểu đồ mới khi hoàn thiện báo cáo'),
            27: ('Đã dựng lại 10 slide PPTX và HTML theo timing mới', 'Nhóm rà trình chiếu thực tế; không đồng nghĩa đã nghiệm thu bảo vệ'),
        }
        for row in rows:
            if int(row['stt']) in updates:
                row['review_status'], row['remaining'] = updates[int(row['stt'])]
            row['evidence'] = ('KET_QUA_HOAN_THIEN_DUC_MANH.md;KIEM_TRA_HOAN_THIEN.json;' if int(row['stt']) in updates else '') + '../kiem_tra_toan_bo_nhom/KET_QUA_KIEM_TRA_12_11.md;../kiem_tra_toan_bo_nhom/AUDIT_FACTS.json'
        with (OUT / 'CHECKLIST_29_CONG_VIEC.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        link_count = 0
        for document in [ROOT / 'README_DUC_10_11.md',
                         delivery_dir / 'BAN_GIAO_SAU_SUA.md',
                         OUT / 'KET_QUA_HOAN_THIEN_DUC_MANH.md',
                         ROOT / 'benchmarks/reference_comparison/README.md']:
            for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
                if '://' in target or target.startswith('#'):
                    continue
                check((document.parent / target.split('#')[0]).is_file(), f'Broken link in {document.name}: {target}')
                link_count += 1
        proof['local_document_links_checked'] = link_count
        proof['status'] = 'PASS'
    except Exception as exc:
        proof.update(status='FAIL', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        (OUT / 'KIEM_TRA_HOAN_THIEN.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(proof, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
