"""XRR-only toolbar, manual/automatic fringe positions, unit handling and CSV."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,traceback,csv
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import numpy as np
from PyQt6.QtCore import QEvent,Qt
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication
from crystalx.xrd_page import XrdPage
from crystalx.xrd_io import XrdScan,read_xrd
from crystalx.dialogs import QFileDialog

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
errors=[]
def report(kind,value,tb): errors.append(value); traceback.print_exception(kind,value,tb)
sys.excepthook=report
root=Path(__file__).resolve().parents[1]; real=len(sys.argv)>1
x=np.linspace(.5,5,6001); q=4*np.pi*np.sin(np.deg2rad(x/2))/1.5406; y=(1+.45*np.cos(q*600))/(x+.1)**4
scan=XrdScan(x.tolist(),y.tolist(),{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega','HW_XG_WAVE_LENGTH_ALPHA1':'1.5406','HW_XG_WAVE_LENGTH_UNIT':'Angstrom'})
scans=read_xrd(sys.argv[1]) if real else [scan]
page=XrdPage(Path('XRR.ras'),scans); page.resize(1400,1000); page.show(); app.processEvents()
assert page.thickness_button.isVisible(); raw=list(page.plot.curves[0].y); bounds=page.plot.bounds
page.thickness_button.click(); app.processEvents(); dialog=page.thickness_dialog
assert dialog.isVisible() and dialog.axis.currentData()=='2theta'
known_q=np.arange(3,10)*2*np.pi/500; known=np.rad2deg(2*np.arcsin(known_q*dialog.wavelength.value()/(4*np.pi)))
dialog.load_rows(known.tolist()); dialog.calculate_button.click(); assert abs(dialog.result.thickness_nm-50)<1e-6
source=page.plot.curves[0]; source.points=[0]; source.peaks=[1]
dialog.show_marks.setChecked(True); assert len(source.thickness_marks)==len(known)
assert len(page.plot.data_axes.thickness_annotations)==len(known)
dialog.table.item(1,0).setCheckState(Qt.CheckState.Unchecked); assert len(source.thickness_marks)==len(known)-1
assert source.points==[0] and source.peaks==[1]
dialog.show_marks.setChecked(False); assert not source.thickness_marks and not page.plot.data_axes.thickness_annotations
assert source.points==[0] and source.peaks==[1]
dialog.consecutive.setChecked(False); dialog.load_rows(known[[0,1,3,4]].tolist())
for row,order in enumerate((1,2,4,5)): dialog.table.item(row,1).setText(str(order))
assert dialog.calculate() and abs(dialog.result.thickness_nm-50)<1e-6
dialog.consecutive.setChecked(True); dialog.load_rows(known.tolist()); dialog.table.item(2,0).setCheckState(Qt.CheckState.Unchecked)
assert dialog.calculate() and dialog.result.thickness_nm<50  # Consecutive mode renumbers the retained peaks.
dialog.load_rows(known.tolist()); dialog.table.item(0,2).setText('bad'); assert not dialog.calculate() and dialog.error.text()
dialog.load_rows(known.tolist()); assert dialog.calculate()
with TemporaryDirectory() as folder:
    path=Path(folder)/'thickness.csv'
    with patch.object(QFileDialog,'getSaveFileName',return_value=(str(path),'')): dialog.export()
    rows=list(csv.reader(path.open(encoding='utf-8-sig'))); assert abs(float(rows[0][1])-50)<1e-6
dialog.minimum.setValue(.9 if real else .7); dialog.maximum.setValue(2.8 if real else 4.8); dialog.detect()
assert dialog.table.rowCount()>3; assert dialog.calculate()
if not real: assert abs(dialog.result.thickness_nm-60)<1
print('Detected fringe count:',dialog.table.rowCount(),'period estimate nm:',dialog.result.thickness_nm)
assert page.plot.curves[0].y==raw and page.plot.bounds==bounds
app.processEvents(); assert dialog.summary.height()>=dialog.summary.minimumSizeHint().height()
dialog.grab().save(str(root/('output/xrr-thickness-real.png' if real else 'output/xrr-thickness-synthetic.png')))
page.selector.setCurrentIndex(0)
other=XrdPage(Path('XRD.ras'),[XrdScan([10,20,30],[1,5,1],{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega'})]); other.show(); app.processEvents(); assert not other.thickness_button.isVisible()
page.close(); other.close(); page.deleteLater(); other.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
assert not errors,errors
print('XRR thickness toolbar, order editing, candidate detection, units, CSV and source isolation passed')
