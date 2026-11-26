"""Independent structure drafts, lattice comparison and checked-row atom editing."""
from copy import deepcopy
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
    QDoubleSpinBox,QPushButton,QTableWidget,QTableWidgetItem,QAbstractItemView,QHeaderView)
from .workspace_tabs import WorkspaceTabs
from .dialog_chrome import install_dialog_chrome
from .dialogs import QMessageBox
from . import lattice_edit
from .document import SnapshotCommand
from .segmented_switch import CoordinateSwitch
from .visibility import VisibilityCheck
from .lattice_comparison import LatticeComparison
from .table_controls import CenteredCheckDelegate

IDENTITY=[[1,0,0],[0,1,0],[0,0,1]]

from .math_ui import MathLabel as QLabel, MathPushButton as QPushButton, MathTableWidget as QTableWidget

class StructureEditor(QDialog):
    def __init__(self,page):
        super().__init__(page); self.page=page; self.snapshot=None; self.mode=0; self.pending=False; self.preview=None; self.staging=False
        self.setWindowTitle('结构编辑'); self.resize(900,700)
        layout=QVBoxLayout(self); self.tabs=WorkspaceTabs(); layout.addWidget(self.tabs)
        cell=QWidget(); cell_layout=QVBoxLayout(cell); grid=QGridLayout(); grid.setHorizontalSpacing(6); grid.setColumnStretch(1,1); grid.setColumnStretch(3,1); self.parameters=[]
        for index,name in enumerate(['a (Å)','b (Å)','c (Å)','α (°)','β (°)','γ (°)']):
            field=QDoubleSpinBox(); field.setDecimals(8); field.setRange(.00000001,100000 if index<3 else 179.99999999)
            field.editingFinished.connect(self.stage_lattice); self.parameters.append(field)
            column=0 if index<3 else 2; row=index%3
            grid.addWidget(QLabel(name),row,column); grid.addWidget(field,row,column+1)
        cell_layout.addLayout(grid); cell_layout.addWidget(QLabel('变换矩阵'))
        grid=QGridLayout(); self.matrix=[]
        for i in range(3):
            row=[]
            for j in range(3):
                field=QDoubleSpinBox(); field.setDecimals(8); field.setRange(-10000,10000); field.setValue(int(i==j)); row.append(field); grid.addWidget(field,i,j); field.editingFinished.connect(self.stage_lattice)
            self.matrix.append(row)
        cell_layout.addLayout(grid); self.error_label=QLabel(); self.error_label.setStyleSheet('color:#b33;background:transparent;'); self.error_label.setWordWrap(True); cell_layout.addWidget(self.error_label)
        self.comparison=LatticeComparison(); cell_layout.addWidget(self.comparison,1); self.tabs.addTab(cell,'晶格')
        atoms=QWidget(); atom_layout=QVBoxLayout(atoms); top=QHBoxLayout()
        self.all_check=VisibilityCheck('全选'); self.all_check.setTristate(True); self.all_check.stateChanged.connect(self.check_all); top.addWidget(self.all_check)
        for text,callback in [('新增',self.add_atom),('删除',self.delete_checked)]:
            button=QPushButton(text); button.clicked.connect(callback); top.addWidget(button)
        top.addStretch(); self.mode_label=QLabel(); top.addWidget(self.mode_label)
        self.switch=CoordinateSwitch(); self.switch.setFixedSize(46,26); self.switch.clicked.connect(lambda:self.set_mode(int(self.switch.isChecked()))); top.addWidget(self.switch); atom_layout.addLayout(top)
        self.table=QTableWidget(0,7); self.table.setItemDelegateForColumn(0,CenteredCheckDelegate(self.table)); self.table.setHorizontalHeaderLabels(['','编号','元素','x','y','z','标签']); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems); self.table.setShowGrid(False)
        self.table.setStyleSheet('QTableWidget::item {border:0;} QTableWidget::item:selected {background:#dce9e1;color:#253d30;}'); self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Fixed); self.table.setColumnWidth(0,30)
        self.table.itemChanged.connect(self.mark_pending); atom_layout.addWidget(self.table); self.tabs.addTab(atoms,'原子')
        footer=QHBoxLayout(); footer.addStretch(); self.apply_button=QPushButton('应用'); self.apply_button.clicked.connect(self.apply_current); footer.addWidget(self.apply_button)
        close=QPushButton('关闭'); close.clicked.connect(self.close); footer.addWidget(close); layout.addLayout(footer); install_dialog_chrome(self,layout); self.update_switch()

    def update_switch(self):
        self.switch.setChecked(self.mode==1); self.mode_label.setText('当前坐标：分数坐标' if self.mode else '当前坐标：笛卡尔坐标')
    def mark_pending(self,item):
        if item.column()==0: self.sync_check_all()
        else: self.pending=True
    def set_mode(self,mode):
        if self.pending:
            QMessageBox.warning(self,'尚未应用','请先应用原子修改，再切换坐标系。'); self.update_switch(); return
        scroll=self.table.verticalScrollBar().value(); self.mode=mode; self.update_switch(); self.fill_atoms(self.preview or self.page.document.structure); self.table.verticalScrollBar().setValue(scroll)
    def put_atom(self,row,element,point,tag,source):
        check=QTableWidgetItem(); check.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable); check.setCheckState(Qt.CheckState.Unchecked); self.table.setItem(row,0,check)
        for col,value in enumerate([str(row+1),element]+[f'{v:.9f}' for v in point]+[tag],1):
            item=QTableWidgetItem(value); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if col==1: item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable); item.setData(Qt.ItemDataRole.UserRole,source)
            self.table.setItem(row,col,item)
    def fill_atoms(self,s):
        selected={(i.row(),i.column()) for i in self.table.selectedIndexes()}; checked={i for i in range(self.table.rowCount()) if self.table.item(i,0) and self.table.item(i,0).checkState()==Qt.CheckState.Checked}
        self.table.blockSignals(True); self.table.setRowCount(len(s.elements)); points=s.positions if self.mode else s.cartesian_positions
        for i,point in enumerate(points):
            self.put_atom(i,s.elements[i],point,s.tags[i],i)
            if i in checked: self.table.item(i,0).setCheckState(Qt.CheckState.Checked)
            for col in range(1,7): self.table.item(i,col).setSelected((i,col) in selected)
        self.table.blockSignals(False); self.pending=False; self.sync_check_all()
    def sync_check_all(self):
        count=sum(self.table.item(i,0).checkState()==Qt.CheckState.Checked for i in range(self.table.rowCount()))
        state=Qt.CheckState.Unchecked if count==0 else (Qt.CheckState.Checked if count==self.table.rowCount() else Qt.CheckState.PartiallyChecked)
        self.all_check.blockSignals(True); self.all_check.setCheckState(state); self.all_check.blockSignals(False)
    def check_all(self,state):
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()): self.table.item(row,0).setCheckState(Qt.CheckState.Checked if state==Qt.CheckState.Checked.value else Qt.CheckState.Unchecked)
        self.table.blockSignals(False); self.sync_check_all()
    def add_atom(self):
        row=self.table.rowCount(); self.table.blockSignals(True); self.table.insertRow(row)
        element=self.page.document.structure.elements[0]; self.put_atom(row,element,[0,0,0],'',None); self.table.blockSignals(False); self.pending=True; self.sync_check_all(); self.table.scrollToBottom()
    def delete_checked(self):
        rows=[i for i in range(self.table.rowCount()) if self.table.item(i,0).checkState()==Qt.CheckState.Checked]
        if not rows: return
        if len(rows)==self.table.rowCount(): QMessageBox.warning(self,'无法删除','请至少保留一个原子。'); return
        self.table.blockSignals(True)
        for row in reversed(rows): self.table.removeRow(row)
        for row in range(self.table.rowCount()): self.table.item(row,1).setText(str(row+1))
        self.table.blockSignals(False); self.pending=True; self.sync_check_all()
    def refresh(self,structure,selected=None):
        if structure is None or self.snapshot==structure: return
        self.preview=None; self.snapshot=deepcopy(structure)
        for i,row in enumerate(self.matrix):
            for j,field in enumerate(row): field.setValue(int(i==j))
        for field,value in zip(self.parameters,lattice_edit.parameters(structure.lattice)): field.setValue(value)
        self.fill_atoms(structure); self.update_pending_fields(); self.update_comparison(structure,structure,False,False)
    def update_pending_fields(self):
        if not self.snapshot: return
        fields=self.parameters+[field for row in self.matrix for field in row]
        baseline=lattice_edit.parameters(self.snapshot.lattice)+[float(v) for row in IDENTITY for v in row]
        for field,value in zip(fields,baseline):
            field.setProperty('pendingEdit',abs(field.value()-value)>1e-7); field.style().unpolish(field); field.style().polish(field); field.update()
    def metric_draft(self):
        draft=deepcopy(self.page.document.structure); values=[f.value() for f in self.parameters]
        changed=any(abs(a-b)>1e-7 for a,b in zip(values,lattice_edit.parameters(draft.lattice)))
        if changed: lattice_edit.set_parameters(draft,values)
        return draft,changed
    def update_comparison(self,metric,final,parameters_changed,matrix_changed):
        self.comparison.set_cells(self.page.document.structure.lattice,metric.lattice,final.lattice,parameters_changed,matrix_changed)
    def lattice_draft(self):
        draft,changed=self.metric_draft(); metric=deepcopy(draft); matrix=[[f.value() for f in row] for row in self.matrix]; matrix_changed=matrix!=IDENTITY
        if matrix_changed: lattice_edit.transform_basis(draft,matrix)
        self.update_comparison(metric,draft,changed,matrix_changed); return draft
    def stage_lattice(self):
        if self.staging: return
        self.update_pending_fields()
        try: draft=self.lattice_draft()
        except ValueError as error:
            self.error_label.setText(str(error)); self.preview=None; return
        self.error_label.clear(); self.preview=draft
        self.page.viewport.set_structure(draft); self.page.cell_preview.lattice=draft.lattice; self.page.cell_preview.update()
        if not self.pending: self.fill_atoms(draft)
    def apply_current(self): self.apply_lattice()
    def apply_lattice(self):
        try:
            draft=self.lattice_draft()
            if self.pending: self.update_atom_draft(draft)
        except (ValueError,RuntimeError) as error: QMessageBox.warning(self,'无法应用',str(error)); return
        topology=[self.table.item(i,1).data(Qt.ItemDataRole.UserRole) for i in range(self.table.rowCount())]!=list(range(len(self.page.document.structure.elements)))
        def replace(structure): structure.__dict__.update(deepcopy(draft.__dict__))
        command=SnapshotCommand(self.page.document.structure,replace)
        self.staging=True
        try:
            if command.before!=command.after: self.page.document.execute(command)
            if topology: self.page.selected.clear(); self.page.viewport.hidden.clear(); self.page.viewport.clear_object_styles()
            for i,row in enumerate(self.matrix):
                for j,field in enumerate(row): field.setValue(int(i==j))
            self.pending=False; self.preview=None; self.page.refresh(); self.update_pending_fields(); self.error_label.clear()
            self.update_comparison(self.page.document.structure,self.page.document.structure,False,False)
        finally: self.staging=False
    def apply_parameters(self): self.apply_lattice()
    def apply_matrix(self): self.apply_lattice()
    def hideEvent(self,event):
        super().hideEvent(event); self.preview=None
        for i,row in enumerate(self.matrix):
            for j,field in enumerate(row): field.setValue(int(i==j))
        self.page.refresh()
        if self.page.document.structure:
            for field,value in zip(self.parameters,lattice_edit.parameters(self.page.document.structure.lattice)): field.setValue(value)
            self.fill_atoms(self.page.document.structure); self.update_pending_fields(); self.update_comparison(self.page.document.structure,self.page.document.structure,False,False)
    def update_atom_draft(self,draft):
        elements=[self.table.item(i,2).text().strip() for i in range(self.table.rowCount())]; tags=[self.table.item(i,6).text() for i in range(self.table.rowCount())]
        points=[[float(self.table.item(i,j).text()) for j in (3,4,5)] for i in range(self.table.rowCount())]
        sources=[self.table.item(i,1).data(Qt.ItemDataRole.UserRole) for i in range(self.table.rowCount())]
        flags=[self.page.document.structure.flags[i][:] if i is not None else ['T']*3 for i in sources]
        lattice_edit.set_atom_rows(draft,elements,points,tags,self.mode==1); draft.flags=flags
    def apply_atoms(self): self.apply_lattice()
