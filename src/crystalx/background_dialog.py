"""Per-curve baseline controls, independent of visual style templates."""
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QDoubleSpinBox
from .math_ui import MathLabel as QLabel,MathComboBox as QComboBox,MathPushButton as QPushButton
from .background import METHODS,validate_background_settings
from .dialog_chrome import install_dialog_chrome
from .theme import CONTROLS,stepper_css

class BackgroundDialog(QDialog):
    def __init__(self,page):
        super().__init__(page); self.page=page
        self.setWindowTitle('背景拟合'); self.resize(470,300)
        self.setStyleSheet(CONTROLS+stepper_css()+'QLabel {background:transparent;}')
        root=QVBoxLayout(self); form=QFormLayout(); root.addLayout(form)
        self.curve=QComboBox()
        for index,curve in enumerate(page.plot.curves): self.curve.addItem(f'{index+1} · {curve.label}')
        self.curve.setCurrentIndex(page.plot.active_curve_index); form.addRow('当前曲线',self.curve)
        self.method=QComboBox()
        for key,label in METHODS.items(): self.method.addItem(label,key)
        form.addRow('拟合方法',self.method)
        self.window_width=QDoubleSpinBox(); self.smoothing=QDoubleSpinBox()
        for widget in (self.window_width,self.smoothing):
            widget.setRange(0,1e6); widget.setDecimals(6); widget.setSpecialValueText('自动'); widget.setFixedWidth(160)
        self.window_width_label=QLabel(); form.addRow(self.window_width_label,self.window_width); form.addRow('预平滑宽度',self.smoothing)
        note=QLabel('窗口单位同横轴。SNIP窗口半宽应大于要排除的峰宽；适当增大可抑制宽峰尾部。\n取消“扣除背景”可恢复原始强度；原始数据不改写。')
        note.setWordWrap(True); root.addWidget(note)
        self.status=QLabel(); root.addWidget(self.status)
        row=QHBoxLayout(); row.addStretch()
        self.apply_button=QPushButton('应用'); self.apply_button.clicked.connect(self.apply); row.addWidget(self.apply_button)
        close=QPushButton('关闭'); close.clicked.connect(self.reject); row.addWidget(close); root.addLayout(row)
        self.curve.currentIndexChanged.connect(self.load_curve); self.method.currentIndexChanged.connect(self.method_changed)
        self.load_curve(); install_dialog_chrome(self,root)

    def load_curve(self,*args):
        values=validate_background_settings(self.page.plot.curves[self.curve.currentIndex()].background_settings)
        self.method.setCurrentIndex(self.method.findData(values['method'])); self.window_width.setValue(values['width']); self.smoothing.setValue(values['smoothing']); self.method_changed()

    def method_changed(self,*args):
        snip=self.method.currentData() in ('snip','auto'); legacy=self.method.currentData()=='asls'
        self.window_width_label.setText('SNIP窗口半宽' if snip else '窗口宽度'); self.window_width.setEnabled(not legacy); self.smoothing.setEnabled(snip)

    def apply(self):
        self.page.plot.select_curve(self.curve.currentIndex())
        settings=dict(method=self.method.currentData(),width=self.window_width.value(),smoothing=self.smoothing.value())
        if self.page.change_background(settings=settings,show=True): self.status.setText('已更新背景。')
