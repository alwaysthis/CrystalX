"""Interactive before/after cell diagrams, including intermediate metric and lattice points."""
import math
from itertools import product
from PyQt6.QtCore import Qt,QPointF,QRectF
from PyQt6.QtGui import QPainter,QPen,QColor,QPolygonF
from PyQt6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QToolButton,QToolTip
from .icons import icon
from .structure import cartesian,fractional,dot
from .view_orientation import standard_orientation


from .math_ui import MathLabel as QLabel, MathToolButton as QToolButton

def corners(basis): return [cartesian(p,basis) for p in product((0,1),repeat=3)]

class HelpButton(QToolButton):
    text='<b>先改晶格参数，再应用矩阵。</b><br>参数改变时保留分数坐标；矩阵改变时保留笛卡尔位置。<br>L′ = Pᵀ L，P 必须为可逆整数矩阵，列表示新基矢系数。<br>灰虚线：原晶格；蓝线：参数变化；黄线：矩阵变化；黑点：参数变化后的点阵。'
    def __init__(self):
        super().__init__(); self.setIcon(icon('help')); self.setFixedSize(25,25); self.setStyleSheet('QToolButton {background:transparent;border:0;padding:2px;} QToolButton:hover {background:#e4ece7;}'); self.clicked.connect(self.toggle)
    def show_help(self): QToolTip.showText(self.mapToGlobal(self.rect().bottomLeft()),self.text,self)
    def enterEvent(self,event): self.show_help(); super().enterEvent(event)
    def leaveEvent(self,event): QToolTip.hideText(); super().leaveEvent(event)
    def toggle(self):
        if QToolTip.isVisible(): QToolTip.hideText()
        else: self.show_help()

class LatticeScene(QWidget):
    def __init__(self):
        super().__init__(); self.setMinimumSize(200,180); self.layers=[]; self.points=[]; self.zoom=1.; self.yaw=0.; self.pitch=0.; self.last=None
        self.setToolTip('拖动旋转 · 滚轮缩放')
    def set_scene(self,layers,all_bases,point_basis=None):
        self.layers=layers; self.camera=standard_orientation(all_bases[0])
        vertices=[p for basis in all_bases for p in corners(basis)]
        low=[min(p[i] for p in vertices) for i in range(3)]; high=[max(p[i] for p in vertices) for i in range(3)]
        self.center=[(a+b)/2 for a,b in zip(low,high)]; self.span=max(math.dist(p,self.center) for p in vertices) or 1
        self.points=[]
        if point_basis:
            fractions=[fractional(p,point_basis) for p in vertices]
            bounds=[(math.floor(min(p[i] for p in fractions)),math.ceil(max(p[i] for p in fractions))) for i in range(3)]
            count=math.prod(b-a+1 for a,b in bounds); step=max(1,math.ceil((count/2200)**(1/3)))
            self.points=[cartesian(p,point_basis) for p in product(*(range(a,b+1,step) for a,b in bounds))]
        self.update()
    def camera_point(self,point):
        x,y,z=[dot(row,[v-c for v,c in zip(point,self.center)]) for row in self.camera]
        x,z=x*math.cos(self.yaw)+z*math.sin(self.yaw),-x*math.sin(self.yaw)+z*math.cos(self.yaw)
        return x,y*math.cos(self.pitch)-z*math.sin(self.pitch),y*math.sin(self.pitch)+z*math.cos(self.pitch)
    def project(self,point):
        x,y,z=self.camera_point(point); scale=min(self.width()-30,self.height()-30)/self.span*.43*self.zoom
        return QPointF(self.width()/2+x*scale,self.height()/2-y*scale),z
    def paintEvent(self,event):
        if not self.layers: return
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.points:
            depths=[self.camera_point(point)[2] for point in self.points]; low=min(depths); high=max(depths)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#000000'))
            for index in sorted(range(len(depths)),key=depths.__getitem__):
                p.setOpacity(.2+.8*(depths[index]-low)/max(1e-9,high-low)); p.drawEllipse(self.project(self.points[index])[0],2.,2.)
        p.setOpacity(1)
        for basis,color,dashed in self.layers:
            vertices=[self.project(v)[0] for v in corners(basis)]
            p.setPen(QPen(QColor(color),1.6,Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine))
            for i in range(8):
                for bit in (1,2,4):
                    if i<(i^bit): p.drawLine(vertices[i],vertices[i^bit])
        basis=self.layers[-1][0]; origin=self.project([0,0,0])[0]
        for i,vector in enumerate(basis):
            end=self.project(vector)[0]; delta=end-origin; length=math.hypot(delta.x(),delta.y())
            if length<2: continue
            unit=delta/length; normal=QPointF(-unit.y(),unit.x()); base=end-unit*7
            p.setPen(QPen(QColor('#111111'),1.2)); p.drawLine(origin,end); p.setBrush(QColor('#111111')); p.drawPolygon(QPolygonF([end,base+normal*3,base-normal*3])); p.drawText(end+QPointF(3,-3),'abc'[i])
    def mousePressEvent(self,event): self.last=event.position()
    def mouseMoveEvent(self,event):
        if self.last is not None:
            delta=event.position()-self.last; self.yaw+=delta.x()*.01; self.pitch+=delta.y()*.01; self.last=event.position(); self.update()
    def mouseReleaseEvent(self,event): self.last=None
    def wheelEvent(self,event): self.zoom=max(.2,min(5.,self.zoom*1.12**(event.angleDelta().y()/120))); self.update()

class LatticeComparison(QWidget):
    def __init__(self):
        super().__init__(); layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0)
        title=QHBoxLayout(); title.addWidget(QLabel('晶格变化')); title.addStretch(); self.help=HelpButton(); title.addWidget(self.help); layout.addLayout(title)
        row=QHBoxLayout(); self.before=LatticeScene(); self.after=LatticeScene()
        for widget,name in [(self.before,'变换前'),(self.after,'变换后')]:
            column=QVBoxLayout(); label=QLabel(name); label.setAlignment(Qt.AlignmentFlag.AlignCenter); label.setFixedHeight(20); column.addWidget(label); column.addWidget(widget,1)
            row.addLayout(column,1)
            if widget is self.before:
                arrow=QLabel('→'); arrow.setStyleSheet('font-size:25px;background:transparent;'); row.addWidget(arrow)
        layout.addLayout(row)
    def set_cells(self,original,metric,final,parameters_changed,matrix_changed):
        all_bases=[original,metric,final]
        self.before.set_scene([(original,'#5c6861',False)],all_bases)
        layers=[(original,'#8d9992',True)]
        if parameters_changed: layers.append((metric,'#2677c9',False))
        if matrix_changed: layers.append((final,'#e2b526',False))
        elif not parameters_changed: layers=[(original,'#5c6861',False)]
        self.after.set_scene(layers,all_bases,metric if matrix_changed else None)
