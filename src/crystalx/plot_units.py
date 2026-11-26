"""Non-destructive instrument-unit preparation for plotting and analysis."""
from copy import deepcopy
import math
from .curve_data import XYScan

def prepare_scan(scan):
    metadata=deepcopy(scan.metadata); x=list(scan.x); y=list(scan.intensity)
    kind=scan.template_name
    if kind in ('XRD','Rocking Curve'):
        unit=metadata.get('MEAS_SCAN_UNIT_Y','').lower().replace(' ','')
        if unit in ('cps','counts/s','count/s','counts/sec','counts/second','counts/seconds'):
            metadata['MEAS_SCAN_UNIT_Y']='counts/s'
        elif unit in ('counts','count'):
            try:
                step=abs(float(metadata['MEAS_SCAN_STEP'])); speed=float(metadata['MEAS_SCAN_SPEED'])
                speed_unit=metadata['MEAS_SCAN_SPEED_UNIT'].lower().replace(' ','')
                if speed_unit not in ('deg/min','deg/s','deg/sec') or not math.isfinite(step+speed) or step<=0 or speed<=0: raise ValueError()
                seconds=step/speed*(60 if speed_unit=='deg/min' else 1)
                y=[v/seconds for v in y]
                metadata.update(MEAS_SCAN_UNIT_Y='counts/s',CRYSTALX_COUNTS_TIME_S=str(seconds),CRYSTALX_Y_CONVERSION='scan step / speed')
            except (KeyError,ValueError):
                metadata['CRYSTALX_UNIT_NOTE']='缺少有效步长/速度，保留原强度单位。'
    if kind=='XRR':
        unit=metadata.get('MEAS_SCAN_UNIT_X','').lower()
        axis=metadata.get('MEAS_SCAN_AXIS_X_INTERNAL','').lower().replace('_','')
        try:
            wavelength=float(metadata['HW_XG_WAVE_LENGTH_ALPHA1'])
            wave_unit=metadata.get('HW_XG_WAVE_LENGTH_UNIT','').lower()
            if wave_unit=='nm': wavelength*=10
            elif wave_unit not in ('angstrom','angstroms','a','å'): raise ValueError()
            if not math.isfinite(wavelength) or wavelength<=0: raise ValueError()
            if unit=='deg' and axis in ('theta','2theta','twotheta','twothetaomega','twothetatheta','omegatwotheta'):
                divisor=1 if axis=='theta' else 2
                x=[4*math.pi*math.sin(math.radians(v/divisor))/wavelength for v in x]
                metadata.update(MEAS_SCAN_AXIS_X_INTERNAL='qz',MEAS_SCAN_AXIS_X='qz',MEAS_SCAN_UNIT_X='1/angstrom',PLOT_X_LABEL=r'$q_z$ (Å$^{-1}$)',EXPERIMENT_TYPE='XRR')
        except (KeyError,ValueError):
            if unit=='deg': metadata['CRYSTALX_UNIT_NOTE']='缺少有效波长，保留角度横坐标。'
    return XYScan(x,y,metadata,list(scan.attenuation))

def prepare_curve(scan,style,label,visible=True,legend_visible=True):
    from .plot_curves import PlotCurve
    prepared=prepare_scan(scan)
    return PlotCurve(prepared.x,prepared.intensity,deepcopy(style),label,visible,legend_visible=legend_visible,metadata=prepared.metadata)

def prepare_state(scan,state):
    """Migrate legacy saved curves and their annotations into the plotted units."""
    first=True
    for curve in state['curves']:
        if curve.role=='expression': continue
        metadata=curve.metadata or scan.metadata
        original=XYScan(curve.x,curve.y,metadata)
        prepared=prepare_scan(original)
        changed=prepared.x!=curve.x or prepared.intensity!=curve.y
        if changed:
            def tx(values): return prepare_scan(XYScan(list(values),[],metadata)).x
            def ty(values): return prepare_scan(XYScan(original.x,list(values),metadata)).intensity
            curve.x=prepared.x; curve.y=prepared.intensity
            curve.background=ty(curve.background); curve.fill_baseline=ty(curve.fill_baseline)
            for mark in curve.thickness_marks: mark['x']=tx([mark['x']])[0]
            for segment in curve.peak_analysis.get('contours',[])+([curve.peak_analysis['smooth']] if curve.peak_analysis.get('smooth') else []):
                segment['x']=tx(segment['x']); segment['y']=ty(segment['y'])
                if 'baseline' in segment: segment['baseline']=ty(segment['baseline'])
                if 'ranges' in segment: segment['ranges']=[tx(pair) for pair in segment['ranges']]
            for position in curve.peak_analysis.get('positions',[])+curve.peak_analysis.get('fringe_candidates',[]):
                position['x']=tx([position['x']])[0]; position['y']=ty([position['y']])[0]
            if first:
                b=state['bounds']; state['bounds']=tuple(tx(b[:2])+ty(b[2:]))
                for side in ('left','right','bottom','top'):
                    axis=state['style']['axes'][side]; transform=tx if side in ('bottom','top') else ty
                    for limit in ('minimum','maximum'):
                        if axis[limit]: axis[limit]=str(transform([float(axis[limit])])[0])
                for side in ('left','right'):
                    if state['style']['axes'][side]['label']=='Intensity (counts)' and prepared.metadata.get('MEAS_SCAN_UNIT_Y')=='counts/s': state['style']['axes'][side]['label']='Intensity (counts/s)'
                for side in ('bottom','top'):
                    if prepared.x!=original.x and state['style']['axes'][side]['label'] in ('2θ (°)','2theta (deg)','2θ (deg)'):
                        state['style']['axes'][side]['label']=prepared.axis_label
        curve.metadata=prepared.metadata; first=False
    return state
