"""Lightweight scientific workspace; viewport is an interactive visual prototype."""
import math
from PyQt6.QtCore import Qt, QPointF, QSize, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient, QPolygonF, QLinearGradient
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QTreeWidget, QTreeWidgetItem, QSplitter, QFormLayout,
    QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QToolBar, QScrollArea, QGroupBox, QFileDialog, QMessageBox, QAbstractItemView, QTabWidget, QToolButton, QMenu, QPlainTextEdit, QButtonGroup)
from pathlib import Path
import logging
import json
ELEMENT_COLORS={entry["name"]:entry["color"] for entry in json.loads((Path(__file__).resolve().parents[2]/"config/default/VESTA.ovito-theme").read_text())["particle_types"]}
from .structure import read_poscar, write_poscar, cartesian, fractional, dot, cross
from .document import StructureDocument, TranslateCommand, SnapshotCommand
from . import operations
from .data_panels import AtomList, CoordinateDialog
from .icons import icon
from .title_bar import TitleBar
from .cell_preview import CellPreview
from .display_geometry import periodic_images

STYLE = """
QWidget { background:#fdfefd; color:#29352f; font-family:'Segoe UI','Microsoft YaHei'; font-size:13px; }
QMainWindow,QMenuBar,QToolBar { background:#fafcfb; }
QToolBar { border-bottom:1px solid #dce3dd; spacing:12px; padding:12px; }
QPushButton { border:1px solid #dce3dd; border-radius:5px; padding:9px 14px; background:#fff; }
QPushButton:disabled { color:#a4ada7; background:#f1f4f0; }
QPushButton:hover { background:#e3eee7; border-color:#94b49f; }
QPushButton:checked { background:#dbece1; color:#286345; }
QTreeWidget,QTableWidget { border:0; background:#fafcfb; alternate-background-color:#f7faf8; }
QTreeWidget::item { padding:9px; }
QTreeWidget::item:selected { background:#deece2; color:#286345; }
QGroupBox { border:0; margin-top:18px; padding-top:22px; font-weight:600; }
QGroupBox::title { subcontrol-origin:margin; top:4px; font-weight:bold; }
QDoubleSpinBox,QComboBox { background:white; border:1px solid #dce3dd; border-radius:4px; padding:6px; }
QHeaderView::section { background:#f7faf8; padding:6px; border:0; }
QStatusBar { border-top:1px solid #dce3dd; color:#718078; }
QSplitter::handle { background:#e0e6e0; width:1px; height:1px; }
"""

class CrystalViewport(QWidget):
    picked = pyqtSignal(int)
    boxed = pyqtSignal(set)
    clicked = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.yaw, self.pitch, self.zoom = .45, -.35, 1.
        self.last = None
        self.setMinimumSize(420, 360)
        self.setToolTip("拖动旋转 · 滚轮缩放 · 单击原子选择")
        self.atoms = []
        self.corners = []
        self.elements = []
        self.selected = set()
        self.press = None
        self.click_timer=QTimer(self); self.click_timer.setSingleShot(True); self.click_timer.timeout.connect(self.clicked.emit)
        self.mode="rotate"; self.pan=QPointF(0,0); self.camera=None; self.box=None; self.lattice=None

    def set_structure(self, structure):
        self.lattice=structure.lattice if structure else None
        self.elements = structure.elements if structure else []
        if structure is None:
            self.atoms=[]; self.corners=[]; self.update(); return
        corners=[cartesian((x,y,z),structure.lattice) for x in (0,1) for y in (0,1) for z in (0,1)]
        points,self.sources=periodic_images(structure)
        self.elements=[structure.elements[i] for i in self.sources]
        all_points=corners+points
        low=[min(p[i] for p in all_points) for i in range(3)]
        high=[max(p[i] for p in all_points) for i in range(3)]
        center=[(a+b)/2 for a,b in zip(low,high)]
        span=max(b-a for a,b in zip(low,high)) or 1
        normalize=lambda p: tuple((v-c)/span for v,c in zip(p,center))
        self.atoms=list(map(normalize,points)); self.corners=list(map(normalize,corners)); self.update()

    def project(self, point):
        x,y,z=self.camera_point(point)
        size = min(self.width(),self.height())*.54*self.zoom
        return QPointF(self.width()/2+x*size+self.pan.x(),self.height()/2-y*size+self.pan.y()),z

    def camera_point(self,point):
        if self.camera: return tuple(dot(row,point) for row in self.camera)
        x,y,z=point
        x,z=x*math.cos(self.yaw)+z*math.sin(self.yaw),-x*math.sin(self.yaw)+z*math.cos(self.yaw)
        return x,y*math.cos(self.pitch)-z*math.sin(self.pitch),y*math.sin(self.pitch)+z*math.cos(self.pitch)

    def rotate_camera(self,dx,dy):
        """Compose screen-space rotations onto the current camera basis."""
        if self.camera is None:
            columns=[self.camera_point(axis) for axis in [(1,0,0),(0,1,0),(0,0,1)]]
            self.camera=[list(row) for row in zip(*columns)]
        yaw,pitch=dx*.01,dy*.01
        cy,sy,cp,sp=math.cos(yaw),math.sin(yaw),math.cos(pitch),math.sin(pitch)
        x,y,z=self.camera
        new_x=[cy*a+sy*b for a,b in zip(x,z)]
        new_z=[-sy*a+cy*b for a,b in zip(x,z)]
        self.camera=[new_x,[cp*a-sp*b for a,b in zip(y,new_z)],[sp*a+cp*b for a,b in zip(y,new_z)]]

    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor('#fdfefd'))
        corners=self.corners
        p.setPen(QPen(QColor('#9ba99f'),1))
        for i,a in enumerate(corners):
            for b in corners[i+1:]:
                if (i ^ corners.index(b)) in (1,2,4): p.drawLine(self.project(a)[0],self.project(b)[0])
        for i in sorted(range(len(self.atoms)),key=lambda i:self.project(self.atoms[i])[1]):
            point,_=self.project(self.atoms[i]); radius=12*self.zoom
            color=QColor.fromRgbF(*ELEMENT_COLORS.get(self.elements[i],[.6,.6,.6]))
            gradient=QRadialGradient(point-QPointF(radius*.3,radius*.35),radius*1.6)
            gradient.setColorAt(0,color.lighter(160)); gradient.setColorAt(.55,color); gradient.setColorAt(1,color.darker(180))
            p.setPen(QPen(QColor('#2e9d62'),3) if self.sources[i] in self.selected else QPen(Qt.PenStyle.NoPen)); p.setBrush(gradient); p.drawEllipse(point,radius,radius)
        origin=QPointF(65,self.height()-75)
        if self.lattice:
            for index in sorted(range(3),key=lambda i:self.camera_point(self.lattice[i])[2]):
                vector=self.lattice[index]; length=math.sqrt(dot(vector,vector))
                unit=[v/length for v in vector]
                x,y,z=self.camera_point(unit); end=origin+QPointF(x*45,-y*45)
                delta=end-origin; screen=math.hypot(delta.x(),delta.y())
                color=QColor(['#d84942','#48a866','#498de0'][index])
                if screen<3:
                    p.setPen(Qt.PenStyle.NoPen); p.setBrush(color); p.drawEllipse(origin,5,5)
                else:
                    direction=delta/screen; normal=QPointF(-direction.y(),direction.x()); base=end-direction*12
                    gradient=QLinearGradient(origin-normal*3,origin+normal*3); gradient.setColorAt(0,color.darker(170)); gradient.setColorAt(.45,color.lighter(160)); gradient.setColorAt(1,color)
                    p.setPen(Qt.PenStyle.NoPen); p.setBrush(gradient)
                    p.drawPolygon(QPolygonF([origin-normal*3,base-normal*3,base+normal*3,origin+normal*3]))
                    p.setBrush(color); p.drawPolygon(QPolygonF([end,base-normal*7,base+normal*7]))
                    p.setBrush(color.lighter(150)); p.drawPolygon(QPolygonF([end,base,base+normal*7]))
                p.setPen(color.darker(130)); p.drawText(end+QPointF(6,-4),'abc'[index])
        if self.box:
            p.setPen(QPen(QColor('#399165'),1,Qt.PenStyle.DashLine)); p.setBrush(QColor(60,150,100,30)); p.drawRect(self.box)

    def mousePressEvent(self,event): self.last=event.position(); self.press=event.position(); self.dragged=False
    def mouseMoveEvent(self,event):
        if self.last is not None:
            self.dragged = self.dragged or (event.position()-self.press).manhattanLength()>4
            delta=event.position()-self.last
            if self.mode=='pan': self.pan+=delta
            elif self.mode=='zoom': self.zoom=max(.1,min(10,self.zoom*math.exp(-delta.y()*.01)))
            elif self.mode=='rotate':
                if self.camera: self.camera=None
                self.yaw+=delta.x()*.01; self.pitch+=delta.y()*.01
            elif self.mode=='select': self.box=QRectF(self.press,event.position()).normalized()
            self.last=event.position(); self.update()
    def hit_atom(self,position):
        hits=[i for i,point in enumerate(self.atoms) if math.hypot(self.project(point)[0].x()-position.x(),self.project(point)[0].y()-position.y())<=12*self.zoom+3]
        if hits: self.picked.emit(self.sources[max(hits,key=lambda i:self.project(self.atoms[i])[1])])
        else: self.clicked.emit()

    def mouseDoubleClickEvent(self,event):
        self.click_timer.stop(); self.hit_atom(event.position()); self.last=None; self.press=None; self.box=None; self.update()

    def mouseReleaseEvent(self,event):
        if self.press is not None and self.mode=='select':
            if self.dragged:
                rect=QRectF(self.press,event.position()).normalized()
                self.boxed.emit({self.sources[i] for i,point in enumerate(self.atoms) if rect.contains(self.project(point)[0])})
            else: self.hit_atom(event.position())
        if self.press is not None and not self.dragged and self.mode!='select':
            from PyQt6.QtWidgets import QApplication
            self.click_timer.start(QApplication.doubleClickInterval())
        self.last=None; self.press=None; self.box=None; self.update()

    def wheelEvent(self,event):
        self.zoom=max(.35,min(2.5,self.zoom* (1.1 if event.angleDelta().y()>0 else .9))); self.update()

class MainWindow(QMainWindow):
    def __init__(self,config):
        super().__init__()
        self.document=StructureDocument(); self.selected=set(); self.path=None
        self.resize(config['window_width'],config['window_height']); self.setStyleSheet(STYLE)
        self.buttons={}
        file_menu=self.menuBar().addMenu('文件')
        for name,callback,shortcut in [('打开',self.open_file,'Ctrl+O'),('保存',self.save_file,'Ctrl+S'),('导出 POSCAR',lambda:self.save_file(True),'Ctrl+Shift+S')]:
            action=file_menu.addAction(name); action.setShortcut(shortcut); action.triggered.connect(callback); self.buttons[name]=action
        file_menu.addSeparator(); file_menu.addAction('退出',self.close)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        menu_bar=self.menuBar()
        self.title_bar=TitleBar(self)
        self.buttons['撤销']=self.title_bar.undo_button; self.buttons['重做']=self.title_bar.redo_button
        for name,callback,shortcut in [('撤销',self.undo,'Ctrl+Z'),('重做',self.redo,'Ctrl+Y')]:
            action=self.addAction(name); action.setShortcut(shortcut); action.triggered.connect(callback)
        chrome=QWidget(); chrome_layout=QVBoxLayout(chrome); chrome_layout.setContentsMargins(0,0,0,0); chrome_layout.setSpacing(0)
        chrome_layout.addWidget(self.title_bar); chrome_layout.addWidget(menu_bar); self.setMenuWidget(chrome)
        self.file_menu_bar=menu_bar
        self.statusBar().setSizeGripEnabled(True)
        outer=QSplitter(Qt.Orientation.Vertical); self.setCentralWidget(outer)
        root=QSplitter(); outer.addWidget(root)
        left=QWidget(); left.setMinimumWidth(300); left_layout=QVBoxLayout(left); left_layout.setContentsMargins(8,8,8,8)
        self.cell_label=QLabel(); self.cell_label.setMargin(8); lattice_group=QGroupBox("晶格参数"); lattice_layout=QHBoxLayout(lattice_group); lattice_layout.addWidget(self.cell_label); self.cell_preview=CellPreview(); lattice_layout.addWidget(self.cell_preview,1); left_layout.addWidget(lattice_group)
        header=QHBoxLayout(); title=QLabel('原子列表'); title.setStyleSheet('font-weight:bold; padding-top:4px;'); header.addWidget(title); header.addStretch()
        more=QToolButton(); more.setIcon(icon('more')); more.setToolTip('原子列表菜单'); more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        atom_menu=QMenu(more); atom_menu.addAction('显示原子坐标',self.show_coordinates); more.setMenu(atom_menu); header.addWidget(more); left_layout.addLayout(header)
        self.atom_list=AtomList(); self.atom_list.atom_requested.connect(self.pick); left_layout.addWidget(self.atom_list); root.addWidget(left)
        self.coordinate_dialog=CoordinateDialog(self); self.coordinate_dialog.selection_changed.connect(self.set_selection)
        center=QWidget(); center_layout=QVBoxLayout(center); center_layout.setContentsMargins(0,0,0,0); center_layout.setSpacing(0)
        views=QHBoxLayout(); views.setContentsMargins(8,6,8,6); views.setSpacing(5); views.addSpacing(38); views.addStretch()
        self.view_buttons=[]
        for index,name in enumerate(['a','b','c','a*','b*','c*','等轴测']):
            button=QToolButton(); button.setIcon(icon('view'+str(index))); button.setIconSize(QSize(25,25)); button.setFixedSize(34,32); button.setToolTip('沿 +'+name+' 方向观察' if index<6 else '等轴测')
            button.clicked.connect(lambda checked=False,index=index:self.set_view(index)); views.addWidget(button); self.view_buttons.append(button)
        fit=QToolButton(); fit.setIcon(icon('fit')); fit.setToolTip('重置视图及缩放'); fit.clicked.connect(self.reset_view); fit.setFixedSize(34,32); fit.setIconSize(QSize(24,24)); views.addWidget(fit); views.addStretch(); views.addSpacing(38)
        center_layout.addLayout(views)
        self.viewport=CrystalViewport(); self.viewport.picked.connect(self.pick); self.viewport.boxed.connect(self.add_selection); self.viewport.clicked.connect(self.clear_selection); center_layout.addWidget(self.viewport); root.addWidget(center)
        tools=QWidget(center); tools.move(4,4); tool_layout=QVBoxLayout(tools); tool_layout.setContentsMargins(0,0,0,0); tool_layout.setSpacing(3)
        self.tool_group=QButtonGroup(self); self.tool_group.setExclusive(True)
        for symbol,name,mode in [('↖','旋转视图（默认）','rotate'),('□','框选 / 点选原子（Ctrl 叠加）','select'),('✥','平移视图','pan'),('⊕','拖动缩放','zoom')]:
            button=QToolButton(); button.setIcon(icon(mode)); button.setToolTip(name); button.setCheckable(True); button.setIconSize(QSize(21,21)); button.setFixedSize(30,30)
            button.clicked.connect(lambda checked=False,mode=mode:self.set_tool(mode)); self.tool_group.addButton(button); tool_layout.addWidget(button)
            button.setChecked(mode=='rotate')
        tools.adjustSize(); tools.raise_()
        self.messages=QPlainTextEdit(); self.messages.setReadOnly(True); self.messages.setMaximumBlockCount(1000)
        info=QWidget(); info_layout=QVBoxLayout(info); info_layout.setContentsMargins(6,4,6,4)
        info_header=QHBoxLayout(); info_header.addWidget(QLabel('交互信息')); info_header.addStretch()
        info_layout.addLayout(info_header); info_layout.addWidget(self.messages); outer.addWidget(info); outer.setSizes([650,140])
        self.output('就绪：打开结构后可选择原子、调整视角并执行编辑。')
        panel=QWidget(); form=QVBoxLayout(panel)
        form.addWidget(QLabel("结构操作"))
        self.coordinates=QComboBox(); self.coordinates.addItems(['Direct','Cartesian (Å)']); self.coordinates.currentIndexChanged.connect(self.refresh); form.addWidget(self.coordinates)
        self.selection_label=QLabel(); form.addWidget(self.selection_label)
        all_button=QPushButton('全选原子'); all_button.clicked.connect(self.select_all); form.addWidget(all_button)
        group=QGroupBox('平移所选原子'); fields=QFormLayout(group); self.translation=[]
        for axis in ['x','y','z']:
            spin=QDoubleSpinBox(); spin.setRange(-10000,10000); spin.setDecimals(6); spin.setSingleStep(.1); fields.addRow(axis,spin); self.translation.append(spin)
        self.apply_button=QPushButton('应用平移'); self.apply_button.clicked.connect(self.translate); fields.addRow(self.apply_button); form.addWidget(group)
        self.edit_buttons=[]
        group=QGroupBox('原子操作'); controls=QVBoxLayout(group)
        for title,callback in [('复制所选（使用上方平移量）',self.duplicate_atoms),('删除所选',self.delete_atoms),('Wrap 所选到晶胞',lambda:self.run_operation(operations.wrap,self.selected))]:
            button=QPushButton(title); button.clicked.connect(callback); controls.addWidget(button); self.edit_buttons.append(button)
        form.addWidget(group)
        group=QGroupBox('旋转所选 · 右手规则'); fields=QFormLayout(group)
        self.rotation_axis=QComboBox(); self.rotation_axis.addItems(['Cartesian X','Cartesian Y','Cartesian Z']); fields.addRow('轴',self.rotation_axis)
        self.rotation_angle=QDoubleSpinBox(); self.rotation_angle.setRange(-360,360); self.rotation_angle.setValue(90); self.rotation_angle.setSuffix(' °'); fields.addRow('角度',self.rotation_angle)
        self.rotation_center=QComboBox(); self.rotation_center.addItems(['所选原子几何中心','笛卡尔原点']); fields.addRow('中心',self.rotation_center)
        button=QPushButton('应用旋转'); button.clicked.connect(self.rotate_atoms); fields.addRow(button); self.edit_buttons.append(button); form.addWidget(group)
        group=QGroupBox('选择性弛豫 · 所选原子'); controls=QVBoxLayout(group); self.flag_boxes=[]
        for axis in 'XYZ':
            checkbox=QCheckBox(f'{axis} 方向允许弛豫 (T)'); checkbox.setChecked(True); controls.addWidget(checkbox); self.flag_boxes.append(checkbox)
        button=QPushButton('应用 T/F 标志'); button.clicked.connect(lambda:self.run_operation(operations.set_flags,self.selected,['T' if box.isChecked() else 'F' for box in self.flag_boxes])); controls.addWidget(button); self.edit_buttons.append(button); form.addWidget(group)
        group=QGroupBox('对角超胞 · 整个结构'); fields=QFormLayout(group); self.repeats=[]
        for axis in 'abc':
            spin=QSpinBox(); spin.setRange(1,20); fields.addRow(axis,spin); self.repeats.append(spin)
        self.supercell_button=QPushButton('生成超胞'); self.supercell_button.clicked.connect(self.make_supercell); fields.addRow(self.supercell_button); form.addWidget(group)
        note=QLabel('默认拖动旋转 · 滚轮缩放\n任意工具双击选择；Ctrl 叠加。\n第二个工具支持框选；单击画布清空。\n平移单位随坐标模式切换。\n周期边界显示已启用；不显示化学键。'); note.setWordWrap(True); form.addWidget(note); form.addStretch()
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(panel); root.addWidget(scroll); root.setSizes([330,700,300]); root.setStretchFactor(1,1)
        self.refresh()

    def refresh(self,*args):
        structure=self.document.structure
        self.setWindowTitle('CrystalX')
        self.cell_preview.lattice=structure.lattice if structure else None; self.cell_preview.update()
        if structure: self.selected.intersection_update(range(len(structure.elements)))
        self.viewport.selected=self.selected; self.viewport.set_structure(structure)
        self.atom_list.refresh(structure,self.selected)
        self.coordinate_dialog.refresh(structure,self.selected)
        if structure:
            vectors=structure.lattice
            lengths=[dot(v,v)**.5 for v in vectors]
            angles=[math.degrees(math.acos(max(-1,min(1,dot(vectors[i],vectors[j])/(lengths[i]*lengths[j]))))) for i,j in [(1,2),(0,2),(0,1)]]
            self.cell_label.setText('\n'.join(f'{key}   {value:.3f} {unit}' for key,value,unit in zip(['a','b','c','α','β','γ'],lengths+angles,['Å']*3+['°']*3)))
        else: self.cell_label.setText('晶格参数\n\n尚未打开结构')
        self.selection_label.setText(f'已选择 {len(self.selected)} 个原子')
        self.buttons['保存'].setEnabled(structure is not None); self.buttons['导出 POSCAR'].setEnabled(structure is not None)
        self.buttons['撤销'].setEnabled(self.document.index>0); self.buttons['重做'].setEnabled(self.document.index<len(self.document.commands))
        self.apply_button.setEnabled(bool(self.selected))
        for button in self.edit_buttons: button.setEnabled(bool(self.selected))
        self.supercell_button.setEnabled(structure is not None)
        self.statusBar().showMessage(f"原子 {len(structure.elements) if structure else 0}  |  已选 {len(self.selected)}  |  {self.coordinates.currentText()}")

    def confirm_changes(self):
        if not self.document.dirty: return True
        answer=QMessageBox.question(self,'未保存修改','是否保存当前结构？',QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
        if answer==QMessageBox.StandardButton.Cancel: return False
        if answer==QMessageBox.StandardButton.Save: return self.save_file()
        return True

    def open_file(self):
        if not self.confirm_changes(): return
        path,_=QFileDialog.getOpenFileName(self,'打开结构','','VASP 结构 (POSCAR* CONTCAR* *.vasp);;所有文件 (*)')
        if path: self.load_path(path)

    def load_path(self,path):
        try: structure=read_poscar(path)
        except (ValueError,OSError) as error:
            self.output(f'打开失败：{error}'); logging.exception('Open structure failed'); QMessageBox.warning(self,'打开失败',str(error)); return False
        self.document=StructureDocument(structure); self.path=Path(path); self.selected=set(); self.reset_view(); self.refresh(); self.output(f"已打开 {path}，{len(structure.elements)} 个原子"); return True

    def save_file(self,save_as=False):
        if self.document.structure is None: return False
        path=str(self.path) if self.path and not save_as else ''
        if not path:
            path,_=QFileDialog.getSaveFileName(self,'导出 POSCAR','POSCAR','VASP 结构 (*)')
        elif Path(path).exists():
            if QMessageBox.question(self,'覆盖文件',f'覆盖 {path}？')!=QMessageBox.StandardButton.Yes: return False
        if not path: return False
        try: write_poscar(self.document.structure,path,self.coordinates.currentIndex()==0)
        except (ValueError,OSError) as error:
            self.output(f'保存失败：{error}'); logging.exception('Save structure failed'); QMessageBox.warning(self,'保存失败',str(error)); return False
        self.path=Path(path); self.document.saved_index=self.document.index; self.refresh(); self.output(f"已保存 {path}"); return True

    def select_all(self):
        self.selected=set(range(len(self.document.structure.elements))) if self.document.structure else set(); self.refresh()

    def pick(self,index):
        self.update_selection({index})
        self.refresh(); self.output(f"拾取原子 {index+1}")

    def set_selection(self,indices):
        self.update_selection(indices); self.refresh()
        self.output(f'选择原子：{", ".join(str(i+1) for i in sorted(indices)) or "无"}')

    def show_coordinates(self):
        self.coordinate_dialog.show(); self.coordinate_dialog.raise_()

    def output(self,text):
        from datetime import datetime
        self.messages.appendPlainText(f'[{datetime.now():%H:%M:%S}] {text}')

    def set_tool(self,mode):
        self.viewport.mode=mode
        self.viewport.setCursor({'select':Qt.CursorShape.ArrowCursor,'rotate':Qt.CursorShape.ArrowCursor,'pan':Qt.CursorShape.OpenHandCursor,'zoom':Qt.CursorShape.SizeVerCursor}[mode])
        self.output('视口工具：'+{'select':'选择','rotate':'旋转','pan':'平移','zoom':'缩放'}[mode])

    def update_selection(self,indices):
        from PyQt6.QtWidgets import QApplication
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier: self.selected.update(indices)
        else: self.selected=set(indices)

    def add_selection(self,indices): self.set_selection(indices)

    def clear_selection(self):
        self.selected.clear(); self.refresh(); self.output('已取消全部选择')

    def fit_view(self):
        self.viewport.zoom=1.; self.viewport.pan=QPointF(0,0); self.viewport.update()
        self.output('缩放至结构，保持当前视角')

    def set_view(self,index):
        if index==6:
            self.viewport.camera=None; self.viewport.yaw=.45; self.viewport.pitch=-.35
        else:
            lattice=self.document.structure.lattice if self.document.structure else [[1,0,0],[0,1,0],[0,0,1]]
            i=index%3
            direction=lattice[i] if index<3 else cross(lattice[(i+1)%3],lattice[(i+2)%3])
            if index>=3 and dot(lattice[0],cross(lattice[1],lattice[2]))<0: direction=[-v for v in direction]
            length=math.sqrt(dot(direction,direction)); forward=[v/length for v in direction]
            up=[0,0,1] if abs(forward[2])<.95 else [0,1,0]
            right=cross(up,forward); length=math.sqrt(dot(right,right)); right=[v/length for v in right]
            self.viewport.camera=[right,cross(forward,right),forward]
        self.viewport.update(); self.output('视角：'+['a','b','c','a*','b*','c*','等轴测'][index])

    def translate(self):
        if not self.selected: return
        vector=[spin.value() for spin in self.translation]
        if not any(vector): return
        if self.coordinates.currentIndex(): vector=fractional(vector,self.document.structure.lattice)
        self.document.execute(TranslateCommand(self.document.structure,self.selected,vector)); self.refresh(); self.output(f"平移 {len(self.selected)} 个原子，Direct 位移 {vector}")

    def run_operation(self,operation,*args,clear_selection=False):
        if self.document.structure is None: return
        try:
            command=SnapshotCommand(self.document.structure,operation,*args)
        except ValueError as error:
            QMessageBox.warning(self,'无法执行',str(error)); return
        if command.before==command.after: return
        self.document.execute(command)
        self.output("完成操作："+operation.__name__)
        if clear_selection: self.selected=set()
        self.refresh()

    def duplicate_atoms(self):
        if not self.selected: return
        shift=[spin.value() for spin in self.translation]
        if not any(shift):
            QMessageBox.warning(self,'复制原子','请先设置非零平移量，避免生成重合原子。'); return
        if self.coordinates.currentIndex(): shift=fractional(shift,self.document.structure.lattice)
        self.run_operation(operations.duplicate,self.selected,shift,clear_selection=True)

    def delete_atoms(self):
        if not self.selected: return
        if QMessageBox.question(self,'删除原子',f'删除所选 {len(self.selected)} 个原子？可撤销。')==QMessageBox.StandardButton.Yes:
            self.run_operation(operations.delete,self.selected,clear_selection=True)

    def rotate_atoms(self):
        if not self.selected: return
        axis=[int(i==self.rotation_axis.currentIndex()) for i in range(3)]
        points=self.document.structure.cartesian_positions
        center=[sum(points[i][j] for i in self.selected)/len(self.selected) for j in range(3)] if self.rotation_center.currentIndex()==0 else [0,0,0]
        self.run_operation(operations.rotate,self.selected,axis,self.rotation_angle.value(),center)

    def make_supercell(self):
        if self.document.structure is None: return
        repeats=[spin.value() for spin in self.repeats]
        count=len(self.document.structure.elements)*math.prod(repeats)
        if count>10000:
            QMessageBox.warning(self,'超胞过大','当前轻量视口限制为 10000 个原子，请减小超胞倍数。'); return
        if repeats==[1,1,1]: return
        if QMessageBox.question(self,'生成超胞',f'晶格将扩展为 {repeats}，原子数为 {count}。继续？')==QMessageBox.StandardButton.Yes:
            self.run_operation(operations.supercell,repeats,clear_selection=True)

    def undo(self): self.document.undo(); self.selected=set(); self.refresh(); self.output("撤销")
    def redo(self): self.document.redo(); self.selected=set(); self.refresh(); self.output("重做")

    def closeEvent(self,event):
        if self.confirm_changes(): event.accept()
        else: event.ignore()

    def reset_view(self):
        self.viewport.camera=None; self.viewport.yaw=.45; self.viewport.pitch=-.35
        self.fit_view()
