"""Instrument units, native round trips and qz thickness without double scaling."""
import os,sys,hashlib
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtCore import QEvent
from crystalx.xrd_page import XrdPage
from crystalx.xrd_io import read_xrd
from crystalx.plot_units import prepare_scan
from crystalx.plot_document import read_document,write_document

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
for argument in sys.argv[1:]:
    path=Path(argument); checksum=hashlib.sha256(path.read_bytes()).hexdigest()
    if path.suffix=='.cxplot': scans,states,active,name=read_document(path)
    else: scans=read_xrd(path); states=None
    original=deepcopy(scans)
    page=XrdPage(path,scans)
    if states is not None: page.restore_document(states,active,name)
    page.resize(1400,950); page.show(); app.processEvents(); plot=page.plot
    expected=prepare_scan(scans[0])
    np.testing.assert_allclose(plot.curves[0].x,expected.x)
    np.testing.assert_allclose(plot.curves[0].y,expected.intensity)
    if scans[0].template_name=='XRR':
        assert plot.display_scan.axis_label==r'$q_z$ (Å$^{-1}$)'
        dialog=page.open_thickness(); assert dialog.axis.currentData()=='q_a'
        orders=np.arange(3,10); q=orders*2*np.pi/500
        dialog.load_rows(q.tolist()); assert dialog.calculate(); assert abs(dialog.result.thickness_nm-50)<1e-6
    else: assert plot.display_scan.y_label=='Intensity (counts/s)'
    info=page.open_file_info(); assert info.table.rowCount()>3; info.close()
    with TemporaryDirectory() as directory:
        saved=Path(directory)/'units.cxplot'; write_document(saved,page)
        s,states,active,name=read_document(saved)
        assert states[active]['curves']==plot.curves
        second=XrdPage(saved,s); second.restore_document(states,active,name); second.show(); app.processEvents()
        assert second.plot.curves==plot.curves
        second.close(); second.deleteLater()
    assert scans==original and hashlib.sha256(path.read_bytes()).hexdigest()==checksum
    page.grab().save(str(Path('output')/('units-'+scans[0].template_name.replace(' ','-')+'.png')))
    page.close(); page.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
    print(path.name,'units, raw data, file information and native round-trip passed')
