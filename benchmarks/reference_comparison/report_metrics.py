"""Measured comparison evidence; no automatic claim of algorithm superiority."""
import numpy as np


def continuous_metrics(actual, reference):
    a=np.asarray(actual,dtype=np.float64)
    b=np.asarray(reference,dtype=np.float64)
    if a.shape!=b.shape or not a.size or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Expected nonempty finite arrays with the same shape')
    delta=a-b
    peak=float(np.max(np.abs(b)))
    maximum=float(np.max(np.abs(delta)))
    defined=a.size>1 and np.ptp(a)>0 and np.ptp(b)>0
    with np.errstate(invalid='ignore',divide='ignore'):
        r=float(np.corrcoef(a.ravel(),b.ravel())[0,1]) if defined else None
    if r is not None and not np.isfinite(r): r=None
    defined=r is not None
    return dict(max_error=maximum,mae=float(np.mean(abs(delta))),rmse=float(np.sqrt(np.mean(delta**2))),
                reference_peak=peak,relative_max_error=maximum/peak if peak>0 else None,
                pearson_r=r,pearson_defined=defined,n_pixels=int(a.size))


def fmt_r(value):
    return 'N/A' if value is None else f'{value:.8f}'


def mask_agreement(actual, reference):
    a=np.asarray(actual,dtype=bool); b=np.asarray(reference,dtype=bool)
    if a.shape!=b.shape or a.ndim!=2: raise ValueError('Expected equally shaped 2D masks')
    overlap=int((a&b).sum()); na=int(a.sum()); nb=int(b.sum()); union=na+nb-overlap
    return dict(iou=overlap/union if union else 0.,dice=2*overlap/(na+nb) if na+nb else 0.,
        overlap_precision=overlap/na if na else 0.,overlap_recall=overlap/nb if nb else 0.,
        custom_pixels=na,reference_pixels=nb,overlap_pixels=overlap,both_empty=not (na or nb))


def component_summary(mask):
    import cv2
    mask=np.asarray(mask,dtype=bool)
    if mask.ndim!=2: raise ValueError('Expected a 2D mask')
    n,_=cv2.connectedComponents(mask.astype(np.uint8),connectivity=8)
    n=int(n)-1  # Exclude background label 0, also for an empty edge mask.
    return dict(components=n,mean_pixels_per_component=float(mask.sum())/n if n else 0.)


def measured_summary_text(pairs,custom_mask,reference_mask):
    lines=['MEASURED COMPARISON']
    for name,(a,b) in pairs.items():
        m=continuous_metrics(a,b)
        lines += [f"{name}: r={fmt_r(m['pearson_r'])}",f"  max |delta|={m['max_error']:.2e}"]
    left,right=component_summary(custom_mask),component_summary(reference_mask)
    lines += [f"8-connected components: {left['components']} / {right['components']}",
              'Mask overlap; no expert GT in this panel.',
              'Different filters/thresholds: report measurements;',
              'no automatic equivalence or superiority verdict.']
    return '\n'.join(lines)


def opencv_border_mode(mode):
    import cv2
    if mode=='mirror': return cv2.BORDER_REFLECT_101
    if mode=='reflect': return cv2.BORDER_REFLECT
    raise ValueError(mode)
