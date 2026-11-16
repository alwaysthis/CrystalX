"""Time the isolated compiled probe including ctypes, buffer and QImage copy.

Build the DLL as documented in native_material_probe.cpp before running.
The application never imports this probe. Full sprite parity is checked first.
"""
import ctypes
import json
from pathlib import Path
from statistics import median
from time import perf_counter
from PyQt6.QtGui import QImage
from crystalx.sphere_material import python_sphere_image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/kernel-assessment'


def main():
    dll=ctypes.CDLL(str(OUT/'material_probe.dll'))
    kernel=dll.sphere_pixels
    kernel.argtypes=[ctypes.c_double]*6+[ctypes.POINTER(ctypes.c_uint8)]
    kernel.restype=None
    def native(rgb,roughness,ior,gloss):
        pixels=(ctypes.c_uint8*(128*128*4))()
        kernel(*rgb,roughness,ior,gloss,pixels)
        return QImage(bytes(pixels),128,128,512,QImage.Format.Format_ARGB32_Premultiplied).copy()
    def raw(image): return image.constBits().asstring(image.sizeInBytes())
    cases=[((.2,.4,.8),r,i,g) for r in (0.,.1,.35,.8,1.) for i in (1.,1.5,3.) for g in (0.,.35,1.)]
    maximum=0
    for case in cases:
        a=raw(python_sphere_image(*case)); b=raw(native(*case))
        maximum=max(maximum,max(abs(x-y) for x,y in zip(a,b)))
    assert maximum<=1,maximum
    case=((.2,.4,.8),.3,1.5,1.)
    python_times=[]; native_times=[]
    for index in range(15):
        calls=[(python_sphere_image,python_times),(native,native_times)]
        for call,values in calls if index%2 else reversed(calls):
            start=perf_counter(); call(*case); values.append((perf_counter()-start)*1000)
    result={'cases':len(cases),'max_channel_error':maximum,
            'python':{'median_ms':median(python_times),'samples_ms':python_times},
            'native_including_boundary_and_image':{'median_ms':median(native_times),'samples_ms':native_times},
            'compiler_flags':'g++ -std=c++17 -O3 -shared -static-libgcc -static-libstdc++'}
    result['speedup']=result['python']['median_ms']/result['native_including_boundary_and_image']['median_ms']
    (OUT/'native-material.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
