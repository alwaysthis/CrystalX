"""Shared compact plot chrome, following the x_rheed Studio hover controls."""
from PyQt6.QtCore import Qt,QTimer,QSize
from PyQt6.QtGui import QCursor,QPainter,QPen,QColor
from PyQt6.QtWidgets import QFrame,QHBoxLayout,QToolButton,QMenu,QApplication,QWidget
from .plot_style import aspect_ratio
from .icons import icon
from .theme import apply_menu_theme

PLOT_FRAME='#8a8a8a'
PLOT_TICK='#808080'
PLOT_TEXT='#000000'
PLOT_FONT_PX=12

from .math_ui import MathMenu as QMenu, MathToolButton as QToolButton

class PlotHeader(QWidget):
    """Keep analysis centred independently of file controls and image tools."""
    def __init__(self,left,center,right,show_center=True):
        super().__init__(); self.left=left; self.center=center; self.right=right; self.show_center=show_center
        self.setObjectName('plotHeader'); self.setStyleSheet('QWidget#plotHeader {background:transparent;}')
        for widget in (left,center,right): widget.setParent(self)
        left.show(); right.show(); center.setVisible(show_center); self.setFixedHeight(34)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.arrange()
    def arrange(self):
        lw=self.left.sizeHint().width(); cw=self.center.sizeHint().width() if self.show_center else 0; rw=self.right.sizeHint().width()
        stacked=self.show_center and ((self.width()-cw)/2<lw+8 or (self.width()+cw)/2>self.width()-rw-8)
        height=68 if stacked else 34
        if self.height()!=height: self.setFixedHeight(height)
        self.left.setGeometry(0,0,lw,34); self.right.setGeometry(max(0,self.width()-rw),0,rw,34)
        if self.show_center: self.center.setGeometry(max(0,(self.width()-cw)//2),34 if stacked else 0,cw,34)

class PlotAspectHost(QWidget):
    """Fit the complete scientific figure without changing data coordinates."""
    def __init__(self,plot):
        super().__init__(); self.plot=plot; plot.setParent(self); plot.setMinimumSize(1,1)
        self.setObjectName('plotAspectHost'); self.setStyleSheet('QWidget#plotAspectHost {background:transparent;}')
        self.grip=AspectGrip(self)
    def fit_plot(self):
        width,height=self.width(),self.height(); ratio=aspect_ratio(self.plot.style['general']['aspect'])
        if ratio is not None:
            width=min(width,round(height*ratio)); height=min(height,round(width/ratio))
        rect=self.rect(); rect.setSize(QSize(max(1,width),max(1,height)))
        rect.moveCenter(self.rect().center())
        changed=rect!=self.plot.geometry()
        if changed: self.plot.setGeometry(rect)
        self.grip.move(rect.right()-self.grip.width()+1,rect.bottom()-self.grip.height()+1); self.grip.raise_()
        return changed
    def resizeEvent(self,event): super().resizeEvent(event); self.fit_plot()

class AspectGrip(QWidget):
    """Screen-only ratio control; data limits and exported pixels stay independent."""
    def __init__(self,host):
        super().__init__(host); self.host=host; self.start=None; self.previous_lock=False
        self.setFixedSize(18,18); self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip('拖动调整图片宽高比；双击恢复自适应。也可右键图片 → 图片样式 → 通用 → 图片比例。')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.timer=QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(40); self.timer.timeout.connect(self.redraw)

    def paintEvent(self,event):
        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing); painter.setPen(QPen(QColor('#8b9e93'),1.3))
            for offset in (4,8,12): painter.drawLine(16-offset,16,16,16-offset)

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton: return
        plot=self.host.plot; self.start=event.globalPosition(); self.initial=plot.size()
        self.previous_lock=plot.history_locked; plot.history_locked=True; event.accept()

    def mouseMoveEvent(self,event):
        if self.start is None: return
        delta=event.globalPosition()-self.start
        ratio=max(.1,min(10,max(100,self.initial.width()+delta.x())/max(100,self.initial.height()+delta.y())))
        self.host.plot.style['general']['aspect']=f'{ratio:.8g}'
        if not self.timer.isActive(): self.timer.start()
        event.accept()

    def redraw(self): self.host.fit_plot(); self.host.plot.rebuild()

    def mouseReleaseEvent(self,event):
        if self.start is None or event.button()!=Qt.MouseButton.LeftButton: return
        self.timer.stop(); self.redraw(); self.start=None
        plot=self.host.plot; plot.history_locked=self.previous_lock; plot.remember(); self.sync_dialog(); event.accept()

    def mouseDoubleClickEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton: return
        plot=self.host.plot
        if self.start is not None: self.start=None; plot.history_locked=self.previous_lock
        self.timer.stop(); plot.style['general']['aspect']='auto'; self.redraw(); plot.remember(); self.sync_dialog()

    def sync_dialog(self):
        plot=self.host.plot; dialog=plot.style_dialog
        if dialog is not None:
            dialog.write_field(*dialog.fields[('general','aspect')],plot.style['general']['aspect'])

class PlotToolbar(QFrame):
    def __init__(self,plot):
        super().__init__(plot); self.plot=plot; self.setObjectName('plotHoverToolbar')
        self.setStyleSheet('QFrame#plotHoverToolbar {background:white;border:1px solid #e0e0e0;border-radius:5px;} '
            'QToolButton {border:0;border-radius:4px;background:transparent;padding:3px;} '
            'QToolButton:hover {background:#e0e8e3;} QToolButton:pressed {background:#cddcd2;}')
        row=QHBoxLayout(self); row.setContentsMargins(3,2,3,2); row.setSpacing(1)
        self.buttons={}
        for name,label,callback in [('plot_reset','重置视图',plot.reset),('eye','可见性',self.visibility_menu),('plot_camera','复制图片（透明背景）',self.copy_image)]:
            button=QToolButton(self); button.setFixedSize(26,26); button.setIconSize(QSize(20,20))
            button.setIcon(icon(name)); button.setToolTip(label); button.clicked.connect(callback)
            self.buttons[name]=button; row.addWidget(button)
        self.adjustSize(); self.hide()

    def position(self):
        if self.parentWidget() is not self.plot: self.raise_(); return
        area=self.plot.area(); self.move(int(area.right()-self.width()-6),int(area.top()+6)); self.raise_()

    def reveal(self): self.position(); self.show()

    def check_leave(self):
        if self.parentWidget() is not self.plot: return
        if not self.plot.rect().contains(self.plot.mapFromGlobal(QCursor.pos())): self.hide()

    def visibility_menu(self):
        menu=QMenu(self); apply_menu_theme(menu)
        for index,curve in enumerate(self.plot.curves):
            action=menu.addAction(f'{index+1} · {curve.label}'); action.setCheckable(True); action.setChecked(curve.visible)
            action.toggled.connect(lambda value,index=index:self.plot.set_series_visible(index,value))
        menu.exec(self.buttons['eye'].mapToGlobal(self.buttons['eye'].rect().bottomLeft()))

    def copy_image(self): QApplication.clipboard().setImage(self.plot.export_image())

    def leaveEvent(self,event):
        super().leaveEvent(event); QTimer.singleShot(30,self.check_leave)
