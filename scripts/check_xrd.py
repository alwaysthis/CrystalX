"""Mixed structure/XRD workspace lifecycle and interactive plot checks."""
import os
import sys
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from tempfile import TemporaryDirectory
from PyQt6.QtCore import QPointF,Qt,QEvent
from PyQt6.QtGui import QWheelEvent,QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication
from crystalx.ui import MainWindow
from crystalx.xrd_page import XrdPage
from crystalx.session_state import SessionState

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
root=Path(__file__).resolve().parents[1]
with TemporaryDirectory() as directory:
    p=Path(directory)/'example.ras'
    rows='\n'.join(f'{10+i*.01:.2f} {100+5000/(1+((i-300)/8)**2):.6f} 1' for i in range(1001))
    p.write_text('*RAS_HEADER_START\n*MEAS_DATA_COUNT "1001"\n*RAS_HEADER_END\n*RAS_INT_START\n'+rows+'\n*RAS_INT_END\n')
    w=MainWindow({'window_width':1400,'window_height':950},session_state=SessionState(Path(directory)/'session.json')); w.show()
    assert w.load_path(root/'examples/Si.vasp'); structure=w.current_page()
    assert w.load_path(p); page=w.current_page(); assert isinstance(page,XrdPage)
    app.processEvents(); assert not w.buttons['保存'].isEnabled(); assert not w.buttons['撤销'].isEnabled()
    assert w.undo() is None; assert not w.call_page('show_coordinates')
    bounds=page.plot.bounds
    pos=page.plot.area().center()
    from PyQt6.QtCore import QPoint
    event=QWheelEvent(pos,pos,QPoint(),QPoint(0,120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
    page.plot.wheelEvent(event); assert page.plot.bounds!=bounds
    page.plot.reset(); assert page.plot.bounds==bounds
    page.set_log(True); assert page.plot.logarithmic
    page.set_log(False); app.processEvents()
    physical=page.plot.canvas.get_width_height(physical=True)
    ratio=page.plot.canvas.device_pixel_ratio
    assert abs(physical[0]-page.plot.width()*ratio)<=1
    assert abs(physical[1]-page.plot.height()*ratio)<=1
    assert page.plot.area().width()>page.plot.width()*.85
    assert page.plot.area().height()>page.plot.height()*.80
    # Screen interior is white; exports retain transparency inside and outside.
    area=page.plot.area(); sample=QPointF(area.left()+area.width()*.75,area.top()+area.height()*.2).toPoint()
    assert page.plot.grab().toImage().pixelColor(sample).name()=='#ffffff'
    before=page.plot.export_image(scale=1)
    assert before.pixelColor(0,0).alpha()==0 and before.pixelColor(sample).alpha()==0
    assert any(before.pixelColor(x,y).alpha()>0 for x in range(before.width()) for y in [round(area.bottom())])
    page.plot.toolbar.reveal(); after=page.plot.export_image(scale=1)
    assert before==after  # Hover tools are absent from exported artwork.
    page.plot.toolbar.copy_image(); assert app.clipboard().image().pixelColor(0,0).alpha()==0
    from unittest.mock import patch
    from crystalx.xrd_page import QFileDialog
    png=Path(directory)/'export.png'
    with patch.object(QFileDialog,'getSaveFileName',return_value=(str(png),'PNG')): page.plot.save_image()
    from PyQt6.QtGui import QImage
    saved=QImage(str(png)); assert not saved.isNull() and saved.pixelColor(0,0).alpha()==0
    page.plot.set_curve_visible(False); assert page.plot.export_image(scale=1)!=before
    page.plot.set_curve_visible(True)
    (root/'output').mkdir(exist_ok=True); page.grab().save(str(root/'output/xrd-preview.png'))
    w.work_tabs.setCurrentWidget(structure); structure.viewport.open_display_style()
    dialog=structure.viewport.style_dialog; dialog.scope.setCurrentIndex(2); dialog.cell_width.setValue(2); assert dialog.apply()
    assert w.buttons['保存'].isEnabled()
    dialog.hide(); assert w.close_tab(w.work_tabs.indexOf(page)); assert w.current_page() is structure
    w.close()
print('XRD and mixed workspace checks passed')

if len(sys.argv)>1:
    path=Path(sys.argv[1]); window=MainWindow({'window_width':1400,'window_height':950},session_state=SessionState(root/f'output/xrd-test-session-{os.getpid()}.json')); window.show()
    assert window.load_path(path); page=window.current_page(); app.processEvents()
    for logarithmic,name in [(False,'linear'),(True,'log')]:
        page.set_log(logarithmic); app.processEvents()
        page.plot.toolbar.reveal()
        assert page.grab().save(str(root/f'output/xrd-real-{name}.png'))
        assert page.plot.export_image().save(str(root/f'output/xrd-real-{name}-transparent.png'))
    print('Actual file:',path.name,'scans:',len(page.scans),'points:',sum(len(s.x) for s in page.scans))
    window.close()
    window.deleteLater()
w.deleteLater()
QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
app.processEvents()
