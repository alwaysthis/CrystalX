"""Portable JSON plot documents containing raw scans, curves and appearance."""
import json,math
from copy import deepcopy
from pathlib import Path
from .curve_data import XYScan
from .plot_curves import PlotCurve
from .plot_style import validate_style,DEFAULT

def state_to_json(state):
    return dict(style=state['style'],curves=[json.loads(curve.clipboard(state['style']['general'])) for curve in state['curves']],
        bounds=state['bounds'],legend_anchor=state['legend_anchor'],selected_curve=state['selected_curve'],curve_visible=state['curve_visible'],template_name=state['template_name'])

def state_from_json(data):
    style=validate_style(data['style']); curves=[PlotCurve.from_clipboard(json.dumps(value).encode('utf-8')) for value in data['curves']]
    if len({curve.uid for curve in curves})!=len(curves): raise ValueError('图文件曲线编号重复。')
    bounds=data['bounds']
    if len(bounds)!=4 or not all(type(v) in (float,int) and math.isfinite(v) for v in bounds) or bounds[0]>=bounds[1] or bounds[2]>=bounds[3]: raise ValueError('图文件坐标范围无效。')
    anchor=data.get('legend_anchor')
    if anchor is not None and (len(anchor)!=2 or not all(type(v) in (int,float) and math.isfinite(v) for v in anchor)): raise ValueError('图例位置无效。')
    selected=data.get('selected_curve'); selected=selected if type(selected) is int and 0<=selected<len(curves) else None
    visible=data.get('curve_visible',True); template=data.get('template_name','global')
    if type(visible) is not bool or not isinstance(template,str): raise ValueError('图文件显示状态无效。')
    return dict(style=style,curves=curves,bounds=tuple(bounds),legend_anchor=anchor,selected_curve=selected,curve_visible=visible,template_name=template,template_path=None)


def initial_state(scan,plot):
    if plot.templates: style,drafts,template,_=plot.templates.resolve(scan)
    else: style,drafts,template=deepcopy(plot.style),plot.default_curves,plot.template_name
    settings=drafts[0] if drafts else dict(style=deepcopy(style['curve']),label='plot 1',visible=True)
    from .plot_units import prepare_curve
    curve=prepare_curve(scan,settings['style'],settings['label'],settings['visible'],settings.get('legend_visible',True))
    return dict(style=style,curves=[curve],bounds=plot.reset_bounds(style,[curve]),legend_anchor=None,selected_curve=None,curve_visible=True,template_name=template)

def write_document(path,page):
    from dataclasses import asdict
    states=[]
    for scan in page.scans:
        if scan is page.plot.scan: state=page.plot.snapshot()
        elif id(scan) in page.plot.committed: state=page.plot.committed[id(scan)]
        else: state=initial_state(scan,page.plot)
        states.append({'scan':asdict(scan),'plot':state_to_json(state)})
    active=next(index for index,scan in enumerate(page.scans) if scan is page.plot.scan)
    data={'format':'CrystalX.PlotDocument','version':1,'name':page.plot.name,'scans':states,'active':active}
    path=Path(path)
    from tempfile import NamedTemporaryFile
    temporary=None
    try:
        with NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name); json.dump(data,stream,ensure_ascii=False,allow_nan=False)
        temporary.replace(path)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)

def read_document(path):
    try:
        data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
        if data.get('format')!='CrystalX.PlotDocument' or data.get('version')!=1 or not isinstance(data.get('scans'),list) or not data['scans']: raise ValueError('不是支持的CrystalX图文件。')
        scans=[]; states=[]
        for item in data['scans']:
            scan=XYScan(**item['scan']); sample=PlotCurve(scan.x,scan.intensity,DEFAULT['curve'],'source')
            PlotCurve.from_clipboard(sample.clipboard({}))
            if not isinstance(scan.metadata,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in scan.metadata.items()): raise ValueError('原始数据文件信息无效。')
            if not isinstance(scan.attenuation,list) or scan.attenuation and (len(scan.attenuation)!=len(scan.x) or any(type(v) not in (int,float) or not math.isfinite(v) for v in scan.attenuation)): raise ValueError('衰减数据无效。')
            from .plot_units import prepare_state
            scans.append(scan); states.append(prepare_state(scan,state_from_json(item['plot'])) if item.get('plot') is not None else None)
        active=data.get('active',0)
        if type(active) is not int or not 0<=active<len(scans): raise ValueError('图文件活动扫描无效。')
        return scans,states,active,str(data.get('name',Path(path).stem))
    except (KeyError,TypeError,AttributeError) as error: raise ValueError('图文件内容不完整或格式无效。') from error
