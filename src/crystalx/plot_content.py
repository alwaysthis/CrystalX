"""Direct editing of plot content, independent of appearance templates."""
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QWidget,QFormLayout
from .dialog_chrome import install_dialog_chrome
from .theme import CONTROLS

from .math_ui import MathLabel as QLabel, MathLineEdit as QLineEdit, MathPushButton as QPushButton

class AxisRangeControls(QWidget):
    def __init__(self,plot,side,menu):
        super().__init__(menu); self.plot=plot; self.side=side; self.menu=menu
        self.setStyleSheet(CONTROLS+'QLabel {background:transparent;}'); self.setFixedWidth(240)
        layout=QVBoxLayout(self); form=QFormLayout(); layout.addLayout(form)
        low,high=plot.axis_limits(side)
        self.minimum=QLineEdit(f'{low:.12g}'); self.maximum=QLineEdit(f'{high:.12g}')
        for label,field in [('最小值',self.minimum),('最大值',self.maximum)]:
            field.setFixedWidth(150); field.setPlaceholderText('自动'); form.addRow(label,field); field.returnPressed.connect(self.apply)
        self.error=QLabel(); self.error.setWordWrap(True); self.error.setStyleSheet('color:#a52d32;background:transparent;'); layout.addWidget(self.error)
        self.button=QPushButton('应用'); self.button.setAutoDefault(False); self.button.clicked.connect(self.apply); layout.addWidget(self.button)

    def apply(self):
        try: self.plot.set_axis_range(self.side,self.minimum.text(),self.maximum.text())
        except ValueError as error: self.error.setText(str(error)); self.adjustSize(); return False
        self.menu.close()
        parent=self.menu.parentWidget()
        if parent: parent.close()
        return True

class PlotTextEditor(QDialog):
    def __init__(self,plot,text,title,caption,save):
        super().__init__(plot); self.save=save
        self.setWindowTitle(title); self.setStyleSheet(CONTROLS+'QLabel {background:transparent;}'); self.resize(430,170)
        layout=QVBoxLayout(self); self.caption=QLabel(caption); layout.addWidget(self.caption)
        self.input=QLineEdit(text); self.input.setToolTip('使用 $...$ 或 $$...$$ 输入数学表达式；编辑时显示源码，失焦后预览。'); layout.addWidget(self.input)
        self.error=QLabel(); self.error.setStyleSheet('color:#a52d32;background:transparent;'); layout.addWidget(self.error)
        row=QHBoxLayout(); row.addStretch()
        for title,callback in [('确定',self.accept),('取消',self.reject)]:
            button=QPushButton(title); button.clicked.connect(callback); row.addWidget(button)
        layout.addLayout(row); install_dialog_chrome(self,layout)
        self.input.returnPressed.connect(self.accept); self.input.selectAll(); self.input.setFocus()

    def accept(self):
        try: self.save(self.input.text())
        except ValueError as error: self.error.setText(str(error)); return
        super().accept()

class AxisLabelEditor(PlotTextEditor):
    def __init__(self,plot,side,text):
        super().__init__(plot,text,'编辑坐标轴标签','标签内容',lambda value:plot.set_axis_label(side,value))

class LegendLabelEditor(PlotTextEditor):
    def __init__(self,plot,index):
        super().__init__(plot,plot.curves[index].label,'编辑图例','图例内容',lambda value:plot.set_legend_label(index,value))

class PointLabelEditor(PlotTextEditor):
    def __init__(self,plot,curve_index,index):
        curve=plot.curves[curve_index]
        default=f'{curve.peak_position(index)[0]:.4f}' if index in curve.peaks and index not in curve.points else f'({curve.x[index]:.6g}, {curve.display_y[index]:.6g})'
        text=curve.point_labels.get(index,default)
        super().__init__(plot,text,'编辑图注','图注内容',lambda value:plot.set_point_label(curve_index,index,value))
