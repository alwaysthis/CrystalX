"""Cache lighting by material only; view-dependent fog is composited by Qt."""
from functools import lru_cache
import math
from PyQt6.QtGui import QImage,QPainter,QColor
from .native_backend import kernels
from .material_math import LIGHT,HALF,surface_shader,to_linear,to_srgb

@lru_cache(maxsize=1)
def _lighting():
    size=128; samples=[]
    light=LIGHT; half=HALF
    for y in range(size):
        for x in range(size):
            nx=(x+.5-size/2)/(size/2); ny=-(y+.5-size/2)/(size/2); rr=nx*nx+ny*ny
            if rr>1: samples.append(None); continue
            nz=math.sqrt(1-rr)
            diffuse=max(0,nx*light[0]+ny*light[1]+nz*light[2])
            spec=max(0,nx*half[0]+ny*half[1]+nz*half[2])
            samples.append((diffuse,nz,spec))
    return samples

@lru_cache(maxsize=128)
def sphere_image(rgb,roughness=.3,ior=1.5,gloss=True):
    if kernels is not None:
        pixels=kernels.sphere_pixels(*rgb,roughness,ior,float(gloss))
        return QImage(pixels,128,128,512,QImage.Format.Format_ARGB32_Premultiplied).copy()
    return python_sphere_image(rgb,roughness,ior,gloss)

def python_sphere_image(rgb,roughness=.3,ior=1.5,gloss=True):
    size=128; pixels=bytearray(size*size*4)
    linear=[to_linear(v) for v in reversed(rgb)]; shader=surface_shader(roughness,ior,gloss)
    # ARGB32 stores bytes in BGRA order on the supported Windows desktops.
    for index,sample in enumerate(_lighting()):
        if sample is None: continue
        nl,nv,nh=sample; offset=index*4
        diffuse,spec=shader(nl,nv,nh)
        for channel,color in enumerate(linear):
            pixels[offset+channel]=round(to_srgb(color*diffuse+spec)*255)
        pixels[offset+3]=255
    return QImage(bytes(pixels),size,size,size*4,QImage.Format.Format_ARGB32_Premultiplied).copy()


@lru_cache(maxsize=256)
def fogged_sphere(rgb,fog_bucket,roughness=.3,ior=1.5,gloss=True):
    """Native compositing keeps fog variants cheap; no pixel loop on cache misses."""
    base=sphere_image(rgb) if (roughness,ior,gloss)==(.3,1.5,True) else sphere_image(rgb,roughness,ior,gloss)
    if fog_bucket==0: return base
    image=base.copy(); painter=QPainter(image)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
    painter.fillRect(image.rect(),QColor(255,255,255,round(fog_bucket*.01*255)))
    painter.end(); return image
