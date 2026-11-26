"""Chinese peak-finding controls, candidate table and independent peak markers."""
import csv
from dataclasses import replace
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QComboBox,
    QDoubleSpinBox,QSpinBox,QCheckBox,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView)
from .peak_finding import PeakSettings,detect_peaks,PEAK_METHODS
from .peak_fit import FIT_MODELS
from .dialog_chrome import install_dialog_chrome
from .dialogs import QFileDialog
from .theme import CONTROLS,stepper_css

from .math_ui import MathCheckBox as QCheckBox, MathComboBox as QComboBox, MathLabel as QLabel, MathPushButton as QPushButton, MathTableWidget as QTableWidget

class PeakFindingDialog(QDialog):
    def __init__(self,plot,region=None):
        super().__init__(plot); self.plot=plot; self.result=None; self.result_index=None; self.region=region
        self.setWindowTitle('寻峰'); self.resize(960,700)
        self.setStyleSheet(CONTROLS+stepper_css()+'QLabel,QCheckBox {background:transparent;} QHeaderView::section {background:transparent;border:0;padding:4px;} QTableWidget {background:white;border:0;} QTableWidget::item:selected {background:#dce7df;color:#23482f;}')
        layout=QVBoxLayout(self); grid=QGridLayout(); grid.setHorizontalSpacing(12); layout.addLayout(grid)
        self.curve=QComboBox()
        for i,curve in enumerate(plot.curves): self.curve.addItem(f'{i+1} · {curve.label}')
        self.curve.setCurrentIndex(plot.active_curve_index); self.curve.currentIndexChanged.connect(self.curve_changed)
        grid.addWidget(QLabel('当前曲线'),0,0); grid.addWidget(self.curve,0,1,1,3)
        self.prominence=self.number(0,1e15,4); self.prominence.setSpecialValueText('自动（噪声估计）')
        self.prominence.setToolTip('自动取5倍噪声估计与信号范围0.01%中的较大值；弱峰可手动降低阈值。')
        self.distance=self.number(0,1e6,6); self.minimum=self.number(0,1e6,6); self.maximum=self.number(0,1e6,6)
        self.maximum.setSpecialValueText('不限'); self.distance.setSpecialValueText('不限'); self.minimum.setSpecialValueText('不限')
        for row,left,right in [(1,('最小突出度',self.prominence),('最小峰间距',self.distance)),(2,('最小峰宽',self.minimum),('最大峰宽',self.maximum))]:
            for column,(title,widget) in zip((0,2),(left,right)): grid.addWidget(QLabel(title),row,column); grid.addWidget(widget,row,column+1)
        self.smooth=QCheckBox('Savitzky–Golay 平滑'); self.smoothing_window=QSpinBox(); self.smoothing_window.setRange(3,1001); self.smoothing_window.setSingleStep(2); self.smoothing_window.setValue(7); self.smoothing_window.setFixedWidth(140); self.smoothing_window.setEnabled(False)
        self.smooth.toggled.connect(self.smoothing_window.setEnabled); grid.addWidget(self.smooth,3,0,1,2); grid.addWidget(QLabel('平滑窗口（点）'),3,2); grid.addWidget(self.smoothing_window,3,3)
        self.method=QComboBox()
        for key,text in PEAK_METHODS.items(): self.method.addItem(text,key)
        if plot.scan.template_name=='XRR': self.method.addItem('XRR条纹识别（周期辅助）','fringe')
        self.method.setCurrentIndex(self.method.findData('fringe' if plot.scan.template_name=='XRR' else 'fit'))
        grid.addWidget(QLabel('寻峰方法'),4,0); grid.addWidget(self.method,4,1,1,3)
        self.wavelet_min=self.number(0,1e6,6); self.wavelet_max=self.number(0,1e6,6)
        for column,title,widget in ((0,'小波尺度下限',self.wavelet_min),(2,'小波尺度上限',self.wavelet_max)):
            widget.setSpecialValueText('自动'); widget.setToolTip('单位同横轴；小波尺度不是FWHM。覆盖预计的峰宽尺度。')
            grid.addWidget(QLabel(title),5,column); grid.addWidget(widget,5,column+1)
        self.fit_model=QComboBox()
        for key,title in FIT_MODELS.items(): self.fit_model.addItem(title,key)
        grid.addWidget(QLabel('拟合峰型'),6,0); grid.addWidget(self.fit_model,6,1,1,3)
        self.method.currentIndexChanged.connect(self.method_changed); self.method_changed()
        self.smooth.toggled.connect(self.method_changed)
        self.region_label=QLabel(); self.region_label.setToolTip('框选请包含峰两侧背景；截断峰形会影响突出度和宽度。'); layout.addWidget(self.region_label); self.update_region_label()
        self.note=QLabel(); self.note.setWordWrap(True); layout.addWidget(self.note)
        actions=QHBoxLayout(); self.run_button=QPushButton('开始寻峰'); self.run_button.clicked.connect(self.run); actions.addWidget(self.run_button)
        self.show_marks=QCheckBox('显示峰位'); self.show_marks.setChecked(True); self.show_marks.toggled.connect(self.mark_result); actions.addWidget(self.show_marks)
        self.show_contours=QCheckBox('显示峰轮廓'); self.show_contours.setToolTip('显示峰附近的检测曲线及局部基底之间的轮廓区域，不是峰型拟合结果。')
        self.show_contours.toggled.connect(self.mark_result); actions.addWidget(self.show_contours)
        self.show_smooth=QCheckBox('显示峰平滑曲线'); self.show_smooth.setToolTip('显示各峰附近实际用于检测的平滑曲线；尚未启用平滑时会启用SG平滑并重新寻峰。')
        self.show_smooth.toggled.connect(self.show_smoothed); actions.addWidget(self.show_smooth)
        self.show_smooth.setChecked(True)
        self.smooth.toggled.connect(lambda value:self.show_smooth.setChecked(False) if not value else None)
        self.summary=QLabel(); actions.addWidget(self.summary,1); layout.addLayout(actions)
        unit=plot.curves[plot.active_curve_index].metadata.get('MEAS_SCAN_UNIT_X','deg'); unit='°' if unit.lower()=='deg' else unit
        self.table=QTableWidget(0,6); self.table.setHorizontalHeaderLabels(['序号',f'峰位 ({unit})','原始强度','突出度',f'半突出度宽度 ({unit})',f'半高峰宽 FWHM ({unit})'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.table.setShowGrid(False); self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); layout.addWidget(self.table,1)
        self.error=QLabel(); self.error.setWordWrap(True); self.error.setStyleSheet('color:#a52d32;background:transparent;'); layout.addWidget(self.error)
        footer=QHBoxLayout()
        for text,callback in [('导出结果',self.export),('清除标记',self.clear_marks)]:
            button=QPushButton(text); button.clicked.connect(callback); footer.addWidget(button)
        footer.addStretch(); close=QPushButton('关闭'); close.clicked.connect(self.reject); footer.addWidget(close); layout.addLayout(footer)
        install_dialog_chrome(self,layout); self.curve_changed(self.curve.currentIndex())
        self.method_changed()

    def number(self,low,high,decimals):
        widget=QDoubleSpinBox(); widget.setRange(low,high); widget.setDecimals(decimals); widget.setFixedWidth(180); return widget

    def method_changed(self,*args):
        fringe=self.method.currentData()=='fringe'
        if hasattr(self,'note'):
            self.note.setText('条纹模式：周期估计辅助局部寻峰；实心标记为可靠候选，空心菱形为待确认。\n检测宽度来自去趋势信号，不是FWHM；“可靠”表示通过算法筛选，仍需核对。' if fringe else '峰型拟合直接使用原始采样强度，联合拟合局部基底；拟合模式FWHM来自模型参数。')
        self.prominence.setToolTip('XRR条纹模式使用自然对数相对突出度，0为自动。' if fringe else '原始强度的最小突出度，0为自动。')
        self.smooth.setEnabled(not fringe)
        wavelet=self.method.currentData()=='wavelet'
        fitting=self.method.currentData()=='fit'
        self.wavelet_min.setEnabled(wavelet); self.wavelet_max.setEnabled(wavelet)
        self.fit_model.setEnabled(fitting); self.smooth.setEnabled(not fitting and not fringe)
        if fitting:
            self.smooth.blockSignals(True); self.smooth.setChecked(False); self.smooth.blockSignals(False)
        self.smoothing_window.setEnabled(not fringe and not fitting and (self.smooth.isChecked() or self.method.currentData()=='derivative'))
        if hasattr(self,'show_smooth'):
            if not fitting and not fringe and self.show_smooth.isChecked() and not self.smooth.isChecked(): self.smooth.setChecked(True)
            self.show_contours.setEnabled(not fringe)
            self.show_smooth.setText('显示峰拟合曲线' if fitting else '显示峰平滑曲线')
            self.show_smooth.setToolTip('显示由原始采样数据拟合得到的连续峰型曲线。' if fitting else '显示各峰附近实际用于检测的平滑曲线；尚未启用平滑时会启用SG平滑并重新寻峰。')
            self.show_contours.setToolTip('显示拟合分峰轮廓与局部基底。' if fitting else '显示峰附近的检测曲线及局部基底之间的区域。')

    def show_smoothed(self,value):
        if self.method.currentData()=='fringe': self.mark_result(); return
        if self.method.currentData()=='fit': self.mark_result(); return
        if value and self.method.currentData()!='derivative' and not self.smooth.isChecked():
            self.smooth.setChecked(True)
            if self.result is not None: self.run(); return
        elif value and self.result is not None and not self.result.overlays.get('smooth'):
            self.run(); return
        self.mark_result()

    def update_region_label(self):
        self.region_label.setText('范围：整条曲线（自动寻峰）' if self.region is None else f'框选范围：X {self.region[0]:.7g} — {self.region[1]:.7g}；Y {self.region[2]:.7g} — {self.region[3]:.7g}')

    def set_region(self,region):
        if region!=self.region:
            self.result=None; self.result_index=None; self.table.setRowCount(0); self.summary.clear()
        self.region=region; self.update_region_label()

    def curve_changed(self,index):
        self.result=None; self.result_index=None
        if not hasattr(self,'table'): return
        self.table.setRowCount(0); self.summary.clear(); self.error.clear()
        x=self.plot.curves[index].x
        step=abs(x[-1]-x[0])/max(1,len(x)-1)
        self.distance.setValue(step*5); self.minimum.setValue(step*2)

    def run(self):
        index=self.curve.currentIndex(); curve=self.plot.curves[index]
        settings=PeakSettings(self.prominence.value(),self.distance.value(),self.minimum.value(),self.maximum.value(),self.smooth.isChecked(),self.smoothing_window.value(),
            self.method.currentData(),self.wavelet_min.value(),self.wavelet_max.value(),self.fit_model.currentData())
        try:
            if self.method.currentData()=='fringe':
                from .xrr_fringe import analyze_fringes
                analysis=analyze_fringes(curve.x,curve.display_y,self.region[0] if self.region else None,self.region[1] if self.region else None,
                    self.prominence.value(),self.distance.value(),self.minimum.value(),self.maximum.value())
                result=analysis.result
                if self.region: result.peaks=[peak for peak in result.peaks if self.region[2]<=peak.intensity<=self.region[3]]
            else: result=detect_peaks(curve.x,curve.display_y,settings,self.region)
        except ValueError as error: self.error.setText(str(error)); return False
        result.peaks=[replace(peak,intensity=curve.y[peak.index]) for peak in result.peaks]
        fitting=self.method.currentData()=='fit'
        self.table.horizontalHeaderItem(3).setText('拟合峰高' if fitting else '突出度')
        self.table.horizontalHeaderItem(4).setText('局部拟合 R²' if fitting else f'半突出度宽度 ({curve.metadata.get("MEAS_SCAN_UNIT_X","deg")})')
        fringe=bool(result.overlays.get('fringe'))
        self.table.setColumnCount(8 if fringe else 6)
        self.table.setColumnHidden(5,fringe)
        if fringe:
            self.table.setHorizontalHeaderItem(6,QTableWidgetItem('可信度')); self.table.setHorizontalHeaderItem(7,QTableWidgetItem('说明'))
            self.table.horizontalHeaderItem(3).setText('对数突出度'); self.table.horizontalHeaderItem(4).setText('检测宽度')
            self.table.horizontalHeaderItem(4).setToolTip('去趋势信号的半突出度宽度，单位同横轴；不是FWHM。')
        self.result=result; self.result_index=index; self.table.setRowCount(len(result.peaks))
        for row,peak in enumerate(result.peaks):
            for column,value in enumerate((row+1,peak.x,peak.intensity,peak.prominence,peak.r2 if fitting else peak.width,peak.fwhm)):
                item=QTableWidgetItem('—' if value is None else str(value) if column==0 else f'{value:.8g}'); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); self.table.setItem(row,column,item)
            if fringe:
                self.table.setItem(row,6,QTableWidgetItem(peak.status))
                reason=QTableWidgetItem(peak.reason or '局部峰顶与周期验证通过'); reason.setToolTip(reason.text()); self.table.setItem(row,7,reason)
        self.summary.setText(f'{len(result.peaks)} 个'+('拟合峰' if fitting else '候选峰')+f' · 突出度阈值 {result.threshold:.6g}')
        if fringe:
            period=result.overlays.get('period'); reliable=sum(p.status=='可靠' for p in result.peaks)
            self.summary.setText(f'{reliable} 个可靠 / {len(result.peaks)-reliable} 个待确认'+(f' · 周期 {period:.6g}' if period else ' · 无可靠周期'))
        if fitting and result.overlays.get('low_signal') and result.peaks:
            self.summary.setText(self.summary.text()+' · 低信噪比宽峰：已拟合原始数据，R²未平滑修饰，请核对结果。')
        self.error.setText('未获得可靠峰型拟合，请扩大框选范围或调整阈值、峰型。' if fitting and not result.peaks else '')
        self.error.setStyleSheet('color:'+('#68766c' if fringe else '#a52d32')+';background:transparent;')
        if fringe: self.error.setText('；'.join(result.overlays.get('notes',[])))
        self.mark_result()
        self.plot.readout.setText(f'寻峰：{curve.label}，{len(result.peaks)} 个候选峰。'); return True

    def mark_result(self,*args):
        if self.result is None: return
        source=self.plot.curves[self.result_index]
        source.peaks=[peak.index for peak in self.result.peaks if peak.status=='可靠'] if self.show_marks.isChecked() else []
        fitted=self.result.overlays.get('model') is not None
        source.peak_analysis={
            'contours':self.result.overlays.get('contours',[]) if self.show_contours.isChecked() else [],
            'contour_curves':True,
            'smooth':{},
            'positions':self.result.overlays.get('positions',[]) if self.show_marks.isChecked() else []}
        if self.result.overlays.get('fringe'):
            source.peak_analysis['fringe_candidates']=[dict(index=p.index,x=p.x,y=source.display_y[p.index]) for p in self.result.peaks if p.status=='待确认'] if self.show_marks.isChecked() else []
        for curve in self.plot.curves:
            if curve.source_id==source.uid and (curve.role in ('fit','smooth') or curve.role.startswith('profile:')): curve.visible=False
        smooth=self.result.overlays.get('smooth',{})
        if smooth:
            self.publish_curve(source,'fit' if fitted else 'smooth',smooth,' fit' if fitted else ' smoothed',self.show_smooth.isChecked())
        for index,contour in enumerate(self.result.overlays.get('contours',[])):
            self.publish_curve(source,f'profile:{index}',contour,f' peak {index+1}',self.show_contours.isChecked())
        self.plot.rebuild()

    def publish_curve(self,source,role,values,suffix,visible):
        from .plot_curves import PlotCurve
        from copy import deepcopy
        existing=next((curve for curve in self.plot.curves if curve.role==role and curve.source_id==source.uid),None)
        if existing is None and not visible: return
        if existing is None:
            style=deepcopy(source.style); style.update(color='#d55e00',width=1.4)
            if role.startswith('profile:'): style.update(style='dashed',color='#0072b2')
            existing=PlotCurve(list(values['x']),list(values['y']),style,source.label+suffix,role=role,source_id=source.uid,metadata=deepcopy(source.metadata)); self.plot.curves.append(existing)
            self.curve.blockSignals(True); self.curve.addItem(f'{len(self.plot.curves)} · {existing.label}'); self.curve.blockSignals(False)
        else: existing.x=list(values['x']); existing.y=list(values['y'])
        existing.fill_baseline=list(values.get('baseline',[])) if role.startswith('profile:') else []
        existing.visible=visible

    def clear_marks(self):
        curve=self.plot.curves[self.curve.currentIndex()]; curve.peaks=[]; curve.peak_analysis={}; self.plot.rebuild()

    def export(self):
        if self.result is None: self.error.setText('请先运行寻峰。'); return
        path,_=QFileDialog.getSaveFileName(self,'导出寻峰结果','peaks.csv','CSV 数据 (*.csv)')
        if not path: return
        if Path(path).suffix.lower()!='.csv': path+='.csv'
        try:
            with open(path,'w',encoding='utf-8-sig',newline='') as stream:
                writer=csv.writer(stream); writer.writerow([self.table.horizontalHeaderItem(i).text() for i in range(1,self.table.columnCount())])
                for row in range(self.table.rowCount()): writer.writerow([self.table.item(row,column).text().replace('—','') for column in range(1,self.table.columnCount())])
        except OSError as error: self.error.setText(str(error))
