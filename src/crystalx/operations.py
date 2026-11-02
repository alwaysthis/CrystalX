"""Structure transformations. Rotation uses a Cartesian axis through an explicit center."""
from copy import deepcopy
from itertools import product
import math
from .structure import cartesian, fractional, dot, cross


def rotate(structure, indices, axis, angle, center):
    length=math.sqrt(dot(axis,axis))
    if length<1e-12: raise ValueError("旋转轴不能为零向量")
    axis=[v/length for v in axis]; radians=math.radians(angle)
    cosine,sine=math.cos(radians),math.sin(radians)
    for i in indices:
        point=[v-c for v,c in zip(cartesian(structure.positions[i],structure.lattice),center)]
        perpendicular=cross(axis,point)
        result=[point[j]*cosine+perpendicular[j]*sine+axis[j]*dot(axis,point)*(1-cosine)+center[j] for j in range(3)]
        structure.positions[i]=fractional(result,structure.lattice)


def wrap(structure,indices):
    for i in indices: structure.positions[i]=[v%1 for v in structure.positions[i]]


def duplicate(structure,indices,shift):
    for i in sorted(indices):
        structure.elements.append(structure.elements[i])
        structure.positions.append([v+s for v,s in zip(structure.positions[i],shift)])
        structure.flags.append(structure.flags[i][:]); structure.tags.append(structure.tags[i])


def delete(structure,indices):
    if len(indices)==len(structure.elements): raise ValueError("不能删除全部原子；请至少保留一个原子")
    for attribute in ['elements','positions','flags','tags']:
        values=getattr(structure,attribute)
        setattr(structure,attribute,[v for i,v in enumerate(values) if i not in indices])


def supercell(structure,repeats):
    if len(repeats)!=3 or any(type(v) is not int or v<1 for v in repeats):
        raise ValueError("超胞倍数必须为三个正整数")
    source=deepcopy(structure)
    structure.lattice=[[v*repeats[i] for v in row] for i,row in enumerate(source.lattice)]
    structure.elements=[]; structure.positions=[]; structure.flags=[]; structure.tags=[]
    for offset in product(*(range(n) for n in repeats)):
        for i,point in enumerate(source.positions):
            structure.elements.append(source.elements[i])
            structure.positions.append([(v+o)/n for v,o,n in zip(point,offset,repeats)])
            structure.flags.append(source.flags[i][:]); structure.tags.append(source.tags[i])


def set_flags(structure,indices,flags):
    structure.selective=True
    for i in indices: structure.flags[i]=flags[:]
