"""Expression creation and legend membership in the shared dialog style."""
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QScrollArea,QWidget
from .math_ui import MathLineEdit as QLineEdit,MathLabel as QLabel,MathPushButton as QPushButton,MathCheckBox as QCheckBox
from .dialog_chrome import install_dialog_chrome
from .theme import CONTROLS

class ExpressionDialog(QDialog):
    def __init__(self,plot):
        super().__init__(plot); self.plot=plot; self.setWindowTitle('新增表达式曲线'); self.resize(520,210); self.setStyleSheet(CONTROLS+'QLabel {background:transparent;}')
        root=QVBoxLayout(self); form=QFormLayout(); root.addLayout(form)
        self.expression=QLineEdit(); self.expression.setPlaceholderText('支持Mathematica：Sin[t]，或 x^2, {x,-1,1}；方程 x=1')
        self.domain=QLineEdit(f'{plot.bounds[0]:.9g}, {plot.bounds[1]:.9g}'); self.domain.setPlaceholderText('最小值, 最大值；优先采用表达式内的定义域')
        form.addRow('表达式',self.expression); form.addRow('定义域',self.domain)
        self.error=QLabel(); self.error.setWordWrap(True); root.addWidget(self.error)
        row=QHBoxLayout(); row.addStretch(); self.add_button=QPushButton('添加'); self.add_button.clicked.connect(self.add); row.addWidget(self.add_button)
        close=QPushButton('取消'); close.clicked.connect(self.reject); row.addWidget(close); root.addLayout(row); install_dialog_chrome(self,root)

    def add(self):
        try: self.plot.add_expression(self.expression.text(),self.domain.text())
        except (ValueError,TypeError,OverflowError) as error: self.error.setText(str(error)); return False
        self.accept(); return True

class LegendEntriesDialog(QDialog):
    def __init__(self,plot):
        super().__init__(plot); self.plot=plot; self.setWindowTitle('图例条目'); self.setStyleSheet(CONTROLS+'QLabel,QCheckBox,QScrollArea {background:transparent;}'); self.resize(380,240)
        root=QVBoxLayout(self); root.addWidget(QLabel('勾选需要在图例中显示的曲线')); self.entries=[]
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content=QWidget(); rows=QVBoxLayout(content); scroll.setWidget(content); root.addWidget(scroll,1)
        for curve in plot.curves:
            box=QCheckBox(curve.label); box.setChecked(curve.legend_visible); rows.addWidget(box); self.entries.append((curve.uid,box))
        rows.addStretch(); row=QHBoxLayout(); row.addStretch(); button=QPushButton('应用'); button.clicked.connect(self.apply); row.addWidget(button)
        close=QPushButton('关闭'); close.clicked.connect(self.reject); row.addWidget(close); root.addLayout(row); install_dialog_chrome(self,root)

    def apply(self):
        legend=self.plot.data_axes.get_legend()
        if legend is not None and self.plot.legend_anchor is None:
            box=legend.get_window_extent(self.plot.canvas.get_renderer()); ratio=self.plot.canvas.figure.bbox.width/self.plot.width(); area=self.plot.area()
            self.plot.legend_anchor=((box.x0/ratio-area.left())/area.width(),(area.bottom()-(self.plot.height()-box.y0/ratio))/area.height())
        values={uid:box.isChecked() for uid,box in self.entries}
        for curve in self.plot.curves:
            if curve.uid in values: curve.legend_visible=values[curve.uid]
        self.plot.rebuild()
