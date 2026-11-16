"""Lightweight scientific workspace; viewport is an interactive visual prototype."""
import math
from copy import deepcopy
from PyQt6.QtCore import Qt, QEvent, QPointF, QSize, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient, QPolygonF, QLinearGradient, QIcon, QImage
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QTreeWidget, QTreeWidgetItem, QSplitter, QFormLayout,
    QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QToolBar, QScrollArea, QGroupBox, QFileDialog, QMessageBox, QAbstractItemView, QTabWidget, QToolButton, QMenu, QPlainTextEdit, QButtonGroup, QSlider, QWidgetAction)
from pathlib import Path
import logging
import json
ELEMENT_COLORS={entry["name"]:entry["color"] for entry in json.loads((Path(__file__).resolve().parents[2]/"config/default/VESTA.ovito-theme").read_text())["particle_types"]}
ELEMENT_RADII={entry["name"]:entry["display_radius"] for entry in json.loads((Path(__file__).resolve().parents[2]/"config/default/VESTA.ovito-theme").read_text())["particle_types"]}
from .structure import read_poscar, write_poscar, cartesian, fractional, dot, cross
from .document import StructureDocument, TranslateCommand, SnapshotCommand
from . import operations
from .data_panels import AtomList
from .structure_editor import StructureEditor
from .bond_editor import BondEditor
from .visibility import VisibilityMenu
from .icons import icon
from .title_bar import TitleBar
from .cell_preview import CellPreview, arrow
from .theme import BASE_STYLE as STYLE, CONTROLS,WheelGuard,ICON_BUTTONS,WORKSPACE_TABS,stepper_css,AXIS_COLORS,SLIDERS,PANELS,PANE_FRAMES,apply_menu_theme,TITLE_BAR_HEIGHT
from .sphere_material import fogged_sphere
from .appearance import AppearanceStore
from .render_material import radius as material_radius, segment as material_segment, axis_arrow
from .view_orientation import standard_orientation
from .dialogs import QMessageBox,QFileDialog
from .display_style import DEFAULT_STYLE,DisplayStyleDialog
from .cif_io import read_cif
from .display_geometry import periodic_images
from .bonds import automatic_bonds,DEFAULT_RANGES
from .panels import framed_panel,WelcomeLogo



class CrystalViewport(QWidget):
    picked = pyqtSignal(int)
    boxed = pyqtSignal(set)
    clicked = pyqtSignal()
    delete_requested=pyqtSignal()
    def __init__(self):
        super().__init__()
        self.yaw, self.pitch, self.zoom = .45, -.35, 1.
        self.last = None
        self.setMinimumSize(420, 360)
        self.setToolTip("拖动旋转 · 滚轮缩放 · 双击选择原子、键或晶胞边")
        self.hidden=set(); self.matched_bond_ranges=set(); self.bond_ranges=DEFAULT_RANGES; self.bonds=[]; self.bond_key=None
        self.atoms = []
        self.corners = []
        self.elements = []
        self.selected = set(); self.selected_bonds=set(); self.selected_edges=set()
        self.atom_overrides={}; self.bond_overrides={}; self.edge_overrides={}
        self.press = None
        self.click_timer=QTimer(self); self.click_timer.setSingleShot(True); self.click_timer.timeout.connect(self.clicked.emit)
        self.appearance=deepcopy(DEFAULT_STYLE); self.style_dialog=None; self.bond_nodes=[]; self.bond_links=[]; self.cell_edges=[]
        self.mode="rotate"; self.pan=QPointF(0,0); self.camera=None; self.box=None; self.lattice=None; self.perspective=0; self.span=1

    def set_structure(self, structure):
        self.lattice=structure.lattice if structure else None
        self.elements = structure.elements if structure else []
        if structure is None:
            self.atoms=[]; self.bonds=[]; self.bond_key=None; self.corners=[]; self.update(); return
        self.hidden.intersection_update(range(len(structure.elements)))
        corners=[cartesian((x,y,z),structure.lattice) for x in (0,1) for y in (0,1) for z in (0,1)]
        points,self.sources=periodic_images(structure)
        self.elements=[structure.elements[i] for i in self.sources]
        all_points=corners+points
        low=[min(p[i] for p in all_points) for i in range(3)]
        high=[max(p[i] for p in all_points) for i in range(3)]
        center=[(a+b)/2 for a,b in zip(low,high)]
        span=max(b-a for a,b in zip(low,high)) or 1
        self.span=span
        normalize=lambda p: tuple((v-c)/span for v,c in zip(p,center))
        self.atoms=list(map(normalize,points)); self.corners=list(map(normalize,corners))
        key=(tuple(tuple(v) for v in structure.lattice),tuple(structure.elements),tuple(tuple(v) for v in structure.positions),tuple((pair,tuple(tuple(r) for r in bounds)) for pair,bounds in sorted(self.bond_ranges.items())))
        if key!=self.bond_key:
            self.selected_bonds.clear(); self.bond_overrides.clear()
            self.matched_bond_ranges=set()
            self.bond_segments=automatic_bonds(structure,self.bond_ranges,matched_ranges=self.matched_bond_ranges); self.bond_key=key
        self.bonds=[(normalize(a),normalize(b),i,j) for a,b,i,j in self.bond_segments]
        self.structure=structure
        atom_nodes={tuple(round(v,8) for v in point):i for i,point in enumerate(self.atoms)}
        self.bond_nodes=[]; self.bond_links=[]; nodes={}
        for a,b,i,j in self.bonds:
            link=[]
            for point in (a,b):
                token=tuple(round(v,8) for v in point)
                if token not in nodes:
                    nodes[token]=len(self.bond_nodes); self.bond_nodes.append((point,atom_nodes.get(token)))
                link.append(nodes[token])
            self.bond_links.append((*link,i,j))
        self.update()

    def project(self, point):
        x,y,z=self.camera_point(point)
        size = min(self.width(),self.height())*.54*self.zoom*self.perspective_scale(z)
        return QPointF(self.width()/2+x*size+self.pan.x(),self.height()/2-y*size+self.pan.y()),z

    def perspective_scale(self,z): return 1/max(.25,1-z*self.perspective*.55)

    def object_appearance(self,kind,index):
        overrides=self.atom_overrides if kind=='atom' else self.bond_overrides if kind=='bond' else self.edge_overrides
        return self.appearance | overrides[index] if index in overrides else self.appearance

    def clear_object_styles(self):
        self.selected_bonds.clear(); self.selected_edges.clear(); self.atom_overrides.clear(); self.bond_overrides.clear(); self.edge_overrides.clear()

    def atom_radius(self,index):
        settings=self.object_appearance('atom',self.sources[index])
        return max(3,material_radius(self.elements[index],settings)/self.span*min(self.width(),self.height())*.54*self.zoom*self.perspective_scale(self.camera_point(self.atoms[index])[2]))

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
        p=QPainter(self); self.paint_scene(p)

    def paint_scene(self,p,transparent=False):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if not transparent: p.fillRect(self.rect(),QColor('#ffffff'))
        corners=self.corners
        self.cell_edges=[(i,i^bit) for i in range(len(corners)) for bit in (1,2,4) if i<(i^bit)]
        for edge,(i,j) in enumerate(self.cell_edges):
            settings=self.object_appearance('edge',edge)
            if not settings['cell_visible']: continue
            color=QColor('#ecb835') if edge in self.selected_edges else QColor(settings['cell_color'])
            material_segment(p,self.project(corners[i])[0],self.project(corners[j])[0],color,settings['cell_width'],settings['cell_line'],settings['cell_roughness'],settings['cell_ior'],settings['cell_gloss'])
        # One camera transform per atom, shared by sorting, drawing and radius.
        transformed=[self.camera_point(point) for point in self.atoms]
        depths=[point[2] for point in transformed]
        far=min(depths,default=0); near=max(depths,default=1)
        size=min(self.width(),self.height())*.54*self.zoom
        atom_settings={source:self.object_appearance('atom',source) for source in set(getattr(self,'sources',[]))}
        radii=[max(3,material_radius(self.elements[i],atom_settings[self.sources[i]])/self.span*size*self.perspective_scale(depths[i])) for i in range(len(self.atoms))]
        cx,cy=self.width()/2+self.pan.x(),self.height()/2+self.pan.y()
        objects=[(depths[i],0,i) for i in range(len(self.atoms)) if self.atom_visible(i)]
        pens={}
        if self.bond_links:
            nodes=[]
            for point,index in self.bond_nodes:
                x,y,z=transformed[index] if index is not None else self.camera_point(point)
                factor=self.perspective_scale(z)
                screen=QPointF(cx+x*size*factor,cy-y*size*factor)
                radius=radii[index] if index is not None and self.atom_visible(index) and atom_settings[self.sources[index]]['atom_mode']!=2 else 0.
                nodes.append((screen,z,radius))
            for bond_index,(a,b,source,target) in enumerate(self.bond_links):
                settings=self.object_appearance('bond',bond_index)
                if not settings['bonds_visible']: continue
                if source in self.hidden or target in self.hidden: continue
                start,za,ra=nodes[a]; end,zb,rb=nodes[b]; delta=end-start
                length=math.hypot(delta.x(),delta.y())
                if length<=ra+rb+.01: continue
                unit=delta/length; start=start+unit*ra; end=end-unit*rb; middle=(start+end)/2
                objects.extend([((3*za+zb)/4,1,(start,middle,source,target,(za+zb)/2,bond_index,0)),((za+3*zb)/4,1,(middle,end,target,source,(za+zb)/2,bond_index,1))])
        for _,kind,i in sorted(objects,key=lambda value:value[0]):
            p.setOpacity(1)
            if kind:
                start,end,source,target,depth,bond_index,half=i
                settings=self.object_appearance('bond',bond_index)
                width=round(max(1,settings['bond_width']/self.span*size*self.perspective_scale(depth)),2)
                style=settings['bond_line']; use_elements=settings['bond_color_mode']==0
                base=QColor.fromRgbF(*ELEMENT_COLORS.get(self.structure.elements[source],[.5,.5,.5])) if use_elements else QColor(settings['bond_color'] if half==0 else settings['bond_color2'])
                if style not in (3,5): base=QColor(settings['bond_color'])
                if bond_index in self.selected_bonds: base=QColor('#e8ae2e')
                key=(base.name(),width,style)
                if style==5 and bond_index not in self.selected_bonds:
                    other=QColor.fromRgbF(*ELEMENT_COLORS.get(self.structure.elements[target],[.5,.5,.5])) if use_elements else QColor(settings['bond_color2'] if half==0 else settings['bond_color'])
                    midpoint=QColor.fromRgbF(*[(x+y)/2 for x,y in zip(base.getRgbF()[:3],other.getRgbF()[:3])])
                    gradient=QLinearGradient(start,end)
                    gradient.setColorAt(0,base if half==0 else midpoint); gradient.setColorAt(1,midpoint if half==0 else base)
                    p.setPen(QPen(gradient,width,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
                else:
                    if key not in pens: pens[key]=QPen(base,width,{1:Qt.PenStyle.DotLine,2:Qt.PenStyle.DashLine}.get(style,Qt.PenStyle.SolidLine),Qt.PenCapStyle.RoundCap)
                    p.setPen(pens[key])
                p.drawLine(start,end)
                continue
            x,y,depth=transformed[i]; perspective=self.perspective_scale(depth)
            point=QPointF(cx+x*size*perspective,cy-y*size*perspective)
            settings=atom_settings[self.sources[i]]; radius=radii[i]
            if point.x()+radius<0 or point.y()+radius<0 or point.x()-radius>self.width() or point.y()-radius>self.height(): continue
            color=QColor.fromRgbF(*ELEMENT_COLORS.get(self.elements[i],[.6,.6,.6])) if settings['atom_color_mode']==0 else QColor(settings['atom_color'])
            if settings['depth_fade']: p.setOpacity(1-.18*(near-depth)/max(near-far,1e-8))
            if self.sources[i] in self.selected:
                p.setOpacity(1); p.setPen(QPen(QColor('#2f4f42'),1.5)); p.setBrush(QColor('#ffcf59')); p.drawEllipse(point,radius,radius)
                p.drawLine(point-QPointF(radius,0),point+QPointF(radius,0)); p.drawLine(point-QPointF(0,radius),point+QPointF(0,radius)); continue
            if settings['atom_mode'] in (1,2):
                p.setPen(Qt.PenStyle.NoPen); p.setBrush(color); r=2.5 if settings['atom_mode']==2 else radius; p.drawEllipse(point,r,r); continue
            fog=round(.15*(near-depth)/max(near-far,1e-8),2) if settings['depth_fade'] else 0
            sprite=fogged_sphere(tuple(color.getRgbF()[:3]),round(fog*100),round(settings['atom_roughness'],2),round(settings['atom_ior'],2),settings['gloss'])
            p.drawImage(QRectF(point.x()-radius,point.y()-radius,2*radius,2*radius),sprite)
            if settings['atom_border_width']>0:
                p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(QColor(settings['atom_border_color']),settings['atom_border_width'])); p.drawEllipse(point,radius,radius)
        p.setOpacity(1)
        if any(self.appearance[key] for key in ('elements_visible','numbers_visible','tags_visible')):
            p.setPen(QColor('#263f31'))
            for i,position in enumerate(self.atoms):
                if not self.atom_visible(i): continue
                source=self.sources[i]; labels=[]
                if self.appearance['elements_visible']: labels.append(self.elements[i])
                if self.appearance['numbers_visible']: labels.append(str(source+1))
                if self.appearance['tags_visible'] and self.structure.tags[source]: labels.append(self.structure.tags[source])
                if labels:
                    point,_=self.project(position); p.drawText(point+QPointF(self.atom_radius(i)+4,0),' · '.join(labels))
        origin=QPointF(65,self.height()-75)
        if self.lattice and self.appearance["axes_visible"]:
            for index in sorted(range(3),key=lambda i:self.camera_point(self.lattice[i])[2]):
                vector=self.lattice[index]; length=math.sqrt(dot(vector,vector))
                unit=[v/length for v in vector]
                x,y,z=self.camera_point(unit); end=origin+QPointF(x*38,-y*38)
                color=QColor(self.appearance['axes_colors'][index]); axis_arrow(p,origin,end,color,self.appearance)
                if self.appearance['axes_labels']:
                    p.setPen(color.darker(130)); p.drawText(end+QPointF(6,-4),'abc'[index])
        if self.box:
            p.setPen(QPen(QColor('#399165'),1,Qt.PenStyle.DashLine)); p.setBrush(QColor(60,150,100,30)); p.drawRect(self.box)

    def scene_image(self):
        image=QImage(self.size(),QImage.Format.Format_ARGB32_Premultiplied); image.fill(Qt.GlobalColor.transparent)
        painter=QPainter(image)
        self.paint_scene(painter,True); painter.end(); return image

    def atom_visible(self,index): return self.object_appearance('atom',self.sources[index])['atoms_visible'] and self.sources[index] not in self.hidden

    def hide_selected(self):
        self.hidden.update(self.selected); self.selected.clear()
        page=self.parentWidget()
        while page and not isinstance(page,StructurePage): page=page.parentWidget()
        if page: page.selected.clear(); page.refresh()
        self.update()

    def context_menu(self):
        menu=apply_menu_theme(QMenu(self)); menu.addAction('显示样式',self.open_display_style)
        if self.selected:
            menu.addSeparator(); menu.addAction('隐藏',self.hide_selected); menu.addAction('删除',self.delete_requested.emit)
        return menu

    def contextMenuEvent(self,event): self.context_menu().exec(event.globalPos())

    def open_display_style(self):
        if self.style_dialog is None: self.style_dialog=DisplayStyleDialog(self,self.window())
        elif not self.style_dialog.isVisible(): self.style_dialog=DisplayStyleDialog(self,self.window())
        self.style_dialog.show(); self.style_dialog.raise_()

    def mousePressEvent(self,event): self.last=event.position(); self.press=event.position(); self.dragged=False
    def mouseMoveEvent(self,event):
        if self.last is not None:
            self.dragged = self.dragged or (event.position()-self.press).manhattanLength()>4
            delta=event.position()-self.last
            if self.mode=='pan': self.pan+=delta
            elif self.mode=='zoom': self.zoom=max(.1,min(10,self.zoom*math.exp(-delta.y()*.01)))
            elif self.mode=='rotate':
                self.rotate_camera(delta.x(),delta.y())
            elif self.mode=='select': self.box=QRectF(self.press,event.position()).normalized()
            self.last=event.position(); self.update()
    def hit_atom(self,position):
        hits=[i for i,point in enumerate(self.atoms) if self.atom_visible(i) and math.hypot(self.project(point)[0].x()-position.x(),self.project(point)[0].y()-position.y())<=self.atom_radius(i)+3]
        if hits: self.picked.emit(self.sources[max(hits,key=lambda i:self.project(self.atoms[i])[1])])
        else:
            candidates=[]
            def distance(point,a,b):
                delta=b-a; denominator=delta.x()**2+delta.y()**2
                t=max(0,min(1,((point-a).x()*delta.x()+(point-a).y()*delta.y())/max(1e-9,denominator)))
                q=a+delta*t; return math.hypot(point.x()-q.x(),point.y()-q.y())
            for index,(a,b,i,j) in enumerate(self.bonds):
                settings=self.object_appearance('bond',index)
                if not settings['bonds_visible'] or i in self.hidden or j in self.hidden: continue
                start,za=self.project(a); end,zb=self.project(b)
                if distance(position,start,end)<=max(5,settings['bond_width']/self.span*min(self.width(),self.height())*.27*self.zoom): candidates.append(((za+zb)/2,'bond',index))
            for index,(i,j) in enumerate(getattr(self,'cell_edges',[])):
                settings=self.object_appearance('edge',index)
                if not settings['cell_visible']: continue
                a,za=self.project(self.corners[i]); b,zb=self.project(self.corners[j])
                if distance(position,a,b)<=max(5,settings['cell_width']/2): candidates.append(((za+zb)/2,'edge',index))
            if not candidates: return False
            _,kind,index=max(candidates)
            from PyQt6.QtWidgets import QApplication
            if not QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier:
                self.clicked.emit(); self.selected_bonds.clear(); self.selected_edges.clear()
            (self.selected_bonds if kind=='bond' else self.selected_edges).add(index); self.update()
        return True

    def mouseDoubleClickEvent(self,event):
        self.click_timer.stop();
        if not self.hit_atom(event.position()): self.clicked.emit()
        self.last=None; self.press=None; self.box=None; self.update()

    def mouseReleaseEvent(self,event):
        if self.press is not None and self.mode=='select':
            if self.dragged:
                rect=QRectF(self.press,event.position()).normalized()
                self.boxed.emit({self.sources[i] for i,point in enumerate(self.atoms) if self.atom_visible(i) and rect.contains(self.project(point)[0])})
            else: self.hit_atom(event.position())
        self.last=None; self.press=None; self.box=None; self.update()

    def wheelEvent(self,event):
        self.zoom=max(.35,min(2.5,self.zoom* (1.1 if event.angleDelta().y()>0 else .9))); self.update()

class MainWindow(QMainWindow):
    def __init__(self,config):
        super().__init__(); self.config=config; self.appearance_store=AppearanceStore()
        if not self.appearance_store.path.exists(): self.appearance_store.current.update(config.get('bond_settings',{}))
        self.resize(config['window_width'],config['window_height']); self.setWindowTitle('CrystalX')
        self.setStyleSheet(STYLE+CONTROLS+ICON_BUTTONS+WORKSPACE_TABS+stepper_css()+SLIDERS+PANELS+PANE_FRAMES)
        from PyQt6.QtWidgets import QApplication
        self.wheel_guard=WheelGuard(self); QApplication.instance().installEventFilter(self.wheel_guard)
        self.setWindowIcon(QIcon(str(Path(__file__).resolve().parents[2]/'assets/crystalx.svg')))
        self.buttons={}
        file_menu=self.menuBar().addMenu('文件')
        for name,callback,shortcut in [('打开',self.open_file,'Ctrl+O'),('保存',self.save_file,'Ctrl+S'),('导出 POSCAR',lambda:self.save_file(True),'Ctrl+Shift+S')]:
            action=file_menu.addAction(name); action.setShortcut(shortcut); action.triggered.connect(callback); self.buttons[name]=action
        file_menu.addSeparator(); file_menu.addAction('退出',self.close)
        edit=self.menuBar().addMenu('编辑'); self.coordinates_action=edit.addAction('结构',lambda:self.call_page('show_coordinates'))
        edit.addAction('键',lambda:self.call_page('show_bonds'))
        view=self.menuBar().addMenu('查看'); view.addAction('显示终端',self.show_terminal)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        menu_bar=self.menuBar(); menu_bar.setFixedHeight(TITLE_BAR_HEIGHT)
        self.title_bar=TitleBar(self)
        self.buttons['撤销']=self.title_bar.undo_button; self.buttons['重做']=self.title_bar.redo_button
        for name,callback,shortcut in [('撤销',self.undo,'Ctrl+Z'),('重做',self.redo,'Ctrl+Y')]:
            action=self.addAction(name); action.setShortcut(shortcut); action.triggered.connect(callback)
        chrome=QWidget(); chrome.setObjectName("titleChrome"); chrome_layout=QVBoxLayout(chrome); chrome_layout.setContentsMargins(0,0,0,0); chrome_layout.setSpacing(0)
        menu_strip=QWidget(); menu_strip.setContentsMargins(0,0,0,0); menu_strip.setObjectName("titleMenuStrip"); menu_strip.setStyleSheet("QWidget#titleMenuStrip {background:transparent;border:0;}"); menu_layout=QHBoxLayout(menu_strip); menu_layout.setContentsMargins(0,0,0,0); menu_layout.setSpacing(0)
        for action in menu_bar.actions():
            apply_menu_theme(action.menu())
            button=QToolButton(); button.setText(action.text()); button.setMenu(action.menu()); button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup); button.setFixedSize(52,TITLE_BAR_HEIGHT)
            button.setStyleSheet('QToolButton {padding:0;border:0;border-radius:0;background:transparent;} QToolButton:hover,QToolButton:pressed {background:#e0e8e3;} QToolButton::menu-indicator {image:none;}')
            menu_layout.addWidget(button)
            for item in action.menu().actions():
                if not item.menu(): self.addAction(item)
        menu_bar.setParent(menu_strip); menu_bar.hide()
        self.title_bar.layout().insertWidget(3,menu_strip); chrome_layout.addWidget(self.title_bar); self.setMenuWidget(chrome)
        self.file_menu_bar=menu_bar
        self.statusBar().setSizeGripEnabled(True)

        self.outer=QSplitter(Qt.Orientation.Vertical); self.outer.setObjectName("workspaceSplit"); self.outer.setContentsMargins(3,3,3,3); self.outer.setHandleWidth(3); self.outer.setChildrenCollapsible(False); self.setCentralWidget(self.outer)
        from .workspace_tabs import StructureTabs
        self.work_tabs=StructureTabs(); self.work_tabs.setObjectName('structureTabs')
        from .workspace_tabs import WorkspaceTabBar
        self.work_tabs.setTabBar(WorkspaceTabBar()); self.work_tabs.setTabsClosable(True); self.work_tabs.setMovable(True)
        self.work_tabs.tabCloseRequested.connect(self.close_tab); self.work_tabs.currentChanged.connect(self.update_actions)
        self.work_panel=framed_panel(self.work_tabs,"workPanel"); self.outer.addWidget(self.work_panel)
        self.welcome_logo=WelcomeLogo(self.work_tabs)
        self.terminal=QTabWidget(); self.terminal.setObjectName('terminalTabs'); self.terminal.setMinimumHeight(80)
        self.messages=QPlainTextEdit(); self.messages.setFrameShape(QPlainTextEdit.Shape.NoFrame); self.messages.setReadOnly(True); self.messages.setMaximumBlockCount(1000)
        self.terminal.addTab(self.messages,'输出'); self.terminal_panel=framed_panel(self.terminal,'terminalPanel'); self.outer.addWidget(self.terminal_panel)
        controls=QWidget(); line=QHBoxLayout(controls); line.setContentsMargins(0,0,4,0)
        self.terminal_max=QToolButton(); self.terminal_max.setProperty("paneControl",True); self.terminal_max.setIcon(icon('window_maximize')); self.terminal_max.setToolTip('最大化 / 还原终端'); self.terminal_max.clicked.connect(self.maximize_terminal); line.addWidget(self.terminal_max)
        close=QToolButton(); close.setProperty('paneControl',True); close.setIcon(icon('window_close')); close.setToolTip('隐藏终端'); close.clicked.connect(self.hide_terminal); line.addWidget(close)
        self.terminal.setCornerWidget(controls); self.outer.setSizes([650,170]); self.terminal_large=False
        self.update_actions()
        from .window_shell import WindowShell
        self.window_shell=WindowShell(self)

    def current_page(self):
        tabs=self.__dict__.get('work_tabs')
        return tabs.currentWidget() if tabs is not None else None

    def call_page(self,name,*args):
        page=self.current_page()
        if page: return getattr(page,name)(*args)
        return False

    def undo(self): self.call_page('undo')
    def redo(self): self.call_page('redo')
    def save_file(self,save_as=False): return self.call_page('save_file',save_as)

    def open_file(self):
        path,_=QFileDialog.getOpenFileName(self,'打开结构','','结构文件 (POSCAR* CONTCAR* *.vasp *.cif);;所有文件 (*)')
        if path: self.load_path(path)

    def load_path(self,path):
        try: structure=read_cif(path) if Path(path).suffix.lower()=='.cif' else read_poscar(path)
        except (ValueError,OSError) as error:
            QMessageBox.warning(self,'打开失败',str(error)); return False
        page=StructurePage(self); page.document=StructureDocument(structure); page.path=Path(path); page.refresh()
        index=self.work_tabs.addTab(page,Path(path).name)
        close=QToolButton(); close.setIcon(icon('window_close')); close.setFixedSize(20,20); close.setToolTip('关闭结构'); close.setStyleSheet('QToolButton {border:0;background:transparent;} QToolButton:hover {background:#ead7d5;}')
        close.clicked.connect(lambda checked=False,page=page:self.close_tab(self.work_tabs.indexOf(page)))
        from PyQt6.QtWidgets import QTabBar
        self.work_tabs.tabBar().setTabButton(index,QTabBar.ButtonPosition.RightSide,close)
        self.work_tabs.setCurrentIndex(index); page.reset_view(); self.update_actions()
        page.output(f'已打开 {Path(path).name}，{len(structure.elements)} 个原子'); return True

    def close_tab(self,index):
        page=self.work_tabs.widget(index)
        if not page or not page.confirm_changes(): return False
        page.coordinate_dialog.close()
        if page.bond_dialog: page.bond_dialog.close()
        if page.viewport.style_dialog: page.viewport.style_dialog.close()
        self.work_tabs.removeTab(index); page.deleteLater(); self.update_actions(); return True

    def update_actions(self,*args):
        page=self.current_page(); document=page.document if page else None
        for key in ['保存','导出 POSCAR']: self.buttons[key].setEnabled(page is not None)
        self.coordinates_action.setEnabled(page is not None)
        self.welcome_logo.setVisible(self.work_tabs.count()==0)
        self.buttons['撤销'].setEnabled(bool(document and document.index>0))
        self.buttons['重做'].setEnabled(bool(document and document.index<len(document.commands)))
        for i in range(self.work_tabs.count()):
            item=self.work_tabs.widget(i)
            if item is not page:
                item.coordinate_dialog.hide()
                if item.bond_dialog: item.bond_dialog.hide()
                if item.viewport.style_dialog: item.viewport.style_dialog.hide()
            self.work_tabs.setTabText(i,(item.path.name if item.path else '结构')+(' *' if item.document.dirty else ''))
        if not page: self.statusBar().showMessage('就绪')
        elif page.document.structure: self.statusBar().showMessage(f'原子 {len(page.document.structure.elements)} | 已选 {len(page.selected)} | {page.coordinates.currentText()}')

    def show_terminal(self): self.terminal_panel.show()
    def hide_terminal(self):
        if self.terminal_large: self.maximize_terminal()
        self.terminal_panel.hide()
    def maximize_terminal(self):
        self.terminal_large=not self.terminal_large
        if self.terminal_large: self.saved_split=self.outer.sizes(); self.work_panel.hide()
        else: self.work_panel.show(); self.outer.setSizes(self.saved_split)
        self.terminal_max.setIcon(icon('window_restore' if self.terminal_large else 'window_maximize'))

    def showEvent(self,event):
        super().showEvent(event)
        if not getattr(self,'_positioned',False):
            self.move(self.screen().availableGeometry().center()-self.rect().center()); self._positioned=True

    def closeEvent(self,event):
        for i in range(self.work_tabs.count()):
            self.work_tabs.setCurrentIndex(i)
            if not self.work_tabs.widget(i).confirm_changes(): event.ignore(); return
        event.accept()

class StructurePage(QWidget):
    def __init__(self,host):
        super().__init__(); self.host=host; self.buttons=host.buttons; self.messages=host.messages
        self.document=StructureDocument(); self.selected=set(); self.path=None
        root=QSplitter(); layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.addWidget(root)
        left=QWidget(); left.setMinimumWidth(300); left_layout=QVBoxLayout(left); left_layout.setContentsMargins(8,8,8,8)
        self.cell_label=QLabel(); self.cell_label.setMargin(8); lattice_group=QGroupBox("晶格参数"); lattice_layout=QHBoxLayout(lattice_group); lattice_layout.addWidget(self.cell_label); self.cell_preview=CellPreview(); lattice_layout.addWidget(self.cell_preview,1); left_layout.addWidget(lattice_group)
        header=QHBoxLayout(); title=QLabel('原子列表'); title.setStyleSheet('font-weight:bold; padding-top:4px;'); header.addWidget(title); header.addStretch()
        left_layout.addLayout(header)
        self.atom_list=AtomList(); self.atom_list.atom_requested.connect(self.toggle_list_atom); left_layout.addWidget(self.atom_list); root.addWidget(left)
        self.coordinate_dialog=StructureEditor(self); self.bond_dialog=None
        center=QWidget(); center.setObjectName("viewportHost"); self.center_host=center; center.installEventFilter(self); center_layout=QVBoxLayout(center); center_layout.setContentsMargins(0,0,0,0); center_layout.setSpacing(0)
        views=QHBoxLayout(); views.setContentsMargins(8,6,8,6); views.setSpacing(5); views.addSpacing(38); views.addStretch()
        self.view_buttons=[]
        for index,name in enumerate(['a','b','c','a*','b*','c*','透视']):
            button=QToolButton(); button.setIcon(icon('view'+str(index))); button.setIconSize(QSize(30,30)); button.setFixedSize(34,32); button.setToolTip('沿 +'+name+' 方向观察' if index<6 else '等轴测')
            if index==6:
                button.setIcon(icon('view6')); button.setToolTip('透视强度（0 为正交）'); button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
                menu=apply_menu_theme(QMenu(button)); action=QWidgetAction(menu); row=QWidget(); line=QHBoxLayout(row); line.addWidget(QLabel('透视强度'))
                self.perspective_slider=QSlider(Qt.Orientation.Horizontal); self.perspective_slider.setRange(0,100); self.perspective_slider.setFixedWidth(150); self.perspective_slider.valueChanged.connect(self.set_perspective); line.addWidget(self.perspective_slider); action.setDefaultWidget(row); menu.addAction(action); button.setMenu(menu)
            else: button.clicked.connect(lambda checked=False,index=index:self.set_view(index))
            views.addWidget(button); self.view_buttons.append(button)
        fit=QToolButton(); fit.setIcon(icon('fit')); fit.setToolTip('重置视图及缩放'); fit.clicked.connect(self.reset_view); fit.setFixedSize(34,32); fit.setIconSize(QSize(24,24)); views.addWidget(fit); views.addStretch(); views.addSpacing(38)
        center_layout.addLayout(views)
        self.viewport=CrystalViewport(); self.viewport.delete_requested.connect(self.delete_atoms); self.viewport.appearance.update(deepcopy(host.appearance_store.current)); self.viewport.picked.connect(self.pick); self.viewport.boxed.connect(self.add_selection); self.viewport.clicked.connect(self.clear_selection); center_layout.addWidget(self.viewport); root.addWidget(center)
        self.visibility_button=QToolButton(); self.visibility_button.setIcon(icon('eye')); self.visibility_button.setIconSize(QSize(24,24)); self.visibility_button.setFixedSize(34,32); self.visibility_button.setToolTip('可见性'); self.visibility_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.visibility_menu=VisibilityMenu(self.viewport,self.visibility_button); self.visibility_button.setMenu(self.visibility_menu)
        views.insertWidget(views.indexOf(self.view_buttons[6]),self.visibility_button)
        tools=QWidget(center); tools.setObjectName("viewportTools"); tools.move(4,4); tool_layout=QVBoxLayout(tools); tool_layout.setContentsMargins(0,0,0,0); tool_layout.setSpacing(3)
        self.tool_group=QButtonGroup(self); self.tool_group.setExclusive(True)
        for symbol,name,mode in [('↖','旋转视图（默认）','rotate'),('□','框选原子 / 点选对象（Ctrl 叠加）','select'),('✥','平移视图','pan'),('⊕','拖动缩放','zoom')]:
            button=QToolButton(); button.setIcon(icon(mode)); button.setToolTip(name); button.setCheckable(True); button.setIconSize(QSize(21,21)); button.setFixedSize(30,30)
            button.clicked.connect(lambda checked=False,mode=mode:self.set_tool(mode)); self.tool_group.addButton(button); tool_layout.addWidget(button)
            button.setChecked(mode=='rotate')
        tools.adjustSize(); tools.raise_()
        self.copy_button=QToolButton(center); self.copy_button.setIcon(icon('copy_image')); self.copy_button.setToolTip('复制图片（透明背景）'); self.copy_button.setIconSize(QSize(22,22)); self.copy_button.setFixedSize(30,30); self.copy_button.clicked.connect(self.copy_image); self.copy_button.raise_()
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
        note=QLabel('默认拖动旋转 · 滚轮缩放\n任意工具双击选择；Ctrl 叠加。\n第二个工具支持框选；双击空白清空。\n平移单位随坐标模式切换。\n周期边界显示已启用；不显示化学键。'); note.setWordWrap(True); form.addWidget(note); form.addStretch()
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(panel); root.addWidget(scroll); root.setSizes([330,700,300]); root.setStretchFactor(1,1)
        self.refresh()

    def eventFilter(self,obj,event):
        if obj is getattr(self,'center_host',None) and event.type()==QEvent.Type.Resize and hasattr(self,'copy_button'):
            self.copy_button.move(obj.width()-self.copy_button.width()-6,6)
        return super().eventFilter(obj,event)

    def copy_image(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setImage(self.viewport.scene_image())
        self.output('图片已复制（透明背景）')

    def refresh(self,*args):
        structure=self.document.structure
        self.host.update_actions()
        self.cell_preview.lattice=structure.lattice if structure else None; self.cell_preview.update()
        if structure: self.selected.intersection_update(range(len(structure.elements)))
        self.viewport.selected=self.selected; self.viewport.set_structure(structure)
        self.atom_list.refresh(structure,self.selected)
        self.coordinate_dialog.refresh(structure,self.selected)
        if self.bond_dialog: self.bond_dialog.refresh()
        if structure:
            vectors=structure.lattice
            lengths=[dot(v,v)**.5 for v in vectors]
            angles=[math.degrees(math.acos(max(-1,min(1,dot(vectors[i],vectors[j])/(lengths[i]*lengths[j]))))) for i,j in [(1,2),(0,2),(0,1)]]
            self.cell_label.setText('<table>'+''.join(f'<tr><td><i>{key}</i></td><td>{value:.3f} {unit}</td></tr>' for key,value,unit in zip(['a','b','c','α','β','γ'],lengths+angles,['Å']*3+['°']*3))+'</table>')
        else: self.cell_label.setText('晶格参数\n\n尚未打开结构')
        self.selection_label.setText(f'已选择 {len(self.selected)} 个原子')
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

    def save_file(self,save_as=False):
        if self.document.structure is None: return False
        path=str(self.path) if self.path and self.path.suffix.lower()!='.cif' and not save_as else ''
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

    def toggle_list_atom(self,index):
        self.selected.symmetric_difference_update({index}); self.refresh()

    def pick(self,index):
        self.update_selection({index})
        self.refresh()

    def set_selection(self,indices):
        self.update_selection(indices); self.refresh()


    def show_bonds(self):
        if self.bond_dialog is None or not self.bond_dialog.isVisible():
            if self.bond_dialog: self.bond_dialog.deleteLater()
            self.bond_dialog=BondEditor(self.viewport,self)
        self.bond_dialog.show(); self.bond_dialog.raise_()

    def show_coordinates(self):
        self.coordinate_dialog.show(); self.coordinate_dialog.raise_()

    def output(self,text):
        from datetime import datetime
        self.messages.appendPlainText(f'[{datetime.now():%H:%M:%S}] {text}')

    def set_tool(self,mode):
        self.viewport.mode=mode
        self.viewport.setCursor({'select':Qt.CursorShape.ArrowCursor,'rotate':Qt.CursorShape.ArrowCursor,'pan':Qt.CursorShape.OpenHandCursor,'zoom':Qt.CursorShape.SizeVerCursor}[mode])


    def update_selection(self,indices):
        from PyQt6.QtWidgets import QApplication
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier: self.selected.update(indices)
        else: self.selected=set(indices); self.viewport.selected_bonds.clear(); self.viewport.selected_edges.clear()

    def add_selection(self,indices): self.set_selection(indices)

    def clear_selection(self):
        self.selected.clear(); self.viewport.selected_bonds.clear(); self.viewport.selected_edges.clear(); self.refresh()

    def set_perspective(self,value):
        self.viewport.perspective=value/100; self.viewport.update()

    def fit_view(self):
        view=self.viewport
        view.zoom=1.; view.pan=QPointF(0,0)
        bounds=[]
        for point in view.corners:
            screen,_=view.project(point); bounds.append((screen.x(),screen.y(),0.))
        if view.appearance['atoms_visible']:
            for index,point in enumerate(view.atoms):
                screen,_=view.project(point); bounds.append((screen.x(),screen.y(),view.atom_radius(index)))
        if bounds:
            left=min(x-r for x,y,r in bounds); right=max(x+r for x,y,r in bounds)
            top=min(y-r for x,y,r in bounds); bottom=max(y+r for x,y,r in bounds)
            view.zoom=max(.1,min(10.,(view.width()-80)/max(1.,right-left),(view.height()-80)/max(1.,bottom-top)))
            view.pan=QPointF((view.width()/2-(left+right)/2)*view.zoom,(view.height()/2-(top+bottom)/2)*view.zoom)
        view.update()


    def set_view(self,index):
        if index==6:
            self.viewport.camera=standard_orientation(self.document.structure.lattice)
        else:
            lattice=self.document.structure.lattice if self.document.structure else [[1,0,0],[0,1,0],[0,0,1]]
            i=index%3
            direction=lattice[i] if index<3 else cross(lattice[(i+1)%3],lattice[(i+2)%3])
            if index>=3 and dot(lattice[0],cross(lattice[1],lattice[2]))<0: direction=[-v for v in direction]
            length=math.sqrt(dot(direction,direction)); forward=[v/length for v in direction]
            up=[0,0,1] if abs(forward[2])<.95 else [0,1,0]
            right=cross(up,forward); length=math.sqrt(dot(right,right)); right=[v/length for v in right]
            self.viewport.camera=[right,cross(forward,right),forward]
        self.viewport.update()

    def translate(self):
        if not self.selected: return
        vector=[spin.value() for spin in self.translation]
        if not any(vector): return
        if self.coordinates.currentIndex(): vector=fractional(vector,self.document.structure.lattice)
        self.document.execute(TranslateCommand(self.document.structure,self.selected,vector)); self.refresh(); self.output(f"已平移 {len(self.selected)} 个原子")

    def run_operation(self,operation,*args,clear_selection=False):
        if self.document.structure is None: return
        try:
            command=SnapshotCommand(self.document.structure,operation,*args)
        except ValueError as error:
            QMessageBox.warning(self,'无法执行',str(error)); return
        if command.before==command.after: return
        self.document.execute(command)
        self.output("完成操作："+operation.__name__)
        if clear_selection: self.selected=set(); self.viewport.hidden.clear(); self.viewport.clear_object_styles()
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

    def undo(self): self.document.undo(); self.selected=set(); self.viewport.hidden.clear(); self.viewport.clear_object_styles(); self.refresh(); self.output("撤销")
    def redo(self): self.document.redo(); self.selected=set(); self.viewport.hidden.clear(); self.viewport.clear_object_styles(); self.refresh(); self.output("重做")

    def statusBar(self): return self.host.statusBar()

    def reset_view(self):
        self.viewport.camera=standard_orientation(self.document.structure.lattice)
        self.perspective_slider.setValue(0)
        self.fit_view()
