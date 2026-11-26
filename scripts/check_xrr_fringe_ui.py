"""Shared XRR detection and uncertainty on actual RAS/RASX files."""
import os,sys,hashlib
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtCore import Qt,QEvent
from crystalx.xrd_io import read_xrd
from crystalx.xrd_page import XrdPage
from crystalx.plot_document import write_document,read_document
app=QApplication([]);QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc');app.setFont(QFont('Microsoft YaHei',10))
for name in sys.argv[1:]:
    path=Path(name); before=hashlib.sha256(path.read_bytes()).hexdigest()
    page=XrdPage(path,read_xrd(path));page.resize(1500,950);page.show();app.processEvents()
    source=page.plot.curves[0]; raw=list(source.y)
    dialog=page.open_peak_finding(run=True);app.processEvents()
    assert dialog.method.currentData()=='fringe' and dialog.table.columnCount()==8
    assert not dialog.smooth.isEnabled() and not dialog.fit_model.isEnabled()
    reliable=[p.x for p in dialog.result.peaks if p.status=='可靠']
    assert len(reliable)>=3,(name,dialog.summary.text())
    assert all(p.fwhm is None for p in dialog.result.peaks)
    thickness=page.open_thickness();thickness.detect();app.processEvents()
    selected=[float(thickness.table.item(row,2).text()) for row in range(thickness.table.rowCount()) if thickness.table.item(row,0).checkState()==Qt.CheckState.Checked]
    np.testing.assert_allclose(reliable,selected,atol=1e-9)
    assert thickness.table.columnCount()==5 and source.y==raw
    print(path.parent.name,'reliable',len(reliable),'candidates',len(dialog.result.peaks),'period',dialog.result.overlays['period'])
    dialog.grab().save(str(Path('output')/('fringe-'+path.parent.name+'.png')))
    thickness.grab().save(str(Path('output')/('fringe-thickness-'+path.parent.name+'.png')))
    with TemporaryDirectory() as directory:
        saved=Path(directory)/'fringe.cxplot';write_document(saved,page)
        assert read_document(saved)[1][0]['curves']==page.plot.curves
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    page.close();page.deleteLater();QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
print('XRR default, shared entry points, pending exclusions, annotations and document round-trip passed')
