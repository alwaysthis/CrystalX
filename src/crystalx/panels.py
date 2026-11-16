"""Fixed bordered panes and an empty-workspace brand surface."""
from PyQt6.QtCore import Qt,QEvent,QRectF,QByteArray
from PyQt6.QtGui import QPainter,QPen,QColor,QFont
from PyQt6.QtWidgets import QWidget,QFrame,QVBoxLayout
from PyQt6.QtSvg import QSvgRenderer
from pathlib import Path
from .theme import PANEL_RADIUS


PANEL_FLOOR='#f1f3f2'
PANEL_EDGE='#9eafa5'

class PanelOutline(QWidget):
    def __init__(self,host):
        super().__init__(host)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(PANEL_EDGE),.7)); painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.75,.75,-.75,-.75),PANEL_RADIUS,PANEL_RADIUS)

class PanelFrame(QFrame):
    """Painted rounded panel with inset children; no clipping or window masks."""
    def __init__(self,content,name):
        super().__init__(); self.setObjectName(name)
        layout=QVBoxLayout(self); layout.setContentsMargins(*((1,1,1,5) if name=='workPanel' else (5,5,5,5))); layout.setSpacing(0); layout.addWidget(content)
        self.outline=PanelOutline(self)
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor(PANEL_FLOOR))
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor('#ffffff'))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.75,.75,-.75,-.75),PANEL_RADIUS,PANEL_RADIUS)
    def sync_outline(self):
        self.outline.setGeometry(self.rect()); self.outline.raise_(); self.outline.update()
    def resizeEvent(self,event): super().resizeEvent(event); self.sync_outline()
    def showEvent(self,event): super().showEvent(event); self.sync_outline()


def framed_panel(content,name):
    return PanelFrame(content,name)

class WelcomeLogo(QWidget):
    def __init__(self,host):
        super().__init__(host); self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet('background:transparent;border:0;')
        svg=(Path(__file__).resolve().parents[2]/'assets/crystalx.svg').read_text(encoding='utf-8')
        import re
        self.renderer=QSvgRenderer(QByteArray(re.sub(r'#[0-9a-fA-F]{6}','#c2c7c4',svg).encode()))
        host.installEventFilter(self); self.setGeometry(host.rect().adjusted(2,2,-2,-2))
    def eventFilter(self,obj,event):
        if event.type()==QEvent.Type.Resize: self.setGeometry(obj.rect().adjusted(2,2,-2,-2))
        return False
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        size=min(320,self.width()*.5,self.height()*.55)
        top=(self.height()-size-48)/2
        self.renderer.render(p,QRectF((self.width()-size)/2,top,size,size))
        font=QFont(self.font()); font.setPixelSize(30); font.setWeight(QFont.Weight.Medium); p.setFont(font); p.setPen(QColor('#bfc5c1'))
        p.drawText(QRectF(0,top+size+10,self.width(),42),Qt.AlignmentFlag.AlignCenter,'CrystalX')
