"""Visibility, checked-row editing and integer cell previews integration."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from PyQt6.QtCore import Qt,QPoint
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase,QFont
from PyQt6.QtTest import QTest
from crystalx.ui import MainWindow
from crystalx.dialogs import QMessageBox

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
w=MainWindow({'window_width':1500,'window_height':1050}); w.show(); w.load_path(Path(__file__).resolve().parents[1]/'examples/Si.vasp'); app.processEvents()
page=w.current_page(); view=page.viewport; menu=page.visibility_menu
page.document.structure.flags[1]=['F','T','F']; page.refresh(); original=deepcopy(page.document.structure)
assert not view.appearance['elements_visible'] and not view.appearance['numbers_visible'] and not view.appearance['tags_visible']
page.pick(0); assert [a.text() for a in view.context_menu().actions()][-2:]==['隐藏','删除']
view.hide_selected(); menu.sync(); assert view.hidden=={0} and not page.selected
assert menu.boxes['atoms_visible'].checkState()==Qt.CheckState.PartiallyChecked
assert all(not view.atom_visible(i) for i,source in enumerate(view.sources) if source==0)
page.select_all(); view.hide_selected(); menu.sync(); assert menu.boxes['atoms_visible'].checkState()==Qt.CheckState.Unchecked
menu.boxes['atoms_visible'].nextCheckState(); assert not view.hidden and view.appearance['atoms_visible']
for key in ['elements_visible','numbers_visible','tags_visible']: menu.boxes[key].nextCheckState(); assert view.appearance[key]
view.scene_image(); assert page.document.structure==original
# Native checkbox click through the table delegate; selection stays independent.
editor=page.coordinate_dialog; page.show_coordinates(); editor.tabs.setCurrentIndex(1); app.processEvents()
page.pick(2); rect=editor.table.visualItemRect(editor.table.item(0,0)); QTest.mouseClick(editor.table.viewport(),Qt.MouseButton.LeftButton,pos=rect.center())
assert editor.table.item(0,0).checkState()==Qt.CheckState.Checked and page.selected=={2} and not editor.pending
editor.delete_checked(); editor.add_atom(); editor.table.item(editor.table.rowCount()-1,2).setText('O')
editor.apply_current(); assert len(page.document.structure.elements)==8 and page.document.structure.elements[-1]=='O' and page.document.structure.flags[-1]==['T']*3
assert not page.selected and page.document.structure.flags[0]==['F','T','F']
page.undo(); assert page.document.structure==original
editor.all_check.nextCheckState(); assert all(editor.table.item(i,0).checkState()==Qt.CheckState.Checked for i in range(8))
editor.all_check.nextCheckState(); assert all(editor.table.item(i,0).checkState()==Qt.CheckState.Unchecked for i in range(8))
editor.tabs.setCurrentIndex(0); editor.parameters[0].setValue(6.2); editor.stage_lattice(); assert editor.parameters[0].property('pendingEdit')
metric=deepcopy(editor.preview); editor.matrix[0][1].setValue(1); editor.stage_lattice(); app.processEvents()
assert len(editor.comparison.after.layers)==3 and editor.comparison.after.points
assert page.document.structure==original
editor.grab().save('output/lattice-comparison.png')
old=editor.comparison.after.yaw
QTest.mousePress(editor.comparison.after,Qt.MouseButton.LeftButton,pos=QPoint(40,50)); QTest.mouseMove(editor.comparison.after,QPoint(55,55)); QTest.mouseRelease(editor.comparison.after,Qt.MouseButton.LeftButton,pos=QPoint(55,55)); assert editor.comparison.after.yaw!=old
editor.matrix[0][0].setValue(.5); editor.stage_lattice()
with patch.object(QMessageBox,'warning') as warning:
    editor.apply_current(); warning.assert_called_once()
assert page.document.structure==original
editor.matrix[0][0].setValue(1); editor.stage_lattice(); expected=deepcopy(editor.preview.cartesian_positions); editor.apply_current()
for p,q in zip(page.document.structure.cartesian_positions,expected):
    for a,b in zip(p,q): assert abs(a-b)<1e-8
assert not editor.parameters[0].property('pendingEdit'); page.undo(); editor.hide()
# Delete via context action invokes the same undoable structural operation.
page.pick(0)
with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes): view.context_menu().actions()[-1].trigger()
assert len(page.document.structure.elements)==7
page.undo(); assert page.document.structure==original
page.show_bonds(); bond=page.bond_dialog; app.processEvents(); bond.clear_rules(); bond.apply(); assert not view.bond_segments
bond.add_rule(); bond.bond_ranges.item(0,3).setText('2.6'); bond.apply(); assert view.bond_segments
bond.add_rule(); bond.bond_ranges.item(1,2).setText('0'); bond.bond_ranges.item(1,3).setText('2.0'); bond.apply()
assert not bond.bond_ranges.isRowHidden(0) and bond.bond_ranges.isRowHidden(1)
bond.bond_ranges.selectRow(0); bond.delete_rules(); bond.apply(); assert not view.bond_segments
bond.close(); view.open_display_style(); style=view.style_dialog
assert style.color_button.text()=='' and style.bond_color_button.text()==''
style.hide(); menu.popup(page.visibility_button.mapToGlobal(page.visibility_button.rect().bottomLeft())); app.processEvents(); menu.grab().save('output/visibility-menu.png'); menu.hide()
w.close(); print('Visibility and editing checks passed')
