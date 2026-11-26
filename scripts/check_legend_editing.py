"""Double-click exact legend rows, including hidden and identically named curves."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,traceback
from pathlib import Path
from tempfile import TemporaryDirectory
from PyQt6.QtCore import Qt,QPointF,QEvent
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication,QLabel
from PyQt6.QtTest import QTest
from crystalx.xrd_page import XrdPlot
from crystalx.xrd_io import XrdScan
from crystalx.plot_presets import PlotDefaults
from crystalx.plot_curves import PlotCurve,CURVE_MIME

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
errors=[]
def report(kind,value,tb): errors.append(value); traceback.print_exception(kind,value,tb)
sys.excepthook=report
with TemporaryDirectory() as directory:
    plot=XrdPlot(QLabel(),PlotDefaults(Path(directory)/'plot.json')); plot.resize(1000,700)
    plot.set_scan(XrdScan([1,2,3],[2,4,3])); plot.add_scan(XrdScan([1,2,3],[3,2,5]))
    plot.curves[1].label=plot.curves[0].label; plot.rebuild(); plot.show(); app.processEvents()
    def click_text(row):
        text=plot.data_axes.get_legend().get_texts()[row]; box=text.get_window_extent(plot.canvas.get_renderer())
        ratio=plot.canvas.figure.bbox.width/plot.width()
        position=QPointF((box.x0+box.x1)/2/ratio,plot.height()-(box.y0+box.y1)/2/ratio)
        QTest.mouseDClick(plot.canvas,Qt.MouseButton.LeftButton,pos=position.toPoint()); app.processEvents()
        assert plot.legend_editor.isVisible() and plot.legend_drag is None
        return plot.legend_editor
    original=plot.curves[1].label; bounds=plot.bounds
    editor=click_text(1); editor.input.setText('cancelled'); editor.reject(); assert plot.curves[1].label==original
    plot.set_series_visible(0,False); app.processEvents()
    assert plot.data_axes.legend_curve_indices==[1]
    dialog=plot.open_style(section='curve'); dialog.curve_selector.setCurrentIndex(1); app.processEvents()
    plot.legend_anchor=(.2,.6); plot.rebuild(); app.processEvents()
    editor=click_text(0); editor.input.setText(r'$\frac{1}{$'); editor.accept()
    assert editor.isVisible() and editor.error.text() and plot.curves[1].label==original
    editor.input.setText(r'$\rm{Film}_{\alpha}$'); QTest.keyClick(editor.input,Qt.Key.Key_Return); app.processEvents()
    assert not editor.isVisible() and plot.curves[1].label==r'$\rm{Film}_{\alpha}$'
    assert plot.curves[0].label==original and plot.bounds==bounds and plot.legend_anchor==(.2,.6)
    assert dialog.fields[('curve','label')][1].text()==plot.curves[1].label
    assert dialog.curve_drafts[1]['label']==plot.curves[1].label
    assert dialog.apply() and plot.curves[1].label==r'$\rm{Film}_{\alpha}$'
    plot.copy_curve(1)
    copied=PlotCurve.from_clipboard(app.clipboard().mimeData().data(CURVE_MIME)); assert copied.label==plot.curves[1].label
    assert not plot.export_image().isNull()
    editor=click_text(0); plot.set_scan(XrdScan([1,2],[3,4])); assert not editor.isVisible()
    dialog.close(); plot.close(); plot.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
assert not errors,errors
print('Legend double-click, row identity, validation, cancel, style synchronization and clipboard passed')
