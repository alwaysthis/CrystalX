"""Real/reciprocal unit cell previews with shaded basis arrows."""
import math
from PyQt6.QtCore import QPointF,Qt
from PyQt6.QtGui import QPainter,QPen,QColor,QPolygonF,QLinearGradient
from PyQt6.QtWidgets import QWidget
from .structure import cartesian
from .display_geometry import reciprocal

def arrow(p,origin,end,color):
    delta=end-origin; length=math.hypot(delta.x(),delta.y())
    if length<2: return
    normal=QPointF(-delta.y()/length,delta.x()/length); base=end-delta*(min(10,length*.3)/length)
    gradient=QLinearGradient(origin-normal*2,origin+normal*2)
    gradient.setColorAt(0,color.darker(160)); gradient.setColorAt(.45,color.lighter(160)); gradient.setColorAt(1,color)
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(gradient)
    p.drawPolygon(QPolygonF([origin-normal*2,base-normal*2,base+normal*2,origin+normal*2]))
    p.setBrush(color); p.drawPolygon(QPolygonF([end,base-normal*5,base+normal*5]))
    p.setBrush(color.lighter(150)); p.drawPolygon(QPolygonF([end,base,base+normal*5]))

class CellPreview(QWidget):
    def __init__(self):
        super().__init__(); self.lattice=None; self.setMinimumSize(145,180)
        self.setToolTip('实空间 / 倒空间晶胞（倒易基矢不含 2π，分别归一化显示）')
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.lattice: return
        for row,basis in enumerate([self.lattice,reciprocal(self.lattice)]):
            def project(v):
                x,y,z=v; return QPointF(.82*x+.57*z,-.24*x-.88*y+.34*z)
            corners=[project(cartesian((x,y,z),basis)) for x in (0,1) for y in (0,1) for z in (0,1)]
            lowx=min(v.x() for v in corners); lowy=min(v.y() for v in corners)
            spanx=max(v.x() for v in corners)-lowx; spany=max(v.y() for v in corners)-lowy
            scale=min((self.width()-34)/max(spanx,1e-8),(self.height()/2-30)/max(spany,1e-8))
            points=[QPointF(14+(v.x()-lowx)*scale,22+row*self.height()/2+(v.y()-lowy)*scale) for v in corners]
            p.setPen(QColor('#687a71')); p.drawText(8,14+row*self.height()//2,'实空间' if row==0 else '倒空间')
            p.setPen(QPen(QColor('#b8c5bd'),1))
            for i in range(8):
                for bit in (1,2,4):
                    if i<(i^bit): p.drawLine(points[i],points[i^bit])
            for i,index in enumerate([4,2,1]):
                color=QColor(['#d84942','#48a866','#498de0'][i]); arrow(p,points[0],points[index],color)
                p.setPen(color.darker(130)); p.drawText(points[index]+QPointF(3,-2),'abc'[i]+('*' if row else ''))
