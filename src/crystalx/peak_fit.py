"""Bounded peak-profile fits to raw observations, separate from smoothing."""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares
from scipy.signal import find_peaks

FIT_MODELS={'split_pv':'不对称伪Voigt','pseudo_voigt':'伪Voigt','gaussian':'高斯','lorentzian':'洛伦兹'}

def profile(x,height,center,left,right,eta):
    width=np.where(x<center,left,right); u=(x-center)/width
    return height*((1-eta)*np.exp(-4*np.log(2)*u*u)+eta/(1+4*u*u))

def _solve(x,y,seeds,model,noise,step):
    midpoint=(x[0]+x[-1])/2; span=x[-1]-x[0]; xx=(x-midpoint)/span
    scale=max(float(np.ptp(y)),1.); yy=y/scale; nedge=max(2,len(x)//10)
    edges=np.array([np.median(yy[:nedge]),np.median(yy[-nedge:])])
    floor=0 if np.min(y)>=0 else min(float(yy.min()),-1.)
    initial=list(np.maximum(edges,floor)); lower=[floor,floor]; upper=[max(2,float(yy.max())*2)]*2
    count=3 if model in ('gaussian','lorentzian') else 4 if model=='pseudo_voigt' else 5
    for i,(center,height,width) in enumerate(seeds):
        c=(center-midpoint)/span; w=np.clip(width/span,step/span,1.)
        lo=(seeds[i-1][0]+center)/2 if i else x[0]
        hi=(seeds[i+1][0]+center)/2 if i+1<len(seeds) else x[-1]
        initial.extend([min(9.9,max(height/scale,1e-6)),c,w]); lower.extend([0,(lo-midpoint)/span,step/span*.5]); upper.extend([10,(hi-midpoint)/span,2])
        if model in ('pseudo_voigt','split_pv'): initial.append(.5); lower.append(0); upper.append(1)
        if model=='split_pv': initial.append(w); lower.append(step/span*.5); upper.append(2)
    def parts(parameters,grid):
        base=np.interp(grid,xx[[0,-1]],parameters[:2]); components=[]
        for i in range(len(seeds)):
            p=parameters[2+i*count:2+(i+1)*count]; height,center,left=p[:3]
            eta=0 if model=='gaussian' else 1 if model=='lorentzian' else p[3]
            right=p[4] if model=='split_pv' else left
            components.append(profile(grid,height,center,left,right,eta))
        return base,components
    dynamic=np.ptp(y)/max(float(np.median(np.abs(y))),1.)
    weights=np.sqrt(np.maximum(np.abs(y),max(1,noise**2))) if dynamic>=1000 else np.full_like(y,max(1,noise))
    robust_scale=2. if dynamic>=1000 else max(2.,.02*np.ptp(y)/max(1,noise))
    def residual(parameters):
        base,components=parts(parameters,xx)
        return (base+np.sum(components,axis=0)-yy)*scale/weights
    solution=least_squares(residual,initial,bounds=(lower,upper),loss='soft_l1',f_scale=robust_scale,x_scale='jac',max_nfev=600)
    if not solution.success or not np.isfinite(solution.x).all(): raise ValueError('峰型拟合未收敛，请缩小框选范围或调整寻峰阈值。')
    base,components=parts(solution.x,xx); fitted=(base+np.sum(components,axis=0))*scale
    r2=1-float(np.sum((fitted-y)**2))/max(float(np.sum((y-np.mean(y))**2)),np.finfo(float).eps)
    bic=len(x)*np.log(max(float(np.mean(residual(solution.x)**2)),1e-20))+len(solution.x)*np.log(len(x))
    parameters=[]
    for i in range(len(seeds)):
        p=solution.x[2+i*count:2+(i+1)*count]
        eta=0 if model=='gaussian' else 1 if model=='lorentzian' else p[3]
        right=p[4] if model=='split_pv' else p[2]
        parameters.append((p[0]*scale,p[1]*span+midpoint,p[2]*span,right*span,eta))
    def evaluate(grid):
        base,components=parts(solution.x,(grid-midpoint)/span)
        return base*scale,[component*scale for component in components]
    return parameters,r2,bic,evaluate

def fit_peaks(x,y,settings,region=None):
    """Retry unresolved low-count scans with broad seeds, still fitting raw y."""
    values=np.asarray(y,dtype=float)
    if region is not None:
        grid=np.asarray(x,dtype=float); values=values[(grid>=region[0])&(grid<=region[1])]
    difference=np.diff(values)
    noise=float(np.median(abs(difference-np.median(difference)))/(.67448975*np.sqrt(2))) if len(difference) else 0.
    broad_retry=len(values)>=49 and noise>0 and np.ptp(values)<25*noise
    try: result=_fit_peaks(x,y,settings,region)
    except ValueError:
        if not broad_retry: raise
        result=None
    if broad_retry and (result is None or not result.peaks):
        return _fit_peaks(x,y,settings,region,seed_sigma=max(3.,min(24.,len(values)/100)))
    return result


def _fit_peaks(x,y,settings,region=None,seed_sigma=1.5):
    from .peak_finding import Peak,PeakResult
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float); mapping=np.arange(len(x))
    if settings.fit_model not in FIT_MODELS: raise ValueError('未知的峰型。')
    if region is not None:
        mask=(x>=region[0])&(x<=region[1]); x=x[mask]; y=y[mask]; mapping=mapping[mask]
    if len(x)<9: raise ValueError('峰型拟合至少需要九个采样点，请扩大框选范围。')
    if x[0]>x[-1]: x=x[::-1]; y=y[::-1]; mapping=mapping[::-1]
    step=float(np.median(np.diff(x))); span=x[-1]-x[0]
    difference=np.diff(y); noise=float(np.median(abs(difference-np.median(difference)))/(.67448975*np.sqrt(2)))
    broad_seed=seed_sigma>1.5
    seed_noise=noise/np.sqrt(2*np.sqrt(np.pi)*seed_sigma) if broad_seed else noise
    threshold=settings.prominence or max(5*seed_noise,float(np.ptp(y))*1e-4,np.finfo(float).eps)
    grid=np.linspace(x[0],x[-1],len(x)); seed_signal=np.interp(x,grid,gaussian_filter1d(np.interp(grid,x,y),seed_sigma))
    indices,properties=find_peaks(seed_signal,prominence=threshold,width=(None,None))
    edge=max(2,len(x)//20); floor=np.interp(x,x[[0,-1]],[np.median(y[:edge]),np.median(y[-edge:])])
    seeds=[]; supports=[]
    for row,index in enumerate(indices):
        height=float(seed_signal[index]-floor[index]); prominence=properties['prominences'][row]
        if prominence<max(threshold,.1*height) or height<=0: continue
        width=float(np.interp(properties['right_ips'][row],np.arange(len(x)),x)-np.interp(properties['left_ips'][row],np.arange(len(x)),x))
        if width<max(settings.min_width,4*step,4*seed_sigma*step if broad_seed else 0) or settings.max_width and width>settings.max_width: continue
        center=float(x[index]); radius=max(4*width,span*.005,step*6)
        seeds.append((center,height,width)); supports.append((max(x[0],center-radius),min(x[-1],center+radius)))
    if len(seeds)>40: raise ValueError('拟合候选峰过多，请提高突出度阈值或框选较小范围。')
    groups=[]
    for seed,support in sorted(zip(seeds,supports),key=lambda item:item[1][0]):
        if groups and support[0]<=groups[-1][1]:
            groups[-1][1]=max(groups[-1][1],support[1]); groups[-1][2].append(seed)
        else: groups.append([support[0],support[1],[seed]])
    peaks=[]; contours=[]; fit_x=[]; fit_y=[]; ranges=[]; positions=[]
    for low,high,group in groups:
        group.sort(key=lambda seed:seed[0])
        if len(group)>8: raise ValueError('局部重叠峰过多，请缩小范围或提高突出度阈值。')
        mask=(x>=low)&(x<=high); xx=x[mask]; yy=y[mask]
        if len(xx)<9: continue
        parameters,r2,bic,evaluate=_solve(xx,yy,group,settings.fit_model,noise,step)
        # Only merge close candidate maxima when the simpler model has better BIC.
        while len(group)>1:
            best=None
            for i,p in enumerate(parameters):
                if not any(i!=j and abs(p[1]-other[1])<.6*min((p[2]+p[3])/2,(other[2]+other[3])/2) for j,other in enumerate(parameters)): continue
                reduced=[seed for j,seed in enumerate(group) if j!=i]
                try: trial=_solve(xx,yy,reduced,settings.fit_model,noise,step)
                except ValueError: continue
                if trial[2]<bic and (best is None or trial[2]<best[1][2]): best=(reduced,trial)
            if best is None: break
            group,(parameters,r2,bic,evaluate)=best
        if r2<.65:
            if not broad_seed or r2<=0: continue
            # A low-count peak may have low raw R² even when its trend is clear.
            # Require both resolved shape and improvement over a linear baseline;
            # keep raw R² in the reported results rather than substituting trend R².
            baseline,parts=evaluate(xx); fitted=baseline+np.sum(parts,axis=0)
            trend=np.interp(xx,x,seed_signal)
            trend_r2=1-float(np.sum((fitted-trend)**2))/max(float(np.sum((trend-trend.mean())**2)),np.finfo(float).eps)
            linear=np.polyval(np.polyfit(xx-xx.mean(),yy,1),xx-xx.mean())
            gain=len(xx)*np.log(max(float(np.sum((linear-yy)**2)),1e-20)/max(float(np.sum((fitted-yy)**2)),1e-20))
            count=3 if settings.fit_model in ('gaussian','lorentzian') else 4 if settings.fit_model=='pseudo_voigt' else 5
            if trend_r2<.85 or gain-count*len(group)*np.log(len(xx))<10: continue
        dense=np.linspace(xx[0],xx[-1],min(1600,max(400,len(xx)*3)))
        base,components=evaluate(dense); total=base+np.sum(components,axis=0)
        fit_x.extend(dense.tolist()); fit_y.extend(total.tolist()); ranges.append([float(dense[0]),float(dense[-1])])
        for height,center,left,right,eta in parameters:
            width=(left+right)/2
            if height<max(3*noise,threshold) or width<settings.min_width or settings.max_width and width>settings.max_width: continue
            index=int(np.argmin(abs(x-center)))
            if region is not None and not region[2]<=y[index]<=region[3]: continue
            if any(abs(center-p.x)<settings.min_distance for p in peaks): continue
            fitted_base,fitted_parts=evaluate(np.array([center])); peak_y=float(fitted_base[0]+sum(part[0] for part in fitted_parts))
            peak=Peak(int(mapping[index]),float(center),float(y[index]),float(height),float(width),float(width),float(r2),peak_y)
            peaks.append(peak); positions.append({'index':peak.index,'x':peak.x,'y':peak_y})
            component=base+profile(dense,height,center,left,right,eta)
            contours.append({'x':dense.tolist(),'y':component.tolist(),'baseline':base.tolist()})
    return PeakResult(sorted(peaks,key=lambda peak:peak.x),threshold,noise,
        {'contours':contours,'smooth':{'x':fit_x,'y':fit_y,'ranges':ranges} if fit_x else {},'positions':positions,'model':settings.fit_model,'low_signal':broad_seed,'seed_sigma':seed_sigma})
