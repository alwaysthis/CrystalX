"""Reproducible Python kernel baselines; run without other performance jobs.

Writes raw wall-clock samples and separate cProfile data to ignored output/.
No timing assertions: results depend on machine and background load.
"""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['CRYSTALX_DISABLE_NATIVE']='1'
import cProfile
import json
import platform
import pstats
import statistics
import sys
from copy import deepcopy
from pathlib import Path
from time import perf_counter
from PyQt6.QtCore import QPointF,QT_VERSION_STR,PYQT_VERSION_STR
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication
from crystalx.bonds import automatic_bonds
from crystalx.operations import supercell
from crystalx.structure import read_poscar
from crystalx.sphere_material import sphere_image,fogged_sphere,_lighting
from crystalx.material_math import surface_shader
from crystalx.render_material import material_brush
from crystalx.ui import CrystalViewport

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/kernel-assessment'


def measure(call,repeats=3,before=None):
    samples=[]
    for _ in range(repeats):
        if before: before()
        start=perf_counter(); result=call(); samples.append((perf_counter()-start)*1000)
    return {'median_ms':statistics.median(samples),'samples_ms':samples},result


def profile(name,call):
    profiler=cProfile.Profile(); profiler.runcall(call)
    profiler.dump_stats(str(OUT/(name+'.prof')))
    with (OUT/(name+'.txt')).open('w',encoding='utf-8') as stream:
        pstats.Stats(profiler,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(18)


def clear_materials():
    sphere_image.cache_clear(); fogged_sphere.cache_clear(); _lighting.cache_clear(); surface_shader.cache_clear()


def main():
    app=QApplication([]); OUT.mkdir(parents=True,exist_ok=True)
    report={'environment':{'python':sys.version,'platform':platform.platform(),'processor':platform.processor(),
                           'qt':QT_VERSION_STR,'pyqt':PYQT_VERSION_STR},'bonds':[],'materials':{},'viewport':[]}
    base=read_poscar(ROOT/'examples/Si.vasp'); cases=[]
    for n in (1,2,4,6,8):
        s=deepcopy(base); supercell(s,[n]*3); cases.append((f'Si-{n}x{n}x{n}',s))
    tilted=deepcopy(cases[2][1]); tilted.lattice[1][0]=tilted.lattice[0][0]*.65
    cases.append(('Si-512-oblique',tilted))
    slab=deepcopy(base); supercell(slab,[8,8,1]); cases.append(('Si-512-thin',slab))
    mixed=deepcopy(cases[2][1]); mixed.elements=[('Si','O','C','Fe')[i%4] for i in range(len(mixed.positions))]
    cases.append(('mixed-512-synthetic',mixed))
    for name,s in cases:
        matched=set()
        timing,bonds=measure(lambda:automatic_bonds(s,matched_ranges=matched))
        timing.update(name=name,atoms=len(s.positions),segments=len(bonds),matched_rules=len(matched))
        report['bonds'].append(timing); print('bonds',json.dumps(timing),flush=True)
    profile('bonds-512',lambda:automatic_bonds(cases[2][1],matched_ranges=set()))
    rgb=(.2,.4,.8)
    timing,_=measure(lambda:sphere_image(rgb),before=clear_materials)
    report['materials']['sphere_cold_including_normals']=timing
    _lighting()
    timing,_=measure(lambda:sphere_image(rgb),before=sphere_image.cache_clear)
    report['materials']['sphere_cold_shared_normals']=timing
    timing,_=measure(lambda:[sphere_image(rgb) for _ in range(10000)])
    report['materials']['sphere_hits_10000']=timing
    colors=[(.1+i*.09,.3,.8-i*.06) for i in range(8)]
    timing,_=measure(lambda:[sphere_image(c) for c in colors],before=sphere_image.cache_clear)
    report['materials']['eight_colors_cold']=timing
    timing,_=measure(lambda:[sphere_image(rgb,.1+i*.04,1.5,.75) for i in range(20)],before=sphere_image.cache_clear)
    report['materials']['twenty_parameter_changes']=timing
    sphere_image(rgb)
    timing,_=measure(lambda:[fogged_sphere(rgb,b) for b in range(1,16)],before=fogged_sphere.cache_clear)
    report['materials']['fifteen_fog_misses']=timing
    timing,_=measure(lambda:[material_brush(QPointF(0,0),QPointF(i+1,50),QColor('#637b6b'),3,.3,1.5,1.) for i in range(100)])
    report['materials']['hundred_cylinder_gradients']=timing
    sphere_image.cache_clear(); profile('sphere',lambda:sphere_image(rgb))
    profile('cylinders',lambda:[material_brush(QPointF(),QPointF(i+1,50),QColor('#637b6b'),3,.3,1.5,1.) for i in range(100)])
    for name,s in (cases[0],cases[2],cases[4]):
        view=CrystalViewport(); view.resize(900,700)
        setup,_=measure(lambda:view.set_structure(s),repeats=1)
        # Same key reuses the search; normalization/node rebuilding still runs.
        refresh,_=measure(lambda:view.set_structure(s))
        clear_materials(); cold,_=measure(view.scene_image,repeats=1)
        def rotate(): view.rotate_camera(3,2); return view.scene_image()
        misses=sphere_image.cache_info().misses
        warm,_=measure(rotate,repeats=7)
        row={'name':name,'atoms':len(s.positions),'setup_ms':setup['median_ms'],
             'cached_refresh_ms':refresh['median_ms'],'cold_frame_ms':cold['median_ms'],
             'rotation':warm,'rotation_sphere_misses':sphere_image.cache_info().misses-misses}
        report['viewport'].append(row); print('viewport',json.dumps(row),flush=True)
        if len(s.positions)==512: profile('rotation-512',rotate)
        view.close()
    path=OUT/'python-baseline.json'; path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('materials',json.dumps(report['materials']),flush=True)
    print(path,flush=True)


if __name__=='__main__': main()
