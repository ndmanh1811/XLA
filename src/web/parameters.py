"""Validated live-demo parameters; measured settings come from shared config."""
import re
import json
import numpy as np
from src.eval.metric_utils import ROOT, RESULTS, strict_config
from src.eval.task5_runtime import read_csv

DISPLAY_TYPES={
    'gaussian':(None,), 'gradient':('mag','lx','ly','angle'), 'canny':(None,),
    'second_order':('laplacian','lxx','lyy','lxy'), 'hessian':('l2','l1'),
    'frangi':(None,), 'blob':(None,), 'structure_tensor':('coherence','mu1','mu2'),
}


def web_settings():
    cfg=strict_config()
    edges=read_csv(RESULTS/'bsds_selected_thresholds.csv')
    edge_pairs={str(float(r['sigma'])):[float(r['p_low']),float(r['p_high'])] for r in edges}
    if any(str(float(s)) not in edge_pairs for s in cfg['sigmas']) or any(
        not (0<=pair[0]<=pair[1]<=100) for pair in edge_pairs.values()
    ):
        raise ValueError('Lưới ngưỡng Canny chưa khớp config; cần chạy lại metric.')
    ridge=next(r for r in read_csv(RESULTS/'ridge_threshold_grid.csv') if r['selected'].lower()=='true')
    blob=next(r for r in read_csv(RESULTS/'blob_threshold_grid.csv') if r['selected'].lower()=='true')
    polarities={p.stem:json.loads(p.read_text(encoding='utf-8'))['polarity'] for p in (ROOT/'data/gt/blob').glob('blob_??.json')}
    return cfg,dict(sigmas=cfg['sigmas'],blob_sigmas=cfg['sigmas_blob'],structure_pairs=cfg['structure_pairs'],
                    image_polarities=polarities,
                    border_mode=cfg['border_mode'],eigen_order=cfg['eigen_order'],
                    canny_thresholds=edge_pairs,
                    ridge_threshold=float(ridge['threshold']),blob_threshold=float(blob['threshold']))


def validate_request(data,settings):
    if not isinstance(data,dict): raise ValueError('JSON phải là một object.')
    p=dict(data)
    p['image_id']=data.get('image_id','bsds_01')
    if not isinstance(p['image_id'],str) or not re.fullmatch(r'(?:(?:bsds|drive|blob)_\d{2}|custom_[A-Za-z0-9_]+)',p['image_id']):
        raise ValueError('Tên ảnh không hợp lệ.')
    algo=data.get('algorithm','canny')
    if not isinstance(algo,str) or algo not in DISPLAY_TYPES: raise ValueError('Thuật toán không được hỗ trợ.')
    p['algorithm']=algo
    default_sigma=2. if 2. in settings['sigmas'] else settings['sigmas'][0]

    def number(key,default,lo=0,hi=32,inclusive=False):
        raw=data.get(key,default)
        if isinstance(raw,bool): raise ValueError(f'{key} phải là số.')
        try: value=float(raw)
        except (TypeError,ValueError): raise ValueError(f'{key} phải là số hữu hạn.')
        if not np.isfinite(value) or value>hi or (value<lo if inclusive else value<=lo):
            raise ValueError(f'{key} ngoài miền hợp lệ ({lo} đến {hi}).')
        p[key]=value
        return value

    sigma=number('sigma',default_sigma)
    pair=settings['structure_pairs'][0]
    number('sigma_d',pair[0]);number('sigma_i',pair[1])
    thresholds=settings['canny_thresholds'].get(str(sigma),settings['canny_thresholds'][str(default_sigma)])
    low=number('p_low',thresholds[0],hi=100,inclusive=True)
    high=number('p_high',thresholds[1],hi=100,inclusive=True)
    if low>high: raise ValueError('Ngưỡng Low phải nhỏ hơn hoặc bằng High.')
    number('beta',.5,hi=10)
    number('threshold',settings['blob_threshold'] if algo=='blob' else settings['ridge_threshold'],hi=1e6,inclusive=True)
    if data.get('c') not in (None,''): number('c',None,hi=1e12)
    else: p['c']=None
    for key,default in [('nms',True),('normalized',True),('use_fov',True),('multiscale',True),('show_ignore',True)]:
        value=data.get(key,default)
        if type(value) is not bool: raise ValueError(f'{key} phải là true hoặc false.')
        p[key]=value
    dtype=data.get('display_type') or DISPLAY_TYPES[algo][0]
    if dtype not in DISPLAY_TYPES[algo]: raise ValueError('Thành phần hiển thị không hợp lệ.')
    p['display_type']=dtype
    polarity=data.get('polarity',settings['image_polarities'].get(p['image_id'],'bright') if algo=='blob' else 'dark')
    if polarity not in ('dark','bright'): raise ValueError('Polarity phải là bright hoặc dark.')
    p['polarity']=polarity
    if data.get('colormap','inferno') not in ('gray','inferno','viridis','magma','plasma','RdBu_r','coolwarm','turbo'):
        raise ValueError('Colormap không được hỗ trợ.')
    p['colormap']=data.get('colormap','inferno')
    return p
