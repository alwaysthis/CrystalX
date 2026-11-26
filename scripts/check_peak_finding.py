"""XRD toolbar, candidate analysis, non-destructive markers and result export."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,csv
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication
from crystalx.xrd_page import XrdPage
from crystalx.xrd_io import XrdScan,read_plot_data
from crystalx.afm_io import read_unit_xy
from crystalx.dialogs import QFileDialog

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
x=np.linspace(10,50,4001); y=10+100*np.exp(-.5*((x-20)/.06)**2)+60*np.exp(-.5*((x-35)/.1)**2)
synthetic=XrdScan(x.tolist(),y.tolist(),{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega'})
scans=read_plot_data(sys.argv[1]) if len(sys.argv)>1 else [synthetic]
page=XrdPage(Path('XRD.ras'),scans); page.resize(1300,900); page.show(); app.processEvents()
assert page.analysis_toolbar.isVisible() and page.find_peaks_button.text()=='自动寻峰'
page.find_peaks_button.click(); app.processEvents(); dialog=page.peak_dialog
assert dialog.isVisible()
plot=page.plot; source=deepcopy(plot.curves[0].y); bounds=plot.bounds
assert dialog.run(),dialog.error.text(); app.processEvents()
assert dialog.result.peaks and plot.curves[0].peaks
assert plot.curves[0].y==source and plot.bounds==bounds
if len(sys.argv)>1:
    strongest=max(dialog.result.peaks,key=lambda p:p.prominence); assert abs(strongest.x-46.47)<.011
    print('Actual XRD candidates:',len(dialog.result.peaks),'threshold:',dialog.result.threshold,'strongest:',strongest.x)
else: np.testing.assert_allclose([p.x for p in dialog.result.peaks],[20,35],atol=.011)
plot.curves[0].points=[0]; saved=list(plot.curves[0].peaks)
style=deepcopy(plot.style); style['general']['width']=2; plot.apply_style(style); assert plot.curves[0].peaks==saved
dialog.show_marks.setChecked(False); assert not plot.curves[0].peaks and plot.curves[0].points==[0]
dialog.show_marks.setChecked(True); assert plot.curves[0].peaks==saved
with TemporaryDirectory() as directory:
    path=Path(directory)/'peaks.csv'
    with patch.object(QFileDialog,'getSaveFileName',return_value=(str(path),'CSV')): dialog.export()
    rows=list(csv.reader(path.open(encoding='utf-8-sig'))); assert len(rows)==len(dialog.result.peaks)+1
    original=list(plot.curves[0].peaks); dialog.method.setCurrentIndex(dialog.method.findData('prominence')); dialog.smooth.setChecked(True); dialog.smoothing_window.setValue(4)
    assert not dialog.run() and dialog.error.text() and plot.curves[0].peaks==original
    dialog.smooth.setChecked(False)
    dialog.smoothing_window.setValue(7)
out=Path(__file__).resolve().parents[1]/'output'; dialog.grab().save(str(out/'xrd-peak-dialog.png'))
dialog.error.clear(); dialog.grab().save(str(out/'xrd-peak-dialog.png')); dialog.hide(); page.grab().save(str(out/'xrd-peak-screen.png'))
assert not plot.export_image().isNull()
dialog.clear_marks(); assert not plot.curves[0].peaks and plot.curves[0].points==[0]
afm=XrdPage(Path('afm.txt'),[read_unit_xy('X Unit: nm\nY Unit: Pixel\nX Y\n0 1\n1 2\n2 1')]); afm.show(); app.processEvents()
assert not afm.analysis_toolbar.isVisible()
page.close(); afm.close(); page.deleteLater(); afm.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
print('Peak toolbar, analysis, results, markers, style retention and export passed')
