"""Top-level-only painted rounded border and soft shadow; no masks."""
from PyQt6.QtCore import QObject,QEvent,Qt,QRectF
from PyQt6.QtGui import QPainter,QColor,QPen
from PyQt6.QtWidgets import QWidget

class WindowEdge(QWidget):
    def __init__(self,window):
        super().__init__(window); self.window=window; self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); inset=1 if self.window.isMaximized() else 9
        p.setPen(QPen(QColor('#9aaba1'),.8)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawRoundedRect(QRectF(self.rect()).adjusted(inset,inset,-inset,-inset),0 if self.window.isMaximized() else 10,0 if self.window.isMaximized() else 10)

class WindowShell(QObject):
    def __init__(self,window):
        super().__init__(window); self.edge=WindowEdge(window); window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground); window.setAutoFillBackground(False)
        window.setObjectName('applicationWindow'); window.setStyleSheet(window.styleSheet()+'QMainWindow#applicationWindow {background:transparent;border:0;}')
        window.installEventFilter(self); self.sync(window)
    def sync(self,w):
        margin=1 if w.isMaximized() else 15
        radius=0 if w.isMaximized() else 7
        w.menuWidget().setStyleSheet(f'QWidget#titleChrome {{background:#f1f3f2;border:0;border-top-left-radius:{radius}px;border-top-right-radius:{radius}px;}}')
        w.title_bar.setStyleSheet('TitleBar {background:transparent;}')
        w.statusBar().setStyleSheet(f'QStatusBar {{background:#e0e6e2;border:0;border-bottom-left-radius:{radius}px;border-bottom-right-radius:{radius}px;}} QStatusBar QWidget {{background:transparent;}}')
        # Shadow occupies 9px; place the bar immediately inside the visible top border.
        top=1 if w.isMaximized() else 10
        w.title_bar.layout().setContentsMargins(12,0,0 if w.isMaximized() else 5,0)
        w.setContentsMargins(margin,top,margin,margin); self.edge.setGeometry(w.rect()); self.edge.raise_(); self.edge.update()
    def eventFilter(self,w,event):
        if event.type() in (QEvent.Type.Resize,QEvent.Type.Show,QEvent.Type.WindowStateChange): self.sync(w)
        if event.type()==QEvent.Type.Paint:
            p=QPainter(w); p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source); p.fillRect(w.rect(),Qt.GlobalColor.transparent); p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            p.setPen(Qt.PenStyle.NoPen)
            if not w.isMaximized():
                for spread in range(8,0,-1):
                    p.setBrush(QColor(18,35,26,3)); p.drawRoundedRect(QRectF(w.rect()).adjusted(9-spread,10-spread,-9+spread,-8+spread),10+spread,10+spread)
            inset=1 if w.isMaximized() else 9
            p.setBrush(QColor('#f1f3f2')); p.drawRoundedRect(QRectF(w.rect()).adjusted(inset,inset,-inset,-inset),0 if w.isMaximized() else 10,0 if w.isMaximized() else 10); p.end(); return True
        return False
