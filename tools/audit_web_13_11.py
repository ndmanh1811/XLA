"""Read-only numerical/API review of the web demo; no production files changed.

Runs the real Flask routes with test_client, compares current presets with the
canonical per-image CSV, and isolates corner cases with mock/temporary inputs.
"""
from collections import Counter
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from PIL import Image
import tifffile
from src.web import app as web
from src.eval.analyze_task5 import verify_metric_delivery
from src.eval.metric_utils import sha256, strict_config, normalize_scale, scores, match_blobs
from src.eval.task5_runtime import read_csv
from src.core.detectors import detect_canny
from src.eval.bsds_threshold_grid import evaluate_prediction

OUT = ROOT / 'docs/13_11/kiem_tra_web_app'


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    protected = [ROOT/'config.yaml', ROOT/'src/web/app.py', ROOT/'src/web/templates/index.html',
                 *sorted((ROOT/'outputs/metrics/duc_10_11').glob('*')),
                 ROOT/'outputs/analysis/duc_task5_10_11/analysis_manifest.json']
    before = {str(p.relative_to(ROOT)): sha256(p) for p in protected if p.is_file()}
    data = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                scope='real Flask test_client + isolated mocks; no browser layout audit',
                api_cases=[], preset_comparison=[], checks={})
    client = web.app.test_client()
    web.app.logger.disabled = True

    def request(payload):
        r = client.post('/api/process', json=payload)
        answer = r.get_json(silent=True)
        row = dict(payload=payload, status_code=r.status_code, json=answer is not None)
        if answer:
            row.update({k: answer[k] for k in ('error','gt_metrics','fiji_metrics','timing') if k in answer})
        data['api_cases'].append(row)
        print(f"API {payload['algorithm']} {payload['image_id']}: HTTP {r.status_code}, F1={answer.get('gt_metrics',{}).get('f1') if answer else None}", flush=True)
        return answer or {}, row

    try:
        verify_metric_delivery()
        data['checks']['canonical_provenance'] = 'PASS'
    except Exception as exc:
        data['checks']['canonical_provenance'] = f'{type(exc).__name__}: {exc}'

    canonical = read_csv(web.RESULTS/'tier2_results_both.csv')
    index = {(r['source'],r['task'],r['image'],r['sigma']):r for r in canonical}
    for cat, count in [('bsds',10),('drive',10),('blob',5)]:
        for i in range(1,count+1):
            image = f'{cat}_{i:02d}'
            if cat=='bsds':
                payload = dict(image_id=image,algorithm='canny',sigma=2,p_low=67,p_high=91)
                key = ('python','edge_bsds',image,'2.0')
            elif cat=='drive':
                payload = dict(image_id=image,algorithm='frangi',threshold=.05,use_fov=True,multiscale=True)
                key = ('python','ridge_drive',image,'multiscale')
            else:
                ann = json.loads((ROOT/f'data/gt/blob/{image}.json').read_text(encoding='utf-8'))
                payload = dict(image_id=image,algorithm='blob',threshold=5,polarity=ann['polarity'],show_ignore=True)
                key = ('python','blob_log',image,'multiscale')
            answer,_ = request(payload)
            expected = index[key]
            measured = answer.get('gt_metrics',{})
            delta = {k: measured.get(k,0)-round(float(expected[k]),4) for k in ('precision','recall','f1')}
            data['preset_comparison'].append(dict(image=image,algorithm=payload['algorithm'],
                web=measured,canonical={k:float(expected[k]) for k in ('precision','recall','f1')},
                delta_at_four_decimals=delta,match=all(abs(v)<1e-10 for v in delta.values())))

    for algorithm, types in [('gaussian',[None]),('gradient',['mag','lx','ly']),
                             ('second_order',['lxx','lyy','lxy']),('hessian',['l1','l2']),
                             ('structure_tensor',['coherence','mu1','mu2'])]:
        for display in types:
            payload=dict(image_id='bsds_01',algorithm=algorithm,sigma=2)
            if display: payload['display_type']=display
            request(payload)
    for sigma in (1,4,8):
        selected=next(r for r in read_csv(web.RESULTS/'bsds_selected_thresholds.csv') if float(r['sigma'])==sigma)
        request(dict(image_id='bsds_01',algorithm='canny',sigma=sigma,
                     p_low=float(selected['p_low']),p_high=float(selected['p_high'])))

    angle,_ = request(dict(image_id='bsds_01',algorithm='gradient',display_type='angle',sigma=2))
    lx = tifffile.imread(ROOT/'outputs/fiji/fiji_bsds_01_lx_s2.0.tif').astype(float)
    ly = tifffile.imread(ROOT/'outputs/fiji/fiji_bsds_01_ly_s2.0.tif').astype(float)
    a = np.asarray(Image.open(ROOT/'data/raw/bsds_01.png'),dtype=float)
    ax,ay = web.compute_derivatives_1st(a,2,mode='mirror')
    correct = np.arctan2(ly,lx)
    data['checks']['gradient_angle'] = dict(
        web=angle.get('fiji_metrics'),
        correct_counterpart='atan2(Fiji Ly, Fiji Lx)',
        correct_mae=float(np.mean(np.abs(np.arctan2(ay,ax)-correct))),
        correct_pearson=float(np.corrcoef(np.arctan2(ay,ax).ravel(),correct.ravel())[0,1]))

    cf,_ = request(dict(image_id='bsds_03',algorithm='canny',sigma=2,p_low=67,p_high=91))
    source=np.asarray(Image.open(ROOT/'data/raw/bsds_03.png'),dtype=float)
    gx,gy=web.compute_derivatives_1st(source,2,mode='mirror')
    fgx=tifffile.imread(ROOT/'outputs/fiji/fiji_bsds_03_lx_s2.0.tif').astype(float)
    fgy=tifffile.imread(ROOT/'outputs/fiji/fiji_bsds_03_ly_s2.0.tif').astype(float)
    mag_python=np.hypot(gx,gy)*2
    mag_fiji=np.hypot(fgx,fgy)*2
    data['checks']['canny_missing_gradient_fallback'] = dict(web=cf.get('fiji_metrics'),
        correct_mae=float(np.mean(np.abs(mag_python-mag_fiji))),
        correct_pearson=float(np.corrcoef(mag_python.ravel(),mag_fiji.ravel())[0,1]))
    bf,_ = request(dict(image_id='bsds_01',algorithm='blob',threshold=5))
    data['checks']['blob_incomplete_stack_fallback'] = bf.get('fiji_metrics')

    on,_ = request(dict(image_id='blob_05',algorithm='blob',threshold=5,show_ignore=True))
    off,_ = request(dict(image_id='blob_05',algorithm='blob',threshold=5,show_ignore=False))
    data['checks']['ignore_toggle'] = dict(enabled=on.get('gt_metrics'),disabled=off.get('gt_metrics'),
        same_metric=on.get('gt_metrics')==off.get('gt_metrics'),
        overlay_changes=on.get('img_gt_overlay')!=off.get('img_gt_overlay'))
    ann=json.loads((ROOT/'data/gt/blob/blob_05.json').read_text(encoding='utf-8'))
    audit=json.loads((web.RESULTS/'blob_matching_audit.json').read_text(encoding='utf-8'))
    det=audit['python_blob_05']['detections']
    pairs,gt_ids,pred_ids=match_blobs(ann['objects'],det,[])
    data['checks']['ignore_toggle']['actual_scores_without_ignore']=dict(zip(('precision','recall','f1'),scores(len(pairs),len(pred_ids),len(gt_ids))))

    shape=a.shape
    with patch.object(web,'gaussian_smooth',return_value=np.ones(shape)), patch.object(web.tifffile,'imread',return_value=np.ones(shape)):
        constant,_ = request(dict(image_id='bsds_01',algorithm='gaussian',sigma=2))
    data['checks']['constant_pearson_isolation'] = dict(reported=constant.get('fiji_metrics'),expected_pearson=None)
    values=np.arange(100,dtype=float).reshape(10,10)
    data['checks']['independent_colormap_ranges'] = dict(
        render_a_equals_render_2a=web.array_to_base64_png(values,cmap='inferno')==web.array_to_base64_png(2*values,cmap='inferno'))

    # Compare full-image live error with the canonical cropped-core protocol.
    for sigma in (2,8):
        response,_=request(dict(image_id='bsds_01',algorithm='second_order',display_type='laplacian',sigma=sigma,normalized=False))
        recorded=next(r for r in read_csv(web.RESULTS/'tier1_report.csv') if r['image']=='bsds_01' and r['operator']=='lap' and float(r['sigma'])==sigma)
        data['checks'][f'live_vs_core_laplacian_sigma{sigma}'] = dict(web=response.get('fiji_metrics'),
            canonical_core={k:recorded[k] for k in ('crop_px','mae','rmse','pearson_r')})

    # Current numeric settings are correct; test whether flags would be honored,
    # without editing the real config or TIFFs.
    cfg=strict_config()
    cfg['featurej_normalized']['laplacian']=True
    with patch('src.config.load_config',return_value=cfg):
        normalized_flag,_=request(dict(image_id='bsds_01',algorithm='second_order',display_type='laplacian',sigma=2))
    data['checks']['normalized_flag_isolation'] = dict(web=normalized_flag.get('fiji_metrics'),
        expected='Fiji Laplacian should not be multiplied by sigma² again when flag is true')

    for payload in [dict(image_id='bsds_01',algorithm='unknown'),
                    dict(image_id='bsds_01',algorithm='gaussian',sigma='abc'),
                    dict(image_id='bsds_01',algorithm='gaussian',sigma=0),
                    dict(image_id='bsds_01',algorithm='canny',p_low=95,p_high=10)]:
        request(payload)

    # Uploaded data is scoped to a temporary directory, never the real upload dir.
    with tempfile.TemporaryDirectory() as tmp, patch.object(web,'UPLOAD_DIR',Path(tmp)):
        r=client.post('/api/upload',data={'file':(io.BytesIO(b'not a png'),'bad.png')})
        data['checks']['invalid_upload'] = dict(status=r.status_code,json=r.is_json)
        rgb=np.zeros((12,12,3),dtype=np.uint8);rgb[:,:,1]=255
        buf=io.BytesIO();Image.fromarray(rgb).save(buf,format='PNG');buf.seek(0)
        r=client.post('/api/upload',data={'file':(buf,'green.png')})
        path=Path(tmp)/(r.get_json()['id']+'.png')
        data['checks']['upload_grayscale'] = dict(status=r.status_code,pixel=int(np.asarray(Image.open(path))[0,0]),
            note='generic upload uses PIL L conversion; not dataset-specific DRIVE green extraction')

    benchmark=client.get('/api/benchmarks')
    figures=client.get('/api/figures')
    images=client.get('/api/images')
    live_bench=benchmark.get_json()
    data['checks']['data_endpoints']=dict(benchmark_status=benchmark.status_code,
        tier1_records=len(live_bench['tier1']),tier1_status=dict(Counter(r['status'] for r in live_bench['tier1'])),
        tier2_summary_matches_csv=live_bench['tier2_summary']==read_csv(web.RESULTS/'tier2_summary.csv'),
        figures=len(figures.get_json()),images={k:len(v) for k,v in images.get_json().items()},
        all_figure_urls_ok=all(client.get(f['url']).status_code==200 for f in figures.get_json()))
    home=client.get('/').get_data(as_text=True)
    headline_rows=[r for r in live_bench['tier2_summary'] if r['source']=='python' and
                   (r['task']!='edge_bsds' or float(r['sigma'])==2)]
    data['checks']['static_benchmark_headlines']=dict(hardcoded_in_template=True,
        expected_from_csv={r['task']:round(float(r['macro_f1']),4) for r in headline_rows},
        current_rounded_values_match=all(f">{float(r['macro_f1']):.4f} <span" in home for r in headline_rows))
    frangi_times=[c['timing'] for c in data['api_cases'] if c['payload']['algorithm']=='frangi' and 'timing' in c]
    data['checks']['frangi_timing_split']=dict(reported_derivative_fractions=[round(t['derivative_ms']/t['total_ms'],3) for t in frangi_times],
        source_rule='t_deriv=t_total*0.7; t_detector=t_total*0.3; not separately measured')
    data['cases_tested']=len(data['api_cases'])
    data['preset_matches']=sum(r['match'] for r in data['preset_comparison'])
    data['preset_total']=len(data['preset_comparison'])
    data['protected_file_changes']=[name for name,digest in before.items() if sha256(ROOT/name)!=digest]
    data['input_sha256']=before
    (OUT/'API_NUMERICAL_AUDIT.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:data[k] for k in ('cases_tested','preset_matches','preset_total','protected_file_changes','checks')},ensure_ascii=True,indent=2))


if __name__=='__main__':
    run()
