"""Validated plot configuration files and user-owned defaults, without data."""
from copy import deepcopy
from pathlib import Path
import json
import logging
from .plot_style import DEFAULT,validate_style
from .plot_curves import validate_curve_settings

def read_plot_config(path):
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict) or data.get('format')!='CrystalX.PlotStyle' or data.get('version')!=1: raise ValueError('不是支持的图片样式配置。')
    style=validate_style(data.get('style'))
    curves=data.get('curves',[])
    if not isinstance(curves,list): raise ValueError('曲线配置必须为列表。')
    return style,[validate_curve_settings(item) for item in curves]

def write_plot_config(path,style,curves=()):
    path=Path(path); style=validate_style(style); curves=[validate_curve_settings(item) for item in curves]
    for axis in style['axes'].values(): axis.update(minimum='',maximum='')
    path.parent.mkdir(parents=True,exist_ok=True)
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,suffix='.tmp',delete=False) as stream:
        json.dump({'format':'CrystalX.PlotStyle','version':1,'style':style,'curves':curves},stream,ensure_ascii=False,indent=2)
        temporary=Path(stream.name)
    try: temporary.replace(path)
    finally: temporary.unlink(missing_ok=True)

class PlotDefaults:
    def __init__(self,path=None):
        self.path=Path(path) if path else Path(__file__).resolve().parents[2]/'config/custom/plot.json'
    def read(self):
        if self.path.exists():
            try: return read_plot_config(self.path)
            except (OSError,ValueError) as error: logging.getLogger(__name__).warning('Invalid plot defaults: %s',error)
        return deepcopy(DEFAULT),[]
    def save(self,style,curves): write_plot_config(self.path,style,curves)

class PlotTemplates:
    def __init__(self,root=None):
        self.root=Path(root) if root else Path(__file__).resolve().parents[2]/'config'

    def writable_path(self,name,path):
        if path is None or Path(path).resolve().is_relative_to((self.root/'default').resolve()):
            return self.root/'custom/plot-templates'/f'{name}.json'
        return Path(path)

    def resolve(self,scan):
        name=scan.template_name
        for candidate in dict.fromkeys((name,'global')):
            for folder in ('custom','default'):
                path=self.root/folder/'plot-templates'/f'{candidate}.json'
                if path.exists():
                    try: style,curves=read_plot_config(path)
                    except (OSError,ValueError) as error:
                        logging.getLogger(__name__).warning('Invalid plot template %s: %s',path,error); continue
                    return style,curves,candidate,path
        return deepcopy(DEFAULT),[],'global',None
