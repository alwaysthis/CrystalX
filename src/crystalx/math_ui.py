"""Shared dollar-delimited math previews without changing editable source text."""
from functools import lru_cache
from io import BytesIO
import html
import re
from PyQt6.QtCore import Qt,QUrl,QSize,QRectF,QPointF
from PyQt6.QtGui import QPainter,QImage,QTextDocument,QTextOption,QPalette,QFont,QColor,QIcon
from PyQt6.QtWidgets import (QLabel,QLineEdit,QComboBox,QPushButton,QToolButton,QCheckBox,QTableWidget,QTreeWidget,QListWidget,
    QPlainTextEdit,QStyledItemDelegate,QStyle,QStyleOptionFrame,QStyleOptionComboBox,QStyleOptionButton,QStyleOptionToolButton,
    QStyleOptionViewItem,QHeaderView,QStyleOptionHeader,QMenu)
from .math_syntax import MATH_SPANS,contains_math

@lru_cache(maxsize=256)
def formula_image(formula,family,size,bold,italic,color,dpi):
    from matplotlib import rc_context
    from matplotlib.mathtext import math_to_image
    from matplotlib.font_manager import FontProperties
    stream=BytesIO(); prop=FontProperties(family=family,size=size,weight='bold' if bold else 'normal',style='italic' if italic else 'normal',math_fontfamily='stix')
    with rc_context({'savefig.transparent':True}):
        math_to_image('$'+formula.strip()+'$',stream,prop=prop,dpi=dpi,format='png',color=color)
    return QImage.fromData(stream.getvalue(),'PNG')

def document(text,font,color,ratio=1,width=None):
    doc=QTextDocument(); doc.setDocumentMargin(0); doc.setDefaultFont(font)
    option=doc.defaultTextOption()
    option.setWrapMode(QTextOption.WrapMode.NoWrap if width is None else QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    doc.setDefaultTextOption(option)
    rich=bool(re.search(r'<(?:table|p|span|b|i|font|br)\b',text,re.I))
    pieces=[]; offset=0
    def ordinary(value): return value if rich else html.escape(value).replace('\n','<br>')
    for index,match in enumerate(MATH_SPANS.finditer(text)):
        pieces.append(ordinary(text[offset:match.start()])); formula=match.group(1) or match.group(2)
        dpi=192*ratio; size=font.pointSizeF() if font.pointSizeF()>0 else max(1,font.pixelSize())*.75
        image=formula_image(formula,font.family(),size,font.bold(),font.italic(),color.name(),dpi)
        name=QUrl(f'crystalx-math:{index}'); doc.addResource(QTextDocument.ResourceType.ImageResource,name,image)
        pieces.append(f'<img src="{name.toString()}" width="{image.width()*96/dpi:g}" height="{image.height()*96/dpi:g}" style="vertical-align:middle">')
        offset=match.end()
    pieces.append(ordinary(text[offset:])); doc.setHtml(f'<span style="color:{color.name()}">'+''.join(pieces)+'</span>')
    if width is not None: doc.setTextWidth(max(1,width))
    else: doc.adjustSize()
    return doc

def draw_text(painter,rect,flags,text,single_line=False):
    if single_line: text=' '.join(text.splitlines())
    if not contains_math(text): painter.drawText(rect,flags,text); return
    try: doc=document(text,painter.font(),painter.pen().color(),painter.device().devicePixelRatioF())
    except ValueError: painter.drawText(rect,flags,text); return
    x=rect.left(); y=rect.top()
    if flags&Qt.AlignmentFlag.AlignHCenter: x+=(rect.width()-doc.size().width())/2
    elif flags&Qt.AlignmentFlag.AlignRight: x+=rect.width()-doc.size().width()
    if flags&Qt.AlignmentFlag.AlignVCenter: y+=(rect.height()-doc.size().height())/2
    factor=min(1,rect.height()/max(1,doc.size().height()))
    if factor<1: y=rect.top(); x=rect.left()
    painter.save(); painter.setClipRect(rect); painter.translate(x,y); painter.scale(factor,factor); doc.drawContents(painter); painter.restore()

def draw_at(painter,point,text):
    if not contains_math(text): painter.drawText(point,text); return
    try: size=document(text,painter.font(),painter.pen().color()).size()
    except ValueError: painter.drawText(point,text); return
    draw_text(painter,QRectF(point.x(),point.y()-size.height(),size.width()+2,size.height()+2),Qt.AlignmentFlag.AlignLeft,text)

class MathLabel(QLabel):
    def paintEvent(self,event):
        if not contains_math(self.text()): return super().paintEvent(event)
        try: doc=document(self.text(),self.font(),self.palette().color(QPalette.ColorRole.WindowText),self.devicePixelRatioF(),self.contentsRect().width() if self.wordWrap() else None)
        except ValueError: return super().paintEvent(event)
        with QPainter(self) as painter:
            rect=QRectF(self.contentsRect()).adjusted(self.margin(),self.margin(),-self.margin(),-self.margin())
            x=rect.x(); y=rect.y(); alignment=self.alignment()
            if alignment&Qt.AlignmentFlag.AlignHCenter: x+=(rect.width()-doc.size().width())/2
            elif alignment&Qt.AlignmentFlag.AlignRight: x+=rect.width()-doc.size().width()
            if alignment&Qt.AlignmentFlag.AlignVCenter: y+=(rect.height()-doc.size().height())/2
            painter.setClipRect(rect); painter.translate(x,y); doc.drawContents(painter)
    def sizeHint(self):
        if contains_math(self.text()):
            try:
                size=document(self.text(),self.font(),self.palette().color(QPalette.ColorRole.WindowText)).size().toSize()
                return size+QSize(self.margin()*2+2,self.margin()*2+2)
            except ValueError: pass
        return super().sizeHint()

class MathLineEdit(QLineEdit):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.textChanged.connect(self.update)
    def focusInEvent(self,event): super().focusInEvent(event); self.update()
    def focusOutEvent(self,event): super().focusOutEvent(event); self.update()
    def paintEvent(self,event):
        if self.hasFocus() or self.echoMode()!=QLineEdit.EchoMode.Normal or not contains_math(self.text()): return super().paintEvent(event)
        try: document(self.text(),self.font(),self.palette().color(QPalette.ColorRole.Text),self.devicePixelRatioF())
        except ValueError: return super().paintEvent(event)
        option=QStyleOptionFrame(); self.initStyleOption(option)
        with QPainter(self) as painter:
            self.style().drawPrimitive(QStyle.PrimitiveElement.PE_PanelLineEdit,option,painter,self)
            rect=QRectF(self.style().subElementRect(QStyle.SubElement.SE_LineEditContents,option,self)).adjusted(4,1,-4,-1)
            painter.setFont(self.font()); painter.setPen(self.palette().color(QPalette.ColorRole.Text))
            draw_text(painter,rect,Qt.AlignmentFlag.AlignVCenter|self.alignment(),self.text(),single_line=True)

class MathItemDelegate(QStyledItemDelegate):
    def paint(self,painter,option,index):
        text=str(index.data() or '')
        if not contains_math(text): return super().paint(painter,option,index)
        opt=QStyleOptionViewItem(option); self.initStyleOption(opt,index); original=opt.text
        # The application uses a light selection; the system palette may pair it
        # with white text. Keep formula foreground readable in tables and lists.
        opt.palette.setColor(QPalette.ColorRole.HighlightedText,QColor('#23482f'))
        rect=option.widget.style().subElementRect(QStyle.SubElement.SE_ItemViewItemText,opt,option.widget); opt.text=''
        option.widget.style().drawControl(QStyle.ControlElement.CE_ItemViewItem,opt,painter,option.widget)
        painter.save(); painter.setFont(opt.font)
        painter.setPen(opt.palette.color(QPalette.ColorRole.HighlightedText if opt.state&QStyle.StateFlag.State_Selected else QPalette.ColorRole.Text))
        draw_text(painter,QRectF(rect).adjusted(2,0,-2,0),opt.displayAlignment|Qt.AlignmentFlag.AlignVCenter,original,single_line=True); painter.restore()
    def sizeHint(self,option,index):
        size=super().sizeHint(option,index); text=str(index.data() or '')
        if contains_math(text):
            try:
                math_size=document(text,option.font,option.palette.color(QPalette.ColorRole.Text)).size().toSize()
                return QSize(max(size.width(),math_size.width()+8),max(size.height(),math_size.height()+4))
            except ValueError: pass
        return size

class MathHeaderView(QHeaderView):
    def paintSection(self,painter,rect,index):
        text=str(self.model().headerData(index,self.orientation()) or '')
        if not contains_math(text): return super().paintSection(painter,rect,index)
        opt=QStyleOptionHeader(); self.initStyleOption(opt); opt.rect=rect; opt.section=index; opt.text=''
        self.style().drawControl(QStyle.ControlElement.CE_Header,opt,painter,self)
        painter.save(); painter.setFont(self.font()); painter.setPen(self.palette().color(QPalette.ColorRole.ButtonText))
        draw_text(painter,QRectF(rect).adjusted(4,0,-4,0),Qt.AlignmentFlag.AlignCenter,text); painter.restore()

class MathComboDelegate(MathItemDelegate):
    """Popup rows use the same light selection for plain and formula text."""
    def paint(self,painter,option,index):
        opt=QStyleOptionViewItem(option); self.initStyleOption(opt,index)
        selected=bool(opt.state&QStyle.StateFlag.State_Selected)
        hovered=bool(opt.state&QStyle.StateFlag.State_MouseOver)
        enabled=bool(opt.state&QStyle.StateFlag.State_Enabled)
        painter.save(); painter.setClipRect(opt.rect)
        painter.fillRect(opt.rect,QColor('#ffffff')); painter.setPen(Qt.PenStyle.NoPen)
        if selected or hovered:
            painter.setBrush(QColor('#dce7df' if selected else '#edf3ef'))
            painter.drawRoundedRect(QRectF(opt.rect).adjusted(2,1,-2,-1),3,3)
        rect=QRectF(opt.rect).adjusted(10,0,-10,0)
        if opt.features&QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator:
            check=QStyleOptionViewItem(opt); check.rect=rect.toRect(); check.rect.setWidth(16)
            check.rect.setTop(check.rect.center().y()-8); check.rect.setHeight(16)
            check.state&=~(QStyle.StateFlag.State_On|QStyle.StateFlag.State_Off|QStyle.StateFlag.State_NoChange)
            check.state|={Qt.CheckState.Checked:QStyle.StateFlag.State_On,Qt.CheckState.Unchecked:QStyle.StateFlag.State_Off,Qt.CheckState.PartiallyChecked:QStyle.StateFlag.State_NoChange}[opt.checkState]
            option.widget.style().drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorItemViewItemCheck,check,painter,option.widget)
            rect.adjust(22,0,0,0)
        if not opt.icon.isNull():
            opt.icon.paint(painter,rect.toRect().adjusted(0,0,-int(max(0,rect.width()-20)),0),Qt.AlignmentFlag.AlignVCenter,
                QIcon.Mode.Normal if enabled else QIcon.Mode.Disabled)
            rect.adjust(24,0,0,0)
        painter.setFont(opt.font); painter.setPen(QColor('#23482f' if selected else '#252525') if enabled else QColor('#9ba69f'))
        draw_text(painter,rect,Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft,opt.text,single_line=True)
        painter.restore()

    def sizeHint(self,option,index):
        size=super().sizeHint(option,index)
        return QSize(size.width()+20,max(26,size.height()+4))

class MathTableWidget(QTableWidget):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.setItemDelegate(MathItemDelegate(self)); self.setHorizontalHeader(MathHeaderView(Qt.Orientation.Horizontal,self)); self.setVerticalHeader(MathHeaderView(Qt.Orientation.Vertical,self))

class MathTreeWidget(QTreeWidget):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.setItemDelegate(MathItemDelegate(self)); self.setHeader(MathHeaderView(Qt.Orientation.Horizontal,self))

class MathListWidget(QListWidget):
    def __init__(self,*args,**kwargs): super().__init__(*args,**kwargs); self.setItemDelegate(MathItemDelegate(self))

class MathComboBox(QComboBox):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.setItemDelegate(MathComboDelegate(self))
        self.view().setStyleSheet('QAbstractItemView {background:white;color:#252525;border:1px solid #b8c5bd;outline:0;padding:2px;}')
    def setEditable(self,enabled):
        super().setEditable(enabled)
        if enabled and not isinstance(self.lineEdit(),MathLineEdit):
            text=self.currentText(); self.setLineEdit(MathLineEdit(self)); self.lineEdit().setText(text)
    def paintEvent(self,event):
        if self.isEditable() or not contains_math(self.currentText()): return super().paintEvent(event)
        option=QStyleOptionComboBox(); self.initStyleOption(option); text=option.currentText; option.currentText=''
        with QPainter(self) as painter:
            self.style().drawComplexControl(QStyle.ComplexControl.CC_ComboBox,option,painter,self)
            rect=self.style().subControlRect(QStyle.ComplexControl.CC_ComboBox,option,QStyle.SubControl.SC_ComboBoxEditField,self)
            painter.setFont(self.font()); painter.setPen(self.palette().color(QPalette.ColorRole.Text)); draw_text(painter,QRectF(rect),Qt.AlignmentFlag.AlignVCenter,text,single_line=True)

class MathPushButton(QPushButton):
    def paintEvent(self,event):
        if not contains_math(self.text()): return super().paintEvent(event)
        option=QStyleOptionButton(); self.initStyleOption(option); option.text=''
        with QPainter(self) as painter:
            self.style().drawControl(QStyle.ControlElement.CE_PushButton,option,painter,self)
            painter.setFont(self.font()); painter.setPen(self.palette().color(QPalette.ColorRole.ButtonText)); draw_text(painter,QRectF(self.rect()).adjusted(4,2,-4,-2),Qt.AlignmentFlag.AlignCenter,self.text())

class MathCheckBox(QCheckBox):
    def paintEvent(self,event):
        if not contains_math(self.text()): return super().paintEvent(event)
        option=QStyleOptionButton(); self.initStyleOption(option); option.text=''
        with QPainter(self) as painter:
            self.style().drawControl(QStyle.ControlElement.CE_CheckBox,option,painter,self)
            rect=self.style().subElementRect(QStyle.SubElement.SE_CheckBoxContents,option,self)
            painter.setFont(self.font()); painter.setPen(self.palette().color(QPalette.ColorRole.WindowText)); draw_text(painter,QRectF(rect),Qt.AlignmentFlag.AlignVCenter,self.text())

class MathToolButton(QToolButton):
    def paintEvent(self,event):
        text=QToolButton.text(self)
        if not contains_math(text): return super().paintEvent(event)
        option=QStyleOptionToolButton(); self.initStyleOption(option); option.text=''
        with QPainter(self) as painter:
            self.style().drawComplexControl(QStyle.ComplexControl.CC_ToolButton,option,painter,self)
            painter.setFont(self.font()); painter.setPen(self.palette().color(QPalette.ColorRole.ButtonText))
            draw_text(painter,QRectF(self.rect()).adjusted(self.iconSize().width()+4 if not self.icon().isNull() else 3,1,-3,-1),Qt.AlignmentFlag.AlignCenter,text)

class MathPlainTextEdit(QPlainTextEdit):
    def paintEvent(self,event):
        super().paintEvent(event)
        if self.hasFocus() and not self.isReadOnly(): return
        with QPainter(self.viewport()) as painter:
            painter.setFont(self.font()); painter.setPen(self.palette().color(QPalette.ColorRole.Text))
            block=self.firstVisibleBlock()
            while block.isValid():
                rect=self.blockBoundingGeometry(block).translated(self.contentOffset())
                if rect.top()>self.viewport().height(): break
                if contains_math(block.text()):
                    painter.fillRect(rect,self.palette().color(QPalette.ColorRole.Base)); draw_text(painter,rect,Qt.AlignmentFlag.AlignVCenter,block.text())
                block=block.next()

class MathMenu(QMenu):
    def paintEvent(self,event):
        from PyQt6.QtWidgets import QStyleOptionMenuItem
        super().paintEvent(event)
        with QPainter(self) as painter:
            painter.setFont(self.font())
            for action in self.actions():
                if not contains_math(action.text()): continue
                option=QStyleOptionMenuItem(); self.initStyleOption(option,action); option.rect=self.actionGeometry(action); option.text=''
                selected=option.state&QStyle.StateFlag.State_Selected
                painter.fillRect(option.rect,self.palette().color(QPalette.ColorRole.Window) if not selected else self.palette().color(QPalette.ColorRole.Highlight))
                self.style().drawControl(QStyle.ControlElement.CE_MenuItem,option,painter,self); painter.setPen(self.palette().color(QPalette.ColorRole.Text))
                draw_text(painter,QRectF(option.rect).adjusted(28,0,-15,0),Qt.AlignmentFlag.AlignVCenter,action.text())
