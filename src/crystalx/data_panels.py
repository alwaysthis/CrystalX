"""Read-only structure data widgets with shared coordinate navigation."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QTabBar,QTableWidget,QTableWidgetItem,
    QAbstractItemView,QTreeWidget,QTreeWidgetItem,QPushButton,QHeaderView,QToolButton,QLabel)

from .icons import icon

class CoordinateDialog(QDialog):
    selection_changed=pyqtSignal(set)
    def __init__(self,parent):
        super().__init__(parent)
        self.setWindowTitle("原子坐标"); self.resize(850,540)
        self.tabs=QTabBar(); self.table=QTableWidget(0,6)
        self.tabs.addTab('Cartesian · Å'); self.tabs.addTab('Direct · 分数坐标')
        self.table.setHorizontalHeaderLabels(['编号','元素','标签','x','y','z'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerItem)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout=QVBoxLayout(self); layout.addWidget(self.tabs); layout.addWidget(self.table)
        self.structure=None; self.selected=set()
        self.tabs.currentChanged.connect(self.switch_mode)
        self.table.itemSelectionChanged.connect(self.on_selection)

    def switch_mode(self,index):
        scroll=self.table.verticalScrollBar().value()
        self.update_values()
        self.table.verticalScrollBar().setValue(scroll)

    def update_values(self):
        if not self.structure: return
        points=self.structure.cartesian_positions if self.tabs.currentIndex()==0 else self.structure.positions
        self.table.blockSignals(True)
        for row,point in enumerate(points):
            for col,value in enumerate(point,3): self.table.item(row,col).setText(f'{value:.9f}')
        self.table.blockSignals(False)

    def refresh(self,structure,selected):
        self.structure=structure; self.selected=set(selected)
        scroll=self.table.verticalScrollBar().value()
        self.table.blockSignals(True)
        count=len(structure.elements) if structure else 0
        self.table.setRowCount(count)
        for row in range(count):
            values=[str(row+1),structure.elements[row],structure.tags[row],'','','']
            for col,value in enumerate(values):
                item=self.table.item(row,col)
                if item is None: item=QTableWidgetItem(); self.table.setItem(row,col,item)
                item.setText(value); item.setSelected(row in selected)
        self.table.blockSignals(False); self.update_values()
        self.table.verticalScrollBar().setValue(scroll)

    def on_selection(self):
        self.selection_changed.emit({index.row() for index in self.table.selectionModel().selectedRows()})

class AtomList(QTreeWidget):
    atom_requested=pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.setColumnCount(5); self.setHeaderLabels(['编号','元素','标签','',''])
        self.setRootIsDecorated(False); self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setStyleSheet('QTreeWidget::item {padding:2px;}')
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        for col,width in [(0,40),(1,42),(3,28),(4,28)]:
            self.header().setSectionResizeMode(col,QHeaderView.ResizeMode.Fixed); self.setColumnWidth(col,width)
        self.setExpandsOnDoubleClick(False)

    def refresh(self,structure,selected):
        expanded={i for i in range(self.topLevelItemCount()) if self.topLevelItem(i).isExpanded()}
        current=self.indexOfTopLevelItem(self.currentItem())
        scroll=self.verticalScrollBar().value()
        self.blockSignals(True); self.clear()
        if structure:
            cart=structure.cartesian_positions
            for i,element in enumerate(structure.elements):
                item=QTreeWidgetItem(self,[str(i+1),element,structure.tags[i],'',''])
                item.setData(0,Qt.ItemDataRole.UserRole,i)
                text='Cartesian · Å  '+ '  '.join(f'{v:8.3f}' for v in cart[i])+'\nDirect         '+'  '.join(f'{v:8.3f}' for v in structure.positions[i])
                detail=QTreeWidgetItem(item,[text]); detail.setFlags(Qt.ItemFlag.ItemIsEnabled); detail.setFirstColumnSpanned(True)
                rows=''.join('<tr><td width=85>'+name+'</td>'+''.join(f'<td width=55 align=right>{v:.3f}</td>' for v in point)+'</tr>' for name,point in [('Cartesian · Å',cart[i]),('Direct',structure.positions[i])])
                label=QLabel('<table cellspacing=0 cellpadding=1>'+rows+'</table>'); label.setStyleSheet("font-family:'Segoe UI','Microsoft YaHei';font-size:12px;padding:3px 0;background:transparent;")
                detail.setText(0,''); detail.setData(0,Qt.ItemDataRole.UserRole,text)
                self.setItemWidget(detail,0,label)
                choose=QToolButton(); choose.setIcon(icon('atom')); choose.setCheckable(True); choose.setChecked(i in selected); choose.setFixedSize(24,22); choose.setToolTip('选择此原子；Ctrl 叠加')
                choose.clicked.connect(lambda checked=False,i=i:self.atom_requested.emit(i)); self.setItemWidget(item,3,choose)
                button=QToolButton(); button.setArrowType(Qt.ArrowType.DownArrow if i in expanded else Qt.ArrowType.RightArrow); button.setFixedSize(24,22); button.setToolTip('展开 / 收起坐标')
                button.clicked.connect(lambda checked=False,item=item,button=button:self.toggle_coordinates(item,button))
                self.setItemWidget(item,4,button); item.setExpanded(i in expanded)
                if i==current: self.setCurrentItem(item)
        self.blockSignals(False); self.verticalScrollBar().setValue(scroll)

    def toggle_coordinates(self,item,button):
        item.setExpanded(not item.isExpanded())
        button.setArrowType(Qt.ArrowType.DownArrow if item.isExpanded() else Qt.ArrowType.RightArrow)
