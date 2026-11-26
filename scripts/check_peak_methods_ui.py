"""Actual method switches and independent peak overlays, with optional real RAS."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,traceback
from pathlib import Path
from copy import deepcopy
import numpy as np
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication
from crystalx.xrd_page import XrdPage
from crystalx.xrd_io import XrdScan,read_xrd
from crystalx.plot_curves import PlotCurve

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
errors=[]
def report(kind,value,tb): errors.append(value); traceback.print_exception(kind,value,tb)
sys.excepthook=report
root=Path(__file__).resolve().parents[1]; real=len(sys.argv)>1
x=np.linspace(10,50,4001); y=10+100*np.exp(-.5*((x-20)/.08)**2)+60*np.exp(-.5*((x-35)/.12)**2)
scans=read_xrd(sys.argv[1]) if real else [XrdScan(x.tolist(),y.tolist(),{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega'})]
page=XrdPage(Path('sample.ras'),scans); page.resize(1500,1000); page.show(); app.processEvents(); plot=page.plot
raw=list(plot.curves[0].y); dialog=page.open_peak_finding(); dialog.prominence.setValue(200 if real else 5)
for index in range(dialog.method.count()):
    dialog.method.setCurrentIndex(index); assert dialog.run(),dialog.error.text(); assert dialog.result.peaks
    if not real: np.testing.assert_allclose([p.x for p in dialog.result.peaks],[20,35],atol=.011)
    print(dialog.method.currentText(),len(dialog.result.peaks),'candidates')
dialog.method.setCurrentIndex(0); assert dialog.run()
dialog.show_contours.setChecked(True); assert plot.curves[0].peak_analysis['contours']
dialog.show_smooth.setChecked(True); assert dialog.smooth.isChecked() and any(c.role=='smooth' and c.visible for c in plot.curves)
dialog.show_marks.setChecked(False); assert not plot.curves[0].peaks and plot.curves[0].peak_analysis['contours']
assert len(plot.data_axes.get_legend().get_texts())==sum(c.visible and c.legend_visible for c in plot.curves)
saved=deepcopy(plot.curves[0].peak_analysis); style=deepcopy(plot.style); style['general']['width']=1.5; plot.apply_style(style)
assert plot.curves[0].peak_analysis==saved and plot.curves[0].y==raw
copy=PlotCurve.from_clipboard(plot.curves[0].clipboard(plot.style['general'])); assert copy.peak_analysis==saved
dialog.show_smooth.setChecked(False); assert not any(c.role=='smooth' and c.visible for c in plot.curves) and plot.curves[0].peak_analysis['contours']
dialog.show_contours.setChecked(False); assert not plot.curves[0].peak_analysis['contours']
dialog.show_marks.setChecked(True); dialog.show_contours.setChecked(True); dialog.show_smooth.setChecked(True)
dialog.hide(); page.background_more.click(); app.processEvents(); background=page.background_dialog
assert background.isVisible() and background.method.count()==4
background.method.setCurrentIndex(background.method.findData('auto')); background.apply_button.click(); app.processEvents()
assert page.background_fit.isChecked() and plot.curves[0].background and plot.curves[0].y==raw
if real:
    fitted=np.array(plot.curves[0].background); assert np.all(fitted>=0) and np.max(fitted)<2
    print('Actual RAS baseline range:',fitted.min(),fitted.max())
background.hide(); page.background_subtract.click(); assert not plot.curves[0].peak_analysis and dialog.result is None
assert dialog.run(); assert plot.curves[0].peak_analysis['contours'] and any(c.role=='smooth' and c.visible for c in plot.curves)
saved=deepcopy(plot.curves[0].peak_analysis); page.background_fit.click(); assert plot.curves[0].peak_analysis==saved
page.background_subtract.click(); np.testing.assert_array_equal(plot.curves[0].display_y,raw)
assert dialog.run(); app.processEvents()
suffix='real' if real else 'synthetic'; dialog.show(); dialog.grab().save(str(root/f'output/peak-methods-{suffix}.png'))
dialog.hide(); plot.select_curve(None); page.grab().save(str(root/f'output/peak-overlays-{suffix}.png')); assert not plot.export_image().isNull()
dialog.clear_marks(); assert not plot.curves[0].peaks and not plot.curves[0].peak_analysis
page.close(); page.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
assert not errors,errors
print('Method switching, independent peak outlines/smoothing, baseline settings, raw data and exports passed')
