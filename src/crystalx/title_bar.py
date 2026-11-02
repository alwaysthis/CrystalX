"""Custom top-level title bar with native system dragging and window controls."""
from PyQt6.QtCore import Qt,QSize,QEvent
from PyQt6.QtWidgets import QWidget,QHBoxLayout,QLabel,QToolButton
from .icons import icon

class TitleBar(QWidget):
    def __init__(self,window):
        super().__init__(window)
        self.window=window; self.setFixedHeight(36)
        layout=QHBoxLayout(self); layout.setContentsMargins(12,0,0,0); layout.setSpacing(3)
        title=QLabel('CrystalX'); title.setStyleSheet('font-size:15px;font-weight:600;'); title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents); layout.addWidget(title)
        self.undo_button=QToolButton(); self.redo_button=QToolButton()
        for button,name,key,callback in [(self.undo_button,'撤销','undo',window.undo),(self.redo_button,'重做','redo',window.redo)]:
            button.setIcon(icon(key)); button.setIconSize(QSize(19,19)); button.setFixedSize(28,28); button.setToolTip(name); button.clicked.connect(callback); layout.addWidget(button)
        layout.addStretch()
        self.minimize=QToolButton(); self.maximize=QToolButton(); self.close_button=QToolButton()
        for button,name,key,callback in [(self.minimize,'最小化','window_minimize',window.showMinimized),(self.maximize,'最大化 / 还原','window_maximize',self.toggle_maximize),(self.close_button,'关闭','window_close',window.close)]:
            button.setIcon(icon(key)); button.setIconSize(QSize(18,18)); button.setToolTip(name); button.setFixedSize(42,36); button.clicked.connect(callback); layout.addWidget(button)
        window.installEventFilter(self)
        self.setStyleSheet('QToolButton {border:0;background:transparent;} QToolButton:hover {background:#e8eeeb;}')
        self.close_button.setStyleSheet('QToolButton:hover {background:#e95c58;}')

    def toggle_maximize(self):
        if self.window.isMaximized(): self.window.showNormal()
        else: self.window.showMaximized()
        self.sync_window_icon()

    def sync_window_icon(self):
        self.maximize.setIcon(icon('window_restore' if self.window.isMaximized() else 'window_maximize'))
        self.maximize.setToolTip('还原' if self.window.isMaximized() else '最大化')

    def eventFilter(self,watched,event):
        if watched is self.window and event.type()==QEvent.Type.WindowStateChange:
            self.sync_window_icon()
        return super().eventFilter(watched,event)

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            handle=self.window.windowHandle()
            if handle: handle.startSystemMove()

    def mouseDoubleClickEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton: self.toggle_maximize()
