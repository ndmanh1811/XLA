"""Comparable Fiji responses and display/statistic rules for the live demo.

No detector or canonical metric is changed here. Missing components never fall
back to an unrelated TIFF. Values are computed in float64, before PNG rendering.
"""
from pathlib import Path
from functools import lru_cache
import csv
import json
import numpy as np

from src.core.detectors import detect_ridge
from src.core.structure_tensor import compute_structure_coherence
from src.eval.metric_utils import ROOT, RESULTS, read_map, normalize_scale, erode_square, sha256


class MissingReference(ValueError):
    pass


@lru_cache(maxsize=4)
def _reference_registry(manifest_stamp, maps_stamp):
    manifest=json.loads((RESULTS/'run_manifest.json').read_text(encoding='utf-8'))
    if manifest['status']!='COMPLETE' or sha256(RESULTS/'map_manifest.csv')!=manifest['outputs']['map_manifest.csv']:
        raise MissingReference('Phiên bản đồ chưa COMPLETE hoặc manifest đã thay đổi.')
    with (RESULTS/'map_manifest.csv').open(encoding='utf-8-sig',newline='') as f:
        records={r['path'].replace('\\','/'):r['sha256'] for r in csv.DictReader(f) if r['source']=='fiji'}
    return manifest['code_config_sha256']['config.yaml'],records


def align_fiji(array, sigma, order, command, cfg, normalized):
    if normalized:
        return normalize_scale(array, sigma, order, 'fiji', command, cfg)
    # Standalone raw displays must undo a normalization already applied by Fiji.
    return array / float(sigma)**order if cfg['featurej_normalized'][command] else array


def build_reference(image_id, algo, dtype, sigma, sigma_d, sigma_i, shape, cfg,
                    normalized=True, scales=None, beta=.5, c=None, polarity='dark',
                    fov=None, use_fov=True, directory=None):
    meta = dict(has_fiji=False, scope='full_image_live', files=[])
    if image_id.startswith('custom_'):
        meta['message'] = 'Ảnh tải lên chưa có bản đồ Fiji tương ứng.'
        return None, meta, None
    directory = Path(directory or ROOT/'outputs/fiji')
    registry=None
    if directory == ROOT/'outputs/fiji':
        try:
            paths=[RESULTS/'run_manifest.json',RESULTS/'map_manifest.csv']
            stamps=[(p.stat().st_mtime_ns,p.stat().st_size) for p in paths]
            recorded_config,registry=_reference_registry(*stamps)
            if sha256(ROOT/'config.yaml')!=recorded_config:
                raise MissingReference('Config đã đổi so với bản đồ Fiji; cần xác minh lại phiên thực nghiệm.')
        except (OSError,ValueError,KeyError) as exc:
            meta['message']=str(exc)
            return None,meta,None

    def load(op, scale=None, pair=None):
        if pair is None:
            # Do not silently round an off-grid request onto another scale.
            if float(scale) != float(f'{scale:.1f}'):
                raise MissingReference(f'Chưa có TIFF Fiji cho σ={scale:g}.')
            name=f'fiji_{image_id}_{op}_s{scale:.1f}.tif'
        else:
            if any(float(v)!=float(f'{v:.1f}') for v in pair):
                raise MissingReference('Chưa có TIFF Fiji cho cặp scale đã chọn.')
            name=f'fiji_{image_id}_{op}_sd{pair[0]:.1f}_si{pair[1]:.1f}.tif'
        path=directory/name
        if not path.is_file():
            raise MissingReference(f'Thiếu {name}; không tính chỉ số cho tham chiếu không đủ.')
        if registry is not None and registry.get(path.relative_to(ROOT).as_posix())!=sha256(path):
            raise MissingReference(f'{name} chưa khớp checksum phiên thực nghiệm.')
        arr=read_map(path,shape)
        meta['files'].append(name)
        return arr

    valid=None
    try:
        if algo=='gaussian':
            result=load('gauss',sigma)
            label='Fiji Gaussian'
        elif algo in ('gradient','canny'):
            if algo=='gradient' and dtype in ('lx','ly'):
                result=align_fiji(load(dtype,sigma),sigma,1,'derivatives',cfg,False)
                label=f'Fiji {dtype}'
            else:
                x=load('lx',sigma);y=load('ly',sigma)
                if dtype=='angle' and algo=='gradient':
                    result=np.arctan2(y,x)
                    mag=np.hypot(x,y)
                    valid=mag>max(1e-12,float(mag.max())*1e-10)
                    label='Fiji atan2(Ly, Lx) · góc gradient'
                else:
                    x=align_fiji(x,sigma,1,'derivatives',cfg,algo=='canny')
                    y=align_fiji(y,sigma,1,'derivatives',cfg,algo=='canny')
                    result=np.hypot(x,y)
                    label='Fiji Lx, Ly → |∇L| (response)'
        elif algo=='second_order':
            op={'lxx':'lxx','lyy':'lyy','lxy':'lxy'}.get(dtype,'lap')
            command='laplacian' if op=='lap' else 'derivatives'
            result=align_fiji(load(op,sigma),sigma,2,command,cfg,normalized)
            label=f'Fiji {op}'
        elif algo=='hessian':
            result=align_fiji(load('hess-'+dtype,sigma),sigma,2,'hessian',cfg,True)
            label=f'Fiji Hessian {dtype} · {cfg["eigen_order"]}'
        elif algo=='frangi':
            responses=[]
            k=max(cfg['kernel_k'].values())
            for s in scales:
                x=align_fiji(load('hess-l1',s),s,2,'hessian',cfg,True)
                y=align_fiji(load('hess-l2',s),s,2,'hessian',cfg,True)
                a=detect_ridge(x,y,sigma=s,beta=beta,c=c,polarity=polarity)
                if use_fov and fov is not None:
                    a[~erode_square(fov,int(np.ceil(k*s)))]=0
                responses.append(a)
            result=np.maximum.reduce(responses)
            label=f'Fiji Hessian → Python Frangi (hybrid, {len(scales)} scale)'
        elif algo=='blob':
            stack=[align_fiji(load('lap',s),s,2,'laplacian',cfg,True) for s in scales]
            result=np.max(np.abs(np.stack(stack)),axis=0)
            label=f'Fiji max |σ²LoG| ({len(scales)} scale, response)'
        elif algo=='structure_tensor':
            pair=(sigma_d,sigma_i)
            a=align_fiji(load('st-l1',pair=pair),sigma_d,2,'structure',cfg,False)
            b=align_fiji(load('st-l2',pair=pair),sigma_d,2,'structure',cfg,False)
            result=a if dtype=='mu1' else b if dtype=='mu2' else compute_structure_coherence(a,b)
            label=f'Fiji Structure Tensor · {dtype}'
        else:
            raise ValueError('Unknown algorithm')
    except (MissingReference, OSError, ValueError) as exc:
        meta['message']=str(exc)
        return None,meta,None
    meta.update(has_fiji=True,fiji_file=' + '.join(meta['files']),title=label,
                message='Toàn ảnh, dữ liệu live; không phải phép nghiệm thu STRICT đã crop lõi.')
    return result,meta,valid


def compare_maps(python, fiji, angular=False, valid=None):
    a=np.asarray(python,dtype=float);b=np.asarray(fiji,dtype=float)
    if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Các bản đồ so sánh phải cùng shape và có giá trị hữu hạn.')
    if angular:
        mask=np.ones(a.shape,dtype=bool) if valid is None else valid
        delta=np.arctan2(np.sin(a-b),np.cos(a-b))
        values=delta[mask]
        stats=dict(kind='angular',unit='rad',pearson=None,valid_pixels=int(mask.sum()),
                   pearson_reason='Góc tuần hoàn: dùng sai lệch góc, không dùng Pearson tuyến tính.')
        stats.update(mae=float(np.mean(np.abs(values))) if values.size else None,
                     rmse=float(np.sqrt(np.mean(values**2))) if values.size else None)
        stats['mean_angular_error_deg']=float(np.rad2deg(stats['mae'])) if values.size else None
        return np.where(mask,np.abs(delta),0),stats
    diff=np.abs(a-b)
    r=None
    if np.ptp(a)>0 and np.ptp(b)>0:
        measured=float(np.corrcoef(a.ravel(),b.ravel())[0,1])
        if np.isfinite(measured): r=measured
    return diff,dict(kind='continuous',unit='response',mse=float(np.mean(diff**2)),
                     mae=float(np.mean(diff)),rmse=float(np.sqrt(np.mean(diff**2))),
                     max_error=float(diff.max()),pearson=r,
                     pearson_reason=None if r is not None else 'Pearson không xác định khi có mảng hằng.')


def shared_limits(python,fiji=None,angular=False,signed=False):
    if angular: return -float(np.pi),float(np.pi)
    arrays=[np.asarray(python)] + ([np.asarray(fiji)] if fiji is not None else [])
    lo=min(float(a.min()) for a in arrays);hi=max(float(a.max()) for a in arrays)
    if signed:
        peak=max(abs(lo),abs(hi),1e-12)
        return -peak,peak
    return min(0.,lo),max(hi,1e-12)
