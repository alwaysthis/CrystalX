"""Scoped display editing, live previews and global appearance preset actions."""
from copy import deepcopy
from PyQt6.QtCore import Qt,QTimer,pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QWidget,QFormLayout,QCheckBox,
    QComboBox,QDoubleSpinBox,QPushButton,QGroupBox,QScrollArea,QLabel)
from .dialogs import QColorDialog,QFileDialog,QMessageBox
from .workspace_tabs import WorkspaceTabs
from .dialog_chrome import install_dialog_chrome
from .appearance import (DEFAULT_STYLE,FACTORY_STYLE,ATOM_KEYS,BOND_KEYS,CELL_KEYS,
    validate_settings,read_preset,write_preset)

from .math_ui import MathCheckBox as QCheckBox, MathComboBox as QComboBox, MathLabel as QLabel, MathPushButton as QPushButton

class ColorButton(QPushButton):
    colorChanged=pyqtSignal()
    def __init__(self):
        super().__init__(); self.setAutoDefault(False); self.setDefault(False); self.setFixedSize(28,28); self.value='#808080'; self.clicked.connect(self.pick); self.setToolTip('选择颜色')
    def set_color(self,value):
        self.value=value; self.setStyleSheet(f'QPushButton {{background:{value};border:1px solid #87998d;border-radius:5px;padding:0;}} QPushButton:hover {{border:2px solid #354f3e;}}'); self.colorChanged.emit()
    def pick(self):
        color=QColorDialog.getColor(QColor(self.value),self,'选择颜色')
        if color.isValid(): self.set_color(color.name())

class AxisColors(QWidget):
    colorChanged=pyqtSignal()
    def __init__(self):
        super().__init__(); row=QHBoxLayout(self); row.setContentsMargins(0,0,0,0); self.buttons=[]
        for name in 'abc':
            row.addWidget(QLabel(name)); button=ColorButton(); self.buttons.append(button); row.addWidget(button); button.colorChanged.connect(self.colorChanged)
        row.addStretch()
    def set_colors(self,values):
        for button,value in zip(self.buttons,values): button.set_color(value)
    def colors(self): return [button.value for button in self.buttons]

class DisplayStyleDialog(QDialog):
    def __init__(self,viewport,parent=None):
        super().__init__(parent); self.viewport=viewport; self.host=viewport.window(); self.fields={}; self.previews=[]; self.loading=True; self.force_all=False; self.atom_color_edited=False; self.atom_radius_edited=False; self.atom_radius_touched=False
        self.setWindowTitle('显示样式'); self.resize(980,720)
        layout=QVBoxLayout(self); top=QHBoxLayout(); scope_label=QLabel('当前设置作用于'); scope_label.setStyleSheet('QLabel {background:transparent;border:0;}'); top.addWidget(scope_label); self.scope=QComboBox(); self.scope.addItems(['当前对象','当前结构','全局']); self.scope.setCurrentIndex(1); top.addWidget(self.scope); top.addStretch(); layout.addLayout(top)
        self.tabs=WorkspaceTabs(); layout.addWidget(self.tabs)
        self.preview_timer=QTimer(self); self.preview_timer.setSingleShot(True); self.preview_timer.timeout.connect(self.refresh_previews)
        page,forms=self.page('晶格',['晶胞','方向轴与箭头'])
        cell,axes=forms
        self.check(cell,'cell_visible','显示晶胞'); self.combo(cell,'cell_line','线型',['实线','划线','点线','点划线','双点划线','圆柱']); self.number(cell,'cell_width','线宽 (px)',.1,40,.2)
        self.swatch(cell,'cell_color','颜色'); self.number(cell,'cell_roughness','粗糙度',0,1,.05); self.number(cell,'cell_ior','折射率',1,3,.05); self.number(cell,'cell_gloss','光泽',0,1,.05)
        self.check(axes,'axes_visible','显示方向轴'); self.check(axes,'axes_labels','显示方向标签'); self.combo(axes,'axes_mode','线型',['线框箭头','立体箭头'])
        colors=AxisColors(); self.register('axes_colors',colors); axes.addRow('颜色',colors)
        self.number(axes,'axes_width','线宽 (px)',.2,20,.2); self.number(axes,'axes_head_width','箭头宽度 (px)',1,40,1); self.number(axes,'axes_head_length','箭头长度 (px)',1,50,1)
        self.number(axes,'axes_roughness','粗糙度',0,1,.05); self.number(axes,'axes_ior','折射率',1,3,.05); self.number(axes,'axes_gloss','光泽',0,1,.05)
        page,forms=self.page('原子',['原子']); form=forms[0]
        self.check(form,'atoms_visible','显示原子'); self.number(form,'gloss','光泽',0,1,.05); self.check(form,'depth_fade','渐淡')
        self.combo(form,'atom_radius_type','半径类型',['原子半径','离子半径','范德华半径']); self.fields['atom_radius_type'].setToolTip('选择基础半径类型，或直接修改当前半径；默认半径表不会改变。离子半径采用代表性价态和配位数。'); self.number(form,'atom_radius','当前半径 (Å)',.01,10,.05); self.number(form,'radius_scale','显示比例',.1,3,.1)
        self.number(form,'atom_roughness','粗糙度',0,1,.05); self.number(form,'atom_ior','折射率',1,3,.05)
        self.swatch(form,'atom_color','当前颜色'); self.swatch(form,'atom_border_color','边框颜色'); self.number(form,'atom_border_width','边框粗细 (px)',0,10,.2)
        page,forms=self.page('键',['键']); form=forms[0]
        self.check(form,'bonds_visible','显示键'); self.combo(form,'bond_line','线型',['实线','点线','划线','双色键','单色键','渐变键']); self.number(form,'bond_width','线宽 (Å)',.01,2,.02)
        self.combo(form,'bond_color_mode','配色',['按元素','自定义']); self.swatch(form,'bond_color','颜色'); self.swatch(form,'bond_color2','第二颜色')
        self.bond_second_label=form.labelForField(self.fields['bond_color2']); self.cell_width_label=cell.labelForField(self.fields['cell_width'])
        footer=QHBoxLayout()
        for text,callback in [('加载',self.load),('导出',self.export),('恢复默认',self.restore_defaults),('设为默认',self.set_default)]:
            button=QPushButton(text); button.clicked.connect(callback); footer.addWidget(button)
        footer.addStretch()
        for text,callback in [('确定',self.accept),('应用',self.apply),('取消',self.reject)]:
            button=QPushButton(text); button.clicked.connect(callback); footer.addWidget(button)
        layout.addLayout(footer); install_dialog_chrome(self,layout)
        self.color_button=self.fields['cell_color']; self.bond_color_button=self.fields['bond_color']
        for key,field in self.fields.items(): setattr(self,key,field)
        self.set_values(viewport.appearance); self.baseline=self.values(); self.loading=False; self.dependencies(); self.refresh_previews(); self.scope.currentIndexChanged.connect(self.change_scope)

    def page(self,title,groups):
        page=QWidget(); row=QHBoxLayout(page); content=QWidget(); columns=QHBoxLayout(content); columns.setContentsMargins(0,0,0,0); forms=[]
        for name in groups:
            group=QGroupBox(name); form=QFormLayout(group); form.setHorizontalSpacing(8); form.setVerticalSpacing(8); columns.addWidget(group,1); forms.append(form)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.Shape.NoFrame); scroll.setWidget(content); row.addWidget(scroll,3)
        from .ui import CrystalViewport
        from .structure import Structure
        from .view_orientation import standard_orientation
        preview=CrystalViewport(); preview.setMinimumSize(210,240); preview.setMaximumWidth(280); preview.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        structure=Structure('preview',[[3.6 if title=='晶格' else 6.,0,0],[0,3.6,0],[0,0,3.6]],['Si','O'],[[.35,.5,.5],[.65,.5,.5]],[['T']*3]*2,['',''])
        preview.set_structure(structure); preview.camera=standard_orientation(structure.lattice); preview.zoom=1.35
        row.addWidget(preview,2); self.previews.append(preview); self.tabs.addTab(page,title); return page,forms
    def register(self,key,widget):
        self.fields[key]=widget
        signal=widget.colorChanged if isinstance(widget,(ColorButton,AxisColors)) else widget.toggled if isinstance(widget,QCheckBox) else widget.currentIndexChanged if isinstance(widget,QComboBox) else widget.valueChanged
        signal.connect(lambda *args,key=key:self.changed(key))
    def check(self,form,key,text):
        widget=QCheckBox(text); self.register(key,widget); form.addRow(widget)
    def combo(self,form,key,text,items):
        widget=QComboBox(); widget.addItems(items); self.register(key,widget); form.addRow(text,widget)
        if key=='atom_radius_type': widget.activated.connect(lambda *args:self.changed('atom_radius_type'))
    def number(self,form,key,text,low,high,step):
        widget=QDoubleSpinBox();
        if key.endswith('_ior'): widget.setToolTip('范围 1–3，默认 1.5。常见非金属材质约为 1–2；此处控制表面反光，不模拟透射。')
        if 'gloss' in key: widget.setToolTip('高光强度：0 为无高光，1 为完整的折射率反射；粗糙度单独控制高光宽度。')
        widget.setRange(low,high); widget.setSingleStep(step); widget.setDecimals(2); self.register(key,widget); form.addRow(text,widget)
    def swatch(self,form,key,text):
        widget=ColorButton(); self.register(key,widget); form.addRow(text,widget)
    def values(self):
        result=deepcopy(self.loaded)
        for key,widget in self.fields.items():
            result[key]=widget.value if isinstance(widget,ColorButton) else widget.colors() if isinstance(widget,AxisColors) else widget.isChecked() if isinstance(widget,QCheckBox) else widget.currentIndex() if isinstance(widget,QComboBox) else widget.value()
        if self.atom_color_edited: result['atom_color_mode']=1
        else: result['atom_color']=self.loaded['atom_color']; result['atom_color_mode']=self.loaded['atom_color_mode']
        source=self.fields['atom_radius_type'].currentIndex(); result['atom_radius_source']=source
        if self.atom_radius_edited:
            result['atom_radius_type']=3; result['atom_radius']=self.fields['atom_radius'].value()*.42 if self.atom_radius_touched else self.loaded['atom_radius']
        else: result['atom_radius_type']=source; result['atom_radius']=self.loaded['atom_radius']
        return validate_settings(result)
    def representative_element(self):
        structure=getattr(self.viewport,'structure',None)
        if not structure or not structure.elements: return 'Si'
        source=min(self.viewport.selected) if self.viewport.selected else 0
        return structure.elements[source]
    def base_radius(self,kind):
        from .render_material import RADII
        return RADII.get(self.representative_element(),{'atomic':1.,'ionic':1.,'vdw':1.5})[['atomic','ionic','vdw'][kind]]
    def set_values(self,values):
        self.loaded=validate_settings(values); self.loading=True
        self.atom_color_edited=self.loaded['atom_color_mode']==1; self.atom_radius_edited=self.loaded['atom_radius_type']==3; self.atom_radius_touched=False
        for key,widget in self.fields.items():
            value=self.loaded[key]
            if key=='atom_radius_type': value=self.loaded['atom_radius_source'] if self.atom_radius_edited else self.loaded['atom_radius_type']
            if key=='atom_radius': value=self.loaded['atom_radius']/.42 if self.atom_radius_edited else self.base_radius(self.loaded['atom_radius_type'])
            if key=='atom_color' and not self.atom_color_edited:
                from .ui import ELEMENT_COLORS
                value=QColor.fromRgbF(*ELEMENT_COLORS.get(self.representative_element(),[.6,.6,.6])).name()
            if isinstance(widget,ColorButton): widget.set_color(value)
            elif isinstance(widget,AxisColors): widget.set_colors(value)
            elif isinstance(widget,QCheckBox): widget.setChecked(value)
            elif isinstance(widget,QComboBox): widget.setCurrentIndex(value)
            else: widget.setValue(value)
        self.loading=False; self.dependencies()
    def changed(self,key=None):
        if self.loading: return
        if key=='atom_color': self.atom_color_edited=True
        if key=='atom_radius': self.atom_radius_edited=True; self.atom_radius_touched=True
        if key=='atom_radius_type':
            self.atom_radius_edited=False; self.atom_radius_touched=False; self.loading=True; self.fields['atom_radius'].setValue(self.base_radius(self.fields['atom_radius_type'].currentIndex())); self.loading=False
        self.dependencies(); self.preview_timer.start(40)
    def dependencies(self):
        for prefix,enabled in [('cell',self.fields['cell_line'].currentIndex()==5),('axes',self.fields['axes_mode'].currentIndex()==1)]:
            for suffix in ('roughness','ior','gloss'): self.fields[prefix+'_'+suffix].setEnabled(enabled)
        self.cell_width_label.setText('直径 (px)' if self.fields['cell_line'].currentIndex()==5 else '线宽 (px)')
        self.fields['atom_radius'].setEnabled(True); self.fields['atom_color'].setEnabled(True)
        two=self.fields['bond_line'].currentIndex() in (3,5)
        self.fields['bond_color2'].setVisible(two); self.bond_second_label.setVisible(two)
        self.fields['bond_color_mode'].setEnabled(two)
        custom=not two or self.fields['bond_color_mode'].currentIndex()==1
        self.fields['bond_color'].setEnabled(custom); self.fields['bond_color2'].setEnabled(custom)
    def refresh_previews(self):
        settings=self.values()
        for index,view in enumerate(self.previews):
            view.appearance=deepcopy(settings)
            if index==0: view.appearance.update(atoms_visible=False,bonds_visible=False)
            if index==1:
                view.appearance.update(cell_visible=False,axes_visible=False,bonds_visible=False); view.camera=[[1,0,0],[0,1,0],[0,0,1]]; view.zoom=2.8
            if index==2:
                view.appearance.update(cell_visible=False,axes_visible=False,atoms_visible=False); view.camera=[[1,0,0],[0,1,0],[0,0,1]]; view.zoom=2.8
            view.update()
    def change_scope(self,index):
        values=deepcopy(self.viewport.appearance)
        if index==0:
            for selected,overrides,keys in [(self.viewport.selected,self.viewport.atom_overrides,ATOM_KEYS),(self.viewport.selected_bonds,self.viewport.bond_overrides,BOND_KEYS),(self.viewport.selected_edges,self.viewport.edge_overrides,CELL_KEYS)]:
                if selected: values.update({k:v for k,v in overrides.get(min(selected),{}).items() if k in keys})
        if index==2 and hasattr(self.host,'appearance_store'): values=deepcopy(self.host.appearance_store.current)
        self.set_values(values); self.baseline=self.values(); self.force_all=False; self.refresh_previews()
    @staticmethod
    def update_view(view,patch):
        view.appearance.update(deepcopy(patch))
        if patch.get('atoms_visible'): view.hidden.clear()
        for overrides in (view.atom_overrides,view.bond_overrides,view.edge_overrides):
            for item in overrides.values():
                for key in patch: item.pop(key,None)
        view.update()
    def global_apply(self,patch):
        if hasattr(self.host,'appearance_store'):
            self.host.appearance_store.current.update(deepcopy(patch))
            for index in range(self.host.work_tabs.count()):
                page=self.host.work_tabs.widget(index)
                if hasattr(page,'viewport'): self.update_view(page.viewport,patch)
        else: self.update_view(self.viewport,patch)
    def apply(self):
        settings=self.values(); patch={k:v for k,v in settings.items() if self.force_all or self.baseline[k]!=v}; scope=self.scope.currentIndex()
        if scope==0:
            applied=False
            for selected,overrides,keys in [(self.viewport.selected,self.viewport.atom_overrides,ATOM_KEYS),(self.viewport.selected_bonds,self.viewport.bond_overrides,BOND_KEYS),(self.viewport.selected_edges,self.viewport.edge_overrides,CELL_KEYS)]:
                local={k:v for k,v in patch.items() if k in keys}
                if local and selected:
                    for index in selected: overrides.setdefault(index,{}).update(deepcopy(local))
                    if keys is ATOM_KEYS and local.get('atoms_visible'): self.viewport.hidden.difference_update(selected)
                    applied=True
            if patch and not applied:
                QMessageBox.warning(self,'请选择对象','请先选择要修改的原子、键或晶胞边。'); return False
            self.viewport.update()
        elif scope==1: self.update_view(self.viewport,patch)
        else: self.global_apply(patch)
        self.baseline=deepcopy(settings); self.force_all=False; return True
    def load_from(self,path):
        values=read_preset(path); self.scope.blockSignals(True); self.scope.setCurrentIndex(2); self.scope.blockSignals(False); self.set_values(values); self.force_all=True; self.refresh_previews()
    def load(self):
        path,_=QFileDialog.getOpenFileName(self,'加载显示设置','','显示设置 (*.json)')
        if path:
            try: self.load_from(path)
            except (OSError,ValueError) as error: QMessageBox.warning(self,'加载失败',str(error))
    def export_to(self,path): write_preset(path,self.values())
    def export(self):
        path,_=QFileDialog.getSaveFileName(self,'导出显示设置','display-style.json','显示设置 (*.json)')
        if path:
            try: self.export_to(path)
            except (OSError,ValueError) as error: QMessageBox.warning(self,'导出失败',str(error))
    def restore_defaults(self):
        values=self.host.appearance_store.defaults if hasattr(self.host,'appearance_store') else FACTORY_STYLE
        self.scope.blockSignals(True); self.scope.setCurrentIndex(2); self.scope.blockSignals(False); self.set_values(values); self.force_all=True; self.refresh_previews()
    def set_default(self):
        if not hasattr(self.host,'appearance_store'): return
        try: self.host.appearance_store.set_default(self.values())
        except (OSError,ValueError) as error: QMessageBox.warning(self,'保存默认失败',str(error)); return
        self.global_apply(self.values()); self.baseline=self.values(); self.force_all=False
    def accept(self):
        if self.apply(): super().accept()
