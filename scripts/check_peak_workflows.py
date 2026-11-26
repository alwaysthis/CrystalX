"""Centred controls, one-click automatic/manual ROI search, metadata and captions."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,traceback
from pathlib import Path
from PyQt6.QtCore import Qt,QPointF,QEvent
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
import numpy as np
from crystalx.xrd_page import XrdPage
from crystalx.xrd_io import XrdScan,read_plot_data
from crystalx.afm_io import read_unit_xy
from crystalx.scan_info import afm_statistics

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
errors=[]
def report(kind,value,tb): errors.append(value); traceback.print_exception(kind,value,tb)
sys.excepthook=report
x=np.linspace(10,50,4001); y=10+100*np.exp(-.5*((x-20)/.06)**2)+60*np.exp(-.5*((x-35)/.1)**2)
scan=XrdScan(x.tolist(),y.tolist(),{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega','MEAS_SCAN_MODE':'CONTINUOUS'})
page=XrdPage(Path('sample.ras'),[scan,XrdScan([10,11,12],[1,4,2])]); page.resize(1300,900); page.show(); app.processEvents(); plot=page.plot
assert not page.selector.isVisible() and page.info_button.text()=='文件信息'
for width in (1300,500):
    page.resize(width,900); app.processEvents()
    assert abs(page.analysis_toolbar.geometry().center().x()-page.header.rect().center().x())<=1
    assert not page.analysis_toolbar.geometry().intersects(page.header.left.geometry())
    assert not page.analysis_toolbar.geometry().intersects(page.header.right.geometry())
page.resize(1300,900); app.processEvents()
page.auto_peaks_button.click(); app.processEvents(); dialog=page.peak_dialog
assert dialog.isVisible() and dialog.result is not None and len(dialog.result.peaks)==2
assert dialog.region is None
dialog.show_marks.setChecked(False); dialog.hide(); page.peaks_more_button.click(); assert page.peak_dialog is dialog and dialog.isVisible()
dialog.hide(); before=plot.bounds; page.manual_peaks_button.click(); assert plot.manual_peak_mode
area=plot.area(); start=QPointF(plot.point(19,20).x(),area.top()+2); end=QPointF(plot.point(21,20).x(),area.bottom()-2)
QTest.mousePress(plot.canvas,Qt.MouseButton.LeftButton,pos=start.toPoint()); QTest.mouseMove(plot.canvas,end.toPoint())
assert plot.peak_rect is not None
QTest.mouseRelease(plot.canvas,Qt.MouseButton.LeftButton,pos=end.toPoint()); app.processEvents()
assert not plot.manual_peak_mode and not page.manual_peaks_button.isChecked() and plot.bounds==before
assert dialog.isVisible() and dialog.region is not None and len(dialog.result.peaks)==1
assert abs(dialog.result.peaks[0].x-20)<.011 and not plot.curves[0].peaks
dialog.show_marks.setChecked(True); assert plot.curves[0].peaks==[dialog.result.peaks[0].index]
dialog.hide(); page.manual_peaks_button.click(); QTest.keyClick(plot.canvas,Qt.Key.Key_Escape); assert not plot.manual_peak_mode
page.auto_peaks_button.click(); assert page.peak_dialog.region is None and len(dialog.result.peaks)==2
dialog.hide(); plot.set_legend_label(0,'$I_{001}$'); assert plot.data_axes.get_legend().get_texts()[0].get_text()=='$I_{001}$'
app.processEvents(); peak_index=plot.curves[0].peaks[0]
annotation=next(a for curve,index,a in plot.data_axes.point_annotations if index==peak_index)
box=annotation.get_window_extent(plot.canvas.get_renderer()); ratio=plot.canvas.figure.bbox.width/plot.width()
position=QPointF((box.x0+box.x1)/2/ratio,plot.height()-(box.y0+box.y1)/2/ratio)
QTest.mouseDClick(plot.canvas,Qt.MouseButton.LeftButton,pos=position.toPoint()); app.processEvents()
assert plot.point_editor.isVisible(); plot.point_editor.input.setText(r'$(00\ell)$'); plot.point_editor.accept(); app.processEvents()
assert plot.curves[0].point_labels[peak_index]==r'$(00\ell)$'
plot.curves[0].points=[1500]; plot.rebuild(); app.processEvents()
annotation=next(a for curve,index,a in plot.data_axes.point_annotations if index==1500); box=annotation.get_window_extent(plot.canvas.get_renderer()); ratio=plot.canvas.figure.bbox.width/plot.width()
position=QPointF((box.x0+box.x1)/2/ratio,plot.height()-(box.y0+box.y1)/2/ratio)
QTest.mouseDClick(plot.canvas,Qt.MouseButton.LeftButton,pos=position.toPoint()); app.processEvents()
editor=plot.point_editor; assert editor.isVisible(); editor.input.setText(r'$\mathscr{I}_{\alpha}$'); QTest.keyClick(editor.input,Qt.Key.Key_Return); app.processEvents()
assert plot.curves[0].point_labels[1500]==r'$\mathscr{I}_{\alpha}$'
assert next(a for curve,index,a in plot.data_axes.point_annotations if index==1500).get_text()==r'$\mathscr{I}_{\alpha}$'
page.info_button.click(); app.processEvents(); info=page.info_dialog
assert info.isVisible() and info.selector.count()==2
assert any(info.table.item(row,0).text()=='扫描轴' for row in range(info.table.rowCount()))
info.selector.setCurrentIndex(1); app.processEvents(); assert plot.scan is page.scans[1]
info.selector.setCurrentIndex(0); app.processEvents(); info.hide()
out=Path(__file__).resolve().parents[1]/'output'; page.grab().save(str(out/'xrd-centered-tools.png'))
afm_scan=read_plot_data(sys.argv[1])[0] if len(sys.argv)>1 else read_unit_xy('X Unit: nm\nY Unit: Pixel\nX Y\n0 1\n2 3\n4 0')
afm=XrdPage(Path(sys.argv[1]) if len(sys.argv)>1 else Path('AFM-height.txt'),[afm_scan]); afm.resize(1000,800); afm.show(); app.processEvents()
assert afm.kind_label.text()=='AFM高度'; afm.info_button.click(); app.processEvents()
assert afm.info_dialog.isVisible(); rows={afm.info_dialog.table.item(i,0).text():afm.info_dialog.table.item(i,1).text() for i in range(afm.info_dialog.table.rowCount())}
stats=afm_statistics(afm_scan); assert '平均高度' in rows and '方差' in rows and '峰值高度（众数）' in rows
print('AFM weighted statistics:',stats)
afm.info_dialog.grab().save(str(out/'afm-height-information.png'))
for widget in (page,afm): widget.close(); widget.deleteLater()
QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents(); assert not errors,errors
print('Centred header, auto/manual search, ROI, information and LaTeX annotations passed')
