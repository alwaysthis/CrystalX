"""Cell edits: metric changes keep fractions; VESTA-style basis changes keep Cartesian positions."""
import math
from .structure import dot,cross,cartesian,fractional

def parameters(lattice):
    lengths=[math.sqrt(dot(v,v)) for v in lattice]
    angles=[math.degrees(math.acos(max(-1,min(1,dot(lattice[i],lattice[j])/(lengths[i]*lengths[j]))))) for i,j in [(1,2),(0,2),(0,1)]]
    return lengths+angles

def set_parameters(structure,values):
    a,b,c,alpha,beta,gamma=values
    if not all(math.isfinite(v) for v in values) or min(a,b,c)<=0 or not all(0<v<180 for v in [alpha,beta,gamma]): raise ValueError('晶格长度必须为正，角度必须在 0–180° 之间')
    ca,cb,cg=[math.cos(math.radians(v)) for v in [alpha,beta,gamma]]; sg=math.sin(math.radians(gamma))
    y=(ca-cb*cg)/sg; z2=1-cb*cb-y*y
    if z2<=1e-12: raise ValueError('这些晶格常数不能构成有效晶胞')
    local=[[a,0,0],[b*cg,b*sg,0],[c*cb,c*y,c*math.sqrt(z2)]]
    # Retain the original a direction, ab plane and handedness.
    old=structure.lattice; e1=[v/math.sqrt(dot(old[0],old[0])) for v in old[0]]
    temp=[v-dot(old[1],e1)*u for v,u in zip(old[1],e1)]; e2=[v/math.sqrt(dot(temp,temp)) for v in temp]; e3=cross(e1,e2)
    if dot(old[2],e3)<0: e3=[-v for v in e3]
    structure.lattice=[cartesian(row,[e1,e2,e3]) for row in local]

def transform_basis(structure,matrix):
    if not all(math.isfinite(v) for row in matrix for v in row): raise ValueError('矩阵必须为有限数值')
    if any(abs(v-round(v))>1e-8 for row in matrix for v in row): raise ValueError('变换矩阵必须为整数矩阵，使新基矢端点位于原基矢的整数格点上')
    new=[[sum(matrix[j][i]*structure.lattice[j][k] for j in range(3)) for k in range(3)] for i in range(3)]
    if abs(dot(new[0],cross(new[1],new[2])))<1e-10: raise ValueError('变换矩阵不可逆或晶胞退化')
    points=structure.cartesian_positions
    structure.lattice=new; structure.positions=[fractional(point,new) for point in points]

def set_atom_rows(structure,elements,points,tags,direct):
    import gemmi
    if any(gemmi.Element(e).atomic_number==0 for e in elements): raise ValueError('存在无法识别的元素')
    if not all(math.isfinite(v) for row in points for v in row): raise ValueError('坐标必须为有限数值')
    if not elements: raise ValueError('请至少保留一个原子')
    structure.elements=elements; structure.tags=tags
    structure.flags=[structure.flags[i][:] if i<len(structure.flags) else ['T']*3 for i in range(len(elements))]
    structure.positions=points if direct else [fractional(p,structure.lattice) for p in points]
