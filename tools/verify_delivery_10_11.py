"""Verify current metrics, labels, timing, figures, slides and TIFF archives.

python tools/verify_delivery_10_11.py --run-tests
Writes evidence only to docs/10_11/sau_sua_loi.
"""
import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.eval.metric_utils import RESULTS,sha256,strict_config,validate_inputs,match_blobs,scores
from src.eval.analyze_task5 import verify_metric_delivery,validate_runtime
from src.eval.task5_runtime import TASK5,read_csv


def check(condition,message):
    if not condition: raise ValueError(message)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-tests',action='store_true')
    args=parser.parse_args()
    out=ROOT/'docs/10_11/sau_sua_loi'; out.mkdir(parents=True,exist_ok=True)
    evidence={'status':'RUNNING'}
    try:
        metric=verify_metric_delivery()
        gt,_=validate_inputs()
        evidence['ground_truth_ready']=len(gt)
        for row in read_csv(RESULTS/'map_manifest.csv'):
            check(sha256(ROOT/row['path'])==row['sha256'],f"Map changed: {row['path']}")
        evidence['metric_manifest']='PASS'
        rows=read_csv(RESULTS/'tier2_results_both.csv')
        check(len(rows)==110,'Expected 55 rows per source')
        check(len({tuple(r[k] for k in ('source','task','image','sigma')) for r in rows})==110,'Duplicate records')
        for r in rows:
            check(all(0<=float(r[k])<=1 for k in ('precision','recall','f1')),'Scores outside [0,1]')
        for r in read_csv(RESULTS/'tier2_summary.csv'):
            group=[x for x in rows if all(x[k]==r[k] for k in ('source','task','sigma'))]
            check(len(group)==int(r['n_images']),'Summary image count mismatch')
            for key in ('precision','recall','f1'):
                check(abs(sum(float(x[key]) for x in group)/len(group)-float(r[f'macro_{key}']))<1e-12,'Macro aggregation mismatch')
            if r['task']!='edge_bsds':
                expected=scores(sum(int(x['tp']) for x in group),sum(int(x['predicted_count']) for x in group),sum(int(x['gt_count']) for x in group))
                check(all(abs(float(r[f'micro_{key}'])-v)<1e-12 for key,v in zip(('precision','recall','f1'),expected)),'Micro aggregation mismatch')
        audit=json.loads((RESULTS/'blob_matching_audit.json').read_text(encoding='utf-8'))
        for r in (x for x in rows if x['task']=='blob_log'):
            saved=audit[f"{r['source']}_{r['image']}"]
            ann=json.loads((ROOT/f"data/gt/blob/{r['image']}.json").read_text(encoding='utf-8'))
            pairs,ids,pids=match_blobs(ann['objects'],saved['detections'],ann.get('ignore_regions',[]))
            check([list(p) for p in pairs]==saved['pairs_gt_prediction'],'Blob assignment mismatch')
            check((len(pairs),len(pids),len(ids))==(int(r['tp']),int(r['predicted_count']),int(r['gt_count'])),'Blob score count mismatch')
        evidence['tier2_aggregation_and_matching']='PASS'
        evidence['tier1']=dict(Counter(r['status'] for r in read_csv(RESULTS/'tier1_report.csv')))
        env=json.loads((TASK5/'runtime/runtime_environment.json').read_text(encoding='utf-8'))
        runtime,paired,_=validate_runtime(TASK5/'runtime',strict_config())
        analysis=json.loads((TASK5/'analysis_manifest.json').read_text(encoding='utf-8'))
        check(analysis['status']=='COMPLETE','Analysis incomplete')
        check(analysis['metric_manifest_sha256']==sha256(RESULTS/'run_manifest.json'),'Analysis source mismatch')
        for key,base in [('outputs',TASK5),('source_metrics',RESULTS),('code_sha256',ROOT)]:
            for name,digest in analysis[key].items():
                check(sha256(base/name)==digest,f'Analysis dependency changed: {name}')
        evidence['analysis_and_runtime']='PASS'
        evidence['runtime_cases_per_source']=len(paired)
        evidence['runtime_samples']=len(paired)*2*6
        for suffix in ('png','svg','pdf'):
            check(len(list((TASK5/'figures').glob(f'*.{suffix}')))==10,f'Missing {suffix} charts')
        spec=importlib.util.spec_from_file_location('current_slide_builder',ROOT/'docs/slides/build_slides.py')
        builder=importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
        contents=builder.slide_content()
        ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
        with ZipFile(ROOT/'docs/slides/BTL_XLA_Nhom_BaoCao.pptx') as z:
            check(z.testzip() is None,'Corrupt PPTX')
            for i,(title,points,_) in enumerate(contents,1):
                xml=ET.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
                text='\n'.join(x.text or '' for x in xml.findall('.//a:t',ns))
                check(title in text and all(p in text for p in points),f'Stale slide {i}')
        page=(ROOT/'bai_trinh_trinh_xla.html').read_text(encoding='utf-8')
        check(page.count('<section>')==10 and 'https://revealjs.com' not in page,'HTML slides not offline/current')
        tex=(ROOT/'docs/report_template/main.tex').read_text(encoding='utf-8')
        for figure in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',tex):
            check((ROOT/'docs/report_template'/figure).is_file(),f'Missing report figure {figure}')
        for bad in ('8 hướng (NMS)','5 ảnh hiệu chuẩn','0.681','0.4651','0.463'):
            check(bad not in tex,f'Stale report text: {bad}')
        evidence['slides_and_report_data']='PASS (LaTeX PDF not compiled locally)'
        files={p.name:p for p in (ROOT/'outputs/python').glob('*.tif')}
        seen=set()
        for p in sorted((ROOT/'outputs/archives/duc_08_11').glob('*.zip')):
            with ZipFile(p) as z:
                check(z.testzip() is None,'Bad archive CRC')
                for name in z.namelist():
                    check(name==Path(name).name and name.endswith('.tif') and name not in seen,'Unexpected ZIP entry')
                    import hashlib
                    check(hashlib.sha256(z.read(name)).hexdigest()==sha256(files[name]),f'ZIP image differs: {name}')
                    seen.add(name)
        check(seen==set(files),'ZIP map coverage mismatch')
        evidence['python_tiffs_in_verified_archives']=len(seen)
        if args.run_tests:
            envvars={**os.environ,'PYTHONIOENCODING':'utf-8','MPLBACKEND':'Agg'}
            for name,command in [('UNITTEST',['-m','unittest','discover','-s','tests','-v']),
                ('CORE',['run_tests.py']),('FIJI',['src/eval/validate_fiji_outputs.py']),
                ('ANALYTICAL',['src/eval/smoke_test_analytical.py'])]:
                p=subprocess.run([sys.executable,'-B','-X','utf8',*command],cwd=ROOT,env=envvars,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
                log=p.stdout.decode('utf-8',errors='replace')
                (out/f'{name}_LOG.txt').write_text(log,encoding='utf-8')
                check(p.returncode==0,f'{name} failed; inspect log')
                evidence[name]='PASS'
        evidence['status']='PASS'
    except Exception as e:
        evidence.update(status='FAIL',error=f'{type(e).__name__}: {e}')
        raise
    finally:
        (out/'KIEM_TRA_SAU_SUA.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(evidence,ensure_ascii=True,indent=2))


if __name__=='__main__': main()
