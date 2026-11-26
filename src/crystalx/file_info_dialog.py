"""File details, scan selection and AFM distribution statistics."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QPushButton
from .dialog_chrome import install_dialog_chrome
from .theme import CONTROLS
from .scan_info import scan_information

from .math_ui import MathComboBox as QComboBox, MathLabel as QLabel, MathPushButton as QPushButton, MathTableWidget as QTableWidget

class FileInfoDialog(QDialog):
    def __init__(self,page):
        super().__init__(page); self.page=page; self.setWindowTitle('文件信息'); self.resize(650,650)
        self.setStyleSheet(CONTROLS+'QLabel {background:transparent;} QTableWidget {border:0;background:white;}')
        layout=QVBoxLayout(self); path=QLabel(str(page.path)); path.setWordWrap(True); path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); layout.addWidget(path)
        row=QHBoxLayout(); row.addWidget(QLabel('当前扫描' if page.data_kind=='XRD' else '当前曲线'))
        self.selector=QComboBox(); self.selector.addItems([f'{i+1} · {len(scan.x)} 点' for i,scan in enumerate(page.scans)]); self.selector.setCurrentIndex(page.selector.currentIndex())
        row.addWidget(self.selector,1); layout.addLayout(row)
        self.table=QTableWidget(0,2); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.setShowGrid(False)
        self.table.horizontalHeader().hide(); self.table.verticalHeader().hide(); self.table.setColumnWidth(0,185); self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch); layout.addWidget(self.table,1)
        close=QPushButton('关闭'); close.clicked.connect(self.reject); layout.addWidget(close,alignment=Qt.AlignmentFlag.AlignRight)
        self.selector.currentIndexChanged.connect(page.selector.setCurrentIndex); page.selector.currentIndexChanged.connect(self.refresh)
        install_dialog_chrome(self,layout); self.refresh(page.selector.currentIndex())

    def refresh(self,index):
        self.selector.blockSignals(True); self.selector.setCurrentIndex(index); self.selector.blockSignals(False)
        rows=[('文件名',self.page.path.name),('扫描/曲线总数',str(len(self.page.scans)))]+scan_information(self.page.scans[index])
        from .plot_units import prepare_scan
        prepared=prepare_scan(self.page.scans[index]); metadata=prepared.metadata
        rows.extend([('绘图横轴',prepared.axis_label),('绘图纵轴',prepared.y_label)])
        if metadata.get('CRYSTALX_COUNTS_TIME_S'):
            seconds=float(metadata['CRYSTALX_COUNTS_TIME_S'])
            rows.extend([('推算每点时间',f'{seconds:.9g} s'),('计数率换算倍数',f'{1/seconds:.9g}'),('换算依据','按文件声明的counts及扫描步长/速度推算。')])
        if metadata.get('CRYSTALX_UNIT_NOTE'): rows.append(('单位说明',metadata['CRYSTALX_UNIT_NOTE']))
        self.table.setRowCount(len(rows))
        for row,pair in enumerate(rows):
            for column,value in enumerate(pair): self.table.setItem(row,column,QTableWidgetItem(value))
        self.table.resizeRowsToContents()
