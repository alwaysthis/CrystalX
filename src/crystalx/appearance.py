"""Validated appearance presets and user-owned global defaults; no Qt dependency."""
from copy import deepcopy
from pathlib import Path
import json,math
ROOT=Path(__file__).resolve().parents[2]
FACTORY_STYLE=json.loads((ROOT/'config/default/display.json').read_text(encoding='utf-8'))['settings']
DEFAULT_STYLE=FACTORY_STYLE
ATOM_KEYS={k for k in FACTORY_STYLE if k.startswith('atom') or k in ('radius_scale','gloss','depth_fade')}
BOND_KEYS={k for k in FACTORY_STYLE if k.startswith('bond')}
CELL_KEYS={k for k in FACTORY_STYLE if k.startswith('cell')}
AXES_KEYS={k for k in FACTORY_STYLE if k.startswith('axes')}
RANGES={'cell_width':(.1,40),'cell_line':(0,5),'axes_mode':(0,1),'axes_width':(.2,20),'axes_head_width':(1,40),'axes_head_length':(1,50),'radius_scale':(.1,3),'atom_radius_type':(0,3),'atom_radius_source':(0,2),'atom_radius':(.01,10),'atom_mode':(0,2),'atom_color_mode':(0,1),'atom_border_width':(0,10),'bond_line':(0,5),'bond_width':(.01,2),'bond_color_mode':(0,1)}

def is_color(value):
    return isinstance(value,str) and len(value)==7 and value[0]=='#' and all(c in '0123456789abcdefABCDEF' for c in value[1:])

def validate_settings(settings):
    if not isinstance(settings,dict) or set(settings)-set(FACTORY_STYLE): raise ValueError('显示设置包含未知字段或格式不正确')
    result=deepcopy(FACTORY_STYLE)
    for key,value in settings.items():
        default=FACTORY_STYLE[key]
        # Version 1 presets used boolean highlight switches.
        if key in ('gloss','cell_gloss','axes_gloss') and type(value) is bool: value=float(value)
        if isinstance(default,bool):
            valid=type(value) is bool
        elif isinstance(default,list): valid=isinstance(value,list) and len(value)==3 and all(is_color(c) for c in value)
        elif isinstance(default,str): valid=is_color(value)
        else:
            low,high=RANGES.get(key,(0.,1.) if 'roughness' in key or 'gloss' in key else (1.,3.))
            valid=isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and low<=value<=high
            if isinstance(default,int): valid=valid and int(value)==value
        if not valid: raise ValueError('显示设置的数值或颜色无效：'+key)
        result[key]=value
    return result

def read_preset(path):
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict) or data.get('format')!='CrystalX.Appearance' or data.get('version')!=1: raise ValueError('不是支持的 CrystalX 显示设置文件')
    return validate_settings(data.get('settings'))

def write_preset(path,settings):
    path=Path(path); data={'format':'CrystalX.Appearance','version':1,'settings':validate_settings(settings)}
    path.parent.mkdir(parents=True,exist_ok=True); temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); temporary.replace(path)

class AppearanceStore:
    def __init__(self,path=None):
        self.path=Path(path) if path is not None else ROOT/'config/custom/display.json'
        self.defaults=read_preset(self.path) if self.path.exists() else deepcopy(FACTORY_STYLE)
        self.current=deepcopy(self.defaults)
    def set_default(self,settings):
        settings=validate_settings(settings); write_preset(self.path,settings); self.defaults=deepcopy(settings)
