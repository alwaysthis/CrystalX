"""Read-only verification of low-count rocking curves in a supplied cxplot."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtCore import QEvent
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from crystalx.plot_document import read_document,write_document
from crystalx.xrd_page import XrdPage

path=Path(sys.argv[1]); before=hashlib.sha256(path.read_bytes()).hexdigest()
scans,states,active,name=read_document(path)
app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
page=XrdPage(path,scans); page.restore_document(states,active,name); page.resize(1400,950); page.show(); app.processEvents()
sources=[curve.uid for curve in page.plot.curves if curve.role=='data']; figure=Figure(figsize=(11,4.8),dpi=150); FigureCanvasAgg(figure)
axes=figure.subplots(1,len(sources),squeeze=False)[0]
for number,(uid,axis) in enumerate(zip(sources,axes)):
    index=next(i for i,curve in enumerate(page.plot.curves) if curve.uid==uid)
    curve=page.plot.curves[index]; original=list(curve.y); page.plot.select_curve(index)
    dialog=page.open_peak_finding(run=True); app.processEvents()
    assert len(dialog.result.peaks)==1,dialog.error.text()
    peak=dialog.result.peaks[0]; assert peak.r2<.65 and 'R²' in dialog.summary.text()
    dialog.show_smooth.setChecked(True)
    fitted=next(c for c in page.plot.curves if c.source_id==uid and c.role=='fit')
    assert fitted.visible and curve.y==original
    print(number,'center',peak.x,'FWHM',peak.fwhm,'raw R2',peak.r2)
    axis.plot(curve.x,curve.y,color='#8c8c8c',linewidth=.5,label='Raw data')
    axis.plot(fitted.x,fitted.y,color='#d55e00',linewidth=1.5,label='Raw-data profile fit')
    axis.set(xlabel='Omega (deg)',ylabel='Intensity (counts)',title=f'Curve {number+1}')
    axis.text(.04,.93,f'Center = {peak.x:.4f}°\nFWHM = {peak.fwhm:.4f}°\nRaw R² = {peak.r2:.3f}',transform=axis.transAxes,va='top')
    axis.legend(loc='upper right',frameon=False,fontsize=8)
    dialog.hide()
figure.tight_layout(); figure.savefig(Path(__file__).resolve().parents[1]/'output/rc-low-count-fit.png')
with TemporaryDirectory() as folder:
    target=Path(folder)/'verified.cxplot'; write_document(target,page); restored=read_document(target)[1]
    assert restored[active]['curves']==page.plot.curves
assert hashlib.sha256(path.read_bytes()).hexdigest()==before
page.close(); page.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
print('Actual low-count curves, UI warning, independent fit curves, round-trip and unmodified input verified')
