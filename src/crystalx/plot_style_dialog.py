"""Compact grouped plot styling with per-curve drafts and portable presets."""
from copy import deepcopy
from pathlib import Path
from PyQt6.QtCore import Qt,QSize
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QListWidget,QStackedWidget,QWidget,QFormLayout,
    QScrollArea,QLineEdit,QDoubleSpinBox,QSpinBox,QComboBox,QCheckBox,QLabel,QPushButton,QStyledItemDelegate,QListView)
from .display_style import ColorButton
from .plot_color import PlotColorButton
from .dialog_chrome import install_dialog_chrome
from .workspace_tabs import WorkspaceTabs
from .dialogs import QFileDialog
from .plot_style import validate_style,LINE_STYLES,MARKERS,axis_label
from .plot_scales import axis_scale
from .plot_curves import validate_curve_settings
from .plot_presets import read_plot_config,write_plot_config,PlotTemplates
from .theme import CONTROLS,WORKSPACE_TABS,stepper_css,DIALOG_BG

from .math_ui import MathCheckBox as QCheckBox, MathComboBox as QComboBox, MathLabel as QLabel, MathLineEdit as QLineEdit, MathListWidget as QListWidget, MathPushButton as QPushButton

class CompactRows(QStyledItemDelegate):
    def sizeHint(self,option,index): return QSize(236,22)

class FontChoice(QComboBox):
    def __init__(self,value,inherit=None):
        super().__init__(); self.inherit=inherit; self.setEditable(True); self.setMaxVisibleItems(12)
        if inherit is not None: self.addItem(inherit)
        self.addItems(QFontDatabase.families()); self.set_family(value)
        self.setView(QListView()); self.view().setItemDelegate(CompactRows(self.view()))
        self.view().setUniformItemSizes(True); self.view().setMaximumHeight(264)
        self.view().setStyleSheet('QListView {background:white;color:#252525;padding:0;} QListView::item {padding:1px 6px;margin:0;border:0;height:22px;}')
        self.setFixedWidth(230)
    def family(self): return self.currentText().strip()
    def set_family(self,value): self.setCurrentText(value or (self.inherit if self.inherit is not None else 'Times New Roman'))
    def currentFont(self): return QFont(self.family())
    def setCurrentFont(self,font): self.set_family(font.family())
    def showPopup(self):
        super().showPopup(); self.view().setFixedWidth(240); self.view().window().setFixedWidth(244)

class PlotStyleDialog(QDialog):
    def __init__(self,plot,section='general',side='left'):
        super().__init__(plot); self.plot=plot; self.fields={}; self.base_style=deepcopy(plot.style)
        self.curve_drafts=[curve.settings() for curve in plot.curves]; self.curve_index=plot.active_curve_index
        self.template_name=plot.template_name; self.template_path=plot.template_path
        self.setWindowTitle('图片样式'); self.resize(850,670)
        self.setStyleSheet(CONTROLS+WORKSPACE_TABS+stepper_css()+'QAbstractSpinBox,QComboBox,QLineEdit {min-height:20px;max-height:24px;padding:2px 6px;} QLabel,QCheckBox {background:transparent;}')
        root=QVBoxLayout(self); body=QHBoxLayout(); body.setSpacing(8)
        self.navigation=QListWidget(); self.navigation.addItems(['通用','坐标轴','图例','曲线'])
        self.navigation.setFixedWidth(128); self.navigation.setSpacing(2)
        for i in range(4): self.navigation.item(i).setSizeHint(QSize(124,28))
        self.navigation.setStyleSheet('QListWidget {background:transparent;border:0;outline:0;} QListWidget::item {padding:3px 8px;border:0;border-radius:4px;} QListWidget::item:selected {background:#dce7df;color:#23482f;}')
        navigation_column=QVBoxLayout(); navigation_column.addWidget(self.navigation,1)
        self.template_button=QPushButton('选择模板'); self.template_button.clicked.connect(self.choose_template); navigation_column.addWidget(self.template_button)
        self.template_label=QLabel(); self.template_label.setWordWrap(True); self.template_label.setFixedWidth(128); self.refresh_template(); navigation_column.addWidget(self.template_label)
        self.pages=QStackedWidget(); body.addLayout(navigation_column); body.addWidget(self.pages,1); root.addLayout(body,1)
        page,form=self.form('通用'); self.pages.addWidget(page)
        for key,label,kind,args in [('font','字体','font',()),('size','字号 (pt)','number',(1,96)),('color','颜色','color',()),('width','全图线宽 (pt)','number',(.1,20)),('background','背景','color',()),('aspect','图片比例','aspect',()),('transparent','导出透明背景','check',()),('grid','网格','check',()),('box','完整图框','check',())]: self.field(form,('general',key),label,kind,*args)
        wrapper=QWidget(); wrapper.setObjectName('plotAxesPage'); wrapper.setStyleSheet(f'QWidget#plotAxesPage {{background:{DIALOG_BG};}}')
        axes_layout=QVBoxLayout(wrapper); axes_layout.setContentsMargins(8,6,8,6)
        self.axis_selector=QComboBox(); self.axis_selector.addItems(['左侧','下侧','右侧','上侧']); self.axis_selector.setFixedWidth(150)
        self.axis_header=self.header('坐标轴',self.axis_selector); axes_layout.addWidget(self.axis_header)
        self.axis_pages=QStackedWidget(); axes_layout.addWidget(self.axis_pages); self.pages.addWidget(wrapper); self.axis_categories=[]
        for side_name in ('left','bottom','right','top'):
            tabs=WorkspaceTabs(); self.axis_categories.append(tabs); self.axis_pages.addWidget(tabs)
            groups=[('轴线',[
                ('visible','显示坐标轴','check',()),('font','字体','inherit_font',()),('size','字号 (pt)','number',(0,96)),('color','颜色','inherit_color',()),('width','线宽 (pt)','number',(0,20))]),
                ('刻度',[
                ('scale','刻度类型','combo',(['linear','sqrt','log'],['线性刻度','根号刻度','对数刻度'])),
                ('ticks','刻度数组','text',()),('interval','刻度间距','number',(0,1e9)),('direction','方向','combo',(['in','out','inout'],['朝内','朝外','内外'])),('tick_length','长度 (pt)','number',(0,30)),
                ('labels','刻度标签','text',()),('number_format','数值格式','combo',(['auto','fixed','E','e','scientific'],['自动','定点','科学计数（E）','科学计数（e）','科学计数（×10ⁿ）'])),('precision','小数位数','integer',(0,12))]),
                ('轴标签',[
                ('label','标签文字','text',()),('label_font','字体','inherit_font',()),('label_size','字号 (pt)','number',(0,96)),('label_color','颜色','inherit_color',())])]
            for title,specs in groups:
                page,form=self.form(); tabs.addTab(page,title)
                for key,label,kind,args in specs: self.field(form,('axes',side_name,key),label,kind,*args)
            self.fields[('axes',side_name,'ticks')][1].textChanged.connect(lambda *args,s=side_name:self.tick_dependencies(s))
            self.tick_dependencies(side_name)
        page,form=self.form('图例'); self.pages.addWidget(page)
        for key,label,kind,args in [('visible','显示图例','check',()),('font','字体','inherit_font',()),('size','字号 (pt)','number',(0,96)),('color','颜色','inherit_color',()),('frame','边框','check',()),('location','位置','combo',(['best','upper right','upper left','lower right','lower left','center'],['自动','右上','左上','右下','左下','居中']))]: self.field(form,('legend',key),label,kind,*args)
        page,form=self.form('曲线'); self.pages.addWidget(page)
        self.curve_selector=QComboBox(); self.curve_selector.setFixedWidth(260)
        for i,c in enumerate(self.curve_drafts): self.curve_selector.addItem(f'{i+1} · {c["label"]}')
        self.curve_selector.setCurrentIndex(self.curve_index); form.addRow('当前曲线',self.curve_selector)
        specs=[('label','图例名称','text',()),('visible','显示曲线','check',()),('style','线型','combo',(list(LINE_STYLES),['实线','点线','划线','点划线','点点划线','无'])),('width','线宽 (pt)','number',(0,20)),('color','颜色','inherit_color',()),
            ('marker','标记','combo',(list(MARKERS),['无','圆','正方形','钻石','星形','三角形','十字','叉号','点'])),('marker_size','标记大小 (pt)','number',(.1,40)),('face','填充色','marker_color',()),('edge','边缘色','marker_color',())]
        for key,label,kind,args in specs: self.field(form,('curve',key),label,kind,*args)
        self.curve_selector.currentIndexChanged.connect(self.change_curve)
        self.error=QLabel(); self.error.setWordWrap(True); self.error.setStyleSheet('color:#a52d32;background:transparent;'); root.addWidget(self.error)
        footer=QHBoxLayout()
        for label,callback in [('加载配置',self.load),('导出配置',self.export)]:
            button=QPushButton(label); button.clicked.connect(callback); footer.addWidget(button)
        footer.addStretch()
        button=QPushButton('确定'); button.clicked.connect(self.accept); footer.addWidget(button)
        self.apply_template_button=QPushButton('应用于模板'); self.apply_template_button.setToolTip('应用当前图并保存到当前模板；其他已打开图保持不变。')
        self.apply_template_button.clicked.connect(self.apply_to_template); footer.addWidget(self.apply_template_button)
        for label,callback in [('应用',self.apply),('取消',self.reject)]:
            button=QPushButton(label); button.clicked.connect(callback); footer.addWidget(button)
        root.addLayout(footer); install_dialog_chrome(self,root)
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex); self.axis_selector.currentIndexChanged.connect(self.change_axis)
        self.navigation.setCurrentRow(['general','axes','legend','curve'].index(section)); self.axis_selector.setCurrentIndex(['left','bottom','right','top'].index(side))
        self.axis_pages.setCurrentIndex(self.axis_selector.currentIndex())
        for path,(kind,widget) in self.fields.items():
            if kind=='color': widget.colorChanged.connect(self.refresh_colors)
            elif kind in ('inherit_color','marker_color'): widget.colorChanged.connect(self.refresh_colors)
        self.refresh_colors()

    def refresh_colors(self,*args):
        if getattr(self,'refreshing_colors',False): return
        self.refreshing_colors=True
        try:
            general=self.fields[('general','color')][1].value
            for path,(kind,widget) in self.fields.items():
                if kind not in ('inherit_color','marker_color') or widget.value not in ('','auto','none'): continue
                color=general
                if kind=='marker_color':
                    field_kind,field=self.fields[('curve','color')]; color=self.read_field(field_kind,field) or general
                elif path[-1]=='label_color':
                    field_kind,field=self.fields[('axes',path[1],'color')]; color=self.read_field(field_kind,field) or general
                widget.fallback=color
        finally: self.refreshing_colors=False

    def header(self,title,control=None):
        row=QWidget(); row.setObjectName('plotStyleHeader'); row.setStyleSheet(f'QWidget#plotStyleHeader {{background:{DIALOG_BG};}}')
        layout=QHBoxLayout(row); layout.setContentsMargins(0,0,0,0)
        heading=QLabel(title); heading.setStyleSheet('font-size:17px;font-weight:bold;background:transparent;'); layout.addWidget(heading); layout.addStretch()
        if control is not None: layout.addWidget(control)
        return row

    def form(self,title=''):
        page=QWidget(); page.setObjectName('plotStylePage'); page.setStyleSheet(f'QWidget#plotStylePage {{background:{DIALOG_BG};}}')
        layout=QVBoxLayout(page); layout.setContentsMargins(8,6,8,6)
        if title: layout.addWidget(self.header(title))
        content=QWidget(); content.setObjectName('plotStyleContent'); content.setStyleSheet('QWidget#plotStyleContent {background:white;}')
        form=QFormLayout(content); form.setVerticalSpacing(7); form.setHorizontalSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint); form.setFormAlignment(Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignLeft)
        scroll=QScrollArea(); scroll.setFrameShape(QScrollArea.Shape.NoFrame); scroll.setWidgetResizable(True); scroll.setWidget(content); layout.addWidget(scroll)
        return page,form

    def change_axis(self,index):
        current=self.axis_pages.currentIndex(); category=self.axis_categories[current].currentIndex()
        self.axis_pages.setCurrentIndex(index); self.axis_categories[index].setCurrentIndex(category)

    def tick_dependencies(self,side):
        self.fields[('axes',side,'interval')][1].setEnabled(not self.fields[('axes',side,'ticks')][1].text().strip())

    def initial(self,path):
        if path[0]=='axes' and path[-1]=='scale': return axis_scale(self.base_style['axes'][path[1]])
        if path[0]=='curve':
            draft=self.curve_drafts[self.curve_index]
            return draft[path[1]] if path[1] in ('label','visible') else draft['style'][path[1]]
        value=self.base_style
        for key in path: value=value[key]
        if path[0]=='axes' and path[-1]=='label' and value is None: return axis_label(self.plot.display_scan,path[1])
        return value

    def field(self,form,path,label,kind,*args):
        value=self.initial(path)
        if kind in ('font','inherit_font'):
            inherit='' if kind=='inherit_font' else None
            widget=FontChoice(value,inherit)
        elif kind=='text':
            widget=QLineEdit(str(value)); widget.setFixedWidth(330 if path[-1] not in ('minimum','maximum') else 140)
            if path[-1] in ('minimum','maximum'): widget.setPlaceholderText('自动')
        elif kind in ('number','integer'):
            widget=QDoubleSpinBox() if kind=='number' else QSpinBox(); widget.setRange(*args); widget.setFixedWidth(140)
            if kind=='number': widget.setDecimals(8 if path[-1]=='interval' else 2); widget.setSingleStep(.1 if path[-1]=='interval' else .5)
            if args[0]==0 and path[-1] in ('size','label_size','width','interval'): widget.setSpecialValueText('自动' if path[-1]=='interval' else ' ')
            widget.setValue(value)
        elif kind=='combo':
            keys,labels=args; widget=QComboBox(); [widget.addItem(text,key) for key,text in zip(keys,labels)]; widget.setCurrentIndex(keys.index(value)); widget.setFixedWidth(200)
        elif kind=='aspect':
            widget=QComboBox(); widget.setEditable(True); widget.addItems(['自适应','4:3','1:1','16:9']); widget.setCurrentText('自适应' if value=='auto' else value); widget.setFixedWidth(200)
            widget.setToolTip('可输入宽:高或宽高比数值。')
        elif kind=='check': widget=QCheckBox(); widget.setChecked(value)
        elif kind=='color': widget=ColorButton(); widget.set_color(value)
        else:
            widget=PlotColorButton(kind=='marker_color'); widget.set_color(value)
        if path[-1]=='interval': widget.setToolTip('0表示自动；对数轴按log10值、根号轴按平方根值设置间距。')
        if path[-1]=='label': widget.setToolTip('使用 $...$ 或 $$...$$ 输入数学表达式。')
        self.fields[path]=(kind,widget); form.addRow(label,widget)

    def read_field(self,kind,widget):
        if kind=='aspect': return 'auto' if widget.currentText().strip()=='自适应' else widget.currentText().strip()
        if kind in ('font','inherit_font'): return widget.family()
        if kind=='text': return widget.text().strip()
        if kind=='check': return widget.isChecked()
        if kind=='combo': return widget.currentData()
        if kind=='color': return widget.value
        if kind in ('number','integer'): return widget.value()
        return widget.value

    def write_field(self,kind,widget,value):
        if kind=='aspect': widget.setCurrentText('自适应' if value=='auto' else value)
        elif kind in ('font','inherit_font'): widget.set_family(value)
        elif kind=='text': widget.setText(str(value))
        elif kind=='check': widget.setChecked(value)
        elif kind=='combo': widget.setCurrentIndex(widget.findData(value))
        elif kind=='color': widget.set_color(value)
        elif kind in ('number','integer'): widget.setValue(value)
        else: widget.set_color(value)

    def stash_curve(self):
        draft=self.curve_drafts[self.curve_index]
        for path,(kind,widget) in self.fields.items():
            if path[0]!='curve': continue
            target=draft if path[1] in ('label','visible') else draft['style']; target[path[1]]=self.read_field(kind,widget)
        self.curve_selector.setItemText(self.curve_index,f'{self.curve_index+1} · {draft["label"]}')

    def change_curve(self,index):
        if index<0: return
        self.stash_curve(); self.curve_index=index
        self.plot.select_curve(index)
        for path,(kind,widget) in self.fields.items():
            if path[0]=='curve': self.write_field(kind,widget,self.initial(path))
        self.refresh_colors()

    def values(self):
        self.stash_curve(); result=deepcopy(self.base_style)
        for path,(kind,widget) in self.fields.items():
            if path[0]=='curve': continue
            value=self.read_field(kind,widget)
            if path[0]=='axes' and path[-1]=='scale':
                result['axes'][path[1]].update(log=value=='log',sqrt=value=='sqrt'); continue
            if path[0]=='axes' and path[-1]=='label' and self.base_style['axes'][path[1]]['label'] is None and value==axis_label(self.plot.display_scan,path[1]): value=None
            target=result
            for key in path[:-1]: target=target[key]
            target[path[-1]]=value
        result['curve']=deepcopy(self.curve_drafts[self.curve_index]['style'])
        for side in result['axes']:
            for key in ('minimum','maximum'): result['axes'][side][key]=self.plot.style['axes'][side][key]
        return validate_style(result)

    def apply(self):
        try:
            style=self.values(); self.plot.apply_style(style,self.curve_drafts)
        except (ValueError,TypeError) as error: self.error.setText(str(error)); return False
        self.plot.template_name=self.template_name; self.plot.template_path=self.template_path
        if id(self.plot.scan) in self.plot.committed:
            self.plot.committed[id(self.plot.scan)].update(template_name=self.template_name,template_path=self.template_path)
        self.refresh_template()
        self.base_style=deepcopy(style); self.error.clear(); return True

    def load_from(self,path,as_template=False):
        config_path=path
        style,curves=read_plot_config(path)
        for side in style['axes']:
            if style['axes'][side]['label'] is None: style['axes'][side]['label']=self.read_field(*self.fields[('axes',side,'label')])
        self.stash_curve(); self.base_style=style
        for index,draft in enumerate(self.curve_drafts):
            if index<len(curves): self.curve_drafts[index]=deepcopy(curves[index])
            else: draft['style']=deepcopy(style['curve'])
        for path,(kind,widget) in self.fields.items(): self.write_field(kind,widget,self.initial(path))
        for i,draft in enumerate(self.curve_drafts): self.curve_selector.setItemText(i,f'{i+1} · {draft["label"]}')
        for side in ('left','bottom','right','top'): self.tick_dependencies(side)
        self.refresh_colors()
        state=getattr(self.plot.window(),'session_state',None)
        if state: state.opened(config_path)
        if as_template:
            self.template_name=Path(config_path).stem; self.template_path=Path(config_path); self.refresh_template()
        self.error.clear()

    def apply_to_template(self):
        if not self.apply(): return False
        templates=self.plot.templates or PlotTemplates()
        destination=templates.writable_path(self.template_name,self.template_path)
        try: write_plot_config(destination,self.values(),self.curve_drafts)
        except (OSError,ValueError) as error: self.error.setText(str(error)); return False
        self.template_path=destination; self.plot.template_path=destination; self.refresh_template()
        self.plot.readout.setText('已应用并保存模板：'+self.template_name); return True

    def refresh_template(self):
        text='当前应用模板：\n'+self.plot.template_name
        if (self.template_name,self.template_path)!=(self.plot.template_name,self.plot.template_path): text+='\n待应用：'+self.template_name
        self.template_label.setText(text)
        self.template_label.setToolTip(str(self.template_path or 'global'))

    def choose_template(self):
        directory=self.template_path.parent if self.template_path else Path(__file__).resolve().parents[2]/'config/default/plot-templates'
        path,_=QFileDialog.getOpenFileName(self,'选择图片模板',str(directory),'图片模板 (*.json)')
        if path:
            try: self.load_from(path,as_template=True)
            except (OSError,ValueError) as error: self.error.setText(str(error))

    def export_to(self,path): write_plot_config(path,self.values(),self.curve_drafts)

    def load(self):
        state=getattr(self.plot.window(),'session_state',None)
        path,_=QFileDialog.getOpenFileName(self,'加载图片配置',state.directory if state else '', '图片配置 (*.json)')
        if path:
            try: self.load_from(path)
            except (OSError,ValueError) as error: self.error.setText(str(error))

    def export(self):
        path,_=QFileDialog.getSaveFileName(self,'导出图片配置','plot.json','图片配置 (*.json)')
        if path:
            try: self.export_to(path)
            except (OSError,ValueError) as error: self.error.setText(str(error))

    def accept(self):
        if self.apply(): super().accept()
