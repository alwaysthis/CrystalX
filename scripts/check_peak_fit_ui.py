"""Verify model fits, fitted markers, CSV and smooth render on a noisy broad peak."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,traceback,csv
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication
from crystalx.xrd_page import XrdPage
from crystalx.xrd_io import XrdScan,read_xrd
from crystalx.peak_fit import profile
from crystalx.dialogs import QFileDialog
from crystalx.plot_curves import PlotCurve

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
errors=[]
def report(kind,value,tb): errors.append(value); traceback.print_exception(kind,value,tb)
sys.excepthook=report
real=len(sys.argv)>1; root=Path(__file__).resolve().parents[1]
x=np.linspace(19,25,1201); truth=10+profile(x,5000,22.21,.75,.60,.4); rng=np.random.default_rng(12)
y=truth+rng.normal(0,np.sqrt(truth)*1.5)
scans=read_xrd(sys.argv[1]) if real else [XrdScan(x.tolist(),y.tolist(),{'MEAS_SCAN_AXIS_X_INTERNAL':'Omega'})]
page=XrdPage(Path('broad-peak.ras'),scans); page.resize(1400,950); page.show(); app.processEvents()
plot=page.plot; raw=list(plot.curves[0].y); dialog=page.open_peak_finding(run=True); app.processEvents()
assert dialog.method.currentData()=='fit' and dialog.fit_model.currentData()=='split_pv'
assert dialog.result and len(dialog.result.peaks)==1,dialog.error.text()
peak=dialog.result.peaks[0]; assert abs(peak.x-22.21)<.03 and peak.r2>.97
assert dialog.show_smooth.text()=='显示峰拟合曲线' and not dialog.smooth.isEnabled()
assert 'R²' in dialog.table.horizontalHeaderItem(4).text()
assert plot.curves[0].peak_position(peak.index)==(peak.x,peak.fitted_y)
assert abs(float(dialog.table.item(0,5).text())-peak.fwhm)<1e-7
fit=next(curve for curve in plot.curves if curve.role=='fit')
assert plot.curves[0].y==raw and fit.visible and len(fit.x)>len(raw)
result=dialog.result; dialog.show_smooth.setChecked(False); assert not fit.visible
dialog.show_smooth.setChecked(True); assert dialog.result is result and fit.visible
dialog.show_contours.setChecked(True); assert plot.curves[0].peak_analysis['contours']
with TemporaryDirectory() as folder:
    path=Path(folder)/'fit.csv'
    with patch.object(QFileDialog,'getSaveFileName',return_value=(str(path),'')): dialog.export()
    rows=list(csv.reader(path.open(encoding='utf-8-sig'))); assert 'R²' in rows[0][3]
    assert abs(float(rows[1][0])-peak.x)<1e-6 and abs(float(rows[1][-1])-peak.fwhm)<1e-7
copied=PlotCurve.from_clipboard(plot.curves[0].clipboard(plot.style['general'])); assert copied.peak_position(peak.index)==(peak.x,peak.fitted_y)
plot.set_legend_label(0,r'$O_2$ annealed at $800^{\circ}\mathrm{C}$ for 30min')
plot.set_axis_scale('left','linear'); plot.bounds=(peak.x-peak.fwhm*5,peak.x+peak.fwhm*5,min(raw),max(raw)*1.1); plot.rebuild(); app.processEvents()
suffix='real' if real else 'synthetic'; dialog.grab().save(str(root/f'output/peak-fit-dialog-{suffix}.png'))
dialog.hide(); plot.select_curve(None); page.grab().save(str(root/f'output/peak-fit-{suffix}.png')); assert not plot.export_image().isNull()
print('Model peak:',peak.x,'FWHM:',peak.fwhm,'R2:',peak.r2)
page.close(); page.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
assert not errors,errors
print('Broad peak model fitting, marker alignment, CSV, clipboard and smooth render passed')
