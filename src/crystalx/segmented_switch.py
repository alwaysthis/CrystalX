from PyQt6.QtCore import Qt,QRectF,QPropertyAnimation,pyqtProperty,QEasingCurve
from PyQt6.QtGui import QPainter,QColor,QPen
from PyQt6.QtWidgets import QToolButton

class CoordinateSwitch(QToolButton):
    def __init__(self):
        super().__init__(); self.setCheckable(True); self.position=0.; self.animation=QPropertyAnimation(self,b'thumb'); self.animation.setDuration(160); self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.toggled.connect(self.animate)
    def animate(self,checked):
        self.animation.stop(); self.animation.setStartValue(self.position); self.animation.setEndValue(float(checked)); self.animation.start()
    @pyqtProperty(float)
    def thumb(self): return self.position
    @thumb.setter
    def thumb(self,value): self.position=value; self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r=QRectF(self.rect()).adjusted(1,1,-1,-1)
        p.setPen(QPen(QColor('#9ab4a6'),1)); p.setBrush(QColor('#7da991') if self.isChecked() else QColor('#dce5df')); p.drawRoundedRect(r,r.height()/2,r.height()/2)
        diameter=self.height()-8; travel=self.width()-self.height()
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#ffffff')); p.drawEllipse(QRectF(4+self.position*travel,4,diameter,diameter))
