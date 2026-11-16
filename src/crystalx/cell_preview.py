"""Real/reciprocal unit cell previews with shaded basis arrows."""
import math
from PyQt6.QtCore import QPointF,Qt
from PyQt6.QtGui import QPainter,QPen,QColor,QPolygonF,QLinearGradient,QRadialGradient
from PyQt6.QtWidgets import QWidget
from .structure import cartesian
from .display_geometry import reciprocal
from .theme import AXIS_COLORS

def arrow(p,origin,end,color,thickness=1.):
    delta=end-origin; length=math.hypot(delta.x(),delta.y())
    if length<2: return
    normal=QPointF(-delta.y()/length,delta.x()/length)*thickness; base=end-delta*(min(10,length*.3)/length)
    gradient=QLinearGradient(origin-normal*2,origin+normal*2)
    gradient.setColorAt(0,color.darker(160)); gradient.setColorAt(.45,color.lighter(160)); gradient.setColorAt(1,color)
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(gradient)
    p.drawPolygon(QPolygonF([origin-normal*2,base-normal*2,base+normal*2,origin+normal*2]))
    # Elliptic cap and smooth cone shading make the shaft cylindrical.
    p.save(); p.translate(base); p.rotate(math.degrees(math.atan2(delta.y(),delta.x())))
    p.setBrush(color.lighter(125)); p.drawEllipse(QPointF(0,0),2.5*thickness,5*thickness); p.restore()
    cone=QLinearGradient(base-normal*5,base+normal*5)
    cone.setColorAt(0,color.darker(160)); cone.setColorAt(.4,color.lighter(170)); cone.setColorAt(1,color.darker(115))
    p.setBrush(cone); p.drawPolygon(QPolygonF([end,base-normal*5,base+normal*5]))

class CellPreview(QWidget):
    def __init__(self):
        super().__init__(); self.lattice=None; self.setMinimumSize(180,180); self.yaw=.6; self.pitch=-.3; self.last=None
        self.setToolTip('实空间 / 倒空间晶胞（倒易基矢不含 2π，分别归一化显示）')
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.lattice: return
        for row,basis in enumerate([self.lattice,reciprocal(self.lattice)]):
            def project(v):
                x,y,z=v
                x,z=x*math.cos(self.yaw)+z*math.sin(self.yaw),-x*math.sin(self.yaw)+z*math.cos(self.yaw)
                return QPointF(x,-y*math.cos(self.pitch)+z*math.sin(self.pitch))
            corners=[project(cartesian((x,y,z),basis)) for x in (0,1) for y in (0,1) for z in (0,1)]
            # A rotation-independent bounding sphere fixes the model scale.
            vectors=[cartesian((x,y,z),basis) for x in (-.5,.5) for y in (-.5,.5) for z in (-.5,.5)]
            radius=max(math.sqrt(sum(v*v for v in point)) for point in vectors)
            scale=min(self.width()-84,self.height()/2-32)/(2*radius)
            center=project(cartesian((.5,.5,.5),basis))
            points=[QPointF((self.width()-70)/2+(v.x()-center.x())*scale,16+row*self.height()/2+(self.height()/2-16)/2+(v.y()-center.y())*scale) for v in corners]
            p.setPen(QColor('#687a71')); p.drawText(8,14+row*self.height()//2,'实空间' if row==0 else '倒空间')
            p.setPen(QPen(QColor('#8faaa0'),1.6))
            for i in range(8):
                for bit in (1,2,4):
                    if i<(i^bit): p.drawLine(points[i],points[i^bit])
            origin=QPointF(self.width()-40,row*self.height()/2+60)
            for i,vector in enumerate(basis):
                length=math.sqrt(sum(v*v for v in vector)); direction=project([v/length for v in vector]); end=origin+direction*18
                color=QColor(AXIS_COLORS[i]); arrow(p,origin,end,color,.65)
                p.setPen(color.darker(130)); p.drawText(end+QPointF(3,-2),'abc'[i]+('*' if row else ''))

    def mousePressEvent(self,event): self.last=event.position()
    def mouseMoveEvent(self,event):
        if self.last is not None:
            delta=event.position()-self.last; self.yaw+=delta.x()*.01; self.pitch+=delta.y()*.01; self.last=event.position(); self.update()
    def mouseReleaseEvent(self,event): self.last=None
