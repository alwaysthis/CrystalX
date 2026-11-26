"""Scientific figure settings, inheritance and safe tick/label validation."""
from copy import deepcopy
from pathlib import Path
import json
import math
import re
from matplotlib.colors import is_color_like
from matplotlib.mathtext import MathTextParser
from .matlab_literals import parse_literal
from .plot_scales import axis_scale
from .math_syntax import figure_text

DEFAULT=json.loads((Path(__file__).resolve().parents[2]/'config/default/plot.json').read_text(encoding='utf-8'))
LINE_STYLES={'solid':'-','dotted':':','dashed':'--','dashdot':'-.','dashdotdot':(0,(3,1,1,1,1,1)),'none':'None'}
MARKERS={'none':'','circle':'o','square':'s','diamond':'D','star':'*','triangle':'^','cross':'+','x':'x','point':'.'}

def default_style(): return deepcopy(DEFAULT)

def aspect_ratio(value):
    if value=='auto': return None
    try:
        parts=value.split(':')
        if len(parts)>2: raise ValueError
        numbers=[float(v) for v in parts]
        if not all(math.isfinite(v) and v>0 for v in numbers): raise ValueError
        ratio=numbers[0]/numbers[1] if len(numbers)==2 else numbers[0]
        if not .1<=ratio<=10: raise ValueError
        return ratio
    except (ValueError,ZeroDivisionError): raise ValueError('图片比例请输入正数或宽:高，宽高比须在0.1至10之间。') from None

def inherited(style,section,key): return section[key] or style['general'][key]

def tick_mode(axis):
    return 'array' if axis['ticks'].strip() else 'spacing' if axis['interval']>0 else 'auto'

def axis_label(scan,side):
    if side=='bottom': return scan.axis_label
    if side=='left': return scan.y_label
    return ''

def math_label(text):
    return figure_text(text)

def validate_style(style):
    def checked(value,template):
        if isinstance(template,dict):
            if not isinstance(value,dict) or set(value)-set(template): raise ValueError('图片样式结构或字段无效。')
            return {key:checked(value.get(key,deepcopy(default)),default) for key,default in template.items()}
        if template is None:
            if value is not None and not isinstance(value,str): raise ValueError('坐标轴标签必须为文本。')
        elif isinstance(template,bool):
            if type(value) is not bool: raise ValueError('显示开关必须为布尔值。')
        elif isinstance(template,(float,int)):
            if type(value) not in (int,float) or not math.isfinite(value): raise ValueError('样式数值必须有限。')
        elif not isinstance(value,str): raise ValueError('样式文本格式无效。')
        return value
    result=checked(style,DEFAULT); parser=MathTextParser('path')
    aspect_ratio(result['general']['aspect'])
    for section in [result['general'],result['legend'],result['curve'],*result['axes'].values()]:
        for key,value in section.items():
            if key in ('color','background','label_color','face','edge') and value and not (key in ('face','edge') and value=='auto') and not is_color_like(value):
                raise ValueError('颜色无效：'+str(value))
            if key in ('size','width','label_size','marker_size','tick_length','interval') and (not math.isfinite(value) or value<0):
                raise ValueError('字号、线宽、间距等必须为有限的非负数值。')
            upper={'size':96,'width':20,'label_size':96,'marker_size':40,'tick_length':30,'interval':1e9}.get(key)
            if upper is not None and value>upper: raise ValueError('样式数值超出可设置范围：'+key)
    for side,axis in result['axes'].items():
        scale=axis_scale(axis)
        if axis['log'] and axis['sqrt']: raise ValueError('坐标轴不能同时使用根号和对数刻度。')
        ticks=parse_literal(axis['ticks']) if tick_mode(axis)=='array' else []
        labels=parse_literal(axis['labels'],strings=True)
        if ticks and any(b<a for a,b in zip(ticks,ticks[1:])): raise ValueError('刻度位置必须按递增顺序排列。')
        if axis['log'] and any(v<=0 for v in ticks): raise ValueError('对数坐标轴刻度必须为正数。')
        if scale=='sqrt' and any(v<0 for v in ticks): raise ValueError('根号坐标轴刻度不能为负数。')
        if axis['direction'] not in ('in','out','inout') or axis['number_format'] not in ('auto','fixed','E','e','scientific'): raise ValueError('坐标轴方向或数值格式无效。')
        if type(axis['precision']) is not int or not 0<=axis['precision']<=12: raise ValueError('小数位数须为0至12的整数。')
        values=[]
        for key in ('minimum','maximum'):
            value=float(axis[key]) if axis[key].strip() else None; values.append(value)
            if value is not None and (not math.isfinite(value) or axis['log'] and value<=0): raise ValueError('范围须为有限数值，对数坐标范围必须为正。')
            if value is not None and scale=='sqrt' and value<0: raise ValueError('根号坐标范围不能为负数。')
        if None not in values and values[0]>=values[1]: raise ValueError('坐标轴最大值必须大于最小值。')
        texts=[axis['label'],*labels]
        for text in texts:
            if text: parser.parse(math_label(text),dpi=96)
    if result['legend']['text']: parser.parse(math_label(result['legend']['text']),dpi=96)
    if result['curve']['style'] not in LINE_STYLES or result['curve']['marker'] not in MARKERS: raise ValueError('曲线线型或标记无效。')
    if result['legend']['location'] not in ('best','upper right','upper left','lower right','lower left','center'): raise ValueError('图例位置无效。')
    if result['general']['size']<=0 or result['general']['width']<=0: raise ValueError('通用字号和线宽必须大于0。')
    return result

def tick_text(value,axis):
    precision=axis['precision']; kind=axis['number_format']
    if kind=='fixed': return f'{value:.{precision}f}'
    if kind=='scientific':
        if value==0: return '0'
        mantissa,exponent=format(value,f'.{precision}e').split('e')
        return rf'${mantissa}\times10^{{{int(exponent)}}}$'
    if kind in ('E','e'):
        mantissa,exponent=format(value,f'.{precision}{kind}').split(kind)
        return mantissa+kind+str(int(exponent))
    return f'{value:g}'
