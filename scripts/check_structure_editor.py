import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from copy import deepcopy
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase,QFont
from crystalx.ui import MainWindow
app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
w=MainWindow({'window_width':1400,'window_height':950}); w.show()
w.load_path(Path(__file__).resolve().parents[1]/'examples/Si.vasp'); page=w.current_page(); editor=page.coordinate_dialog
segments=page.viewport.bond_segments
page.pick(0)
assert page.viewport.bond_segments is segments and len(segments)>0
page.atom_list.setCurrentItem(page.atom_list.topLevelItem(3)); page.show_coordinates(); app.processEvents()
editor.tabs.setCurrentIndex(1); editor.table.selectRow(2)
assert page.selected=={0} and page.atom_list.indexOfTopLevelItem(page.atom_list.currentItem())==3
editor.tabs.setCurrentIndex(0)
original=deepcopy(page.document.structure); editor.parameters[0].setValue(7); editor.stage_lattice()
assert page.document.structure==original and not page.document.dirty
assert abs(page.viewport.structure.lattice[0][0]-7)<1e-8
editor.apply_button.click()
assert page.document.structure.positions==original.positions and page.document.dirty
page.undo(); assert page.document.structure==original
before=page.document.structure.cartesian_positions
editor.matrix[0][1].setValue(1); editor.apply_matrix()
for p,q in zip(before,page.document.structure.cartesian_positions):
    for a,b in zip(p,q): assert abs(a-b)<1e-10
page.undo(); assert page.document.structure==original
page.pick(0); editor.tabs.setCurrentIndex(1); editor.table.item(0,3).setText('0.25'); editor.apply_atoms()
assert abs(page.document.structure.cartesian_positions[0][0]-.25)<1e-9
assert page.selected=={0}
page.undo(); editor.tabs.setCurrentIndex(0); app.processEvents()
editor.parameters[0].setValue(8); editor.stage_lattice(); editor.hide(); app.processEvents()
assert page.document.structure==original and page.viewport.structure==original
editor.show(); editor.tabs.setCurrentIndex(1); app.processEvents()
assert not editor.table.showGrid() and editor.switch.width()<60
editor.grab().save(str(Path(__file__).resolve().parents[1]/'output/structure-editor-atoms.png'))
editor.tabs.setCurrentIndex(0); app.processEvents()
editor.grab().save(str(Path(__file__).resolve().parents[1]/'output/structure-editor.png'))
label=editor.parameters[0].parentWidget().layout().itemAt(0).layout().itemAtPosition(0,0).widget()
assert editor.parameters[0].geometry().left()-label.geometry().right()<10
editor.hide(); page.show_bonds(); app.processEvents()
bond_editor=page.bond_dialog
assert bond_editor.isVisible() and page.viewport.style_dialog is None
assert bond_editor.bond_ranges.columnCount()==4
bond_editor.bond_ranges.item(0,3).setText('2.0'); bond_editor.apply(); assert not page.viewport.bond_segments and bond_editor.bond_ranges.isRowHidden(0)
bond_editor.bond_ranges.item(0,3).setText('2.6'); bond_editor.apply(); assert page.viewport.bond_segments and not bond_editor.bond_ranges.isRowHidden(0)
bond_editor.grab().save(str(Path(__file__).resolve().parents[1]/'output/bond-editor.png'))
# Closing without applying discards draft search changes.
bond_editor.bond_ranges.item(0,3).setText('1.0'); bond_editor.close(); page.show_bonds()
assert page.bond_dialog.bond_ranges.item(0,3).text()=='2.6'
page.viewport.open_display_style(); style=page.viewport.style_dialog; style.tabs.setCurrentIndex(2)
assert not hasattr(style,'bond_ranges')
ranges=deepcopy(page.viewport.bond_ranges)
style.bonds_visible.setChecked(False); style.apply()
assert page.viewport.bond_ranges==ranges and not page.viewport.appearance['bonds_visible']
style.bonds_visible.setChecked(True); style.apply(); app.processEvents()
style.grab().save(str(Path(__file__).resolve().parents[1]/'output/display-style-bonds.png'))
# Switching structures hides both dialogs and each page retains its own rules.
w.load_path(Path(__file__).resolve().parents[1]/'examples/Si.vasp'); app.processEvents()
assert not page.bond_dialog.isVisible() and not style.isVisible()
w.work_tabs.setCurrentWidget(page); style.hide()
page.reset_view(); assert page.viewport.camera_point(page.document.structure.lattice[2])[1]>0
w.showMaximized(); app.processEvents()
assert w.contentsMargins().left()==1 and 'radius:0px' in w.menuWidget().styleSheet()
w.grab().save(str(Path(__file__).resolve().parents[1]/'output/maximized-preview.png'))
w.showNormal(); app.processEvents()
assert w.contentsMargins().left()==15
# Reset fits spheres as well as the cell in wide, tall and oblique structures.
original_lattice=deepcopy(page.document.structure.lattice)
for lattice in [[[18,0,0],[0,2,0],[0,0,2]],[[2,0,0],[0,2,0],[0,0,18]],[[5,0,0],[3,2,0],[2,1,4]]]:
    page.document.structure.lattice=lattice; page.refresh(); app.processEvents(); page.reset_view()
    view=page.viewport
    for index,point in enumerate(view.atoms):
        screen,_=view.project(point); radius=view.atom_radius(index)
        assert screen.x()-radius>=35 and screen.x()+radius<=view.width()-35
        assert screen.y()-radius>=35 and screen.y()+radius<=view.height()-35
    camera=deepcopy(view.camera); view.rotate_camera(0,0)
    for a,b in zip(camera,view.camera):
        for x,y in zip(a,b): assert abs(x-y)<1e-12
page.document.structure.lattice=original_lattice; page.refresh(); page.reset_view()
w.close(); print('Structure editor checks passed')
