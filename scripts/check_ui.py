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
shell=window
assert shell.work_tabs.count()==0 and shell.terminal.count()==1
shell.show(); app.processEvents()
assert shell.welcome_logo.isVisible()
shell.grab().save(str(Path(__file__).resolve().parents[1]/'output/startup-preview.png'))
assert shell.load_path(Path(__file__).resolve().parents[1]/'examples/Si.vasp')
assert not shell.welcome_logo.isVisible()
window=shell.current_page()
app.processEvents()
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
dialog.tabs.setCurrentIndex(1); dialog.set_mode(1); app.processEvents()
assert table.verticalScrollBar().value()==scroll
assert table.item(1,3).text()==f'{window.document.structure.positions[1][0]:.9f}'
# Editor row selection is independent from viewport and information-list selection.
window.clear_selection(); window.atom_list.setCurrentItem(window.atom_list.topLevelItem(3))
table.selectRow(2); app.processEvents()
assert not window.selected and window.atom_list.indexOfTopLevelItem(window.atom_list.currentItem())==3
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
QTest.mouseDClick(window.viewport,Qt.MouseButton.LeftButton,pos=QPoint(window.viewport.width()-8,10))
from PyQt6.QtCore import QElapsedTimer
wait=QElapsedTimer(); wait.start()
while window.selected and wait.elapsed()<3000: QTest.qWait(25)
assert not window.selected
window.undo(); window.undo(); assert not window.document.dirty
window.viewport.zoom=2; window.viewport.pan=QPoint(20,20)
window.reset_view()
assert window.viewport.camera_point(window.document.structure.lattice[2])[1]>0 and window.viewport.zoom>0 and abs(window.viewport.pan.x())<1e-6
assert shell.windowTitle()=='CrystalX'
assert shell.file_menu_bar.actions()[0].text()=='文件'
assert shell.mask().isEmpty()
assert shell.title_bar.mapTo(shell,QPoint()).x()>0
assert len(window.viewport.atoms)>len(window.document.structure.elements)
assert shell.title_bar.undo_button is window.buttons['撤销']
for button in [shell.title_bar.minimize,shell.title_bar.maximize,shell.title_bar.close_button]:
    assert button.isVisible() and not button.icon().isNull()
    pixels=button.icon().pixmap(18,18).toImage()
    assert any(pixels.pixelColor(x,y).alpha()>0 for x in range(18) for y in range(18))
shell.title_bar.minimize.click(); app.processEvents(); assert shell.isMinimized()
shell.showNormal(); app.processEvents()
shell.title_bar.toggle_maximize(); app.processEvents(); assert shell.isMaximized()
shell.title_bar.toggle_maximize(); app.processEvents(); assert not shell.isMaximized()
assert len(window.view_buttons)==7
window.perspective_slider.setValue(50); assert window.viewport.perspective==.5
window.perspective_slider.setValue(0)
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtCore import QPointF
spin=window.translation[0]; before=spin.value()
event=QWheelEvent(QPointF(5,5),QPointF(5,5),QPoint(),QPoint(0,120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
QApplication.sendEvent(spin,event); assert spin.value()==before
window.pick(0)
window.copy_image(); image=QApplication.clipboard().image()
assert not image.isNull() and image.hasAlphaChannel() and image.pixelColor(0,0).alpha()==0
assert window.atom_list.itemWidget(window.atom_list.topLevelItem(0),3).isChecked()
window.viewport.open_display_style(); app.processEvents()
style=window.viewport.style_dialog
assert style.tabs.count()==3
assert style.windowFlags() & Qt.WindowType.FramelessWindowHint
assert style.mask().isEmpty()
from crystalx.dialogs import QFileDialog as AppFileDialog
from PyQt6.QtWidgets import QFileDialog as NativeFileDialog,QWidget
assert AppFileDialog is NativeFileDialog
assert all(child.mask().isEmpty() for child in style.findChildren(QWidget))

app.processEvents(); style.grab().save(str(Path(__file__).resolve().parents[1]/'output/display-style-preview.png'))
page_rect=style.tabs._stack.geometry()
style.tabs.setCurrentIndex(1); app.processEvents()
assert style.tabs._stack.geometry()==page_rect
style.grab().save(str(Path(__file__).resolve().parents[1]/'output/display-style-atoms.png'))
style.resize(560,430); app.processEvents()
assert style.mask().isEmpty()
style.grab().save(str(Path(__file__).resolve().parents[1]/'output/display-style-resized.png'))
style.tabs.setCurrentIndex(0)

style.cell_visible.setChecked(False); style.radius_scale.setValue(.7); style.apply()
assert not window.viewport.appearance['cell_visible']
assert window.viewport.appearance['radius_scale']==.7
style.cell_visible.setChecked(True); style.radius_scale.setValue(1); style.apply(); style.close()
preview=window.cell_preview
old=(preview.yaw,preview.pitch)
QTest.mousePress(preview,Qt.MouseButton.LeftButton,pos=QPoint(50,40))
QTest.mouseMove(preview,QPoint(60,50)); QTest.mouseRelease(preview,Qt.MouseButton.LeftButton,pos=QPoint(60,50))
assert (preview.yaw,preview.pitch)!=old
dialog.hide()
app.processEvents()
output=Path(__file__).resolve().parents[1]/'output'; output.mkdir(exist_ok=True)
assert shell.grab().save(str(output/'workspace-preview.png'))
shell.close()
print('UI integration checks passed')
