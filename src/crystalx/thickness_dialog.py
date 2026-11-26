"""User-confirmed Kiessig fringe orders and wavelength for XRR thickness."""
import csv
from pathlib import Path
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QGridLayout,QDoubleSpinBox,QTableWidgetItem,QHeaderView,QAbstractItemView
from .math_ui import MathLabel as QLabel,MathComboBox as QComboBox,MathPushButton as QPushButton,MathTableWidget as QTableWidget,MathCheckBox as QCheckBox
from .xrr_thickness import estimate_thickness,detect_fringe_maxima,wavelength_from_metadata
from .table_controls import CenteredCheckDelegate
from .dialog_chrome import install_dialog_chrome
from .dialogs import QFileDialog
from .theme import CONTROLS,stepper_css

class ThicknessDialog(QDialog):
    def __init__(self,page):
        super().__init__(page); self.page=page; self.result=None
        self.setWindowTitle('计算膜厚'); self.resize(860,650)
        self.setStyleSheet(CONTROLS+stepper_css()+'QLabel,QCheckBox {background:transparent;} QTableWidget {background:white;border:0;} QHeaderView::section {background:transparent;border:0;}')
        root=QVBoxLayout(self); grid=QGridLayout(); root.addLayout(grid)
        self.curve=QComboBox()
        for i,curve in enumerate(page.plot.curves): self.curve.addItem(f'{i+1} · {curve.label}')
        self.curve.setCurrentIndex(page.plot.active_curve_index); grid.addWidget(QLabel('当前曲线'),0,0); grid.addWidget(self.curve,0,1,1,3)
        self.axis=QComboBox()
        for key,title in [('2theta','2θ (°)'),('theta','θ (°)'),('q_a',r'$q_z$ (Å$^{-1}$)'),('q_nm',r'$q_z$ (nm$^{-1}$)')]: self.axis.addItem(title,key)
        self.wavelength=self.number(.0001,100,6); value,note=wavelength_from_metadata(page.plot.scan.metadata); self.wavelength.setValue(value)
        metadata=page.plot.scan.metadata; axis_name=metadata.get('MEAS_SCAN_AXIS_X_INTERNAL','').lower(); unit=metadata.get('MEAS_SCAN_UNIT_X','').lower().replace(' ','')
        inferred='theta' if axis_name=='theta' else 'q_nm' if unit in ('nm^-1','1/nm','nm⁻¹') else 'q_a' if unit in ('a^-1','1/a','å⁻¹','angstrom^-1','1/angstrom') else '2theta'
        self.axis.setCurrentIndex(self.axis.findData(inferred))
        grid.addWidget(QLabel('横轴类型'),1,0); grid.addWidget(self.axis,1,1); grid.addWidget(QLabel('波长 (Å)'),1,2); grid.addWidget(self.wavelength,1,3)
        self.minimum=self.number(-1e6,1e6,6); self.maximum=self.number(-1e6,1e6,6)
        grid.addWidget(QLabel('搜索起点'),2,0); grid.addWidget(self.minimum,2,1); grid.addWidget(QLabel('搜索终点'),2,2); grid.addWidget(self.maximum,2,3)
        self.critical=self.number(0,89,6); self.critical.setSpecialValueText('不修正')
        grid.addWidget(QLabel('临界角 θc (°)'),3,0); grid.addWidget(self.critical,3,1)
        self.consecutive=QCheckBox('连续级次（自动编号）'); self.consecutive.setChecked(True); self.consecutive.setToolTip('漏峰时取消自动编号，并手动保留缺失级次的间隔。')
        grid.addWidget(self.consecutive,3,2,1,2)
        source_row=QHBoxLayout(); self.source_note=QLabel(note.replace('Kα₁',r'$K\alpha_1$')); source_row.addWidget(self.source_note); source_row.addStretch()
        self.show_marks=QCheckBox('在图中显示峰位'); self.show_marks.toggled.connect(self.sync_marks); source_row.addWidget(self.show_marks); root.addLayout(source_row)
        actions=QHBoxLayout()
        for title,callback in [('自动识别条纹峰',self.detect),('读取寻峰结果',self.from_peaks),('读取图中标点',self.from_points),('新增',self.add_row),('删除',self.delete_rows)]:
            button=QPushButton(title); button.clicked.connect(callback); actions.addWidget(button)
        root.addLayout(actions)
        self.table=QTableWidget(0,5); self.table.setHorizontalHeaderLabels(['使用','级次','峰位',r'$q_z$ (Å$^{-1}$)','判断 / 说明'])
        self.table.setItemDelegateForColumn(0,CenteredCheckDelegate(self.table)); self.table.setShowGrid(False); self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        root.addWidget(self.table,1)
        self.help=QLabel('请选择连续的同类Kiessig条纹峰（不要混用峰、谷）。\n'+r'$t=2\pi/\Delta q_z$；$q_z=4\pi\sin\theta/\lambda$。默认按级次与$q_z$的线性斜率估算膜厚；临界边附近应排除或设置θc修正，多层膜结果仅代表所选周期。')
        self.help.setWordWrap(True); root.addWidget(self.help)
        self.summary=QLabel('选择至少两个峰后点击“计算”。'); self.summary.setWordWrap(True); root.addWidget(self.summary)
        self.error=QLabel(); self.error.setStyleSheet('color:#a52d32;background:transparent;'); self.error.setWordWrap(True); root.addWidget(self.error)
        footer=QHBoxLayout(); self.export_button=QPushButton('导出结果'); self.export_button.clicked.connect(self.export); footer.addWidget(self.export_button); footer.addStretch()
        self.calculate_button=QPushButton('计算'); self.calculate_button.clicked.connect(self.calculate); footer.addWidget(self.calculate_button)
        close=QPushButton('关闭'); close.clicked.connect(self.reject); footer.addWidget(close); root.addLayout(footer)
        self.curve.currentIndexChanged.connect(self.change_curve); self.table.cellChanged.connect(self.invalidate)
        self.axis.currentIndexChanged.connect(self.invalidate); self.consecutive.toggled.connect(self.toggle_orders)
        self.wavelength.valueChanged.connect(self.invalidate); self.critical.valueChanged.connect(self.invalidate)
        self.change_curve(); install_dialog_chrome(self,root)
        if not self.table.rowCount(): self.from_peaks(silent=True)

    def number(self,low,high,decimals):
        widget=QDoubleSpinBox(); widget.setRange(low,high); widget.setDecimals(decimals); widget.setFixedWidth(170); return widget

    def invalidate(self,*args):
        self.result=None; self.summary.setText('峰位或参数已变更，请重新计算。'); self.error.clear()
        previous=self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item=self.table.item(row,3)
            if item is not None: item.setText('')
        self.table.blockSignals(previous)
        self.sync_marks()

    def sync_marks(self,*args):
        if not hasattr(self,'table'): return
        marks=[]
        if self.show_marks.isChecked():
            for row in range(self.table.rowCount()):
                check=self.table.item(row,0); position=self.table.item(row,2); order=self.table.item(row,1)
                if check is None or position is None or order is None or check.checkState()!=Qt.CheckState.Checked: continue
                try:
                    x=float(position.text()); level=float(order.text())
                    if not np.isfinite(x) or not np.isfinite(level) or not level.is_integer(): continue
                except ValueError: continue
                marks.append({'x':x,'order':int(level)})
            if self.consecutive.isChecked():
                marks.sort(key=lambda mark:mark['x'])
                for index,mark in enumerate(marks): mark['order']=index+1
        curve=self.page.plot.curves[self.curve.currentIndex()]
        if curve.thickness_marks!=marks:
            curve.thickness_marks=marks; self.page.plot.rebuild()

    def toggle_orders(self,*args):
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item=self.table.item(row,1)
            item.setFlags(item.flags()&~Qt.ItemFlag.ItemIsEditable if self.consecutive.isChecked() else item.flags()|Qt.ItemFlag.ItemIsEditable)
        self.table.blockSignals(False); self.invalidate()

    def change_curve(self,*args):
        curve=self.page.plot.curves[self.curve.currentIndex()]; low,high=min(curve.x),max(curve.x)
        metadata=curve.metadata or self.page.plot.scan.metadata
        value,note=wavelength_from_metadata(metadata)
        self.wavelength.blockSignals(True); self.wavelength.setValue(value); self.wavelength.blockSignals(False)
        self.source_note.setText(note.replace('Kα₁',r'$K\alpha_1$'))
        axis_name=metadata.get('MEAS_SCAN_AXIS_X_INTERNAL','').lower(); unit=metadata.get('MEAS_SCAN_UNIT_X','').lower().replace(' ','')
        inferred='theta' if axis_name=='theta' else 'q_nm' if unit in ('nm^-1','1/nm','nm⁻¹') else 'q_a' if unit in ('a^-1','1/a','å⁻¹','angstrom^-1','1/angstrom') else '2theta'
        self.axis.blockSignals(True); self.axis.setCurrentIndex(self.axis.findData(inferred)); self.axis.blockSignals(False)
        saved=list(curve.thickness_marks)
        self.show_marks.blockSignals(True); self.show_marks.setChecked(bool(saved)); self.show_marks.blockSignals(False)
        self.consecutive.blockSignals(True); self.consecutive.setChecked(all(mark['order']==index+1 for index,mark in enumerate(sorted(saved,key=lambda mark:mark['x'])))); self.consecutive.blockSignals(False)
        self.minimum.setValue(low+(high-low)*.1); self.maximum.setValue(high); self.load_rows([mark['x'] for mark in saved],{mark['x']:mark['order'] for mark in saved})
        try:
            from .xrr_fringe import analyze_fringes
            analysis=analyze_fringes(curve.x,curve.display_y)
            self.minimum.setValue(analysis.interval[0]); self.maximum.setValue(analysis.interval[1])
        except ValueError: pass

    def load_rows(self,positions,orders=None,checks=None,descriptions=None):
        self.table.blockSignals(True); self.table.setRowCount(0)
        for value in sorted(set(positions)):
            self.add_row(value)
            if orders is not None: self.table.item(self.table.rowCount()-1,1).setText(str(orders[value]))
            if checks is not None: self.table.item(self.table.rowCount()-1,0).setCheckState(Qt.CheckState.Checked if checks[value] else Qt.CheckState.Unchecked)
            if descriptions is not None: self.table.item(self.table.rowCount()-1,4).setText(descriptions[value])
        self.table.blockSignals(False); self.invalidate()

    def add_row(self,value=None):
        row=self.table.rowCount(); self.table.insertRow(row)
        for column,text in enumerate(('',str(row+1),str(self.minimum.value()) if value is None or type(value) is bool else f'{value:.10g}','','手动 / 已保存')):
            item=QTableWidgetItem(text); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if column==0: item.setFlags((item.flags()|Qt.ItemFlag.ItemIsUserCheckable)&~Qt.ItemFlag.ItemIsEditable); item.setCheckState(Qt.CheckState.Checked)
            if column in (3,4): item.setFlags(item.flags()&~Qt.ItemFlag.ItemIsEditable)
            if column==1 and self.consecutive.isChecked(): item.setFlags(item.flags()&~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row,column,item)

    def delete_rows(self):
        for row in sorted({item.row() for item in self.table.selectedItems()},reverse=True): self.table.removeRow(row)
        self.invalidate()

    def detect(self):
        curve=self.page.plot.curves[self.curve.currentIndex()]
        try:
            if self.minimum.value()>=self.maximum.value(): raise ValueError('搜索起点须小于终点。')
            from .xrr_fringe import analyze_fringes
            analysis=analyze_fringes(curve.x,curve.display_y,self.minimum.value(),self.maximum.value())
            candidates=analysis.result.peaks; positions=[peak.x for peak in candidates]
        except ValueError as error: self.error.setText(str(error)); return
        self.load_rows(positions,checks={p.x:p.status=='可靠' for p in candidates},descriptions={p.x:p.status+('：'+p.reason if p.reason else '') for p in candidates})
        reliable=sum(p.status=='可靠' for p in candidates)
        self.summary.setText(f'{reliable} 个可靠、{len(candidates)-reliable} 个待确认；待确认项默认不用于计算。'+(' 检测到多个周期，请核对。' if any('多个' in note for note in analysis.notes) else ''))
        self.error.setText('；'.join(analysis.notes))

    def from_peaks(self,silent=False):
        index=self.curve.currentIndex(); dialog=self.page.peak_dialog; curve=self.page.plot.curves[index]
        if dialog is not None and dialog.result is not None and dialog.result_index==index: values=[peak.x for peak in dialog.result.peaks if peak.status=='可靠']
        else: values=[curve.peak_position(i)[0] for i in curve.peaks]
        if values: self.load_rows(values)
        elif not silent: self.error.setText('当前曲线没有寻峰结果，请先寻峰或自动识别条纹峰。')

    def from_points(self):
        curve=self.page.plot.curves[self.curve.currentIndex()]
        if curve.points: self.load_rows([curve.x[i] for i in curve.points])
        else: self.error.setText('请先在图中单击标出条纹峰，再读取标点。')

    def calculate(self):
        rows=[row for row in range(self.table.rowCount()) if self.table.item(row,0).checkState()==Qt.CheckState.Checked]
        try:
            values=[float(self.table.item(row,2).text()) for row in rows]
            orders=None if self.consecutive.isChecked() else [float(self.table.item(row,1).text()) for row in rows]
            result=estimate_thickness(values,self.wavelength.value(),self.axis.currentData(),orders,self.critical.value())
        except (ValueError,TypeError) as error: self.error.setText(str(error)); self.result=None; return False
        sorting=np.argsort(values); self.table.blockSignals(True)
        self.table.horizontalHeaderItem(3).setText(('修正 ' if self.critical.value()>0 else '')+r'$q_z$ (Å$^{-1}$)')
        for order,index in enumerate(sorting):
            row=rows[index]
            if self.consecutive.isChecked(): self.table.item(row,1).setText(str(order+1))
            self.table.item(row,3).setText(f'{result.q[order]:.9g}')
        self.table.blockSignals(False); self.result=result
        self.sync_marks()
        uncertainty='' if result.standard_error_nm is None else f' · 拟合标准误 {result.standard_error_nm:.4g} nm'
        quality=f'R² = {result.r2:.6f}' if len(rows)>2 else '两峰估计，无法评估拟合误差'
        self.summary.setText(f'膜厚：{result.thickness_nm:.6g} nm（{result.thickness_nm*10:.6g} Å）{uncertainty}\n{len(rows)} 个峰 · Δqz = {result.slope:.6g} Å⁻¹ · {quality}\n相邻峰对估计：'+ '、'.join(f'{value:.5g}' for value in result.intervals_nm)+' nm')
        spread=np.std(result.intervals_nm)/np.mean(result.intervals_nm)
        self.error.setText('峰间距差异较大，请核对是否漏峰、混入噪声峰或包含多个周期。拟合标准误不包含这些系统误差。' if spread>.15 else '')
        return True

    def export(self):
        if not self.calculate(): return
        path,_=QFileDialog.getSaveFileName(self,'导出膜厚结果',self.page.path.stem+'_thickness.csv','CSV 数据 (*.csv)')
        if not path: return
        if Path(path).suffix.lower()!='.csv': path+='.csv'
        try:
            with open(path,'w',encoding='utf-8-sig',newline='') as stream:
                writer=csv.writer(stream); writer.writerow(['膜厚 (nm)',self.result.thickness_nm]); writer.writerow(['拟合标准误 (nm)',self.result.standard_error_nm]); writer.writerow(['R²',self.result.r2])
                writer.writerow(['波长 (Å)',self.wavelength.value()]); writer.writerow(['横轴',self.axis.currentText()]); writer.writerow(['临界角θc (°)',self.critical.value()]); writer.writerow(['级次','峰位','qz (Å⁻¹)'])
                for row in range(self.table.rowCount()):
                    if self.table.item(row,0).checkState()==Qt.CheckState.Checked: writer.writerow([self.table.item(row,c).text() for c in (1,2,3)])
        except OSError as error: self.error.setText(str(error))
