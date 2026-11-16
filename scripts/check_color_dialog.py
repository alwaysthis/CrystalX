"""Enter never opens auxiliary color dialogs; color controls are Chinese/themed."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtCore import Qt,QPoint,QCoreApplication
from PyQt6.QtGui import QColor,QFontDatabase,QFont
from PyQt6.QtWidgets import QApplication,QLabel,QPushButton,QLineEdit,QWidget,QDialogButtonBox
from PyQt6.QtTest import QTest
from crystalx.ui import MainWindow
from crystalx.dialogs import QColorDialog
app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
w=MainWindow({'window_width':1400,'window_height':900}); w.show(); root=Path(__file__).resolve().parents[1]; w.load_path(root/'examples/Si.vasp'); page=w.current_page(); page.viewport.open_display_style(); style=page.viewport.style_dialog; app.processEvents()
with patch.object(QColorDialog,'getColor',return_value=QColor('#778899')) as picker:
    style.cell_width.setFocus(); QTest.keyClick(style.cell_width,Qt.Key.Key_Return); QTest.keyClick(style.cell_width,Qt.Key.Key_Enter)
    style.color_button.setFocus(); QTest.keyClick(style.color_button,Qt.Key.Key_Return)
    app.processEvents(); picker.assert_not_called(); assert style.isVisible()
    style.color_button.click(); picker.assert_called_once()
assert all(not button.autoDefault() and not button.isDefault() for button in style.findChildren(QPushButton))
editor=page.coordinate_dialog; editor.show(); editor.parameters[0].setFocus(); app.processEvents()
with patch.object(QColorDialog,'getColor') as picker:
    QTest.keyClick(editor.parameters[0],Qt.Key.Key_Return); picker.assert_not_called(); assert editor.isVisible()
editor.hide()
dialog=QColorDialog.create(QColor('#123456'),style); dialog.show(); app.processEvents()
assert QCoreApplication.translate('QColorDialog','Cursor at %1, %2\nPress ESC to cancel').startswith('光标位置')
labels={label.text().replace('&','') for label in dialog.findChildren(QLabel)}
assert {'基本颜色','自定义颜色','色相：','饱和度：','明度：','十六进制：'}<=labels
assert not any('HTML' in text or 'Basic' in text or 'Custom' in text for text in labels)
buttons={button.text().replace('&','') for button in dialog.findChildren(QPushButton)}
assert {'确定','取消','屏幕取色','添加到自定义颜色'}<=buttons
hex_input=next(field for field in dialog.findChildren(QLineEdit) if field.text().startswith('#'))
hex_input.setFocus(); hex_input.selectAll(); QTest.keyClicks(hex_input,'#9acde2'); app.processEvents(); assert dialog.currentColor().name()=='#9acde2'
dialog.grab().save(str(root/'output/color-dialog-fixed.png'))
track=next(child for child in dialog.findChildren(QWidget) if 'LuminancePicker' in child.metaObject().className())
image=dialog.grab().toImage(); origin=track.mapTo(dialog,QPoint())
# Empty area beside the color bar exposes the dialog theme instead of a white strip.
assert image.pixelColor(origin.x()+track.width()-2,origin.y()+12).name()=='#f1f3f2'
box=dialog.findChild(QDialogButtonBox); QTest.mouseClick(box.button(QDialogButtonBox.StandardButton.Cancel),Qt.MouseButton.LeftButton); assert dialog.result()==0
accepted=QColorDialog.create(QColor('#9acde2'),style); accepted.show(); app.processEvents(); box=accepted.findChild(QDialogButtonBox); QTest.mouseClick(box.button(QDialogButtonBox.StandardButton.Ok),Qt.MouseButton.LeftButton); assert accepted.result()==1 and accepted.currentColor().name()=='#9acde2'
style.hide(); w.close(); print('Color dialog and Enter checks passed')
