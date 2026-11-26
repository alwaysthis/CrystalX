"""Read unit-labelled XY text, including AFM height-frequency exports."""
import math
import re
from .curve_data import XYScan

UNIT_HEADER=re.compile(r'^([XY])\s+Unit\s*:\s*(.*?)\s*$',re.I)
UNITS={'nanometer':'nm','nanometre':'nm','nm':'nm','micrometer':'µm','micrometre':'µm','um':'µm','µm':'µm',
       'millimeter':'mm','millimetre':'mm','mm':'mm','meter':'m','metre':'m','m':'m','angstrom':'Å','pixel':'pixels','pixels':'pixels',
       'picometer':'pm','picometre':'pm','pm':'pm'}

def has_unit_header(text):
    return any(UNIT_HEADER.match(line.strip().lstrip('\ufeff')) for line in text.splitlines()[:12])

def read_unit_xy(text):
    units={}; x=[]; y=[]
    for number,line in enumerate(text.splitlines(),1):
        line=line.strip().lstrip('\ufeff')
        if not line or line.startswith(('#','!',';')): continue
        header=UNIT_HEADER.match(line)
        if header:
            key,unit=header.group(1).upper(),header.group(2).strip()
            if x or not unit or key in units: raise ValueError(f'第 {number} 行的单位头重复、缺失或位于数据之后。')
            units[key]=unit; continue
        if not x and re.fullmatch(r'X[\s,;]+Y',line,re.I): continue
        try: values=[float(value) for value in re.split(r'[\s,;]+',line)]
        except ValueError as error: raise ValueError(f'第 {number} 行不是有效的XY数值。') from error
        if len(values)!=2 or not all(math.isfinite(value) for value in values): raise ValueError(f'第 {number} 行需要两列有限数值。')
        x.append(values[0]); y.append(values[1])
    if set(units)!={'X','Y'}: raise ValueError('XY文本需要完整的 X Unit 和 Y Unit 单位头。')
    if len(x)<2: raise ValueError('XY数据至少需要两个点。')
    ux,uy=(UNITS.get(units[key].casefold(),units[key]) for key in ('X','Y'))
    lengths=('pm','nm','µm','mm','m','Å')
    histogram=ux in lengths and uy=='pixels'
    profile=ux in lengths and uy in lengths
    if histogram and any(value<0 for value in y): raise ValueError('高度分布的像素数不能为负。')
    metadata={'DATA_KIND':'AFM' if histogram or profile else 'XY','X_UNIT':units['X'],'Y_UNIT':units['Y'],
              'PLOT_X_LABEL':f'Height ({ux})' if histogram else f'Distance ({ux})' if profile else f'X ({ux})',
              'PLOT_Y_LABEL':'Pixel count' if histogram else f'Height ({uy})' if profile else f'Y ({uy})'}
    if histogram or profile: metadata['AFM_TYPE']='profile' if profile else 'distribution'
    return XYScan(x,y,metadata)
