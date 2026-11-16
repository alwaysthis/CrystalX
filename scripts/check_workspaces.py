"""Multi-document lifecycle, terminal layout and independent selection integration."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt,QPoint
from PyQt6.QtTest import QTest
from crystalx.ui import MainWindow
from crystalx.dialogs import QMessageBox

app=QApplication([]); w=MainWindow({'window_width':1440,'window_height':900}); w.show(); app.processEvents()
assert w.work_tabs.count()==0 and w.terminal.isVisible()
assert not w.buttons['撤销'].isEnabled()
for panel in [w.work_panel,w.terminal_panel]:
    assert panel.mask().isEmpty()
    image=panel.grab().toImage()
    assert image.pixelColor(0,0).name()=='#f1f3f2'
    # Both side strokes must remain visible above all content.
    for x in [0,image.width()-1]:
        color=image.pixelColor(x,image.height()//2)
        assert color.green()<235,(x,color.name())

root=Path(__file__).resolve().parents[1]
with TemporaryDirectory() as folder:
    first=Path(folder)/'first.vasp'; second=Path(folder)/'second.vasp'
    first.write_text((root/'examples/Si.vasp').read_text()); second.write_text(first.read_text())
    assert w.load_path(first); a=w.current_page()
    app.processEvents()
    strip=w.work_tabs.grab().toImage()
    assert strip.pixelColor(strip.width()-1,0).name()!='#e3eae5'
    assert strip.pixelColor(strip.width()-20,0).name()=='#e3eae5'
    a.toggle_list_atom(0); a.toggle_list_atom(1); assert a.selected=={0,1}
    a.toggle_list_atom(0); assert a.selected=={1}
    a.atom_list.setCurrentItem(a.atom_list.topLevelItem(3)); assert a.selected=={1}
    a.translation[0].setValue(.1); a.translate(); assert a.document.dirty
    assert w.buttons['撤销'].isEnabled()
    assert w.load_path(second); b=w.current_page()
    assert not b.document.dirty and not b.selected and not w.buttons['撤销'].isEnabled()
    a.viewport.zoom=1.8
    w.work_tabs.tabBar().moveTab(0,1); assert w.work_tabs.indexOf(a)==1
    w.work_tabs.setCurrentWidget(a); assert w.current_page() is a and a.viewport.zoom==1.8
    w.undo(); assert not a.document.dirty and b.document.structure.positions[0][0]==0
    w.redo(); assert a.document.dirty and b.document.structure.positions[0][0]==0
    with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Cancel): assert not w.close_tab(w.work_tabs.indexOf(a))
    assert w.work_tabs.count()==2
    with patch.object(QMessageBox,'question',side_effect=[QMessageBox.StandardButton.Save,QMessageBox.StandardButton.Yes]): assert w.close_tab(w.work_tabs.indexOf(a))
    assert w.work_tabs.count()==1 and first.read_text()!=second.read_text()
    w.maximize_terminal(); assert not w.work_tabs.isVisible() and w.terminal.isVisible()
    w.hide_terminal(); assert w.work_tabs.isVisible() and not w.terminal.isVisible()
    w.show_terminal(); w.maximize_terminal(); w.maximize_terminal(); assert w.work_tabs.isVisible()
    w.work_tabs.setCurrentWidget(b); b.pick(2)
    QTest.mouseClick(b.viewport,Qt.MouseButton.LeftButton,pos=QPoint(b.viewport.width()-5,5)); assert b.selected=={2}
    QTest.mouseDClick(b.viewport,Qt.MouseButton.LeftButton,pos=QPoint(b.viewport.width()-5,5)); assert not b.selected
    assert w.close_tab(0); assert w.work_tabs.count()==0 and w.current_page() is None
    assert w.welcome_logo.isVisible()
w.close(); print('Workspace lifecycle checks passed')
