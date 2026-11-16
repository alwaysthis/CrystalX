"""Compare deployed optional C++ dispatch against the retained Python reference."""
import json
import platform
from copy import deepcopy
from pathlib import Path
from statistics import median
from time import perf_counter
from unittest.mock import patch
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor
from crystalx import render_material
from crystalx.native_backend import kernels
from crystalx.bonds import automatic_bonds,python_automatic_bonds
from crystalx.operations import supercell
from crystalx.structure import read_poscar
from crystalx.sphere_material import sphere_image,python_sphere_image

ROOT=Path(__file__).resolve().parents[1]


def compare(python,native,repeats=5):
    samples={'python':[],'native':[]}
    for i in range(repeats):
        calls=[('python',python),('native',native)]
        for name,call in calls if i%2 else reversed(calls):
            start=perf_counter(); call(); samples[name].append((perf_counter()-start)*1000)
    result={name:{'median_ms':median(values),'samples_ms':values} for name,values in samples.items()}
    result['speedup']=result['python']['median_ms']/result['native']['median_ms']
    return result


def main():
    if kernels is None: raise RuntimeError('Build the C++ module before running this comparison')
    report={'python_version':platform.python_version(),'platform':platform.platform(),'bonds':[]}
    rgb=(.2,.4,.8)
    python_sphere_image(rgb)  # Initialize shared normals, exclude first-use setup.
    report['sphere']=compare(lambda:python_sphere_image(rgb),lambda:sphere_image.__wrapped__(rgb),15)
    def cylinders():
        return [render_material.material_brush(QPointF(),QPointF(i+1,50),QColor('#637b6b'),3,.3,1.5,1.) for i in range(100)]
    def python_cylinders():
        with patch.object(render_material,'kernels',None): return cylinders()
    report['hundred_cylinders']=compare(python_cylinders,cylinders,15)
    base=read_poscar(ROOT/'examples/Si.vasp')
    for n in (1,4,8):
        s=deepcopy(base); supercell(s,[n]*3)
        row=compare(lambda:python_automatic_bonds(s,matched_ranges=set()),
                    lambda:automatic_bonds(s,matched_ranges=set()))
        row['atoms']=len(s.positions); report['bonds'].append(row)
        print(json.dumps(row),flush=True)
    out=ROOT/'output/native-benchmark.json'; out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['sphere']),flush=True)


if __name__=='__main__': main()
