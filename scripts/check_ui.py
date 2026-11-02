"""Offscreen integration checks for data panels, coordinate navigation and edits."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase,QFont
from crystalx.ui import MainWindow
from crystalx import operations
app=QApplication([])
for font in ['C:/Windows/Fonts/segoeui.ttf','C:/Windows/Fonts/msyh.ttc']: QFontDatabase.addApplicationFont(font)
app.setFont(QFont('Microsoft YaHei',10))
window=MainWindow({'window_width':1500,'window_height':1000})
assert window.load_path(Path(__file__).resolve().parents[1]/'examples/Si.vasp')
window.show(); app.processEvents()
assert window.viewport.mode=="rotate"
item=window.atom_list.topLevelItem(0); item.setExpanded(True)
assert item.child(0).data(0,Qt.ItemDataRole.UserRole).count('\n')==1
assert '0.000' in item.child(0).data(0,Qt.ItemDataRole.UserRole)
window.atom_list.setCurrentItem(window.atom_list.topLevelItem(1))
assert not window.selected
button=window.atom_list.itemWidget(item,4)
button.click(); assert not item.isExpanded()
button.click(); assert item.isExpanded()
window.atom_list.itemWidget(item,3).click(); assert window.selected=={0}
window.clear_selection()
window.show_coordinates(); app.processEvents()
window.coordinate_dialog.resize(800,230)
window.run_operation(operations.supercell,[4,2,1],clear_selection=True)
app.processEvents()
dialog=window.coordinate_dialog; table=dialog.table
assert table.rowCount()==64
table.verticalScrollBar().setValue(24); app.processEvents()
scroll=table.verticalScrollBar().value()
dialog.tabs.setCurrentIndex(1); app.processEvents()
assert table.verticalScrollBar().value()==scroll
assert table.item(1,3).text()==f'{window.document.structure.positions[1][0]:.9f}'
window.set_selection({1})
window.translation[0].setValue(.1); window.translate()
assert dialog.table.item(1,3).text()==f'{window.document.structure.positions[1][0]:.9f}'
assert window.atom_list.topLevelItem(0).isExpanded()
window.set_tool('pan'); assert window.viewport.mode=='pan'
# Every preset, including skew direct/reciprocal directions, must remain continuous.
from copy import deepcopy
original=deepcopy(window.document.structure.lattice)
window.document.structure.lattice=[[3,0,0],[1,4,0],[.5,1,5]]
for preset in range(7):
    window.set_view(preset)
    v=window.viewport
    before=[v.camera_point(axis) for axis in [(1,0,0),(0,1,0),(0,0,1)]]
    v.rotate_camera(0,0)
    after=[v.camera_point(axis) for axis in [(1,0,0),(0,1,0),(0,0,1)]]
    assert all(abs(a-b)<1e-12 for row1,row2 in zip(before,after) for a,b in zip(row1,row2))
    v.rotate_camera(.1,0)
    moved=[v.camera_point(axis) for axis in [(1,0,0),(0,1,0),(0,0,1)]]
    assert max(abs(a-b) for row1,row2 in zip(before,moved) for a,b in zip(row1,row2))<.002
    v.rotate_camera(-.1,0)
    restored=[v.camera_point(axis) for axis in [(1,0,0),(0,1,0),(0,0,1)]]
    assert all(abs(a-b)<1e-12 for row1,row2 in zip(before,restored) for a,b in zip(row1,row2))
window.document.structure.lattice=original
window.set_view(3); assert window.viewport.camera is not None
camera=window.viewport.camera
window.fit_view(); assert window.viewport.camera==camera
window.pick(2); window.pick(3); assert window.selected=={3}
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
button=window.atom_list.itemWidget(window.atom_list.topLevelItem(2),3)
QTest.mouseClick(button,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.ControlModifier)
assert window.selected=={2,3}
window.clear_selection(); assert not window.selected
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt,QPoint
window.set_tool('pan')
point=window.viewport.project(window.viewport.atoms[0])[0].toPoint()
QTest.mouseDClick(window.viewport,Qt.MouseButton.LeftButton,pos=point)
assert window.selected
window.clear_selection()
window.set_tool('select')
QTest.mousePress(window.viewport,Qt.MouseButton.LeftButton,pos=QPoint(45,45))
QTest.mouseMove(window.viewport,QPoint(window.viewport.width()-10,window.viewport.height()-10))
QTest.mouseRelease(window.viewport,Qt.MouseButton.LeftButton,pos=QPoint(window.viewport.width()-10,window.viewport.height()-10))
assert window.selected
window.clear_selection(); window.set_tool('rotate')
window.pick(1)
QTest.mouseClick(window.viewport,Qt.MouseButton.LeftButton,pos=QPoint(window.viewport.width()-8,10))
QTest.qWait(QApplication.doubleClickInterval()+40)
assert not window.selected
window.undo(); window.undo(); assert not window.document.dirty
window.viewport.zoom=2; window.viewport.pan=QPoint(20,20)
window.reset_view()
assert window.viewport.camera is None and window.viewport.zoom==1 and window.viewport.pan.x()==0
assert window.windowTitle()=='CrystalX'
assert window.file_menu_bar.actions()[0].text()=='文件'
assert len(window.viewport.atoms)>len(window.document.structure.elements)
assert window.title_bar.undo_button is window.buttons['撤销']
for button in [window.title_bar.minimize,window.title_bar.maximize,window.title_bar.close_button]:
    assert button.isVisible() and not button.icon().isNull()
    pixels=button.icon().pixmap(18,18).toImage()
    assert any(pixels.pixelColor(x,y).alpha()>0 for x in range(18) for y in range(18))
window.title_bar.minimize.click(); app.processEvents(); assert window.isMinimized()
window.showNormal(); app.processEvents()
window.title_bar.toggle_maximize(); app.processEvents(); assert window.isMaximized()
window.title_bar.toggle_maximize(); app.processEvents(); assert not window.isMaximized()
dialog.hide()
app.processEvents()
output=Path(__file__).resolve().parents[1]/'output'; output.mkdir(exist_ok=True)
assert window.grab().save(str(output/'workspace-preview.png'))
window.close()
print('UI integration checks passed')
