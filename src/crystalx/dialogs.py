"""Theme-owned Chinese file, color and message dialogs."""
from PyQt6.QtWidgets import QMessageBox as QtMessageBox,QFileDialog as QtFileDialog,QColorDialog as QtColorDialog,QDialogButtonBox
from .dialog_chrome import install_dialog_chrome

def prepare(dialog):
    install_dialog_chrome(dialog,dialog.layout())
    for box in dialog.findChildren(QDialogButtonBox):
        for role,text in [(QDialogButtonBox.StandardButton.Ok,'确定'),(QDialogButtonBox.StandardButton.Cancel,'取消'),(QDialogButtonBox.StandardButton.Open,'打开'),(QDialogButtonBox.StandardButton.Save,'保存'),(QDialogButtonBox.StandardButton.Yes,'是'),(QDialogButtonBox.StandardButton.No,'否')]:
            button=box.button(role)
            if button: button.setText(text)
    return dialog

class QMessageBox(QtMessageBox):
    @staticmethod
    def question(parent,title,text,buttons=QtMessageBox.StandardButton.Yes|QtMessageBox.StandardButton.No):
        return QMessageBox.run(parent,title,text,buttons,QtMessageBox.Icon.Question)
    @staticmethod
    def warning(parent,title,text):
        return QMessageBox.run(parent,title,text,QtMessageBox.StandardButton.Ok,QtMessageBox.Icon.Warning)
    @staticmethod
    def run(parent,title,text,buttons,kind):
        dialog=QtMessageBox(kind,title,text,buttons,parent); prepare(dialog)
        for role,label in [(QtMessageBox.StandardButton.Save,'保存'),(QtMessageBox.StandardButton.Discard,'不保存'),(QtMessageBox.StandardButton.Cancel,'取消'),(QtMessageBox.StandardButton.Ok,'确定'),(QtMessageBox.StandardButton.Yes,'是'),(QtMessageBox.StandardButton.No,'否')]:
            button=dialog.button(role)
            if button: button.setText(label)
        return dialog.exec()

# File and directory selection deliberately retain the native OS interface.
QFileDialog = QtFileDialog


# Keep the native color-selection logic while drawing the luminance track without
# QColorLuminancePicker's opaque eraseRect strip beside its pointer.
from PyQt6.QtCore import QObject,QEvent,Qt,QRectF,QPointF
from PyQt6.QtGui import QPainter,QLinearGradient,QColor,QPen,QPolygonF

class LuminanceSurface(QObject):
    def __init__(self,widget,dialog):
        super().__init__(widget); self.dialog=dialog; self.widget=widget; widget.installEventFilter(self)
        dialog.currentColorChanged.connect(widget.update)
    def eventFilter(self,widget,event):
        if event.type()!=QEvent.Type.Paint: return False
        p=QPainter(widget); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        hue,saturation,value,_=self.dialog.currentColor().getHsv(); hue=max(0,hue)
        rect=QRectF(1,4,widget.width()-7,widget.height()-8)
        gradient=QLinearGradient(rect.topLeft(),rect.bottomLeft()); gradient.setColorAt(0,QColor.fromHsv(hue,saturation,255)); gradient.setColorAt(1,QColor('#000000'))
        p.setPen(QPen(QColor('#87998d'),1)); p.setBrush(gradient); p.drawRect(rect)
        y=4+(255-value)*(widget.height()-9)/255
        x=widget.width()-5; p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#364c3e')); p.drawPolygon(QPolygonF([QPointF(x,y),QPointF(x+5,y-4),QPointF(x+5,y+4)])); p.end(); return True

COLOR_TEXT={'Basic colors':'基本颜色','Custom colors':'自定义颜色','Pick Screen Color':'屏幕取色','Add to Custom Colors':'添加到自定义颜色','Hue:':'色相：','Sat:':'饱和度：','Val:':'明度：','Red:':'红：','Green:':'绿：','Blue:':'蓝：','Alpha channel:':'透明度：','HTML:':'十六进制：','Select Color':'选择颜色','Cursor at %1, %2\nPress ESC to cancel':'光标位置：%1，%2\n按 Esc 取消取色'}

from PyQt6.QtCore import QTranslator
COLOR_TEXT['Basic colors']='预设颜色'
class ColorTranslator(QTranslator):
    def isEmpty(self): return False
    def translate(self,context,sourceText,disambiguation=None,n=-1):
        return COLOR_TEXT.get(sourceText.replace('&',''),'') if context=='QColorDialog' else ''

class QColorDialog(QtColorDialog):
    @staticmethod
    def create(initial,parent=None,title='选择颜色'):
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QColor,QPalette
        from PyQt6.QtWidgets import QWidget,QLabel,QPushButton,QApplication
        from .theme import CONTROLS,stepper_css
        import json
        from pathlib import Path
        colors=json.loads((Path(__file__).resolve().parents[2]/'config/default/plot-colors.json').read_text(encoding='utf-8'))
        for index,color in enumerate(colors): QtColorDialog.setStandardColor(index,QColor(color))
        app=QApplication.instance()
        if not hasattr(app,'_crystalx_color_translation'):
            app._crystalx_color_translation=ColorTranslator(app); app.installTranslator(app._crystalx_color_translation)
        dialog=QtColorDialog(initial,parent); dialog.setWindowTitle(title); dialog.setOption(QtColorDialog.ColorDialogOption.DontUseNativeDialog); prepare(dialog)
        dialog.color_surfaces=[]
        translations=COLOR_TEXT
        for widget in dialog.findChildren(QWidget):
            if isinstance(widget,(QLabel,QPushButton)):
                text=widget.text().replace('&','')
                if text in translations: widget.setText(translations[text])
            if isinstance(widget,QLabel): widget.setStyleSheet('QLabel {background:transparent;border:0;}')
            name=widget.metaObject().className()
            if name in ('QColorWell','QtPrivate::QColorPicker','QtPrivate::QColorLuminancePicker','QtPrivate::QColorShower','QDialogButtonBox'):
                unique='colorSurface'+str(id(widget)); widget.setObjectName(unique)
                widget.setStyleSheet(f'QWidget#{unique} {{background:transparent;border:0;}}')
                widget.setAutoFillBackground(False)
                palette=widget.palette(); palette.setColor(QPalette.ColorRole.Window,QColor(Qt.GlobalColor.transparent)); widget.setPalette(palette)
            if name=='QtPrivate::QColorLuminancePicker': dialog.color_surfaces.append(LuminanceSurface(widget,dialog))
            if isinstance(widget,QPushButton): widget.setAutoDefault(False); widget.setDefault(False); widget.setMinimumHeight(28)
        dialog.setStyleSheet(dialog.styleSheet()+CONTROLS+stepper_css()+"""
QDialog#themedDialog {background:transparent;border:0;}
QLineEdit {background:#fff;border:1px solid #ddd;border-radius:4px;padding:3px 6px;color:#29352f;}
QLineEdit:focus {border-color:#91aa9c;}
QAbstractSpinBox QLineEdit {background:transparent;border:0;padding:0;}
QDialogButtonBox {background:transparent;border:0;}
""")
        return dialog

    @staticmethod
    def getColor(initial,parent=None,title='选择颜色'):
        from PyQt6.QtGui import QColor
        dialog=QColorDialog.create(initial,parent,title)
        return dialog.currentColor() if dialog.exec() else QColor()
