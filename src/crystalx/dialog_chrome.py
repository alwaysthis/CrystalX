"""Antialiased, alpha-painted dialog shell; no window or widget masks."""
from PyQt6.QtCore import Qt,QSize,QObject,QEvent,QRectF
from PyQt6.QtWidgets import QWidget,QHBoxLayout,QLabel,QToolButton,QSizeGrip,QPushButton
from PyQt6.QtGui import QPainter,QPen,QColor
from .icons import icon
from .theme import DIALOG_BG,window_control_css

class DialogTitleBar(QWidget):
    def __init__(self,dialog):
        super().__init__(dialog); self.dialog=dialog; self.setFixedHeight(34)
        self.setStyleSheet('DialogTitleBar {background:transparent;border:0;} QToolButton {background:transparent;border:0;} QToolButton:hover {background:#e9eeeb;}')
        row=QHBoxLayout(self); row.setContentsMargins(2,0,0,0)
        label=QLabel(dialog.windowTitle()); label.setStyleSheet('background:transparent;border:0;'); label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents); row.addWidget(label); row.addStretch()
        close=QToolButton(); close.setStyleSheet(window_control_css(close=True)); close.setIcon(icon('window_close')); close.setIconSize(QSize(16,16)); close.setFixedSize(30,28); close.setToolTip('关闭'); close.clicked.connect(dialog.reject); row.addWidget(close)
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.dialog.windowHandle(): self.dialog.windowHandle().startSystemMove()

class DialogOutline(QWidget):
    """Draw the stroke above children, as in the reference's RoundOutlineOverlay."""
    def __init__(self,dialog):
        super().__init__(dialog); self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground); self.setAutoFillBackground(False)
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#aab7af'),1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1,1,-1,-1),10,10)

class DialogShell(QObject):
    def __init__(self,dialog):
        super().__init__(dialog); self.outline=DialogOutline(dialog)
        self.grip=QSizeGrip(dialog); self.grip.setFixedSize(12,12); self.grip.setStyleSheet('background:transparent;border:0;')
    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Type.Resize,QEvent.Type.Show,QEvent.Type.LayoutRequest):
            self.outline.setGeometry(obj.rect()); self.outline.raise_()
            self.grip.move(obj.width()-24,obj.height()-24); self.grip.raise_()
        if event.type()==QEvent.Type.Paint:
            p=QPainter(obj); p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source); p.fillRect(obj.rect(),Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(DIALOG_BG))
            p.drawRoundedRect(QRectF(obj.rect()).adjusted(1,1,-1,-1),10,10); p.end()
            return True
        return False

def install_dialog_chrome(dialog,layout):
    dialog.setWindowFlag(Qt.WindowType.FramelessWindowHint)
    dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    dialog.setAutoFillBackground(False); dialog.setObjectName('themedDialog')
    dialog.setStyleSheet(dialog.styleSheet()+'QDialog#themedDialog {background:transparent;border:0;}')
    dialog.setSizeGripEnabled(False)
    for button in dialog.findChildren(QPushButton):
        button.setAutoDefault(False); button.setDefault(False)
    # Keep all opaque children inside the rounded surface rather than clipping them.
    layout.setContentsMargins(12,8,12,12)
    dialog.title_bar=DialogTitleBar(dialog)
    if hasattr(layout,'insertWidget'): layout.insertWidget(0,dialog.title_bar)
    else:
        items=[]
        while layout.count():
            row,col,rows,cols=layout.getItemPosition(0); items.append((layout.takeAt(0),row,col,rows,cols))
        for item,row,col,rows,cols in items: layout.addItem(item,row+1,col,rows,cols)
        layout.addWidget(dialog.title_bar,0,0,1,max(1,layout.columnCount()))
    dialog.shell=DialogShell(dialog); dialog.installEventFilter(dialog.shell)
