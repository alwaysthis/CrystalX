"""Round-top workspace tabs, matching x_rheed studio workspace silhouette."""
from PyQt6.QtCore import Qt,QRectF,QSize,QPointF,pyqtSignal
from PyQt6.QtGui import QPainter,QPainterPath,QColor,QCursor
from PyQt6.QtWidgets import QTabBar,QWidget,QStackedWidget,QSizePolicy,QTabWidget
from .theme import DIALOG_BG,PAGE_BG,PANEL_RADIUS

class WorkspaceTabBar(QTabBar):
    def __init__(self,parent=None):
        super().__init__(parent); self.setExpanding(False); self.setDrawBase(False); self.setMouseTracking(True)
    def tabSizeHint(self,index):
        return QSize(max(64,self.fontMetrics().horizontalAdvance(self.tabText(index))+(44 if self.tabsClosable() else 24)),30)
    def mouseMoveEvent(self,event): super().mouseMoveEvent(event); self.update()
    def leaveEvent(self,event): super().leaveEvent(event); self.update()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.tabsClosable(): p.fillRect(self.rect(),QColor('#f1f3f2'))
        for i in range(self.count()):
            r=QRectF(self.tabRect(i)); path=QPainterPath()
            if i==self.currentIndex():
                radius=PANEL_RADIUS if self.tabsClosable() else 6
                path.moveTo(r.left(),r.bottom()+1); path.lineTo(r.left(),r.top()+radius)
                path.arcTo(QRectF(r.left(),r.top(),2*radius,2*radius),180,-90); path.lineTo(r.right()-radius,r.top())
                path.arcTo(QRectF(r.right()-2*radius,r.top(),2*radius,2*radius),90,-90); path.lineTo(r.right(),r.bottom()+1); path.closeSubpath()
                p.fillPath(path,QColor('#ffffff'))
            elif r.contains(QPointF(self.mapFromGlobal(QCursor.pos()))):
                path.addRoundedRect(r.adjusted(2,2,-2,-2),5,5); p.fillPath(path,QColor('#f3f3f3'))
            p.setPen(QColor('#808080')); p.drawText(r.adjusted(0,0,-18 if self.tabsClosable() else 0,0),Qt.AlignmentFlag.AlignCenter,self.tabText(i))


def tab_page_path(page,tab):
    """One continuous rounded tab/page silhouette, with no corner cutting."""
    path=QPainterPath(); path.addRoundedRect(page,8,8)
    if tab is not None:
        left,right,top=tab.left(),tab.right(),tab.top()
        bottom=page.top()+9
        cap=QPainterPath(); cap.moveTo(left,bottom); cap.lineTo(left,top+6)
        cap.quadTo(left,top,left+6,top); cap.lineTo(right-6,top)
        cap.quadTo(right,top,right,top+6); cap.lineTo(right,bottom); cap.closeSubpath()
        path=path.united(cap)
    return path

class PageOutline(QWidget):
    def __init__(self,host):
        super().__init__(host); self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    def paintEvent(self,event):
        from PyQt6.QtGui import QPen
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#d4e0d9'),.7)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(self.parentWidget().outline_path())

class WorkspaceTabs(QWidget):
    """Stable sibling bar/stack with a rounded painted surface and top outline.

    Mirrors the reference's StableTabs + RoundedSurface + outline composition.
    Pages are transparent and inset, so children cannot overwrite page corners.
    """
    currentChanged=pyqtSignal(int)
    def __init__(self,parent=None):
        super().__init__(parent); self.setObjectName('workspaceTabs')
        self._bar=WorkspaceTabBar(self); self._bar.setFixedHeight(30)
        self._stack=QStackedWidget(self); self._stack.setObjectName('workspaceStack')
        self._stack.setStyleSheet('QStackedWidget#workspaceStack {background:transparent;border:0;}')
        self._stack.setAutoFillBackground(False); self._pages=[]
        self._outline=PageOutline(self); self._bar.currentChanged.connect(self._change)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(150)
    def addTab(self,widget,label):
        widget.setObjectName('workspacePage')
        widget.setStyleSheet('QWidget#workspacePage {background:transparent;border:0;} QLabel,QCheckBox {background:transparent;}')
        widget.setAutoFillBackground(False)
        if widget.layout(): widget.layout().setContentsMargins(12,12,12,12)
        if self._stack.indexOf(widget)<0: self._stack.addWidget(widget)
        self._pages.append(widget); index=self._bar.addTab(label); self._change(self._bar.currentIndex()); return index
    def _change(self,index):
        if 0<=index<len(self._pages): self._stack.setCurrentWidget(self._pages[index])
        self.update(); self._outline.update(); self.currentChanged.emit(index)
    def tabBar(self): return self._bar
    def count(self): return self._bar.count()
    def currentIndex(self): return self._bar.currentIndex()
    def setCurrentIndex(self,index): self._bar.setCurrentIndex(index)
    def widget(self,index): return self._pages[index]
    def outline_path(self):
        page=QRectF(1,29,self.width()-2,self.height()-30)
        tab=QRectF(self._bar.tabRect(self._bar.currentIndex())).adjusted(.5,.5,-.5,0) if self.count() else None
        return tab_page_path(page,tab)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._bar.setGeometry(0,0,self.width(),30)
        self._stack.setGeometry(9,37,max(1,self.width()-18),max(1,self.height()-46))
        self._outline.setGeometry(self.rect()); self._outline.raise_()
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor(DIALOG_BG)); p.fillPath(self.outline_path(),QColor(PAGE_BG))


class StructureTabs(QTabWidget):
    def paintEvent(self,event):
        super().paintEvent(event)
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        height=self.tabBar().height() if self.count() else 30
        path=QPainterPath(); path.addRoundedRect(QRectF(0,0,self.width(),height+PANEL_RADIUS),PANEL_RADIUS,PANEL_RADIUS)
        painter.setClipRect(0,0,self.width(),height); painter.fillPath(path,QColor('#e3eae5'))
