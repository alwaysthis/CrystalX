"""Direct color swatches with an empty, dashed inherited state."""
from PyQt6.QtCore import Qt,QRectF,QPointF
from PyQt6.QtGui import QColor,QPainter,QPen
from PyQt6.QtWidgets import QMenu
from .display_style import ColorButton
from .dialogs import QColorDialog
from .theme import apply_menu_theme

class PlotColorButton(ColorButton):
    def __init__(self,marker=False):
        super().__init__(); self.marker=marker; self.fallback='#000000'
        self.setToolTip('点击选择颜色；虚线空框表示使用默认颜色。右键可恢复默认'+('或设为透明。' if marker else '。'))

    def set_color(self,value):
        self.value=value
        self.setStyleSheet('QPushButton {background:transparent;border:0;padding:0;}')
        self.setText(''); self.update(); self.colorChanged.emit()

    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled(): painter.setOpacity(.45)
        rect=QRectF(self.rect()).adjusted(1.5,1.5,-1.5,-1.5); radius=4.
        inherited=self.value in ('','auto','none')
        color=QColor('#6c8073' if self.underMouse() or self.hasFocus() else '#9aa39e')
        painter.setPen(QPen(color,1)); painter.setBrush(QColor('#edf3ef') if self.isDown() else Qt.BrushStyle.NoBrush)
        if not inherited:
            painter.setBrush(QColor(self.value)); painter.drawRoundedRect(rect,radius,radius); return
        if self.isDown(): painter.drawRoundedRect(rect,radius,radius)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Equal corner arcs and mirrored dash spacing avoid the asymmetric Qt
        # stylesheet dash pattern around such a small rounded rectangle.
        for x,y,start in ((rect.left(),rect.top(),90),(rect.right()-2*radius,rect.top(),0),
                          (rect.left(),rect.bottom()-2*radius,180),(rect.right()-2*radius,rect.bottom()-2*radius,270)):
            painter.drawArc(QRectF(x,y,2*radius,2*radius),start*16,90*16)
        for edge in (rect.top(),rect.bottom()):
            step=(rect.width()-2*radius)/5
            for index in (0,2,4):
                x=rect.left()+radius+index*step; painter.drawLine(QPointF(x,edge),QPointF(x+step,edge))
        for edge in (rect.left(),rect.right()):
            step=(rect.height()-2*radius)/5
            for index in (0,2,4):
                y=rect.top()+radius+index*step; painter.drawLine(QPointF(edge,y),QPointF(edge,y+step))
        if self.value=='none': painter.drawLine(rect.topLeft()+QPointF(5,5),rect.bottomRight()-QPointF(5,5))

    def pick(self):
        value=self.fallback if self.value in ('','auto','none') else self.value
        color=QColorDialog.getColor(QColor(value),self,'选择颜色')
        if color.isValid(): self.setText(''); self.set_color(color.name())

    def contextMenuEvent(self,event):
        menu=QMenu(self); apply_menu_theme(menu)
        menu.addAction('恢复默认颜色',lambda:self.set_color('auto' if self.marker else ''))
        if self.marker: menu.addAction('透明',lambda:self.set_color('none'))
        try: menu.exec(event.globalPos())
        finally: menu.deleteLater()
