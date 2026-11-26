"""Open real or synthetic AFM height-frequency text through the workspace."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PyQt6.QtCore import QEvent,Qt
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from crystalx.ui import MainWindow
from crystalx.session_state import SessionState
from crystalx.xrd_io import read_plot_data
from crystalx.xrd_page import XrdPage
from crystalx.dialogs import QFileDialog,QMessageBox

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
root=Path(__file__).resolve().parents[1]; out=root/'output'
with TemporaryDirectory() as directory:
    directory=Path(directory); synthetic=directory/'arbitrary.txt'
    synthetic.write_text('X Unit:\tNanoMeter\nY Unit:\tPixel\n\nX\tY\n2\t0\t\n1\t5\t\n0\t8\t\n-1\t2\t\n')
    path=Path(sys.argv[1]) if len(sys.argv)>1 else synthetic; scan=read_plot_data(path)[0]
    window=MainWindow({'window_width':1450,'window_height':1000},session_state=SessionState(directory/'session.json')); window.show()
    assert window.load_path(path); page=window.current_page(); assert isinstance(page,XrdPage); app.processEvents()
    plot=page.plot
    assert page.data_kind=='AFM' and plot.template_name=='AFM' and page.kind_label.text()=='AFM高度'
    assert plot.axis_artists['bottom'].get_xlabel()=='Height (nm)'
    assert plot.axis_artists['left'].get_ylabel()=='Pixel count'
    assert 'AFM' in window.statusBar().currentMessage()
    assert plot.curves[0].x==scan.x and plot.curves[0].y==scan.intensity
    assert SessionState(window.session_state.path).directory==str(path.parent.resolve())
    index=max(range(len(scan.x)),key=lambda i:scan.intensity[i]); point=plot.point(scan.x[index],scan.intensity[index])
    QTest.mouseMove(plot.canvas,point.toPoint()); app.processEvents(); assert 'Pixel count' in page.readout.text()
    bounds=plot.bounds; plot.move_bounds(.5,.5,.8); assert plot.bounds!=bounds; plot.reset(); app.processEvents()
    style=plot.open_style(); app.processEvents()
    assert style.fields[('axes','left','label')][1].text()=='Pixel count'; style.reject()
    image=plot.export_image(scale=1); assert not image.isNull() and image.pixelColor(0,0).alpha()==0
    image.save(str(out/'afm-distribution-transparent.png')); page.grab().save(str(out/'afm-distribution-screen.png'))
    for suffix in ('svg','pdf'):
        destination=directory/f'height.{suffix}'
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(destination),suffix)): plot.save_image()
        assert destination.exists() and destination.stat().st_size>100
    previous=window.session_state.directory; bad=directory/'bad.txt'; bad.write_text('X Unit: nm\nY Unit: Pixel\nX Y\n1 nan\n2 3')
    with patch.object(QMessageBox,'warning'): assert not window.load_path(bad)
    assert window.session_state.directory==previous
    assert window.load_path(root/'examples/Si.vasp'); structure=window.current_page()
    window.work_tabs.setCurrentWidget(page); assert not window.buttons['保存'].isEnabled()
    assert window.close_tab(window.work_tabs.indexOf(page)); assert window.current_page() is structure
    print('AFM actual data:',path.name,'points:',len(scan.x),'height:',min(scan.x),max(scan.x),'pixels:',sum(scan.intensity))
    window.close(); window.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
print('AFM parsing, units, plotting, interactions, exports and mixed workspace passed')
