import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from tempfile import TemporaryDirectory
from PyQt6.QtCore import Qt,QPoint,QEvent
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from crystalx.xrd_page import XrdPage
from crystalx.curve_data import XYScan
from crystalx.plot_document import write_document,read_document
app=QApplication([])
page=XrdPage(Path('test.xy'),[XYScan([1,2,3],[3,1,5])]);page.resize(1100,800);page.show();app.processEvents()
plot=page.plot; grip=page.plot_host.grip; bounds=plot.bounds; original=list(plot.curves[0].y)
dialog=plot.open_style();app.processEvents()
grip.setFocus(); position=QPoint(8,8)
QTest.mousePress(grip,Qt.MouseButton.LeftButton,pos=position)
QTest.mouseMove(grip,position+QPoint(-250,0));QTest.mouseRelease(grip,Qt.MouseButton.LeftButton,pos=position+QPoint(-250,0));app.processEvents()
ratio=float(plot.style['general']['aspect']);assert abs(plot.width()/plot.height()-ratio)<.005
assert dialog.fields[('general','aspect')][1].currentText()==plot.style['general']['aspect']
assert plot.bounds==bounds and plot.curves[0].y==original and plot.can_undo
image=plot.export_image(1);assert abs(image.width()/image.height()-ratio)<.005
with TemporaryDirectory() as folder:
    target=Path(folder)/'ratio.cxplot';write_document(target,page)
    assert read_document(target)[1][0]['style']['general']['aspect']==plot.style['general']['aspect']
page.undo();assert plot.style['general']['aspect']=='auto'
page.redo();assert abs(float(plot.style['general']['aspect'])-ratio)<1e-7
QTest.mouseDClick(grip,Qt.MouseButton.LeftButton,pos=position);app.processEvents();assert plot.style['general']['aspect']=='auto'
assert plot.geometry()==page.plot_host.rect()
page.close();page.deleteLater();QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
print('Drag ratio, style field sync, undo/redo, export, document persistence and auto reset passed')
