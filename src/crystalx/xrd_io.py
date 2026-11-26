"""Qt-independent RAS, plain XY and unit-labelled experimental text readers."""
from pathlib import Path
import math
import re
from .curve_data import XYScan as XrdScan
from .afm_io import has_unit_header,read_unit_xy

def _text(path):
    data=Path(path).read_bytes()
    for encoding in ('utf-8-sig','cp932','gb18030'):
        try: return data.decode(encoding)
        except UnicodeDecodeError: pass
    raise ValueError('无法识别文本编码；当前仅支持文本曲线数据。')

def _values(line,line_number):
    try: values=[float(v) for v in re.split(r'[\s,;]+',line.strip())]
    except ValueError as error: raise ValueError(f'第 {line_number} 行不是有效数值。') from error
    if len(values)<2 or not all(math.isfinite(v) for v in values):
        raise ValueError(f'第 {line_number} 行需要至少两列有限数值。')
    return values

def read_ras(text):
    scans=[]; metadata={}; scan=None
    for number,line in enumerate(text.splitlines(),1):
        line=line.strip()
        if not line: continue
        if line=='*RAS_HEADER_START':
            if scan is not None: raise ValueError('RAS 数据段未结束。')
            metadata={}
        elif line=='*RAS_INT_START':
            if scan is not None: raise ValueError('RAS 数据段重复开始。')
            scan=XrdScan([],[],dict(metadata))
        elif line=='*RAS_INT_END':
            if scan is None or len(scan.x)<2: raise ValueError('RAS 数据段缺失或少于两个点。')
            expected=scan.metadata.get('MEAS_DATA_COUNT')
            if expected is not None and int(expected)!=len(scan.x): raise ValueError('RAS 数据点数与头部声明不一致。')
            scans.append(scan); scan=None
        elif scan is not None:
            values=_values(line,number)
            if len(values) not in (2,3): raise ValueError(f'第 {number} 行需要角度、强度及可选的衰减系数。')
            scan.x.append(values[0]); scan.intensity.append(values[1]); scan.attenuation.append(values[2] if len(values)==3 else 1.)
        elif line.startswith('*'):
            parts=line[1:].split(maxsplit=1)
            if len(parts)==2: metadata[parts[0]]=parts[1].strip().strip('"')
    if scan is not None: raise ValueError('RAS 数据不完整，缺少 RAS_INT_END。')
    if not scans: raise ValueError('未找到 RAS_INT_START 数据段。')
    return scans

def read_xrd(path):
    if Path(path).suffix.lower()=='.rasx': return read_rasx(path)
    text=_text(path)
    if Path(path).suffix.lower()=='.ras': return read_ras(text)
    if has_unit_header(text): return [read_unit_xy(text)]
    x=[]; intensity=[]
    for number,line in enumerate(text.splitlines(),1):
        line=line.strip()
        if not line or line.startswith(('#','!',';')): continue
        # A single initial column-heading line is allowed for exported text.
        if not x and re.match(r'^(2theta|2θ|angle|角度|x)[,;\s]',line,re.I): continue
        values=_values(line,number)
        if len(values)!=2: raise ValueError(f'第 {number} 行应为角度和强度两列。')
        x.append(values[0]); intensity.append(values[1])
    if len(x)<2: raise ValueError('衍射数据至少需要两个点。')
    return [XrdScan(x,intensity)]

# Existing callers keep read_xrd; new callers can use the format-neutral name.
read_plot_data=read_xrd

def read_rasx(path):
    import zipfile
    import xml.etree.ElementTree as ET
    scans=[]
    try:
        with zipfile.ZipFile(path) as archive:
            for name in sorted(archive.namelist()):
                if not name.endswith('.xml') or 'MesurementConditions' not in name: continue
                root=ET.fromstring(archive.read(name)); metadata={}
                for pair in root.findall('RASHeader/Pair'):
                    strings=pair.findall('string')
                    if len(strings)==2: metadata[(strings[0].text or '').lstrip('*')]=strings[1].text or ''
                fields={'AxisName':'AXIS_X_INTERNAL','Mode':'MODE','Start':'START','Stop':'STOP','Step':'STEP','Speed':'SPEED','SpeedUnit':'SPEED_UNIT','PositionUnit':'UNIT_X','IntensityUnit':'UNIT_Y','StartTime':'START_TIME','EndTime':'END_TIME'}
                for field,key in fields.items():
                    value=root.findtext('ScanInformation/'+field)
                    if value is not None: metadata['MEAS_SCAN_'+key]=value
                count=root.findtext('ScanInformation/DataCount')
                if count: metadata['MEAS_DATA_COUNT']=count
                wave=root.findtext('HWConfigurations/XrayGenerator/WavelengthKalpha1')
                if wave:
                    metadata['HW_XG_WAVE_LENGTH_ALPHA1']=wave
                    metadata.setdefault('HW_XG_WAVE_LENGTH_UNIT','angstrom')
                for element in root.iter():
                    if len(element)==0 and element.text and element.text.strip(): metadata.setdefault('RASX_'+element.tag,element.text.strip())
                profile=name.replace('MesurementConditions','Profile').replace('.xml','.txt')
                x=[]; y=[]; attenuation=[]
                for number,line in enumerate(archive.read(profile).decode('utf-8-sig').splitlines(),1):
                    if not line.strip(): continue
                    values=_values(line,number)
                    if len(values)!=3: raise ValueError('RASX数据应有三列。')
                    x.append(values[0]); y.append(values[1]); attenuation.append(values[2])
                if len(x)<2 or int(metadata.get('MEAS_DATA_COUNT',len(x)))!=len(x): raise ValueError('RASX数据点数不一致。')
                scans.append(XrdScan(x,y,metadata,attenuation))
    except (zipfile.BadZipFile,ET.ParseError,KeyError,UnicodeError) as error: raise ValueError('RASX文件缺失数据或格式无效。') from error
    if not scans: raise ValueError('RASX文件没有找到扫描数据。')
    return scans
