"""CIF import with symmetry expansion through Gemmi."""
from pathlib import Path
import math
from .structure import Structure

def read_cif(path):
    import gemmi
    try:
        doc=gemmi.cif.read_file(str(path))
        if len(doc)!=1: raise ValueError('请选择只包含一个结构数据块的 CIF')
        small=gemmi.make_small_structure_from_block(doc[0])
        if not small.sites or small.cell.volume<=0: raise ValueError('CIF 缺少有效晶格或原子坐标')
        sites=small.get_all_unit_cell_sites()
        lattice=[]
        for axis in [(1,0,0),(0,1,0),(0,0,1)]:
            p=small.cell.orthogonalize(gemmi.Fractional(*axis)); lattice.append([p.x,p.y,p.z])
        elements=[]; positions=[]; tags=[]
        for site in sites:
            if abs(site.occ-1)>1e-6: raise ValueError('暂不支持部分占位或无序结构，避免导出错误的 POSCAR')
            if site.element.atomic_number==0: raise ValueError('无法识别 CIF 元素')
            point=[v%1 for v in [site.fract.x,site.fract.y,site.fract.z]]
            if not all(math.isfinite(v) for v in point): raise ValueError('CIF 坐标无效')
            if any(sum(min(abs(a-b),1-abs(a-b))**2 for a,b in zip(point,q))<1e-12 for q in positions):
                raise ValueError('CIF 含重合或混合占位原子')
            elements.append(site.element.name); positions.append(point); tags.append(site.label)
        return Structure(small.name or Path(path).stem,lattice,elements,positions,[['T']*3 for _ in sites],tags)
    except (RuntimeError,ValueError) as error: raise ValueError(f'CIF 读取失败：{error}') from error
