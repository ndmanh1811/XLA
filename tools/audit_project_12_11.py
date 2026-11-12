"""Read-only audit of the updated team delivery; evidence goes to docs/12_11.

Never runs the calibration analyzer/publisher or overwrites existing metrics.
"""
from collections import Counter, defaultdict
from datetime import datetime,timedelta
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
import tifffile
import yaml

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/12_11/kiem_tra_toan_bo_nhom'
sys.path.insert(0,str(ROOT))
from src.eval.metric_utils import RESULTS,sha256,validate_inputs,strict_config,match_blobs,scores
from src.eval.analyze_task5 import verify_metric_delivery,validate_runtime
from src.eval.task5_runtime import TASK5,read_csv,runtime_fingerprint


def write(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def measure_calibration():
    folder=ROOT/'docs/fiji/calibration'
    manifest=read_csv(folder/'output_manifest.csv')
    measured=read_csv(folder/'measurement_results.csv')
    profiles=read_csv(folder/'kernel_profiles.csv')
    environment={r['key']:r['value'] for r in read_csv(folder/'environment.csv')}
    arrays={}; issues=[]; roi_errors=[]; grouped=defaultdict(list)
    for row in manifest:
        p=folder/'outputs'/row['filename']
        if not p.is_file(): issues.append('Missing '+str(p)); continue
        with tifffile.TiffFile(p) as tf:
            a=tf.asarray()
            if a.dtype!=np.float32 or not np.isfinite(a).all() or int(tf.pages[0].compression)!=1:
                issues.append('Invalid TIFF '+p.name)
        arrays[p.name]=a.astype(np.float64)
        if sha256(p).lower()!=row['sha256'].lower() or p.stat().st_size!=int(row['size_bytes']):
            issues.append('Manifest mismatch '+p.name)
        if a.shape!=(int(row['height']),int(row['width'])): issues.append('Shape mismatch '+p.name)
    for row in measured:
        a=arrays[row['output_name']]
        x,y,w,h=[int(row[k]) for k in ('roi_x','roi_y','roi_width','roi_height')]
        crop=a[y:y+h,x:x+w]
        actual=dict(mean=float(crop.mean()),min=float(crop.min()),max=float(crop.max()),sum=float(crop.sum()),stddev=float(crop.std(ddof=1)))
        errors={key:abs(float(row['measured_'+key])-v) for key,v in actual.items()}
        if any(errors[k]>(1e-5 if k=='sum' else 1e-6) for k in errors):
            issues.append('ROI CSV differs from TIFF '+row['output_name'])
        roi_errors.append(dict(output=row['output_name'],**errors))
        if row['image'] in ('ramp.tif','parabola.tif','saddle.tif'):
            grouped[row['command']].append((float(row['sigma']),actual['mean']))
    max_profile_error=0.
    for row in profiles:
        a=arrays[row['output_name']]
        err=abs(a[int(row['y']),int(row['x'])]-float(row['value']))
        max_profile_error=max(max_profile_error,float(err))
    if max_profile_error>2e-9: issues.append('Profile CSV differs from TIFF')
    for name in ('ramp','parabola','saddle','dirac','bright_border'):
        if environment.get(f'input_{name}_sha256','').lower()!=sha256(ROOT/f'data/calib/{name}.tif').lower():
            issues.append('Input hash mismatch '+name)
    norm=[]
    for command,values in grouped.items():
        values.sort(); s=np.array([v[0] for v in values]); a=np.array([v[1] for v in values])
        if not np.any(a):
            norm.append(dict(command=command,classification='UNINFORMATIVE_ZERO')); continue
        order=1 if command in ('lx','grad') else 2
        def residual(model):
            coefficient=float(np.dot(a,model)/np.dot(model,model))
            return float(np.linalg.norm(a-coefficient*model)/np.linalg.norm(a))
        raw= residual(np.ones_like(s)); normalized=residual(s**order)
        norm.append(dict(command=command,values=a.tolist(),raw_residual=raw,normalized_residual=normalized,
                         classification='RAW' if raw<normalized else 'NORMALIZED'))
    supports=[]; border=[]; kernels=[]
    for sigma in (1.,2.,4.):
        raw_gauss=arrays[f'calib_dirac_gauss_s{sigma:.1f}.tif']
        cy,cx=np.array(raw_gauss.shape)//2
        g=raw_gauss[cy,:]/raw_gauss[cy,:].sum()
        observed=arrays[f'calib_bright_border_gauss_s{sigma:.1f}.tif'][128,0]
        border.append(dict(sigma=sigma,observed=float(observed),mirror_error=float(abs(observed-g[cx])),
                           reflect_error=float(abs(observed-g[cx]-g[cx-1]))))
        for command,order,k in [('gauss',0,3),('lx',1,4),('lxx',2,4)]:
            a=arrays[f'calib_dirac_{command}_s{sigma:.1f}.tif']
            xp=a[cy,:]; yp=a[:,int(np.argmax(abs(xp)))]
            def radius(p,center):
                return int(np.max(abs(np.flatnonzero(abs(p)>max(abs(p))*1e-7)-center)))
            rx,ry=radius(xp,cx),radius(yp,cy)
            supports.append(dict(command=command,sigma=sigma,rx=rx,ry=ry,sum2d=float(a.sum()),
                                 matches_config=rx==int(k*sigma) and ry==int(3*sigma)))
            x=np.arange(-cx,a.shape[1]-cx,dtype=float); y=np.arange(-cy,a.shape[0]-cy,dtype=float)
            gx=np.exp(-x*x/(2*sigma*sigma))/(np.sqrt(2*np.pi)*sigma)
            gy=np.exp(-y*y/(2*sigma*sigma))/(np.sqrt(2*np.pi)*sigma)
            gy[abs(y)>3*sigma]=0; gy/=gy.sum()
            if order==0:
                gx[abs(x)>3*sigma]=0; gx/=gx.sum()
            elif order==1: gx*= -x/(sigma*sigma); gx[abs(x)>k*sigma]=0
            else: gx*= (x*x-sigma*sigma)/sigma**4; gx[abs(x)>k*sigma]=0
            ref=gy[:,None]*gx[None,:]
            kernels.append(dict(command=command,sigma=sigma,relative_max_error=float(np.max(abs(a-ref))/np.max(abs(ref)))))
    screenshots=[str(p.relative_to(ROOT)) for p in (folder/'screenshots').glob('*') if p.suffix.lower() in ('.png','.jpg','.jpeg')]
    result=dict(tiffs=len(arrays),manifest_rows=len(manifest),measurements=len(measured),profiles=len(profiles),issues=issues,
                roi_max_errors={k:max(r[k] for r in roi_errors) for k in ('mean','min','max','sum','stddev')},
                maximum_profile_error=max_profile_error,normalization=norm,support=supports,border=border,
                analytic_kernel_comparison=kernels,screenshots=screenshots,environment=environment)
    write('CALIBRATION_CHECKS.json',result)
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    facts={}
    envvars={**os.environ,'PYTHONIOENCODING':'utf-8','MPLBACKEND':'Agg'}
    for name,args in [('UNITTEST',['-m','unittest','discover','-s','tests','-v']),('CORE',['run_tests.py']),
                     ('FIJI',['src/eval/validate_fiji_outputs.py']),('ANALYTICAL',['src/eval/smoke_test_analytical.py'])]:
        p=subprocess.run([sys.executable,'-B','-X','utf8',*args],cwd=ROOT,env=envvars,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
        log=p.stdout.decode('utf-8',errors='replace'); (OUT/f'{name}_LOG.txt').write_text(log,encoding='utf-8')
        facts[name]=dict(returncode=p.returncode,tail=log.splitlines()[-5:])
    gt,_=validate_inputs(); facts['gt_ready']=len(gt)
    for key,fn in [('metric_verification',verify_metric_delivery),('runtime_verification',lambda:validate_runtime(TASK5/'runtime',strict_config()))]:
        try: fn(); facts[key]='PASS'
        except Exception as e: facts[key]=f'{type(e).__name__}: {e}'
    metric=json.loads((RESULTS/'run_manifest.json').read_text(encoding='utf-8'))
    changed=[name for name,digest in metric['code_config_sha256'].items() if sha256(ROOT/name)!=digest]
    facts['metric_changed_dependencies']=changed
    facts['changed_metric_outputs']=[name for name,digest in metric['outputs'].items() if sha256(RESULTS/name)!=digest]
    facts['changed_maps']=[r['path'] for r in read_csv(RESULTS/'map_manifest.csv') if sha256(ROOT/r['path'])!=r['sha256']]
    environment=json.loads((TASK5/'runtime/runtime_environment.json').read_text(encoding='utf-8'))
    current=runtime_fingerprint()
    facts['runtime_changed_dependencies']=[name for name,digest in environment['measurement_inputs_code_sha256'].items() if current.get(name)!=digest]
    facts['runtime_changed_samples']=[name for name,digest in environment['sample_files_sha256'].items() if sha256(TASK5/'runtime'/name)!=digest]
    analysis=json.loads((TASK5/'analysis_manifest.json').read_text(encoding='utf-8'))
    facts['analysis_changed_outputs']=[name for name,digest in analysis['outputs'].items() if not (TASK5/name).is_file() or sha256(TASK5/name)!=digest]
    facts['analysis_matches_metric_manifest']=analysis['metric_manifest_sha256']==sha256(RESULTS/'run_manifest.json')
    t2=read_csv(RESULTS/'tier2_results_both.csv'); summary=read_csv(RESULTS/'tier2_summary.csv')
    errors=[]
    for r in summary:
        group=[x for x in t2 if all(x[k]==r[k] for k in ('source','task','sigma'))]
        for key in ('precision','recall','f1'):
            if abs(sum(float(x[key]) for x in group)/len(group)-float(r['macro_'+key]))>1e-12: errors.append(r)
    audit=json.loads((RESULTS/'blob_matching_audit.json').read_text(encoding='utf-8'))
    for r in (x for x in t2 if x['task']=='blob_log'):
        a=audit[f"{r['source']}_{r['image']}"]
        ann=json.loads((ROOT/f"data/gt/blob/{r['image']}.json").read_text(encoding='utf-8'))
        pairs,ids,pids=match_blobs(ann['objects'],a['detections'],ann.get('ignore_regions',[]))
        if (len(pairs),len(ids),len(pids))!=(int(r['tp']),int(r['gt_count']),int(r['predicted_count'])): errors.append(r)
    facts['tier2_internal_errors']=len(errors)
    facts['tier2_rows']=len(t2)
    facts['tier1']=dict(Counter(r['status'] for r in read_csv(RESULTS/'tier1_report.csv')))
    cfg=strict_config(); old_digest=metric['code_config_sha256']['config.yaml']; proof=[]
    candidates=[ROOT.parent/'config.yaml',Path('C:/Users/admin/Documents/XLA-dev-NguyenDucManh/config.yaml'),Path('C:/Users/admin/Documents/git desktop/XLA/config.yaml')]
    for p in candidates:
        if not p.is_file(): continue
        text=p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
        for newline in ('\n','\r\n'):
            for bom in ('','\ufeff'):
                data=(bom+text.replace('\n',newline)).encode('utf-8')
                if hashlib.sha256(data).hexdigest()==old_digest:
                    proof.append(dict(path=str(p),matches_previous_digest=True,same_yaml_values=yaml.safe_load(text)==cfg))
    facts['previous_config_proof']=proof
    calibration=measure_calibration()
    facts['calibration']=dict(tiffs=calibration['tiffs'],measurements=calibration['measurements'],profiles=calibration['profiles'],issues=calibration['issues'],screenshots=len(calibration['screenshots']))
    with ZipFile(ROOT/'docs/slides/BTL_XLA_Nhom_BaoCao.pptx') as z:
        slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
        facts['slides']=dict(count=len(slides),corrupt_entry=z.testzip())
    tex=(ROOT/'docs/report_template/main.tex').read_text(encoding='utf-8')
    sections=list(re.finditer(r'\\section\{([^}]+)\}',tex))
    facts['report']=dict(lines=len(tex.splitlines()),section_tokens={m.group(1):len(tex[m.end():sections[i+1].start() if i+1<len(sections) else len(tex)].split()) for i,m in enumerate(sections)},
        missing_figures=[p for p in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',tex) if not (ROOT/'docs/report_template'/p).is_file()],
        compilers={x:shutil.which(x) for x in ('pdflatex','xelatex','lualatex','latexmk')})
    facts['report_pdfs']=[str(p.relative_to(ROOT)) for p in (ROOT/'docs').rglob('*.pdf')]
    seen=set(); zip_errors=[]
    files={p.name:p for p in (ROOT/'outputs/python').glob('*.tif')}
    for p in (ROOT/'outputs/archives/duc_08_11').glob('*.zip'):
        with ZipFile(p) as z:
            if z.testzip() is not None: zip_errors.append(p.name)
            for name in z.namelist():
                if name not in files or hashlib.sha256(z.read(name)).hexdigest()!=sha256(files[name]): zip_errors.append(name)
                seen.add(name)
    facts['archives']=dict(maps=len(seen),source_maps=len(files),complete=seen==set(files),issues=zip_errors)
    write('AUDIT_FACTS.json',facts)
    print(json.dumps(facts,ensure_ascii=True,indent=2),flush=True)


def supplement():
    facts=json.loads((OUT/'AUDIT_FACTS.json').read_text(encoding='utf-8'))
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    tasks=[]
    with ZipFile(next(ROOT.glob('*.xlsx'))) as z:
        shared=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)] if 'xl/sharedStrings.xml' in z.namelist() else []
        for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//s:row',ns):
            cells={}
            for c in row.findall('s:c',ns):
                v=c.find('s:v',ns)
                value=v.text if v is not None else ''.join(c.itertext())
                if c.get('t')=='s': value=shared[int(value)]
                cells[re.sub(r'\d','',c.get('r'))]=value
            if not (cells.get('A') or '').isdigit(): continue
            n=int(cells['A'])
            tasks.append(dict(stt=n,group=cells.get('B',''),task=cells.get('C',''),required=cells.get('D',''),
                deadline=(datetime(1899,12,30)+timedelta(days=float(cells['E']))).strftime('%Y-%m-%d'),
                assigned_in_sheet=cells.get('F',''),role_for_review='Hưng' if n<=7 else 'Mạnh' if n<=14 else 'Lộc' if n<=19 else 'Đức' if n<=24 else 'Nhóm'))
    with (OUT/'TASKS_FROM_WORKBOOK.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(tasks[0]));writer.writeheader();writer.writerows(tasks)
    facts['workbook_tasks']=len(tasks)
    ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
    with ZipFile(ROOT/'docs/slides/BTL_XLA_Nhom_BaoCao.pptx') as z:
        text='\n'.join(' '.join(x.text or '' for x in ET.fromstring(z.read(n)).findall('.//a:t',ns)) for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n))
    facts['slide_current_scores_present']={score:score in text for score in ['0.477886','0.477382','0.473863','0.492091','0.486865']}
    tex=(ROOT/'docs/report_template/main.tex').read_text(encoding='utf-8')
    labels=set(re.findall(r'\\label\{([^}]+)\}',tex))
    refs=set(re.findall(r'\\(?:ref|eqref)\{([^}]+)\}',tex))
    citations={k.strip() for c in re.findall(r'\\cite\w*\{([^}]+)\}',tex) for k in c.split(',')}
    bib=(ROOT/'docs/report_template/references.bib').read_text(encoding='utf-8')
    keys=set(re.findall(r'@\w+\{\s*([^,]+),',bib))
    facts['report'].update(missing_refs=sorted(refs-labels),missing_citations=sorted(citations-keys),bib_entries=len(keys))
    opt=read_csv(ROOT/'outputs/metrics/optimization_benchmark.csv')
    facts['optimization']=dict(rows=len(opt),repeats=dict(Counter(r['reps'] for r in opt)),maximum_error=max(float(r['max_abs_diff']) for r in opt))
    cross=json.loads((OUT/'TIMING_LIBRARY_CALIBRATION.json').read_text(encoding='utf-8'))
    facts['cross_library_calibration']=cross
    write('AUDIT_FACTS.json',facts)
    print(json.dumps(dict(tasks=len(tasks),cross_library=cross,slide_scores=facts['slide_current_scores_present']),ensure_ascii=True))


if __name__=='__main__':
    supplement() if '--supplement-only' in sys.argv else main()
