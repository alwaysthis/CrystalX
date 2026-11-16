"""Checkable visibility popup with a mixed state for individually hidden atoms."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMenu,QCheckBox,QWidgetAction
from .theme import apply_menu_theme

class VisibilityCheck(QCheckBox):
    def nextCheckState(self):
        self.setCheckState(Qt.CheckState.Unchecked if self.checkState()==Qt.CheckState.Checked else Qt.CheckState.Checked)

class VisibilityMenu(QMenu):
    def __init__(self,viewport,parent):
        super().__init__(parent); self.viewport=viewport; self.boxes={}; apply_menu_theme(self)
        for key,text in [('axes_visible','方向轴'),('atoms_visible','原子'),('cell_visible','晶格'),('elements_visible','元素'),('numbers_visible','编号'),('tags_visible','标签')]:
            box=VisibilityCheck(text); box.setStyleSheet('QCheckBox {background:transparent;padding:5px 9px;color:#29352f;} QCheckBox:hover {background:#e8eeeb;}'); box.setCursor(Qt.CursorShape.PointingHandCursor)
            if key=='atoms_visible': box.setTristate(True)
            action=QWidgetAction(self); action.setDefaultWidget(box); self.addAction(action); self.boxes[key]=box
            box.stateChanged.connect(lambda state,key=key:self.change(key,state))
        self.aboutToShow.connect(self.sync)
    def sync(self):
        view=self.viewport
        for key,box in self.boxes.items():
            state=Qt.CheckState.Checked if view.appearance[key] else Qt.CheckState.Unchecked
            if key=='atoms_visible' and getattr(view,'structure',None):
                count=len(view.structure.elements)
                visible=sum(i not in view.hidden and view.object_appearance('atom',i)['atoms_visible'] for i in range(count))
                state=Qt.CheckState.Unchecked if visible==0 else Qt.CheckState.Checked if visible==count else Qt.CheckState.PartiallyChecked
            box.blockSignals(True); box.setCheckState(state); box.blockSignals(False)
    def change(self,key,state):
        visible=state==Qt.CheckState.Checked.value
        if key=='atoms_visible':
            self.viewport.hidden.clear()
            for item in self.viewport.atom_overrides.values(): item.pop('atoms_visible',None)
        if key=='cell_visible':
            for item in self.viewport.edge_overrides.values(): item.pop('cell_visible',None)
        self.viewport.appearance[key]=visible; self.viewport.update(); self.sync()
