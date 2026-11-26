"""Background correction, FWHM output and direct inherited color controls."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,traceback,csv
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QFont,QFontDatabase,QColor
from PyQt6.QtWidgets import QApplication,QComboBox
from crystalx.xrd_page import XrdPage
from crystalx.xrd_io import XrdScan
from crystalx.plot_curves import PlotCurve
from crystalx.dialogs import QColorDialog,QFileDialog
from crystalx.plot_presets import read_plot_config

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
errors=[]
def report(kind,value,tb): errors.append(value); traceback.print_exception(kind,value,tb)
sys.excepthook=report
root=Path(__file__).resolve().parents[1]
for path in (root/'config/default/plot-templates').glob('*.json'):
    assert read_plot_config(path)[0]['general']['size']==25,path
x=np.linspace(10,50,2001); raw=10+.5*x+100*np.exp(-.5*((x-20)/.08)**2)+60*np.exp(-.5*((x-35)/.12)**2)
scans=[XrdScan(x.tolist(),raw.tolist(),{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega'}),XrdScan(x.tolist(),(raw*2).tolist(),{'MEAS_SCAN_AXIS_X_INTERNAL':'Omega'})]
page=XrdPage(Path('sample.ras'),scans); page.resize(1400,950); page.show(); app.processEvents()
plot=page.plot; assert page.background_fit.isVisible() and page.background_subtract.isVisible()
page.background_fit.click(); app.processEvents()
curve=plot.curves[0]; assert curve.show_background and len(curve.background)==len(x) and curve.y==raw.tolist()
assert np.max(np.abs(np.array(curve.background)-(10+.5*x)))<.05
page.background_subtract.click(); app.processEvents()
assert curve.subtract_background
np.testing.assert_allclose(plot.data_axes.curve_artists[0].get_ydata(),raw-curve.background)
np.testing.assert_allclose(curve.y,raw)
dialog=page.open_peak_finding(); dialog.prominence.setValue(2); assert dialog.run(); app.processEvents()
assert dialog.table.columnCount()==6 and len(dialog.result.peaks)==2
np.testing.assert_allclose([p.fwhm for p in dialog.result.peaks],2*np.sqrt(2*np.log(2))*np.array([.08,.12]),atol=.002)
for peak in dialog.result.peaks: assert peak.intensity==raw[peak.index]
with TemporaryDirectory() as folder:
    path=Path(folder)/'peaks.csv'
    with patch.object(QFileDialog,'getSaveFileName',return_value=(str(path),'')): dialog.export()
    rows=list(csv.reader(path.open(encoding='utf-8-sig'))); assert len(rows[0])==5 and 'FWHM' in rows[0][-1]
dialog.hide(); styles=plot.open_style(section='curve'); app.processEvents()
color=styles.fields[('curve','color')][1]; color.set_color('')
assert color.value=='' and color.width()==28 and not color.findChildren(QComboBox)
with patch.object(QColorDialog,'getColor',return_value=QColor('#332288')): color.click()
assert color.value=='#332288' and styles.apply(),styles.error.text()
assert plot.curves[0].subtract_background and plot.curves[0].background==curve.background
assert plot.data_axes.curve_artists[0].get_color()=='#332288'
assert styles.fields[('legend','font')][1].family()==''
assert styles.fields[('curve','width')][1].specialValueText()==' '
styles.grab().save(str(root/'output/direct-plot-colors.png')); styles.hide()
copy=PlotCurve.from_clipboard(plot.curves[0].clipboard(plot.style['general'])); np.testing.assert_allclose(copy.display_y,plot.curves[0].display_y)
page.selector.setCurrentIndex(1); app.processEvents(); assert not page.background_fit.isChecked() and not page.background_subtract.isChecked()
page.selector.setCurrentIndex(0); app.processEvents(); assert page.background_fit.isChecked() and page.background_subtract.isChecked()
page.background_subtract.click(); app.processEvents(); np.testing.assert_allclose(plot.data_axes.curve_artists[0].get_ydata(),raw)
plot.add_scan(scans[1]); app.processEvents(); assert not page.background_subtract.isChecked()
plot.select_curve(0); assert page.background_fit.isChecked()
page.background_subtract.click(); page.grab().save(str(root/'output/background-corrected.png'))
assert not plot.export_image().isNull()
page.close(); page.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
assert not errors,errors
print('25pt templates, direct color picking, reversible background, FWHM/CSV and scan isolation passed')
