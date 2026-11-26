"""Dollar-only Qt/figure text, editable source, target inheritance and multi-open."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,traceback
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from copy import deepcopy
from PyQt6.QtCore import Qt,QEvent
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication,QWidget,QVBoxLayout,QHBoxLayout,QTableWidgetItem
from PyQt6.QtTest import QTest
from crystalx.math_ui import (formula_image,MathLabel,MathLineEdit,MathComboBox,MathPushButton,MathToolButton,MathCheckBox,
    MathTableWidget,MathTreeWidget,MathPlainTextEdit,MathMenu,document)
from crystalx.math_syntax import contains_math
from crystalx.workspace_tabs import WorkspaceTabs
from crystalx.theme import CONTROLS
from crystalx.ui import MainWindow
from crystalx.session_state import SessionState
from crystalx.dialogs import QFileDialog,QMessageBox
from crystalx.plot_curves import PlotCurve

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
errors=[]
def report(kind,value,tb): errors.append(value); traceback.print_exception(kind,value,tb)
sys.excepthook=report
root=Path(__file__).resolve().parents[1]; out=root/'output'
panel=QWidget(); panel.setStyleSheet(CONTROLS+'QWidget {background:#f1f3f2;color:#29352f;}'); layout=QVBoxLayout(panel)
label=MathLabel(r'强度 $\mathscr{I}_{\alpha}=\frac{1}{2}$'); layout.addWidget(label)
plain=MathLabel(r'I_{001} 与 \alpha：没有美元符号时原样显示'); layout.addWidget(plain)
edit=MathLineEdit(r'$I_{001}=\frac{1}{2}$'); layout.addWidget(edit)
row=QHBoxLayout(); layout.addLayout(row)
combo=MathComboBox(); combo.addItems([r'$\alpha$',r'$\beta$']); row.addWidget(combo)
for cls,text in ((MathPushButton,r'$x^2$'),(MathToolButton,r'$\sqrt{x}$'),(MathCheckBox,r'$\alpha$')):
    widget=cls(); widget.setText(text); row.addWidget(widget)
table=MathTableWidget(2,2); table.setHorizontalHeaderLabels([r'$x_i$',r'$I_i$']); table.setItem(0,0,QTableWidgetItem(r'$\alpha_1$')); table.setItem(0,1,QTableWidgetItem(r'\alpha_1'))
table.setItem(1,0,QTableWidgetItem(r'$\frac{1}{2}$')); table.resizeRowsToContents(); layout.addWidget(table)
tabs=WorkspaceTabs(); tabs.addTab(QWidget(),r'$I_{001}$'); tabs.addTab(QWidget(),'I_{001}'); layout.addWidget(tabs)
output=MathPlainTextEdit(); output.setReadOnly(True); output.setPlainText(r'输出 $\sigma=\sqrt{v}$'); output.setMaximumHeight(55); layout.addWidget(output)
panel.resize(720,610); panel.show(); edit.setFocus(); app.processEvents()
source=edit.text(); edit.selectAll(); QTest.keyClick(edit,Qt.Key.Key_C,Qt.KeyboardModifier.ControlModifier); assert app.clipboard().text()==source
combo.setFocus(); app.processEvents(); assert edit.text()==source
assert contains_math(source) and not contains_math(plain.text())
assert '<img' in document(label.text(),label.font(),label.palette().color(label.foregroundRole())).toHtml()
formula=formula_image(r'\frac{1}{2}','Times New Roman',10,False,False,'#29352f',192)
assert formula.hasAlphaChannel() and formula.pixelColor(0,0).alpha()==0
long_label=r'$O_2$ annealed at $800^{\circ}\mathrm{C}$ for 30min'
preview=document(long_label,edit.font(),edit.palette().color(edit.foregroundRole()))
assert preview.begin().layout().lineCount()==1
assert preview.size().height()<edit.fontMetrics().height()*2
edit.setText(long_label); combo.addItem(long_label); combo.setCurrentIndex(combo.count()-1); plain.setFocus(); app.processEvents()
assert edit.text()==long_label and combo.currentText()==long_label
panel.grab().save(str(out/'math-widgets-dollar-rule.png'))
menu=MathMenu(); menu.setStyleSheet(CONTROLS); menu.addAction(r'$\alpha_{001}$'); menu.popup(panel.mapToGlobal(panel.rect().center())); app.processEvents(); menu.grab().save(str(out/'math-menu.png')); menu.close()
with TemporaryDirectory() as folder:
    folder=Path(folder); a=folder/'a'; b=folder/'b'; a.mkdir(); b.mkdir()
    data=a/'curve.txt'; data.write_text('1 2\n2 6\n3 2\n')
    afm=b/'height.txt'; afm.write_text('X Unit: nm\nY Unit: Pixel\nX Y\n0 1\n1 3\n2 0\n')
    invalid=folder/'bad.txt'; invalid.write_text('bad data')
    window=MainWindow({'window_width':1400,'window_height':1000},session_state=SessionState(folder/'session.json')); window.show()
    paths=[str(root/'examples/Si.vasp'),str(data),str(invalid),str(afm),str(folder/'absent.txt')]
    with patch.object(QFileDialog,'getOpenFileNames',return_value=(paths,'')),patch.object(QMessageBox,'warning') as warning:
        window.open_file(); assert warning.call_count==1
    assert window.work_tabs.count()==3 and window.session_state.directory==str(b.resolve())
    assert window.current_page().data_kind=='AFM'
    with patch.object(QFileDialog,'getOpenFileNames',return_value=([],'')): window.open_file()
    assert window.work_tabs.count()==3
    page=window.work_tabs.widget(1); plot=page.plot
    source_style=deepcopy(plot.curves[0].style); source_style.update(color='#dd2222',width=4,face='#dd2222',edge='#aa0000',marker='circle')
    curve=PlotCurve([1,2,3],[2,5,3],source_style,r'$I_{001}$',points=[1],point_labels={1:r'$\alpha$'})
    from PyQt6.QtCore import QMimeData
    from crystalx.plot_curves import CURVE_MIME
    mime=QMimeData(); mime.setData(CURVE_MIME,curve.clipboard(plot.style['general'])); app.clipboard().setMimeData(mime)
    style=deepcopy(plot.style); style['general'].update(color='#2244cc',width=1.5); plot.apply_style(style)
    assert plot.paste_curve(); bounds=plot.bounds
    assert plot.curves[1].label==r'$I_{001}$' and plot.curves[1].style['marker']=='circle'
    assert plot.data_axes.curve_artists[1].get_color()=='#2244cc'
    style=deepcopy(plot.style); style['general'].update(color='#118844',width=3); plot.apply_style(style); app.processEvents()
    line=plot.data_axes.curve_artists[1]
    assert line.get_color()=='#118844' and line.get_linewidth()==3
    from matplotlib.colors import to_hex
    assert to_hex(line.get_markerfacecolor())=='#118844' and to_hex(plot.data_axes.get_legend().get_texts()[1].get_color())=='#118844'
    assert plot.bounds==bounds and curve.style['color']=='#dd2222'
    assert plot.curves[1].point_labels[1]==r'$\alpha$'
    with patch.object(QFileDialog,'getOpenFileNames',return_value=([str(data),str(afm)],'')): plot.add_file_curves()
    assert len(plot.curves)==4 and window.session_state.directory==str(b.resolve())
    window.close(); window.deleteLater()
panel.close(); panel.deleteLater(); menu.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
assert not errors,errors
print('Qt mathematics, source editing, target style inheritance and multi-file opening passed')
