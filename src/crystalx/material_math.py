"""Dielectric Fresnel and isotropic GGX/Smith shading for projected solids.

Uses Principled-style perceptual roughness (GGX alpha = roughness squared).
This is a single-light surface BRDF, not Blender's full path tracer.
"""
import math
from functools import lru_cache
LIGHT_RAW=(-.36,.44,.82)
_length=math.sqrt(sum(v*v for v in LIGHT_RAW)); LIGHT=tuple(v/_length for v in LIGHT_RAW)
_half=(LIGHT[0],LIGHT[1],LIGHT[2]+1); _length=math.sqrt(sum(v*v for v in _half)); HALF=tuple(v/_length for v in _half)

def fresnel(ior,cosine):
    if abs(ior-1)<1e-12: return 0.
    f0=((ior-1)/(ior+1))**2
    return f0+(1-f0)*(1-max(0.,min(1.,cosine)))**5

def ggx_distribution(nh,roughness):
    alpha=max(.002,roughness*roughness); a2=alpha*alpha
    return a2/(math.pi*max(1e-14,(nh*nh*(a2-1)+1)**2))

def smith_g1(n,roughness):
    n=max(0.,n); alpha=max(.002,roughness*roughness)
    return 2*n/max(1e-12,n+math.sqrt(alpha*alpha+(1-alpha*alpha)*n*n))

@lru_cache(maxsize=128)
def surface_shader(roughness,ior,gloss):
    alpha=max(.002,roughness*roughness); a2=alpha*alpha
    f=fresnel(ior,HALF[2])*gloss
    def terms(nl,nv,nh):
        nl=max(0.,nl); nv=max(.0001,nv); nh=max(0.,nh)
        diffuse=.20+.80*nl*(1-f)
        if not gloss or nl<=0: return diffuse,0.
        d=a2/(math.pi*max(1e-14,(nh*nh*(a2-1)+1)**2))
        gv=2*nv/(nv+math.sqrt(a2+(1-a2)*nv*nv))
        gl=2*nl/max(1e-12,nl+math.sqrt(a2+(1-a2)*nl*nl))
        return diffuse,d*gv*gl*f/(4*nv)
    return terms

def shade_terms(nl,nv,nh,roughness,ior,gloss):
    return surface_shader(roughness,ior,gloss)(nl,nv,nh)

def to_linear(v): return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4

def to_srgb(v):
    v=max(0.,min(1.,v))
    return v*12.92 if v<=.0031308 else 1.055*v**(1/2.4)-.055
