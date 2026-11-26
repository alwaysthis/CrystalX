"""Kiessig fringe spacing estimates, independent of Qt and plot styling."""
from dataclasses import dataclass
import math
import numpy as np
from scipy.ndimage import gaussian_filter1d,median_filter
from scipy.signal import find_peaks

@dataclass(frozen=True)
class ThicknessResult:
    thickness_nm: float
    standard_error_nm: float|None
    r2: float
    slope: float
    q: list
    intervals_nm: list

def wavelength_from_metadata(metadata):
    try: value=float(metadata.get('HW_XG_WAVE_LENGTH_ALPHA1',''))
    except (TypeError,ValueError): return 1.5406,'未读取到波长，暂用 Cu Kα₁；请核对。'
    unit=metadata.get('HW_XG_WAVE_LENGTH_UNIT','').lower().strip()
    if unit in ('nm','nanometer'): value*=10
    elif unit not in ('angstrom','angstroms','a','å'): return 1.5406,'波长单位未知，暂用 Cu Kα₁；请核对。'
    if not math.isfinite(value) or value<=0: return 1.5406,'波长无效，暂用 Cu Kα₁；请核对。'
    return value,'波长读取自文件 Kα₁。'

def estimate_thickness(positions,wavelength=1.5406,axis='2theta',orders=None,critical_angle=0):
    values=np.asarray(positions,dtype=float)
    if values.ndim!=1 or len(values)<2 or not np.isfinite(values).all(): raise ValueError('至少需要两个有限、不同的同类条纹峰位。')
    if not math.isfinite(wavelength) or wavelength<=0: raise ValueError('波长须为正数，单位Å。')
    if not math.isfinite(critical_angle) or not 0<=critical_angle<90: raise ValueError('临界角θc须在0到90°之间。')
    if axis in ('2theta','theta'):
        theta=values/2 if axis=='2theta' else values
        if np.any(theta<=0) or np.any(theta>=90): raise ValueError('入射角θ须在0到90°之间，请检查横轴是θ还是2θ。')
        q=4*np.pi*np.sin(np.deg2rad(theta))/wavelength
    elif axis in ('q_a','q_nm'): q=values if axis=='q_a' else values/10
    else: raise ValueError('不支持的横轴类型。')
    qc=4*np.pi*np.sin(np.deg2rad(critical_angle))/wavelength
    if np.any(q<=qc): raise ValueError('所选峰须位于临界角之上；请去掉临界边附近的峰。')
    q=np.sqrt(q*q-qc*qc)
    if orders is None: orders=np.argsort(np.argsort(q))
    orders=np.asarray(orders,dtype=float)
    if orders.shape!=q.shape or not np.isfinite(orders).all() or np.any(orders!=np.round(orders)): raise ValueError('级次须为整数，且与所选峰一一对应。')
    sorting=np.argsort(q); q=q[sorting]; orders=orders[sorting]
    if np.any(np.diff(q)<=0) or np.any(np.diff(orders)<=0): raise ValueError('峰位不能重复，级次须随峰位严格递增；漏峰时请保留级次间隔。')
    centered=orders-orders.mean(); slope=float(np.dot(centered,q-q.mean())/np.dot(centered,centered))
    prediction=q.mean()+slope*centered; residual=float(np.sum((q-prediction)**2)); total=float(np.sum((q-q.mean())**2))
    thickness=2*np.pi/slope/10
    error=thickness*math.sqrt(residual/(len(q)-2)/float(np.dot(centered,centered)))/slope if len(q)>2 else None
    return ThicknessResult(thickness,error,1-residual/total,slope,q.tolist(),(2*np.pi*np.diff(orders)/np.diff(q)/10).tolist())

def detect_fringe_maxima(x,y,minimum=None,maximum=None):
    from .xrr_fringe import analyze_fringes
    result=analyze_fringes(x,y,minimum,maximum)
    return [peak.x for peak in result.result.peaks if peak.status=='可靠']
