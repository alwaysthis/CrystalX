"""Peak-resistant baselines, with raw XY data left untouched."""
import math
import numpy as np
from scipy.ndimage import uniform_filter1d,median_filter,gaussian_filter1d
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve

METHODS={'auto':'自动（强峰自适应）','snip':'SNIP（强峰抑制）','median':'稳健中位数','asls':'AsLS（线性强度）'}

def validate_background_settings(settings):
    if not isinstance(settings,dict) or set(settings)-{'method','width','smoothing'}: raise ValueError('背景设置格式无效。')
    result={'method':'auto','width':0.,'smoothing':0.}; result.update(settings)
    if result['method'] not in METHODS: raise ValueError('未知的背景拟合方法。')
    for key in ('width','smoothing'):
        if type(result[key]) not in (int,float) or not math.isfinite(result[key]) or result[key]<0: raise ValueError('背景窗口须为有限非负数。')
    return result

def fit_background(x,y,method='auto',width=0,smoothing=0):
    settings=validate_background_settings(dict(method=method,width=width,smoothing=smoothing))
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float)
    if x.ndim!=1 or y.shape!=x.shape or len(x)<5 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('背景拟合需要至少五个有限的XY数据点。')
    descending=np.all(np.diff(x)<0)
    if descending: x=x[::-1]; y=y[::-1]
    if not np.all(np.diff(x)>0): raise ValueError('背景拟合要求横坐标严格递增或递减。')
    if method=='auto':
        reference=max(float(np.median(np.abs(y))),float(np.ptp(y))*1e-9,np.finfo(float).eps)
        method='snip' if np.ptp(y)/reference>=1000 else 'asls'
        settings['method']=method
    # Uniform x sampling makes the smoothness independent of irregular spacing.
    grid=np.linspace(x[0],x[-1],min(len(x),3000 if method=='asls' else 20000)); values=np.interp(grid,x,y)
    if settings['method']!='asls':
        step=grid[1]-grid[0]; span=grid[-1]-grid[0]
        if settings['method']=='snip':
            half=min((len(grid)-1)//2,max(1,round((width or span*.025)/step)))
            average=min(len(grid)//2*2-1,max(1,round((smoothing or span*.01)/step)//2*2+1))
            # Smooth counts before the LLS transform so isolated zero-count noise
            # does not become a zero baseline throughout the spectrum.
            offset=min(0.,float(values.min())); counts=uniform_filter1d(values-offset,average,mode='reflect')
            transformed=np.log1p(np.log1p(np.sqrt(np.maximum(counts,0)+1)))
            clipped=np.pad(transformed,half,mode='reflect')
            for distance in range(half,0,-1):
                clipped[distance:-distance]=np.minimum(clipped[distance:-distance],(clipped[:-2*distance]+clipped[2*distance:])/2)
            baseline=np.maximum(np.expm1(np.expm1(clipped[half:-half]))**2-1,0)+offset
        else:
            block=max(1,len(grid)//1000); starts=np.arange(0,len(grid),block); lengths=np.diff(np.r_[starts,len(grid)])
            centers=np.add.reduceat(grid,starts)/lengths; means=np.add.reduceat(values,starts)/lengths
            window=max(3,round((width or span*.2)/span*len(centers))//2*2+1)
            window=min(window,len(centers)//2*2-1)
            medians=median_filter(means,window,mode='nearest')
            baseline=np.interp(grid,centers,gaussian_filter1d(medians,max(1,window/20),mode='nearest'))
        result=np.interp(x,grid,baseline)
        return (result[::-1] if descending else result).tolist()
    # The legacy method remains explicit; it is no longer the default for counts
    # spanning many orders of magnitude.
    n=len(grid); weights=np.ones(n); difference=diags([np.ones(n-2),-2*np.ones(n-2),np.ones(n-2)],[0,1,2],shape=(n-2,n),format='csc')
    penalty=(1e6*(n/1000)**4)*(difference.T@difference)
    scale=max(float(np.ptp(values)),1); offset=float(np.min(values)); signal=(values-offset)/scale
    for _ in range(30):
        baseline=spsolve(diags(weights,format='csc')+penalty,weights*signal)
        updated=np.where(signal>baseline,.001,.999)
        if np.array_equal(weights,updated): break
        weights=updated
    result=np.interp(x,grid,baseline*scale+offset)
    return (result[::-1] if descending else result).tolist()
