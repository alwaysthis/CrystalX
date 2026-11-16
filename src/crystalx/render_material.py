"""Shared projected cylinders, arrowheads and radius tables for viewport/previews."""
import json,math
from pathlib import Path
from PyQt6.QtCore import Qt,QPointF
from PyQt6.QtGui import QColor,QPen,QLinearGradient,QPolygonF
from .appearance import ROOT
from .material_math import LIGHT,HALF,surface_shader,to_linear,to_srgb
RADII=json.loads((ROOT/'config/default/atomic-radii.json').read_text(encoding='utf-8'))['radii']
LINE_STYLES=[Qt.PenStyle.SolidLine,Qt.PenStyle.DashLine,Qt.PenStyle.DotLine,Qt.PenStyle.DashDotLine,Qt.PenStyle.DashDotDotLine]

def radius(element,settings):
    kind=settings['atom_radius_type']
    if kind==3: return settings['atom_radius']*settings['radius_scale']
    values=RADII.get(element,{'atomic':1.,'ionic':1.,'vdw':1.5})
    return values[['atomic','ionic','vdw'][kind]]*.42*settings['radius_scale']

def material_brush(start,end,color,width,roughness,ior,gloss):
    delta=end-start; length=math.hypot(delta.x(),delta.y())
    normal=QPointF(-delta.y(),delta.x())/max(length,1e-9)*width/2
    gradient=QLinearGradient(start-normal,start+normal)
    shader=surface_shader(roughness,ior,gloss); screen_normal=normal/max(width/2,1e-9); linear=[to_linear(v) for v in color.getRgbF()[:3]]
    for i in range(33):
        t=-1+2*i/32; nz=math.sqrt(max(0,1-t*t)); nx,ny=screen_normal.x()*t,-screen_normal.y()*t
        nl=nx*LIGHT[0]+ny*LIGHT[1]+nz*LIGHT[2]; nh=nx*HALF[0]+ny*HALF[1]+nz*HALF[2]
        diffuse,spec=shader(nl,nz,nh)
        gradient.setColorAt(i/32,QColor.fromRgbF(*(to_srgb(v*diffuse+spec) for v in linear)))
    return gradient

def segment(p,start,end,color,width,line=0,roughness=.3,ior=1.5,gloss=True):
    if line==5:
        brush=material_brush(start,end,color,width,roughness,ior,gloss)
        p.setPen(QPen(brush,width,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
    else: p.setPen(QPen(color,width,LINE_STYLES[line],Qt.PenCapStyle.RoundCap))
    p.drawLine(start,end)

def axis_arrow(p,start,end,color,settings):
    delta=end-start; length=math.hypot(delta.x(),delta.y())
    if length<2: return
    unit=delta/length; normal=QPointF(-unit.y(),unit.x()); head=min(settings['axes_head_length'],length*.7); base=end-unit*head
    solid=settings['axes_mode']==1
    segment(p,start,base,color,settings['axes_width'],5 if solid else 0,settings['axes_roughness'],settings['axes_ior'],settings['axes_gloss'])
    left,right=base+normal*settings['axes_head_width']/2,base-normal*settings['axes_head_width']/2
    if solid:
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(material_brush(base,end,color,settings['axes_head_width'],settings['axes_roughness'],settings['axes_ior'],settings['axes_gloss'])); p.drawPolygon(QPolygonF([end,left,right]))
    else:
        p.setPen(QPen(color,settings['axes_width'])); p.drawLine(left,end); p.drawLine(end,right)
