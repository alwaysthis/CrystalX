"""Non-destructive peak candidates in physical x units, independent of Qt."""
from bisect import bisect_left,insort
from dataclasses import dataclass,field
import math
import numpy as np
from scipy.signal import find_peaks,find_peaks_cwt,savgol_filter
from scipy.ndimage import gaussian_filter1d

PEAK_METHODS={'prominence':'突出度法','derivative':'导数法（高斯平滑）','wavelet':'连续小波法（CWT）','fit':'峰型拟合（推荐）'}

@dataclass(frozen=True)
class PeakSettings:
    prominence: float=0
    min_distance: float=0
    min_width: float=0
    max_width: float=0
    smoothing: bool=False
    window: int=7
    method: str='prominence'
    wavelet_min: float=0
    wavelet_max: float=0
    fit_model: str='split_pv'

@dataclass(frozen=True)
class Peak:
    index: int
    x: float
    intensity: float
    prominence: float
    width: float
    fwhm: float|None=None
    r2: float|None=None
    fitted_y: float|None=None
    status: str='可靠'
    reason: str=''

def half_maximum_width(x,signal,index,left,right):
    """Interpolate half height above the line joining the two local bases."""
    if not left<index<right: return None
    corrected=signal[left:right+1]-np.interp(x[left:right+1],[x[left],x[right]],[signal[left],signal[right]])
    center=index-left; level=corrected[center]/2
    if level<=0: return None
    low=center
    while low>0 and corrected[low]>level: low-=1
    high=center
    while high<len(corrected)-1 and corrected[high]>level: high+=1
    if corrected[low]>level or corrected[high]>level: return None
    a=float(np.interp(level,corrected[low:low+2],x[left+low:left+low+2]))
    b=float(np.interp(level,corrected[high-1:high+1][::-1],x[left+high-1:left+high+1][::-1]))
    return b-a

@dataclass
class PeakResult:
    peaks: list
    threshold: float
    noise: float
    overlays: dict=field(default_factory=dict)

def detect_peaks(x,y,settings=PeakSettings(),region=None):
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float)
    source_x,source_y=x,y
    if x.ndim!=1 or y.ndim!=1 or len(x)!=len(y) or len(x)<3 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('寻峰需要至少三个有限的XY数据点。')
    if settings.method not in PEAK_METHODS: raise ValueError('未知的寻峰方法。')
    for value in (settings.prominence,settings.min_distance,settings.min_width,settings.max_width,settings.wavelet_min,settings.wavelet_max):
        if not math.isfinite(value) or value<0: raise ValueError('突出度、间距和宽度必须为有限非负数。')
    if settings.max_width and settings.max_width<settings.min_width: raise ValueError('最大峰宽不能小于最小峰宽。')
    if settings.wavelet_max and settings.wavelet_max<settings.wavelet_min: raise ValueError('小波宽度上限不能小于下限。')
    mapping=np.arange(len(x))
    if region is not None:
        if len(region)!=4 or not all(math.isfinite(v) for v in region) or region[0]>=region[1] or region[2]>=region[3]: raise ValueError('框选范围无效。')
        mask=(x>=region[0])&(x<=region[1]); mapping=mapping[mask]; x=x[mask]; y=y[mask]
        if len(x)<3: raise ValueError('框选范围内至少需要三个数据点。')
    if np.all(np.diff(x)<0): x=x[::-1]; y=y[::-1]; mapping=mapping[::-1]
    if not np.all(np.diff(x)>0): raise ValueError('寻峰要求横坐标严格递增或递减，不能重复。')
    if settings.method=='fit':
        from .peak_fit import fit_peaks
        return fit_peaks(source_x,source_y,settings,region)
    signal=y.copy()
    if settings.smoothing:
        if type(settings.window) is not int or settings.window<3 or settings.window%2!=1 or settings.window>len(x):
            raise ValueError('平滑窗口须为不小于3且不超过数据长度的奇数。')
        step=np.diff(x)
        if not np.allclose(step,np.median(step),rtol=1e-3,atol=1e-10): raise ValueError('Savitzky–Golay平滑需要等间距横坐标；请关闭平滑。')
        signal=savgol_filter(signal,settings.window,2)
    if settings.method=='derivative':
        grid=np.linspace(x[0],x[-1],len(x))
        signal=np.interp(x,grid,gaussian_filter1d(np.interp(grid,x,signal),max(.5,settings.window/6)))
    differences=np.diff(y); noise=float(np.median(np.abs(differences-np.median(differences)))/(.67448975*math.sqrt(2)))
    threshold=settings.prominence or max(5*noise,float(np.ptp(signal))*1e-4,np.finfo(float).eps)
    indices,properties=find_peaks(signal,prominence=threshold,width=(None,None),rel_height=.5)
    candidates=set(map(int,indices))
    if len(indices) and settings.method!='prominence':
        if settings.method=='wavelet':
            grid=np.linspace(x[0],x[-1],len(x)); step=grid[1]-grid[0]
            minimum=max(1,settings.wavelet_min/step or 2); maximum=settings.wavelet_max/step or min(50,len(x)/20)
            if maximum<minimum: raise ValueError('小波宽度范围过小或与采样间距不匹配。')
            widths=np.geomspace(minimum,max(minimum,maximum),min(32,max(2,int(maximum-minimum+1))))
            centers=grid[find_peaks_cwt(np.interp(grid,x,signal),widths,min_snr=2)]
            tolerance=max(2*step,maximum*step)
        else:
            derivative=np.gradient(signal,x)
            crossings=np.flatnonzero((derivative[:-1]>0)&(derivative[1:]<=0))
            centers=(x[crossings]+x[crossings+1])/2; tolerance=max(np.diff(x))*2
        candidates=set()
        for center in centers:
            near=int(indices[np.argmin(abs(x[indices]-center))])
            if abs(x[near]-center)<=tolerance: candidates.add(near)
    positions=np.arange(len(x))
    widths=np.interp(properties['right_ips'],positions,x)-np.interp(properties['left_ips'],positions,x)
    # Suppress close candidates in x units, including nonuniform scan sampling.
    accepted=[]; chosen=[]
    for row in sorted(range(len(indices)),key=lambda i:(-properties['prominences'][i],int(indices[i]))):
        width=float(widths[row]); index=int(indices[row]); position=float(x[index])
        if index not in candidates: continue
        if region is not None and not region[2]<=y[index]<=region[3]: continue
        if width<settings.min_width or settings.max_width and width>settings.max_width: continue
        insertion=bisect_left(accepted,position)
        if insertion and position-accepted[insertion-1]<settings.min_distance: continue
        if insertion<len(accepted) and accepted[insertion]-position<settings.min_distance: continue
        insort(accepted,position)
        fwhm=half_maximum_width(x,signal,index,int(properties['left_bases'][row]),int(properties['right_bases'][row]))
        chosen.append(Peak(int(mapping[index]),position,float(y[index]),float(properties['prominences'][row]),width,fwhm))
    chosen.sort(key=lambda peak:peak.x); contours=[]
    for peak in chosen:
        center=int(np.searchsorted(x,peak.x)); row=int(np.searchsorted(indices,center))
        radius=3*(peak.fwhm or peak.width)
        left=max(int(properties['left_bases'][row]),int(np.searchsorted(x,peak.x-radius)))
        right=min(int(properties['right_bases'][row]),int(np.searchsorted(x,peak.x+radius)),len(x)-1)
        if left>=right: continue
        xx=x[left:right+1]; yy=signal[left:right+1]
        baseline=np.interp(xx,[xx[0],xx[-1]],[yy[0],yy[-1]])
        contours.append({'x':xx.tolist(),'y':yy.tolist(),'baseline':baseline.tolist()})
    smooth={'x':x.tolist(),'y':signal.tolist(),'ranges':[[curve['x'][0],curve['x'][-1]] for curve in contours]} if settings.smoothing or settings.method=='derivative' else {}
    return PeakResult(chosen,float(threshold),noise,{'contours':contours,'smooth':smooth})
