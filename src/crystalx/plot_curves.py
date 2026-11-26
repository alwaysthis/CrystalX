"""Independent curve data, appearance and portable clipboard payloads."""
from copy import deepcopy
from dataclasses import dataclass,field
import json
import math
from uuid import uuid4
from .plot_style import DEFAULT,validate_style,inherited,math_label
from matplotlib.mathtext import MathTextParser

CURVE_MIME='application/x-crystalx-curve+json'

@dataclass
class PlotCurve:
    x: list
    y: list
    style: dict
    label: str
    visible: bool=True
    points: list=field(default_factory=list)
    peaks: list=field(default_factory=list)
    point_labels: dict=field(default_factory=dict)
    background: list=field(default_factory=list)
    show_background: bool=False
    subtract_background: bool=False
    peak_analysis: dict=field(default_factory=dict)
    background_settings: dict=field(default_factory=dict)
    thickness_marks: list=field(default_factory=list)
    legend_visible: bool=True
    expression: str=''
    role: str='data'
    uid: str=field(default_factory=lambda:uuid4().hex)
    source_id: str=''
    metadata: dict=field(default_factory=dict)
    fill_baseline: list=field(default_factory=list)

    @property
    def display_y(self):
        return [y-b for y,b in zip(self.y,self.background)] if self.subtract_background and self.background else self.y

    def settings(self): return dict(style=deepcopy(self.style),label=self.label,visible=self.visible,legend_visible=self.legend_visible)

    def peak_position(self,index):
        for position in self.peak_analysis.get('positions',[]):
            if position['index']==index: return position['x'],position['y']
        return self.x[index],self.display_y[index]

    def clipboard(self,general):
        style=deepcopy(self.style)
        return json.dumps({'format':'CrystalX.Curve','version':1,'x':self.x,'y':self.y,
            **self.settings(),'style':style,'points':self.points,'peaks':self.peaks,'point_labels':self.point_labels,
            'background':self.background,'show_background':self.show_background,'subtract_background':self.subtract_background,
            'peak_analysis':self.peak_analysis,'background_settings':self.background_settings,'thickness_marks':self.thickness_marks,
            'expression':self.expression,'role':self.role,'uid':self.uid,'source_id':self.source_id,'metadata':self.metadata,'fill_baseline':self.fill_baseline},ensure_ascii=False).encode('utf-8')

    def inherit_plot_appearance(self):
        self.style.update(color='',width=0)
        for key in ('face','edge'):
            if self.style[key]!='none': self.style[key]='auto'

    @classmethod
    def from_clipboard(cls,payload):
        try: data=json.loads(bytes(payload))
        except (ValueError,UnicodeError) as error: raise ValueError('曲线剪贴板格式无效。') from error
        if not isinstance(data,dict) or data.get('format')!='CrystalX.Curve' or data.get('version')!=1: raise ValueError('不是支持的曲线剪贴板数据。')
        x,y=data.get('x'),data.get('y')
        if not isinstance(x,list) or not isinstance(y,list) or len(x)!=len(y) or not 2<=len(x)<=1000000: raise ValueError('曲线数据长度无效。')
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in x+y): raise ValueError('曲线坐标必须为有限数值。')
        settings=validate_curve_settings(data)
        metadata=data.get('metadata',{})
        if not isinstance(metadata,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in metadata.items()): raise ValueError('曲线文件信息无效。')
        fill=data.get('fill_baseline',[])
        if not isinstance(fill,list) or fill and (len(fill)!=len(x) or any(type(v) not in (int,float) or not math.isfinite(v) for v in fill)): raise ValueError('曲线轮廓基底无效。')
        points=data.get('points',[])
        if not isinstance(points,list) or any(type(i) is not int or not 0<=i<len(x) for i in points): raise ValueError('曲线标点索引无效。')
        peaks=data.get('peaks',[])
        if not isinstance(peaks,list) or any(type(i) is not int or not 0<=i<len(x) for i in peaks): raise ValueError('曲线峰位索引无效。')
        labels=data.get('point_labels',{})
        if not isinstance(labels,dict): raise ValueError('图注格式无效。')
        parsed={}; parser=MathTextParser('path')
        for key,value in labels.items():
            if not key.isdecimal() or not 0<=int(key)<len(x) or not isinstance(value,str): raise ValueError('图注索引或内容无效。')
            parser.parse(math_label(value),dpi=96); parsed[int(key)]=value
        background=data.get('background',[]); show=data.get('show_background',False); subtract=data.get('subtract_background',False)
        if not isinstance(background,list) or background and (len(background)!=len(y) or any(type(v) not in (int,float) or not math.isfinite(v) for v in background)):
            raise ValueError('曲线背景数据无效。')
        if type(show) is not bool or type(subtract) is not bool or (show or subtract) and not background: raise ValueError('曲线背景状态无效。')
        analysis=validate_peak_analysis(data.get('peak_analysis',{}),len(x))
        from .background import validate_background_settings
        baseline_settings=data.get('background_settings',{})
        if not isinstance(baseline_settings,dict): raise ValueError('背景设置格式无效。')
        if baseline_settings: baseline_settings=validate_background_settings(baseline_settings)
        marks=data.get('thickness_marks',[])
        if not isinstance(marks,list) or len(marks)>10000: raise ValueError('膜厚峰位标记格式无效。')
        for mark in marks:
            if not isinstance(mark,dict) or type(mark.get('x')) not in (int,float) or not math.isfinite(mark['x']) or type(mark.get('order')) is not int:
                raise ValueError('膜厚峰位标记无效。')
        return cls(x,y,settings['style'],settings['label'],settings['visible'],list(dict.fromkeys(points)),list(dict.fromkeys(peaks)),parsed,
            background,show,subtract,analysis,baseline_settings,marks,settings['legend_visible'],str(data.get('expression','')),str(data.get('role','data')),str(data.get('uid') or uuid4().hex),str(data.get('source_id','')),metadata,fill)

def validate_peak_analysis(analysis,length):
    if not isinstance(analysis,dict): raise ValueError('峰轮廓格式无效。')
    contours=analysis.get('contours',[]); smooth=analysis.get('smooth',{})
    positions=analysis.get('positions',[])
    candidates=analysis.get('fringe_candidates',[])
    if not isinstance(candidates,list) or len(candidates)>length: raise ValueError('条纹候选格式无效。')
    if not isinstance(positions,list) or len(positions)>length: raise ValueError('拟合峰位格式无效。')
    for position in positions+candidates:
        if not isinstance(position,dict) or type(position.get('index')) is not int or not 0<=position['index']<length or any(type(position.get(key)) not in (int,float) or not math.isfinite(position[key]) for key in ('x','y')):
            raise ValueError('拟合峰位无效。')
    if not isinstance(contours,list) or len(contours)>length or not isinstance(smooth,dict): raise ValueError('峰轮廓格式无效。')
    ranges=smooth.get('ranges',[])
    if not isinstance(ranges,list) or len(ranges)>length or any(not isinstance(r,list) or len(r)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in r) or r[0]>r[1] for r in ranges):
        raise ValueError('平滑峰范围无效。')
    for segment in contours+([smooth] if smooth else []):
        if not isinstance(segment,dict): raise ValueError('峰轮廓格式无效。')
        xx=segment.get('x'); yy=segment.get('y')
        if not isinstance(xx,list) or not isinstance(yy,list) or not 2<=len(xx)<=max(length,64000) or len(xx)!=len(yy): raise ValueError('峰轮廓长度无效。')
        arrays=[xx,yy]
        if 'baseline' in segment:
            if not isinstance(segment['baseline'],list) or len(segment['baseline'])!=len(xx): raise ValueError('峰轮廓基底无效。')
            arrays.append(segment['baseline'])
        if any(type(v) not in (int,float) or not math.isfinite(v) for array in arrays for v in array): raise ValueError('峰轮廓必须为有限数值。')
    return deepcopy(analysis)

def validate_curve_settings(settings):
    if not isinstance(settings,dict) or not isinstance(settings.get('label'),str) or type(settings.get('visible')) is not bool: raise ValueError('曲线样式或图例名称无效。')
    base=deepcopy(DEFAULT); base['curve']=settings.get('style')
    style=validate_style(base)['curve']
    MathTextParser('path').parse(math_label(settings['label']),dpi=96)
    legend=settings.get('legend_visible',True)
    if type(legend) is not bool: raise ValueError('图例显示状态无效。')
    return dict(style=style,label=settings['label'],visible=settings['visible'],legend_visible=legend)
