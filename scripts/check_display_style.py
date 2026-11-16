"""Appearance scope, persistence, previews and picking integration."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont,QFontDatabase,QColor
from PyQt6.QtWidgets import QApplication
from crystalx.ui import MainWindow
from crystalx.appearance import AppearanceStore,FACTORY_STYLE,read_preset
app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
w=MainWindow({'window_width':1500,'window_height':1000}); w.show(); root=Path(__file__).resolve().parents[1]
with TemporaryDirectory() as folder:
    w.appearance_store=AppearanceStore(Path(folder)/'custom/display.json')
    w.load_path(root/'examples/Si.vasp'); a=w.current_page(); w.load_path(root/'examples/Si.vasp'); b=w.current_page(); w.work_tabs.setCurrentWidget(a); app.processEvents()
    a.viewport.open_display_style(); style=a.viewport.style_dialog; app.processEvents()
    style.gloss.setValue(.35); style.refresh_previews(); assert style.previews[1].appearance['gloss']==.35
    style.apply(); assert a.viewport.appearance['gloss']==.35
    assert not style.cell_roughness.isEnabled() and not style.cell_ior.isEnabled()
    style.cell_line.setCurrentIndex(5); style.cell_width.setValue(5); style.cell_roughness.setValue(.65)
    assert style.cell_roughness.isEnabled() and style.cell_gloss.isEnabled()
    style.axes_mode.setCurrentIndex(0); assert not style.axes_ior.isEnabled()
    style.axes_mode.setCurrentIndex(1); style.axes_width.setValue(4); style.apply()
    assert a.viewport.appearance['cell_line']==5 and b.viewport.appearance['cell_line']==0
    # Draft changes update previews only until Apply; Cancel preserves the applied baseline.
    style.cell_width.setValue(9); style.refresh_previews(); assert a.viewport.appearance['cell_width']==5 and style.previews[0].appearance['cell_width']==9
    style.reject(); a.viewport.open_display_style(); style=a.viewport.style_dialog; app.processEvents()
    a.pick(0); style.scope.setCurrentIndex(0)
    from crystalx.render_material import RADII
    from crystalx.ui import ELEMENT_COLORS
    original_radii=deepcopy(RADII); original_colors=deepcopy(ELEMENT_COLORS)
    assert 'atom_color_mode' not in style.fields and style.atom_color.isEnabled() and style.atom_radius.isEnabled()
    assert style.atom_radius_type.count()==3 and abs(style.atom_radius.value()-1.18)<1e-8
    assert style.atom_color.value==QColor.fromRgbF(*ELEMENT_COLORS['Si']).name()
    style.atom_radius_type.setCurrentIndex(1); assert abs(style.atom_radius.value()-.26)<1e-8
    style.atom_radius_type.setCurrentIndex(2); assert abs(style.atom_radius.value()-2.1)<1e-8
    style.atom_radius_type.setCurrentIndex(0)
    style.atom_color.set_color('#df3b43'); style.atom_radius.setValue(1.36); style.apply()
    assert a.viewport.atom_overrides[0]['atom_radius_type']==3
    assert abs(a.viewport.atom_overrides[0]['atom_radius']-1.36*.42)<1e-10
    assert RADII==original_radii and ELEMENT_COLORS==original_colors
    assert a.viewport.atom_overrides[0]['atom_color']=='#df3b43' and 1 not in a.viewport.atom_overrides
    assert b.viewport.appearance['atom_color_mode']==0
    style.atoms_visible.setChecked(False); style.apply(); a.visibility_menu.sync(); assert a.visibility_menu.boxes['atoms_visible'].checkState()==Qt.CheckState.PartiallyChecked
    a.visibility_menu.boxes['atoms_visible'].nextCheckState(); assert a.viewport.object_appearance('atom',0)['atoms_visible']
    # Pick a bond without atom or cell obstruction, then edit that bond alone.
    a.clear_selection(); a.viewport.appearance.update(atoms_visible=False,cell_visible=False); a.viewport.repaint(); app.processEvents()
    start,end,_,_=a.viewport.bonds[0]; p=(a.viewport.project(start)[0]+a.viewport.project(end)[0])/2
    assert a.viewport.hit_atom(p) and a.viewport.selected_bonds
    chosen=next(iter(a.viewport.selected_bonds)); style.scope.setCurrentIndex(1); style.scope.setCurrentIndex(0); style.bond_line.setCurrentIndex(5); style.bond_color_mode.setCurrentIndex(1); style.bond_color.set_color('#ee3322'); style.bond_color2.set_color('#2244ee'); style.apply()
    assert a.viewport.bond_overrides[chosen]['bond_line']==5
    a.clear_selection(); a.viewport.appearance.update(bonds_visible=False,cell_visible=True); a.viewport.repaint(); app.processEvents()
    i,j=a.viewport.cell_edges[0]; p=(a.viewport.project(a.viewport.corners[i])[0]+a.viewport.project(a.viewport.corners[j])[0])/2
    assert a.viewport.hit_atom(p) and a.viewport.selected_edges
    chosen=next(iter(a.viewport.selected_edges)); style.scope.setCurrentIndex(1); style.scope.setCurrentIndex(0); style.cell_color.set_color('#cd2b79'); style.apply(); assert a.viewport.edge_overrides[chosen]['cell_color']=='#cd2b79'
    # Global application reaches existing and subsequently opened structures.
    style.scope.setCurrentIndex(2); style.cell_width.setValue(3.3); style.bonds_visible.setChecked(True); style.apply()
    assert a.viewport.appearance['cell_width']==3.3 and b.viewport.appearance['cell_width']==3.3
    w.load_path(root/'examples/Si.vasp'); c=w.current_page(); assert c.viewport.appearance['cell_width']==3.3
    w.work_tabs.setCurrentWidget(a); style.show(); style.set_default()
    assert read_preset(w.appearance_store.path)['cell_width']==3.3
    path=Path(folder)/'preset.json'; style.export_to(path); style.cell_width.setValue(1.1); style.load_from(path); assert style.cell_width.value()==3.3
    style.cell_width.setValue(2.2); style.restore_defaults(); assert style.cell_width.value()==3.3
    # All controls/line styles feed actual renderers and previews.
    for index in range(6):
        style.cell_line.setCurrentIndex(index); style.bond_line.setCurrentIndex(index); style.refresh_previews()
        for preview in style.previews: assert not preview.scene_image().isNull()
    style.cell_line.setCurrentIndex(5); style.cell_width.setValue(6); style.cell_gloss.setValue(1.); style.refresh_previews(); app.processEvents()
    for index,name in enumerate(['cell','atoms','bonds']):
        style.tabs.setCurrentIndex(index); app.processEvents(); style.grab().save(str(root/f'output/display-style-{name}-new.png'))
    assert all(not page.document.dirty for page in (a,b,c))
    style.hide(); w.close()
print('Display style checks passed')
