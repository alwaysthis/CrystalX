"""Element-pair bond search rules, independent of rendering appearance."""
from itertools import combinations_with_replacement
import math
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QWidget,QLabel,
    QTableWidget,QTableWidgetItem,QHeaderView,QPushButton)
from .bonds import pair_key
from .dialog_chrome import install_dialog_chrome
from .dialogs import QMessageBox


from .math_ui import MathLabel as QLabel, MathPushButton as QPushButton, MathTableWidget as QTableWidget

class BondEditor(QDialog):
    def __init__(self,viewport,parent):
        super().__init__(parent); self.viewport=viewport
        self.setWindowTitle('键编辑'); self.resize(590,430)
        layout=QVBoxLayout(self)
        surface=QWidget(); surface.setObjectName('bondEditorSurface')
        surface.setStyleSheet('QWidget#bondEditorSurface {background:white;border:1px solid #d4e0d9;border-radius:8px;}')
        form=QVBoxLayout(surface); form.setContentsMargins(12,12,12,12)
        toolbar=QHBoxLayout()
        for text,callback in [('新建',self.add_rule),('删除',self.delete_rules),('清除',self.clear_rules)]:
            button=QPushButton(text); button.clicked.connect(callback); toolbar.addWidget(button)
        toolbar.addStretch(); form.addLayout(toolbar)
        self.bond_ranges=QTableWidget(0,4); self.bond_ranges.setHorizontalHeaderLabels(['元素 1','元素 2','最小键长','最大键长']); self.bond_ranges.verticalHeader().hide(); self.bond_ranges.setShowGrid(False)
        self.bond_ranges.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bond_ranges.setMinimumHeight(135); form.addWidget(self.bond_ranges)
        layout.addWidget(surface)
        footer=QHBoxLayout(); footer.addStretch()
        apply=QPushButton('应用'); apply.clicked.connect(self.apply); footer.addWidget(apply)
        close=QPushButton('关闭'); close.clicked.connect(self.close); footer.addWidget(close)
        layout.addLayout(footer); install_dialog_chrome(self,layout)
        self.species=None; self.pending=False; self.refresh()
        self.bond_ranges.itemChanged.connect(self.mark_pending)

    def mark_pending(self,*args): self.pending=True

    def refresh(self):
        species=sorted(set(self.viewport.structure.elements)) if self.viewport.lattice else []
        if species==self.species:
            self.filter_rows(); return
        self.species=species; self.edited_pairs=set(); self.bond_ranges.blockSignals(True); self.bond_ranges.setRowCount(0)
        species=sorted(set(self.viewport.structure.elements)) if self.viewport.lattice else []
        for a,b in combinations_with_replacement(species,2):
            bounds=self.viewport.bond_ranges.get(pair_key(a,b),[])
            for low,high in bounds:
                self.insert_rule(a,b,low,high)
                self.edited_pairs.add(pair_key(a,b))
        self.bond_ranges.blockSignals(False); self.pending=False; self.filter_rows()

    def filter_rows(self):
        if self.pending: return
        for row in range(self.bond_ranges.rowCount()):
            try:
                pair=pair_key(*(self.bond_ranges.item(row,col).text().strip() for col in (0,1)))
                low,high=[float(self.bond_ranges.item(row,col).text()) for col in (2,3)]
            except ValueError: continue
            hidden=(pair,low,high) not in self.viewport.matched_bond_ranges
            self.bond_ranges.setRowHidden(row,hidden)
            if hidden:
                for col in range(4): self.bond_ranges.item(row,col).setSelected(False)

    def insert_rule(self,a,b,low=0.,high=3.):
        row=self.bond_ranges.rowCount(); self.bond_ranges.insertRow(row)
        for col,value in enumerate([a,b,str(low),str(high)]):
            item=QTableWidgetItem(value); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.bond_ranges.setItem(row,col,item)
    def add_rule(self):
        if self.species:
            self.insert_rule(self.species[0],self.species[min(1,len(self.species)-1)]); self.bond_ranges.scrollToBottom()
    def delete_rules(self):
        self.pending=True
        for row in sorted({index.row() for index in self.bond_ranges.selectedIndexes()},reverse=True): self.bond_ranges.removeRow(row)
    def clear_rules(self): self.bond_ranges.setRowCount(0); self.pending=True

    def apply(self):
        ranges=dict(self.viewport.bond_ranges)
        for key in self.edited_pairs: ranges[key]=[]
        for row in range(self.bond_ranges.rowCount()):
            key=pair_key(self.bond_ranges.item(row,0).text().strip(),self.bond_ranges.item(row,1).text().strip()); ranges[key]=[]
        try:
            for row in range(self.bond_ranges.rowCount()):
                elements=[self.bond_ranges.item(row,col).text().strip() for col in (0,1)]
                if any(element not in self.species for element in elements): raise ValueError('请选择当前结构中存在的元素')
                key=pair_key(*elements)
                low,high=[float(self.bond_ranges.item(row,col).text()) for col in (2,3)]
                if not all(math.isfinite(v) for v in (low,high)) or not 0<=low<high: raise ValueError('键长范围应满足 0 ≤ 最小值 < 最大值')
                ranges[key].append([low,high])
        except ValueError as error:
            QMessageBox.warning(self,'搜索范围无效',str(error)); return False
        self.edited_pairs.update(pair_key(self.bond_ranges.item(row,0).text().strip(),self.bond_ranges.item(row,1).text().strip()) for row in range(self.bond_ranges.rowCount()))
        self.viewport.bond_ranges=ranges
        if self.viewport.lattice: self.viewport.set_structure(self.viewport.structure)
        self.viewport.update(); self.pending=False; self.filter_rows(); return True
