"""Cold and warm rotated frame timings (offscreen; excludes editor panels)."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from time import perf_counter
from statistics import median
from PyQt6.QtWidgets import QApplication
from crystalx.ui import CrystalViewport
from crystalx.structure import Structure
from crystalx.sphere_material import sphere_image,fogged_sphere

app=QApplication([])
for count,colors in [(8,['Si']),(512,['Si','O','C','N','Fe','Al','Cu','Ti'])]:
    positions=[[(i*.6180339887)%1,(i*.4142135623)%1,(i*.7320508075)%1] for i in range(count)]
    structure=Structure('benchmark',[[12,0,0],[0,12,0],[0,0,12]],[colors[i%len(colors)] for i in range(count)],positions,[['T']*3 for _ in range(count)],['']*count)
    view=CrystalViewport(); view.resize(900,700); view.set_structure(structure)
    sphere_image.cache_clear(); fogged_sphere.cache_clear(); times=[]
    for frame in range(8):
        start=perf_counter(); view.rotate_camera(3,2); view.scene_image(); times.append((perf_counter()-start)*1000)
    print({'atoms':count,'cold_ms':round(times[0],2),'median_ms':round(median(times[1:]),2),'max_ms':round(max(times),2),'cache':str(sphere_image.cache_info())},flush=True)
