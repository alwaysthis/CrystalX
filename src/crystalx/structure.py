"""Qt-independent structure model and explicit VASP 5 POSCAR subset."""
from dataclasses import dataclass
from pathlib import Path
import math
import os
import tempfile


def dot(a, b):
    return sum(x*y for x,y in zip(a,b))


def cross(a,b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def cartesian(vector, lattice):
    return [sum(vector[i]*lattice[i][j] for i in range(3)) for j in range(3)]


def fractional(vector, lattice):
    volume=dot(lattice[0],cross(lattice[1],lattice[2]))
    if abs(volume)<1e-12:
        raise ValueError("晶格矩阵不可逆")
    return [dot(vector,cross(lattice[(i+1)%3],lattice[(i+2)%3]))/volume for i in range(3)]


@dataclass
class Structure:
    name: str
    lattice: list
    elements: list
    positions: list
    flags: list
    tags: list
    selective: bool = False

    @property
    def cartesian_positions(self):
        return [cartesian(p,self.lattice) for p in self.positions]


def read_poscar(path):
    lines=Path(path).read_text(encoding="utf-8-sig").splitlines()
    try:
        scale_values=lines[1].split()
        if len(scale_values)!=1:
            raise ValueError("首版仅支持单一缩放因子")
        scale=float(scale_values[0])
        lattice=[list(map(float,line.split())) for line in lines[2:5]]
        if any(len(row)!=3 for row in lattice): raise ValueError("晶格必须为 3×3")
        volume=abs(dot(lattice[0],cross(lattice[1],lattice[2])))
        if volume<1e-12 or scale==0: raise ValueError("晶格或缩放因子无效")
        if scale<0: scale=(abs(scale)/volume)**(1/3)
        lattice=[[v*scale for v in row] for row in lattice]
        species=lines[5].split()
        if not species or any(s.isdigit() for s in species): raise ValueError("需要 VASP 5 元素名称行")
        counts=list(map(int,lines[6].split()))
        if len(species)!=len(counts) or any(n<0 for n in counts) or sum(counts)==0:
            raise ValueError("元素数量无效")
        index=7; selective=lines[index].strip().lower().startswith('s')
        if selective: index+=1
        mode=lines[index].strip().lower()
        if not mode.startswith(('d','c','k')): raise ValueError("坐标模式必须为 Direct 或 Cartesian")
        index+=1; positions=[]; flags=[]; tags=[]
        for line in lines[index:index+sum(counts)]:
            values=line.split(); point=list(map(float,values[:3]))
            if len(point)!=3: raise ValueError("原子坐标不完整")
            positions.append(point if mode.startswith('d') else fractional([v*scale for v in point],lattice))
            flag=[v.upper() for v in values[3:6]] if selective else ['T']*3
            if len(flag)!=3 or any(v not in ('T','F') for v in flag): raise ValueError("选择性弛豫标志必须为 T/F")
            flags.append(flag); tags.append(' '.join(values[6 if selective else 3:]))
        if len(positions)!=sum(counts): raise ValueError("原子行数不足")
        if any(line.strip() for line in lines[index+sum(counts):]):
            raise ValueError("首版不读取速度等附加区段，请先移除后再打开")
        if not all(math.isfinite(v) for row in lattice+positions for v in row): raise ValueError("坐标和晶格必须为有限数值")
        return Structure(lines[0],lattice,[s for s,n in zip(species,counts) for _ in range(n)],positions,flags,tags,selective)
    except (IndexError,ValueError) as error:
        raise ValueError(f"POSCAR 格式错误：{error}") from error


def write_poscar(structure,path,direct=True):
    species=list(dict.fromkeys(structure.elements))
    order=[i for s in species for i,e in enumerate(structure.elements) if e==s]
    lines=[structure.name,'1.0']+[' '.join(f'{v:.16g}' for v in row) for row in structure.lattice]
    lines+=[' '.join(species),' '.join(str(structure.elements.count(s)) for s in species)]
    if structure.selective: lines.append('Selective dynamics')
    lines.append('Direct' if direct else 'Cartesian')
    positions=structure.positions if direct else structure.cartesian_positions
    for i in order:
        line=' '.join(f'{v:.16g}' for v in positions[i])
        if structure.selective: line+='  '+' '.join(structure.flags[i])
        if structure.tags[i]: line+='  '+structure.tags[i]
        lines.append(line)
    destination=Path(path)
    handle,temp=tempfile.mkstemp(dir=destination.parent,prefix='.crystalx-',suffix='.tmp')
    try:
        with os.fdopen(handle,'w',encoding='utf-8',newline='\n') as stream: stream.write('\n'.join(lines)+'\n')
        os.replace(temp,destination)
    finally:
        if os.path.exists(temp): os.unlink(temp)
