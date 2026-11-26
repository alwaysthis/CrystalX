"""Period-assisted XRR fringe candidates, with raw-maximum validation."""
from dataclasses import dataclass
import numpy as np
from scipy.ndimage import gaussian_filter1d,median_filter
from scipy.signal import find_peaks,periodogram,correlate
from .peak_finding import Peak,PeakResult

@dataclass
class FringeAnalysis:
    result: PeakResult
    period: float|None
    interval: tuple
    notes: list

def analyze_fringes(x,y,minimum=None,maximum=None,prominence=0,min_distance=0,min_width=0,max_width=0):
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float)
    if x.ndim!=1 or y.shape!=x.shape or len(x)<16 or not np.isfinite(x).all() or not np.isfinite(y).all(): raise ValueError('条纹识别需要至少16个有限XY采样点。')
    order=np.argsort(x); xx=x[order]; yy=y[order]
    if np.any(np.diff(xx)<=0): raise ValueError('条纹识别要求横坐标不重复。')
    if minimum is not None and maximum is not None and minimum>=maximum: raise ValueError('搜索范围无效。')
    if any(not np.isfinite(v) or v<0 for v in (prominence,min_distance,min_width,max_width)) or max_width and max_width<min_width: raise ValueError('突出度、间距及宽度参数无效。')
    if any(v is not None and not np.isfinite(v) for v in (minimum,maximum)): raise ValueError('搜索范围必须为有限数值。')
    positive=yy>0
    if positive.sum()<16: raise ValueError('正强度采样点不足，无法识别条纹。')
    grid=np.linspace(xx[0],xx[-1],len(xx)); step=grid[1]-grid[0]; span=grid[-1]-grid[0]
    logy=np.interp(grid,xx[positive],np.log(yy[positive])); initial=gaussian_filter1d(logy,max(1,len(grid)/1500))
    dynamic=float(np.ptp(initial)); notes=[]
    zero_fraction=gaussian_filter1d(np.interp(grid,xx,(yy<=0).astype(float)),max(2,len(grid)/100))
    low=grid[0]; high=grid[-1]
    if dynamic>np.log(100):
        after=np.flatnonzero((np.arange(len(grid))>np.argmax(initial))&(initial<initial.max()-np.log(50)))
        if len(after): low=grid[after[0]]; notes.append('自动避开低角度强衰减区；可手动调整范围。')
        noise=median_filter(abs(logy-initial),size=max(5,len(grid)//80//2*2+1))*1.4826
        noise=gaussian_filter1d(noise,max(2,len(grid)/100))
        bad=np.flatnonzero((grid>low+span*.15)&((noise>.28)|(zero_fraction>.1)))
        if len(bad): high=grid[bad[0]]; notes.append('自动截去高噪声尾部。')
    if high-low<step*32: low,high=grid[0],grid[-1]
    calibration=(grid>=low)&(grid<=high); n=int(calibration.sum()); length=high-low
    trend=gaussian_filter1d(initial,max(2,length/8/step)); residual=initial-trend
    frequency,power=periodogram(residual[calibration],fs=1/step,window='hann',nfft=max(256,n*8))
    valid=(frequency>=2.5/length)&(frequency<=1/(12*step))
    period=None; multiple=False; agreement=False
    if valid.any() and power[valid].max()>0:
        locations=np.flatnonzero(valid); best=locations[np.argmax(power[valid])]; period=float(1/frequency[best])
        spectral,_=find_peaks(power)
        alternatives=[i for i in spectral if valid[i] and power[i]>.55*power[best] and abs(frequency[i]/frequency[best]-1)>.25 and abs(frequency[i]/frequency[best]-2)>.2 and abs(frequency[best]/frequency[i]-2)>.2]
        multiple=bool(alternatives)
        signal=residual[calibration]-np.mean(residual[calibration]); ac=correlate(signal,signal,mode='full',method='fft')[n-1:]
        lags=np.arange(n)*step; region=(lags>=period*.7)&(lags<=period*1.3)
        peaks,_=find_peaks(ac)
        agreement=any(region[i] and ac[i]>0 for i in peaks)
    if period is None:
        return FringeAnalysis(PeakResult([],0,0,{'fringe':True}),None,(low,high),['没有可辨认的条纹周期。'])
    if multiple: notes.append('检测到多个显著周期，候选需人工核对，不能据此唯一确定膜层厚度。')
    if not agreement: notes.append('FFT周期未获自相关确认，候选列为待确认。')
    sigma=max(.7,period/60/step); smooth=gaussian_filter1d(logy,sigma)
    envelope=gaussian_filter1d(smooth,max(2,period*.8/step)); ripple=smooth-envelope
    window=max(5,int(period/step)//2*2+1)
    noise=median_filter(abs(logy-smooth),size=window)*1.4826/np.sqrt(2*np.sqrt(np.pi)*sigma)
    noise=np.maximum(noise,zero_fraction*.5)
    threshold=max(.025,prominence)
    indices,properties=find_peaks(ripple,prominence=threshold,distance=max(1,int(max(period*.55,min_distance)/step)),width=(None,None))
    raw_indices,raw_properties=find_peaks(smooth,prominence=.005,width=(None,None))
    selected=[]; positions=[]
    start=low if minimum is None else minimum; stop=high if maximum is None else maximum
    for row,index in enumerate(indices):
        if not start<=grid[index]<=stop: continue
        width=float(properties['widths'][row]*step); strength=float(properties['prominences'][row])
        if width<max(period*.06,min_width) or max_width and width>max_width or strength<2*max(noise[index],.005): continue
        near=np.flatnonzero(abs(grid[raw_indices]-grid[index])<period*.25)
        near=[j for j in near if raw_properties['widths'][j]*step>=period*.035 and raw_properties['prominences'][j]>=max(.005,2*noise[raw_indices[j]])]
        reason=[]
        if near: index=int(raw_indices[min(near,key=lambda j:abs(raw_indices[j]-index))])
        else: reason.append('原始平滑曲线无明确峰顶，仅为去趋势条纹候选')
        if strength<3.5*max(noise[index],.005): reason.append('局部信噪比较低')
        if multiple: reason.append('存在多个周期')
        if not agreement: reason.append('周期未获自相关确认')
        if not start<=grid[index]<=stop: continue
        source=int(order[np.argmin(abs(xx-grid[index]))]); position=float(x[source])
        if selected and position-selected[-1].x<period*.4: continue
        previous=next((peak for peak in reversed(selected) if peak.status=='可靠'),None)
        if previous is not None:
            cycles=(position-previous.x)/period; nearest=max(1,round(cycles))
            if abs(cycles-nearest)>.30: reason.append('与相邻可靠条纹的周期不一致')
            elif nearest>1: reason.append(f'间隔约{nearest}个周期，可能漏峰，请核对级次')
        status='待确认' if reason else '可靠'
        selected.append(Peak(source,position,float(y[source]),strength,width,status=status,reason='；'.join(reason)))
        positions.append({'index':source,'x':position,'y':float(y[source])})
    # No fabricated FWHM: residual widths describe the detection signal only.
    display=(grid>=start)&(grid<=stop)
    overlays={'fringe':True,'period':period,'interval':[start,stop],'notes':notes,'positions':positions,
              'smooth':{'x':grid[display].tolist(),'y':np.exp(smooth[display]).tolist(),'ranges':[[start,stop]]} if display.sum()>=2 else {},'contours':[]}
    return FringeAnalysis(PeakResult(selected,threshold,float(np.median(noise)),overlays),period,(start,stop),notes)
