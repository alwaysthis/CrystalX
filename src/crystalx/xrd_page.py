"""Scientific diffraction canvas with shared screen/vector-export rendering."""
from bisect import bisect_left
from copy import deepcopy
from dataclasses import replace
from io import BytesIO
from contextlib import contextmanager
from pathlib import Path
import math
from PyQt6.QtCore import Qt,QRectF,QPointF,QTimer,QEvent,QMimeData,pyqtSignal,QSize
from PyQt6.QtGui import QImage,QKeySequence,QActionGroup
from PyQt6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QMenu,QApplication,QWidgetAction,QToolButton,QFrame
from matplotlib.figure import Figure
from matplotlib import rc_context
from matplotlib.legend import Legend
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from .plot_chrome import PlotToolbar,PlotAspectHost,PlotHeader
from .plot_style import default_style,validate_style,tick_mode,math_label
from .plot_scales import axis_scale
from .plot_curves import PlotCurve,CURVE_MIME,validate_curve_settings
from .plot_presets import PlotDefaults,PlotTemplates
from .plot_selection import CurveSelection,curve_hit,nearest_point
from .icons import icon
from .scientific_figure import make_figure
from .xrd_io import read_xrd
from .dialogs import QFileDialog,QMessageBox
from .theme import apply_menu_theme
from .plot_history import PlotHistory
from .plot_units import prepare_scan,prepare_curve

from .math_ui import MathComboBox as QComboBox, MathLabel as QLabel, MathMenu as QMenu, MathToolButton as QToolButton, MathCheckBox as QCheckBox

class XrdPlot(QWidget,PlotHistory):
    selection_changed=pyqtSignal()
    history_changed=pyqtSignal()
    curve_removed=pyqtSignal()
    peak_region_selected=pyqtSignal(object)
    peak_selection_finished=pyqtSignal()
    def __init__(self,readout,defaults=None):
        super().__init__(); self.readout=readout; self.scan=None; self.drag=None; self.defaults=defaults or PlotDefaults(); self.style,self.default_curves=self.defaults.read(); self.name='XRD'
        self.curves=[]; self.scan_curves={}; self.selected_curve=None; self.press_position=None
        self.templates=PlotTemplates() if defaults is None else None
        self.template_name='global'; self.template_path=None; self.scan_states={}
        self.legend_anchor=None; self.legend_drag=None; self.hover_point=None; self.label_editor=None; self.legend_editor=None
        self.point_editor=None; self.manual_peak_mode=False; self.peak_start=None; self.peak_rect=None
        self.setMinimumSize(400,260); self.setMouseTracking(True); self.curve_visible=True; self.style_dialog=None
        self.canvas=FigureCanvasQTAgg(Figure()); self.canvas.setParent(self); self.canvas.setMouseTracking(True); self.canvas.installEventFilter(self)
        self.selection_overlay=CurveSelection(self)
        from .plot_selection import LegendHandle
        self.legend_handle=LegendHandle(self); self.legend_hover=False
        self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.toolbar=PlotToolbar(self); self.setToolTip('滚轮缩放 · 拖动平移 · 单击标点 · 双击轴标签编辑 · 右键图片样式')
        self.init_history()

    @property
    def logarithmic(self): return self.primary(False)['log']
    @logarithmic.setter
    def logarithmic(self,value): self.style['axes']['left'].update(log=bool(value),sqrt=False)

    def set_scan(self,scan):
        self.history_locked=True
        self.cancel_peak_selection()
        self.close_editors()
        if self.scan is not None:
            self.scan_curves[id(self.scan)]=self.curves
            self.scan_states[id(self.scan)]=(deepcopy(self.style),self.template_name,self.template_path,self.legend_anchor)
        self.scan=scan
        self.display_scan=prepare_scan(scan)
        self.hover_point=None; self.legend_drag=None
        if id(scan) in self.scan_curves:
            self.curves=self.scan_curves[id(scan)]
            self.style,self.template_name,self.template_path,self.legend_anchor=self.scan_states[id(scan)]
        else:
            self.legend_anchor=None; self.curve_visible=True
            if self.templates:
                self.style,self.default_curves,self.template_name,self.template_path=self.templates.resolve(scan)
            settings=self.default_curves[0] if self.default_curves else dict(style=deepcopy(self.style['curve']),label='plot 1',visible=True)
            self.curves=[prepare_curve(scan,settings['style'],settings['label'],settings['visible'],settings.get('legend_visible',True))]
        self.selected_curve=None
        if self.curves:
            from .curve_data import XYScan
            self.display_scan=XYScan(self.curves[0].x,self.curves[0].y,self.curves[0].metadata or scan.metadata)
        self.sorted_points=sorted(zip(self.display_scan.x,self.display_scan.intensity)); self.sorted_x=[p[0] for p in self.sorted_points]; self.reset()
        if id(scan) in self.committed:
            self.bounds=self.committed[id(scan)]['bounds']; self.curve_visible=self.committed[id(scan)]['curve_visible']; self.rebuild()
        self.history_locked=False; self.remember()

    def primary(self,horizontal):
        first,second=('bottom','top') if horizontal else ('left','right')
        return self.style['axes'][first] if self.style['axes'][first]['visible'] else self.style['axes'][second]

    def reset_bounds(self,style=None,curves=None):
        if self.scan is None: return (0,1,0,1)
        previous=self.style
        if style is not None: self.style=style
        try:
            result=[]
            items=self.curves if curves is None else curves
            for horizontal,values in [(True,[x for c in items if c.visible for x in c.x]),(False,[y for c in items if c.visible for y in c.display_y])]:
                axis=self.primary(horizontal); scale=axis_scale(axis)
                positive=[v for v in values if (v>0 if scale=='log' else v>=0 if scale=='sqrt' else True)]
                if not positive: positive=[1.,10.]
                low,high=min(positive),max(positive)
                if axis['log']:
                    low,high=math.log10(low),math.log10(high); margin=(high-low)*.04 or .5
                    low,high=10**(low-margin),10**(high+margin)
                elif scale=='sqrt':
                    low,high=math.sqrt(low),math.sqrt(high); margin=(high-low)*.04 or .5
                    low,high=max(0,low-margin)**2,(high+margin)**2
                else:
                    margin=(high-low)*(.025 if horizontal else .06) or 1
                    low,high=(max(0,low-margin) if not horizontal and low>=0 else low-margin),high+margin
                if axis['minimum'].strip(): low=float(axis['minimum'])
                if axis['maximum'].strip(): high=float(axis['maximum'])
                if low>=high: raise ValueError('坐标轴最小值必须小于最大值。')
                result.extend((low,high))
            return tuple(result)
        finally: self.style=previous

    def reset(self):
        self.bounds=self.reset_bounds(); self.rebuild()

    def rebuild(self):
        # Qt can briefly give the canvas a 1px height while the header changes rows.
        if self.scan is None or self.width()<32 or self.height()<32: return
        host=self.parentWidget()
        if isinstance(host,PlotAspectHost): host.fit_plot()
        if self.width()<32 or self.height()<32: return
        self.hover_point=None
        figure,data,axes=make_figure(self.display_scan,self.style,self.bounds,(self.width(),self.height()),self.curve_visible,self.name,curves=self.curves)
        self.install_figure(figure,data,axes)

    def install_figure(self,figure,data,axes):
        self.data_axes=data; self.axis_artists=axes
        self.canvas.figure=figure; figure.set_canvas(self.canvas)
        # Qt's ratio-change handler does not run when only Figure is replaced.
        figure.set_dpi(96*self.canvas.device_pixel_ratio)
        if self.legend_anchor is not None and data.get_legend() is not None: data.get_legend().set_loc(self.legend_anchor)
        self.canvas.draw_idle(); self.selection_overlay.setGeometry(self.rect()); self.selection_overlay.raise_(); self.selection_overlay.update(); self.toolbar.position()
        self.remember()
        self.legend_handle.setGeometry(self.rect()); self.legend_handle.raise_(); self.legend_handle.update()

    def apply_style(self,style,curve_settings=None):
        settings=validate_style(style)
        drafts=[c.settings() for c in self.curves]
        if curve_settings is not None:
            if len(curve_settings)!=len(self.curves): raise ValueError('曲线数量已改变，请重新打开图片样式。')
            drafts=[validate_curve_settings(v) for v in curve_settings]
        elif self.curves and settings['curve']!=self.style['curve']: drafts[self.active_curve_index]['style']=deepcopy(settings['curve'])
        candidates=[replace(c,style=v['style'],label=v['label'],visible=v['visible'],legend_visible=v.get('legend_visible',c.legend_visible)) for c,v in zip(self.curves,drafts)]
        def view_key(s):
            x=s['axes']['bottom'] if s['axes']['bottom']['visible'] else s['axes']['top']
            y=s['axes']['left'] if s['axes']['left']['visible'] else s['axes']['right']
            return tuple((axis_scale(a),a['minimum'],a['maximum']) for a in (x,y))
        bounds=self.reset_bounds(settings) if view_key(settings)!=view_key(self.style) else self.bounds
        # Build and validate all text/locators before committing any settings.
        figure,data,axes=make_figure(self.display_scan,settings,bounds,(self.width(),self.height()),self.curve_visible,self.name,curves=candidates)
        if settings['legend']['location']!=self.style['legend']['location']: self.legend_anchor=None
        self.style=settings; self.bounds=bounds; self.curves=candidates; self.hover_point=None; self.install_figure(figure,data,axes)
        host=self.parentWidget()
        if isinstance(host,PlotAspectHost): host.fit_plot()

    def area(self):
        if not hasattr(self,'data_axes'): return QRectF(70,25,max(1,self.width()-100),max(1,self.height()-85))
        bbox=self.data_axes.get_position(); return QRectF(bbox.x0*self.width(),(1-bbox.y1)*self.height(),bbox.width*self.width(),bbox.height*self.height())

    def point(self,x,y):
        px,py=self.data_axes.transData.transform((x,y)); ratio=self.canvas.figure.bbox.width/self.width()
        return QPointF(px/ratio,self.height()-py/ratio)

    @property
    def active_curve_index(self): return self.selected_curve if self.selected_curve is not None else 0

    def select_curve(self,index):
        if index is None: self.hover_point=None; self.readout.clear()
        self.selected_curve=index; self.selection_overlay.update(); self.selection_changed.emit()
        if index is not None: self.readout.setText(self.curves[index].label)

    def set_background(self,show=None,subtract=None,settings=None):
        from .background import fit_background
        curve=self.curves[self.active_curve_index]
        previous_subtract=curve.subtract_background
        computed=settings is not None or (show or subtract) and not curve.background
        parameters=curve.background_settings if settings is None else settings
        if computed:
            fitted=fit_background(curve.x,curve.y,**parameters)
            curve.background=fitted; curve.background_settings=dict(parameters)
        if show is not None: curve.show_background=show
        if subtract is not None: curve.subtract_background=subtract
        changed=previous_subtract!=curve.subtract_background or previous_subtract and computed
        if changed:
            curve.peaks=[]; curve.peak_analysis={}
            for derived in self.curves:
                if derived.source_id==curve.uid: derived.visible=False
        self.bounds=self.reset_bounds(); self.rebuild(); self.selection_changed.emit()
        return bool(changed)

    def copy_curve(self,index=None):
        if index is None: index=self.selected_curve
        if index is None: return False
        mime=QMimeData(); mime.setData(CURVE_MIME,self.curves[index].clipboard(self.style['general']))
        QApplication.clipboard().setMimeData(mime); return True

    def paste_curve(self):
        mime=QApplication.clipboard().mimeData()
        if not mime or not mime.hasFormat(CURVE_MIME): return False
        try: curve=PlotCurve.from_clipboard(mime.data(CURVE_MIME))
        except ValueError as error: self.readout.setText(str(error)); return False
        curve.inherit_plot_appearance()
        from uuid import uuid4
        curve.uid=uuid4().hex; curve.source_id=''
        self.curves.append(curve); self.selected_curve=len(self.curves)-1; self.rebuild(); self.selection_changed.emit(); return True

    def delete_curve(self,index=None):
        if index is None: index=self.selected_curve
        if index is None or not 0<=index<len(self.curves): return False
        removed=self.curves.pop(index)
        for curve in self.curves:
            if curve.source_id==removed.uid: curve.source_id=''
        self.selected_curve=None; self.hover_point=None
        self.close_editors()
        self.rebuild(); self.selection_changed.emit(); self.curve_removed.emit(); return True

    def close_editors(self):
        for name in ('style_dialog','legend_editor','point_editor','label_editor','legend_entries_dialog','expression_dialog'):
            dialog=getattr(self,name,None)
            if dialog is not None: dialog.close(); dialog.deleteLater(); setattr(self,name,None)

    def add_scan(self,scan):
        index=len(self.curves)
        settings=self.default_curves[index] if index<len(self.default_curves) else dict(style=deepcopy(self.style['curve']),label=f'plot {index+1}',visible=True)
        self.curves.append(prepare_curve(scan,settings['style'],settings['label'],settings['visible'],settings.get('legend_visible',True)))
        self.selected_curve=index; self.rebuild(); self.selection_changed.emit()

    def add_file_curves(self):
        state=getattr(self.window(),'session_state',None)
        paths,_=QFileDialog.getOpenFileNames(self,'添加曲线',state.directory if state else '', '曲线数据 (*.ras *.rasx *.xy *.dat *.txt *.csv)')
        if not paths: return
        added=0; failures=[]
        for path in paths:
            try: scans=read_xrd(path)
            except (OSError,ValueError) as error: failures.append(f'{path}：{error}'); continue
            for scan in scans: self.add_scan(scan); added+=1
            if state: state.opened(path)
        self.readout.setText(f'已添加 {added} 条曲线；可重置视图显示全部数据。')
        if failures: QMessageBox.warning(self,'部分文件打开失败','\n'.join(failures))

    def annotate_point(self,index,position):
        point=nearest_point(self,index,position)
        if point not in self.curves[index].points: self.curves[index].points.append(point)
        self.select_curve(index); self.rebuild()

    def clear_points(self,index):
        curve=self.curves[index]
        for point in curve.points: curve.point_labels.pop(point,None)
        curve.points.clear(); self.rebuild()

    def point_annotation_at(self,position):
        renderer=self.canvas.get_renderer(); ratio=self.canvas.figure.bbox.width/self.width()
        for curve,index,annotation in self.data_axes.point_annotations:
            if annotation.get_window_extent(renderer).contains(position.x()*ratio,(self.height()-position.y())*ratio): return curve,index
        return None

    def set_point_label(self,curve_index,index,text):
        from matplotlib.mathtext import MathTextParser
        from dataclasses import replace
        MathTextParser('path').parse(math_label(text),dpi=96)
        curves=list(self.curves); labels=dict(curves[curve_index].point_labels); labels[index]=text
        curves[curve_index]=replace(curves[curve_index],point_labels=labels)
        figure,data,axes=make_figure(self.display_scan,self.style,self.bounds,(self.width(),self.height()),self.curve_visible,self.name,curves=curves)
        self.curves=curves; self.install_figure(figure,data,axes)

    def edit_point_label(self,curve_index,index):
        from .plot_content import PointLabelEditor
        if self.point_editor is not None: self.point_editor.close(); self.point_editor.deleteLater()
        self.point_editor=PointLabelEditor(self,curve_index,index); self.point_editor.show(); return self.point_editor

    def start_peak_selection(self):
        self.manual_peak_mode=True; self.drag=None; self.legend_drag=None; self.hover_point=None; self.peak_start=None; self.peak_rect=None
        self.canvas.setFocus(); self.canvas.setCursor(Qt.CursorShape.CrossCursor); self.selection_overlay.update()
        self.readout.setText('拖动框选寻峰范围，松开后显示结果；Esc取消。')

    def cancel_peak_selection(self):
        self.manual_peak_mode=False; self.peak_start=None; self.peak_rect=None
        self.canvas.unsetCursor(); self.selection_overlay.update(); self.peak_selection_finished.emit()

    def set_series_visible(self,index,value):
        self.curves[index].visible=value
        if not value and self.selected_curve==index: self.select_curve(None)
        self.rebuild()

    def set_curve_visible(self,value):
        self.curve_visible=value; self.rebuild()

    def export_image(self,scale=2):
        buffer=BytesIO()
        with self.export_context(): self.canvas.figure.savefig(buffer,format='png',dpi=96*scale,transparent=self.style['general']['transparent'])
        return QImage.fromData(buffer.getvalue(),'PNG')

    @contextmanager
    def export_context(self):
        frames=[item.get_frame() for item in self.canvas.figure.findobj(Legend)]
        colors=[frame.get_facecolor() for frame in frames]
        if self.style['general']['transparent']:
            for frame in frames: frame.set_facecolor('none')
        try:
            with rc_context({'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none'}): yield
        finally:
            for frame,color in zip(frames,colors): frame.set_facecolor(color)

    def save_image(self,vector=False):
        path,kind=QFileDialog.getSaveFileName(self,'导出图片','plot.svg' if vector else 'plot.png','SVG 矢量图 (*.svg);;PDF 矢量图 (*.pdf)' if vector else 'PNG 图片 (*.png);;SVG 矢量图 (*.svg);;PDF 矢量图 (*.pdf)')
        if path:
            from pathlib import Path
            if Path(path).suffix.lower() not in ('.png','.svg','.pdf'): path+=('.svg' if 'svg' in kind else '.pdf' if 'pdf' in kind else '.png')
            try:
                with self.export_context(): self.canvas.figure.savefig(path,dpi=300,transparent=self.style['general']['transparent'])
            except (OSError,ValueError) as error: QMessageBox.warning(self,'导出失败',str(error))

    def axis_at(self,point):
        a=self.area()
        if a.top()-10<=point.y()<=a.bottom()+10:
            if point.x()<a.left()+7: return 'left'
            if point.x()>a.right()-7: return 'right'
        if a.left()-10<=point.x()<=a.right()+10:
            if point.y()>a.bottom()-7: return 'bottom'
            if point.y()<a.top()+7: return 'top'
        return None

    def legend_at(self,position):
        return self.legend_rect().contains(position)

    def legend_rect(self):
        legend=self.data_axes.get_legend()
        if legend is None: return QRectF()
        ratio=self.canvas.figure.bbox.width/self.width(); box=legend.get_window_extent(self.canvas.get_renderer())
        rect=QRectF(box.x0/ratio,self.height()-box.y1/ratio,box.width/ratio,box.height/ratio)
        if not self.data_axes.legend_curve_indices:
            rect.setWidth(max(84,rect.width())); rect.setHeight(max(28,rect.height()))
        return rect

    def legend_entry_at(self,position):
        legend=self.data_axes.get_legend()
        if legend is None: return None
        ratio=self.canvas.figure.bbox.width/self.width(); renderer=self.canvas.get_renderer()
        for index,text in zip(self.data_axes.legend_curve_indices,legend.get_texts()):
            if text.get_window_extent(renderer).expanded(1.1,1.2).contains(position.x()*ratio,(self.height()-position.y())*ratio): return index
        return None

    def set_legend_label(self,index,text):
        drafts=[curve.settings() for curve in self.curves]; drafts[index]['label']=text
        self.apply_style(self.style,drafts)
        dialog=self.style_dialog
        if dialog is not None and index<len(dialog.curve_drafts):
            dialog.curve_drafts[index]['label']=text
            dialog.curve_selector.setItemText(index,f'{index+1} · {text}')
            if dialog.curve_index==index: dialog.fields[('curve','label')][1].setText(text)

    def edit_legend_label(self,index):
        from .plot_content import LegendLabelEditor
        if self.legend_editor is not None: self.legend_editor.close(); self.legend_editor.deleteLater()
        self.legend_editor=LegendLabelEditor(self,index); self.legend_editor.show(); return self.legend_editor

    def label_at(self,position):
        ratio=self.canvas.figure.bbox.width/self.width(); renderer=self.canvas.get_renderer()
        for side,axis in self.axis_artists.items():
            label=(axis.xaxis if side in ('bottom','top') else axis.yaxis).label
            if self.style['axes'][side]['visible'] and label.get_text() and label.get_window_extent(renderer).expanded(1.15,1.2).contains(position.x()*ratio,(self.height()-position.y())*ratio): return side
        return None

    def set_axis_label(self,side,text):
        style=deepcopy(self.style); style['axes'][side]['label']=text; self.apply_style(style)
        # A content edit must survive applying a previously opened appearance draft.
        if self.style_dialog is not None:
            self.style_dialog.base_style['axes'][side]['label']=text
            self.style_dialog.fields[('axes',side,'label')][1].setText(text)

    def edit_axis_label(self,side):
        from .plot_content import AxisLabelEditor
        from .plot_style import axis_label
        if self.label_editor is not None: self.label_editor.close(); self.label_editor.deleteLater()
        text=self.style['axes'][side]['label']
        self.label_editor=AxisLabelEditor(self,side,axis_label(self.display_scan,side) if text is None else text)
        self.label_editor.show(); return self.label_editor

    def open_style(self,side=None,section=None):
        if not self.curves: self.readout.setText('请先新增曲线。'); return None
        from .plot_style_dialog import PlotStyleDialog
        if self.style_dialog: self.style_dialog.close(); self.style_dialog.deleteLater()
        self.style_dialog=PlotStyleDialog(self,section or ('axes' if side else 'general'),side or 'left'); self.style_dialog.show()
        return self.style_dialog

    def context_menu(self,position):
        # Context-menu events use QPoint; mouse picking and QRectF use QPointF.
        position=QPointF(position)
        menu=QMenu(self); apply_menu_theme(menu)
        def action(text,logo,callback): return menu.addAction(icon(logo),text,callback)
        action('重置视图','plot_reset',self.reset)
        side=self.interaction_axis(position); legend=self.legend_at(position)
        curve=None if side or legend else curve_hit(self,position)
        if side:
            scales=menu.addMenu(icon('plot_linear'),'刻度'); apply_menu_theme(scales)
            group=QActionGroup(scales); group.setExclusive(True)
            for scale,label in [('linear','线性刻度'),('sqrt','根号刻度'),('log','对数刻度')]:
                item=scales.addAction(label,lambda checked=False,value=scale:self.set_axis_scale(side,value))
                group.addAction(item)
                item.setCheckable(True); item.setChecked(axis_scale(self.style['axes'][side])==scale)
            from .plot_content import AxisRangeControls
            ranges=menu.addMenu(icon('plot_linear'),'范围'); apply_menu_theme(ranges)
            controls=AxisRangeControls(self,side,ranges); entry=QWidgetAction(ranges); entry.setDefaultWidget(controls); ranges.addAction(entry)
            action('图片样式','plot_style',lambda:self.open_style(side))
        elif legend:
            action('图片样式','plot_style',lambda:self.open_style(section='legend'))
            action('图例条目','eye',self.open_legend_entries)
        elif curve is not None:
            self.select_curve(curve)
            action('复制曲线','curve_copy',lambda:self.copy_curve(curve))
            action('删除曲线','clear',lambda:self.delete_curve(curve))
            action('标注坐标','plot_point',lambda:self.annotate_point(curve,position))
            action('清除标点','clear',lambda:self.clear_points(curve)).setEnabled(bool(self.curves[curve].points))
            action('图片样式','plot_style',lambda:self.open_style(section='curve'))
        else:
            paste=action('粘贴曲线','curve_paste',self.paste_curve)
            mime=QApplication.clipboard().mimeData(); paste.setEnabled(bool(mime and mime.hasFormat(CURVE_MIME)))
            add=menu.addMenu(icon('plot_open'),'新增曲线'); apply_menu_theme(add)
            add.addAction(icon('plot_point'),'表达式',self.open_expression); add.addAction(icon('plot_open'),'文件',self.add_file_curves)
            action('图片样式','plot_style',self.open_style)
            export=menu.addMenu(icon('plot_save'),'导出图片'); apply_menu_theme(export)
            export.addAction(icon('plot_camera'),'复制图片',self.toolbar.copy_image)
            export.addAction(icon('plot_save'),'保存图片',lambda:self.save_image(False))
            export.addAction(icon('plot_save'),'矢量文件（SVG/PDF）',lambda:self.save_image(True))
        return menu

    def open_expression(self):
        from .curve_dialogs import ExpressionDialog
        self.expression_dialog=ExpressionDialog(self); self.expression_dialog.show(); return self.expression_dialog

    def add_expression(self,text,domain):
        from .expressions import expression_curves
        segments=expression_curves(text,domain,self.bounds)
        for index,(x,y) in enumerate(segments):
            self.curves.append(PlotCurve(x,y,deepcopy(self.style['curve']),text+(f' ({index+1})' if len(segments)>1 else ''),expression=text,role='expression'))
        self.selected_curve=len(self.curves)-1; self.rebuild(); self.selection_changed.emit()

    def open_legend_entries(self):
        from .curve_dialogs import LegendEntriesDialog
        self.legend_entries_dialog=LegendEntriesDialog(self); self.legend_entries_dialog.show(); return self.legend_entries_dialog

    def contextMenuEvent(self,event):
        menu=self.context_menu(event.pos())
        event.accept()
        try: menu.exec(event.globalPos())
        finally: menu.deleteLater()

    def set_axis_scale(self,side,value):
        scale=('log' if value else 'linear') if isinstance(value,bool) else value
        if scale not in ('linear','sqrt','log'): raise ValueError('未知刻度类型。')
        style=deepcopy(self.style); style['axes'][side].update(log=scale=='log',sqrt=scale=='sqrt')
        try: self.apply_style(style)
        except ValueError as error: self.readout.setText(str(error))

    def axis_limits(self,side):
        axis=self.axis_artists[side]
        return axis.get_xlim() if side in ('bottom','top') else axis.get_ylim()

    def interaction_axis(self,position):
        side=self.axis_at(position)
        if side and not self.style['axes'][side]['visible'] and self.style['general']['box']:
            first,second=('bottom','top') if side in ('bottom','top') else ('left','right')
            side=first if self.style['axes'][first]['visible'] else second
        return side

    def set_axis_range(self,side,minimum,maximum):
        style=deepcopy(self.style); style['axes'][side].update(minimum=str(minimum).strip(),maximum=str(maximum).strip())
        style=validate_style(style); horizontal=side in ('bottom','top')
        first,second=('bottom','top') if horizontal else ('left','right')
        primary=first if style['axes'][first]['visible'] else second
        bounds=list(self.bounds)
        if side==primary:
            automatic=self.reset_bounds(style); offset=0 if horizontal else 2
            bounds[offset:offset+2]=automatic[offset:offset+2]
        else:
            low,high=self.bounds[:2] if horizontal else self.bounds[2:]
            settings=style['axes'][side]
            low=float(settings['minimum']) if settings['minimum'] else low
            high=float(settings['maximum']) if settings['maximum'] else high
            if low>=high: raise ValueError('坐标轴最大值必须大于最小值。')
        figure,data,axes=make_figure(self.display_scan,style,tuple(bounds),(self.width(),self.height()),self.curve_visible,self.name,curves=self.curves)
        self.style=style; self.bounds=tuple(bounds); self.install_figure(figure,data,axes)
        if self.style_dialog is not None:
            self.style_dialog.base_style['axes'][side].update(minimum=style['axes'][side]['minimum'],maximum=style['axes'][side]['maximum'])

    def zoom_axis(self,side,position,factor):
        low,high=self.axis_limits(side); scale=axis_scale(self.style['axes'][side]); area=self.area()
        fraction=(position.x()-area.left())/area.width() if side in ('bottom','top') else (area.bottom()-position.y())/area.height()
        fraction=max(0,min(1,fraction))
        if scale=='log': low,high=math.log10(low),math.log10(high)
        elif scale=='sqrt': low,high=math.sqrt(max(0,low)),math.sqrt(max(0,high))
        pivot=low+fraction*(high-low); low,high=pivot+(low-pivot)*factor,pivot+(high-pivot)*factor
        if high-low<1e-10: return
        if scale=='log':
            if max(abs(low),abs(high))>250: return
            low,high=10**low,10**high
        elif scale=='sqrt':
            if high<=0: return
            low,high=max(0,low)**2,high**2
        self.set_axis_range(side,f'{low:.15g}',f'{high:.15g}')

    def keyPressEvent(self,event):
        if event.matches(QKeySequence.StandardKey.Undo): self.restore_history(); event.accept()
        elif event.matches(QKeySequence.StandardKey.Redo) or (event.key()==Qt.Key.Key_Z and event.modifiers()==(Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.ShiftModifier)): self.restore_history(True); event.accept()
        elif event.key()==Qt.Key.Key_Delete: self.delete_curve(); event.accept()
        elif event.key()==Qt.Key.Key_Escape and self.manual_peak_mode: self.cancel_peak_selection(); event.accept()
        elif event.key()==Qt.Key.Key_Escape: self.select_curve(None); event.accept()
        elif event.matches(QKeySequence.StandardKey.Copy): self.copy_curve(); event.accept()
        elif event.matches(QKeySequence.StandardKey.Paste): self.paste_curve(); event.accept()
        else: super().keyPressEvent(event)

    def eventFilter(self,obj,event):
        if obj is self.canvas:
            handlers={QEvent.Type.KeyPress:self.keyPressEvent,QEvent.Type.Wheel:self.wheelEvent,QEvent.Type.MouseButtonPress:self.mousePressEvent,
                QEvent.Type.MouseButtonRelease:self.mouseReleaseEvent,QEvent.Type.MouseMove:self.mouseMoveEvent,
                QEvent.Type.MouseButtonDblClick:self.mouseDoubleClickEvent,QEvent.Type.ContextMenu:self.contextMenuEvent}
            if event.type() in handlers: handlers[event.type()](event); return True
        return super().eventFilter(obj,event)

    def enterEvent(self,event): super().enterEvent(event); self.toolbar.reveal()
    def leaveEvent(self,event):
        super().leaveEvent(event); self.hover_point=None; self.selection_overlay.update(); QTimer.singleShot(30,self.toolbar.check_leave)
    def resizeEvent(self,event):
        super().resizeEvent(event); self.canvas.setGeometry(self.rect())
        if self.scan is not None: self.rebuild()

    def coordinates(self,point):
        ratio=self.canvas.figure.bbox.width/self.width()
        return self.data_axes.transData.inverted().transform((point.x()*ratio,(self.height()-point.y())*ratio))

    def move_bounds(self,fx,fy,factor=1,dx=0,dy=0):
        result=[]
        for index,(fraction,delta) in enumerate(((fx,dx),(fy,dy))):
            low,high=self.bounds[index*2:index*2+2]; scale=axis_scale(self.primary(index==0)); logarithmic=scale=='log'
            if logarithmic: low,high=math.log10(low),math.log10(high)
            elif scale=='sqrt': low,high=math.sqrt(max(0,low)),math.sqrt(max(0,high))
            pivot=low+fraction*(high-low); shift=delta*(high-low)
            a,b=pivot+(low-pivot)*factor+shift,pivot+(high-pivot)*factor+shift
            if b-a<1e-10 or not all(math.isfinite(v) for v in (a,b)): return
            if logarithmic and max(abs(a),abs(b))>250: return
            if scale=='sqrt':
                if b<=0: return
                result.extend((max(0,a)**2,b**2))
            else: result.extend((10**a,10**b) if logarithmic else (a,b))
        for side,settings in self.style['axes'].items():
            if settings['visible'] and tick_mode(settings)=='spacing' and not settings['labels']:
                low,high=result[:2] if side in ('bottom','top') else result[2:]
                if settings['log']:
                    if low<=0: continue
                    low,high=math.log10(low),math.log10(high)
                elif axis_scale(settings)=='sqrt': low,high=math.sqrt(max(0,low)),math.sqrt(max(0,high))
                if (high-low)/settings['interval']>9998:
                    self.readout.setText('刻度过密，请在图片样式中增大间距。'); return
        for horizontal in (True,False):
            axis=self.primary(horizontal); offset=0 if horizontal else 2
            if axis['minimum'] or axis['maximum']: axis.update(minimum=f'{result[offset]:.15g}',maximum=f'{result[offset+1]:.15g}')
        self.bounds=tuple(result); self.sync_view()

    def sync_view(self):
        l,r,b,t=self.bounds; self.data_axes.set_xlim(l,r); self.data_axes.set_ylim(b,t)
        for side,axis in self.axis_artists.items():
            settings=self.style['axes'][side]; low,high=(l,r) if side in ('bottom','top') else (b,t)
            if settings['minimum'].strip(): low=float(settings['minimum'])
            if settings['maximum'].strip(): high=float(settings['maximum'])
            if settings['log'] and low<=0: continue
            if axis_scale(settings)=='sqrt': low=max(0,low); high=max(high,low+1e-10)
            if side in ('bottom','top'): axis.set_xlim(low,high)
            else: axis.set_ylim(low,high)
        self.canvas.draw_idle(); self.selection_overlay.update()
        if self.drag is None: self.remember()

    def wheelEvent(self,event):
        if self.manual_peak_mode: event.accept(); return
        a=self.area()
        side=self.interaction_axis(event.position())
        if side and self.style['axes'][side]['visible']:
            try: self.zoom_axis(side,event.position(),.8 if event.angleDelta().y()>0 else 1.25)
            except ValueError as error: self.readout.setText(str(error))
            event.accept(); return
        if not a.contains(event.position()): return
        self.move_bounds((event.position().x()-a.left())/a.width(),(a.bottom()-event.position().y())/a.height(),.8 if event.angleDelta().y()>0 else 1.25); event.accept()

    def mousePressEvent(self,event):
        self.canvas.setFocus()
        if self.manual_peak_mode:
            if event.button()==Qt.MouseButton.RightButton: self.cancel_peak_selection()
            elif event.button()==Qt.MouseButton.LeftButton and self.area().contains(event.position()): self.peak_start=event.position(); self.peak_rect=QRectF(event.position(),event.position())
            return
        if event.button()==Qt.MouseButton.LeftButton and self.legend_at(event.position()):
            legend=self.data_axes.get_legend(); box=legend.get_window_extent(self.canvas.get_renderer()); ratio=self.canvas.figure.bbox.width/self.width()
            self.legend_drag=(event.position(),box.x0/ratio,self.height()-box.y0/ratio,box.width/ratio,box.height/ratio)
            self.drag=None; self.hover_point=None; self.selection_overlay.update(); self.canvas.setCursor(Qt.CursorShape.ClosedHandCursor); return
        if event.button()==Qt.MouseButton.LeftButton and self.area().contains(event.position()):
            self.press_position=event.position(); self.drag=(event.position(),self.bounds)
    def mouseReleaseEvent(self,event):
        if self.manual_peak_mode:
            if event.button()!=Qt.MouseButton.LeftButton: return
            rectangle=self.peak_rect; self.cancel_peak_selection()
            if rectangle is None or rectangle.width()<4 or rectangle.height()<4:
                self.readout.setText('框选范围过小，请重新选择。'); return
            x0,y0=self.coordinates(rectangle.bottomLeft()); x1,y1=self.coordinates(rectangle.topRight())
            self.peak_region_selected.emit((min(x0,x1),max(x0,x1),min(y0,y1),max(y0,y1))); return
        if self.legend_drag is not None:
            self.legend_drag=None; self.canvas.unsetCursor(); self.remember(); return
        if event.button()==Qt.MouseButton.LeftButton and self.press_position is not None and (event.position()-self.press_position).manhattanLength()<4:
            curve=curve_hit(self,event.position())
            if curve is not None: self.annotate_point(curve,event.position())
            else: self.select_curve(None)
        self.drag=None; self.press_position=None; self.remember()
    def mouseDoubleClickEvent(self,event):
        self.drag=None; self.press_position=None
        if event.button()!=Qt.MouseButton.LeftButton: return
        if self.manual_peak_mode: return
        self.legend_drag=None; self.canvas.unsetCursor()
        annotation=self.point_annotation_at(event.position())
        if annotation is not None: self.edit_point_label(*annotation); return
        index=self.legend_entry_at(event.position())
        if index is not None: self.edit_legend_label(index); return
        side=self.label_at(event.position())
        if side is not None: self.edit_axis_label(side); return
        if self.legend_at(event.position()): return
        curve=curve_hit(self,event.position())
        if curve is None: self.reset()
        else: self.annotate_point(curve,event.position())
    def mouseMoveEvent(self,event):
        self.legend_hover=self.legend_at(event.position()); self.legend_handle.update()
        self.toolbar.reveal(); a=self.area()
        if self.manual_peak_mode:
            if self.peak_start is not None:
                end=QPointF(max(a.left(),min(a.right(),event.position().x())),max(a.top(),min(a.bottom(),event.position().y())))
                self.peak_rect=QRectF(self.peak_start,end).normalized(); self.selection_overlay.update()
            return
        if self.legend_drag is not None:
            start,x,y,width,height=self.legend_drag; delta=event.position()-start
            x=max(a.left(),min(x+delta.x(),a.right()-width)); y=max(a.top()+height,min(y+delta.y(),a.bottom()))
            self.legend_anchor=((x-a.left())/a.width(),(a.bottom()-y)/a.height())
            self.data_axes.get_legend().set_loc(self.legend_anchor); self.canvas.draw_idle(); self.legend_handle.update(); return
        if self.drag:
            start,bounds=self.drag; self.bounds=bounds; delta=event.position()-start
            if delta.manhattanLength()>=4:
                self.hover_point=None; self.move_bounds(.5,.5,dx=-delta.x()/a.width(),dy=delta.y()/a.height())
            return
        curve=None if self.legend_at(event.position()) else curve_hit(self,event.position())
        self.hover_point=(curve,nearest_point(self,curve,event.position())) if curve is not None else None
        self.selection_overlay.update()
        self.canvas.setCursor(Qt.CursorShape.OpenHandCursor if self.legend_at(event.position()) else Qt.CursorShape.CrossCursor if curve is not None else Qt.CursorShape.ArrowCursor)
        if a.contains(event.position()):
            x,_=self.coordinates(event.position())
            if self.selected_curve is not None:
                curve=self.curves[self.selected_curve]; i=nearest_point(self,self.selected_curve,event.position()); x,y=curve.x[i],curve.display_y[i]
            else:
                index=min(bisect_left(self.sorted_x,x),len(self.sorted_x)-1)
                if index and abs(self.sorted_x[index-1]-x)<abs(self.sorted_x[index]-x): index-=1
                x,y=self.sorted_points[index]
            self.readout.setText(f'{self.display_scan.axis_label}: {x:.5f}    {self.display_scan.y_label}: {y:.6g}')

class XrdPage(QWidget):
    def __init__(self,path,scans):
        super().__init__(); self.path=path; self.scans=scans; self.data_kind=scans[0].data_kind; self.peak_dialog=None; self.info_dialog=None; self.thickness_dialog=None
        self.series_label='条曲线' if self.data_kind in ('AFM','XY') else '个扫描'
        layout=QVBoxLayout(self); layout.setContentsMargins(10,8,10,8)
        self.selector=QComboBox(self); self.selector.addItems([f'{i+1} · {len(s.x)} 点' for i,s in enumerate(scans)]); self.selector.hide()
        left=QWidget(); row=QHBoxLayout(left); row.setContentsMargins(0,0,0,0)
        self.kind_label=QLabel(); row.addWidget(self.kind_label)
        self.info_button=QToolButton(); self.info_button.setText('文件信息'); self.info_button.clicked.connect(self.open_file_info); row.addWidget(self.info_button)
        self.analysis_toolbar=QFrame(); self.analysis_toolbar.setObjectName('xrdAnalysisToolbar')
        self.analysis_toolbar.setStyleSheet('QFrame#xrdAnalysisToolbar {background:transparent;border:0;}')
        analysis=QHBoxLayout(self.analysis_toolbar); analysis.setContentsMargins(0,0,0,0); analysis.setSpacing(4)
        self.manual_peaks_button=QToolButton(); self.manual_peaks_button.setText('手动寻峰'); self.manual_peaks_button.setIcon(icon('select')); self.manual_peaks_button.setCheckable(True)
        self.auto_peaks_button=QToolButton(); self.auto_peaks_button.setText('自动寻峰'); self.auto_peaks_button.setIcon(icon('find_peaks'))
        for button in (self.manual_peaks_button,self.auto_peaks_button):
            button.setIconSize(QSize(20,20)); button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon); analysis.addWidget(button)
        self.manual_peaks_button.clicked.connect(self.begin_manual_peaks); self.auto_peaks_button.clicked.connect(lambda:self.open_peak_finding(run=True))
        self.peaks_more_button=QToolButton(); self.peaks_more_button.setIcon(icon('more')); self.peaks_more_button.setToolTip('寻峰设置与结果'); self.peaks_more_button.setIconSize(QSize(20,20))
        self.peaks_more_button.setStyleSheet('QToolButton {border:0;background:transparent;} QToolButton:hover {background:#e0e8e3;}'); self.peaks_more_button.clicked.connect(lambda:self.open_peak_finding())
        analysis.addWidget(self.peaks_more_button); self.find_peaks_button=self.auto_peaks_button
        self.thickness_button=QToolButton(); self.thickness_button.setText('计算膜厚'); self.thickness_button.setIcon(icon('film_thickness'))
        self.thickness_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon); self.thickness_button.setIconSize(QSize(20,20))
        self.thickness_button.setToolTip('根据Kiessig条纹峰间距估算膜厚'); self.thickness_button.clicked.connect(self.open_thickness); analysis.addWidget(self.thickness_button)
        self.background_fit=QCheckBox('拟合背景'); self.background_subtract=QCheckBox('扣除背景')
        self.background_fit.setToolTip('拟合并显示当前曲线的背景，强峰数据自动用SNIP；三点可选方法与窗口，再次点击隐藏背景线。')
        self.background_subtract.setToolTip('从当前曲线扣除拟合背景；取消勾选恢复原始强度，原始文件不变。')
        analysis.addWidget(self.background_fit); analysis.addWidget(self.background_subtract)
        self.background_more=QToolButton(); self.background_more.setIcon(icon('more')); self.background_more.setToolTip('背景拟合方法与窗口')
        self.background_more.setStyleSheet('QToolButton {border:0;background:transparent;} QToolButton:hover {background:#e0e8e3;}')
        self.background_more.clicked.connect(self.open_background_settings); analysis.addWidget(self.background_more)
        self.background_dialog=None
        self.readout=QLabel(); self.plot=XrdPlot(self.readout); self.plot.name=path.stem
        self.background_fit.toggled.connect(lambda value:self.change_background(show=value))
        self.background_subtract.toggled.connect(lambda value:self.change_background(subtract=value))
        self.plot.selection_changed.connect(self.sync_background)
        self.plot.history_changed.connect(self.update_history_actions)
        self.plot.curve_removed.connect(self.close_analysis)
        self.header=PlotHeader(left,self.analysis_toolbar,self.plot.toolbar,self.data_kind=='XRD'); layout.addWidget(self.header)
        self.plot_host=PlotAspectHost(self.plot); layout.addWidget(self.plot_host,1); layout.addWidget(self.readout)
        self.plot.peak_region_selected.connect(lambda region:self.open_peak_finding(run=True,region=region))
        self.plot.peak_selection_finished.connect(lambda:self.manual_peaks_button.setChecked(False))
        self.selector.currentIndexChanged.connect(self.select_scan); self.select_scan(0)
    def sync_background(self):
        available=bool(self.plot.curves)
        for widget in (self.manual_peaks_button,self.auto_peaks_button,self.peaks_more_button,self.thickness_button,self.background_fit,self.background_subtract,self.background_more): widget.setEnabled(available)
        if not available: return
        curve=self.plot.curves[self.plot.active_curve_index]
        for widget,value in ((self.background_fit,curve.show_background),(self.background_subtract,curve.subtract_background)):
            widget.blockSignals(True); widget.setChecked(value); widget.blockSignals(False)

    def change_background(self,**options):
        try: changed=self.plot.set_background(**options)
        except ValueError as error:
            QMessageBox.warning(self,'背景拟合失败',str(error)); self.sync_background(); return False
        else:
            if changed and self.peak_dialog is not None: self.peak_dialog.curve_changed(self.peak_dialog.curve.currentIndex())
        self.sync_background()
        return True

    def open_background_settings(self):
        from .background_dialog import BackgroundDialog
        if self.background_dialog is not None: self.background_dialog.close(); self.background_dialog.deleteLater()
        self.background_dialog=BackgroundDialog(self); self.background_dialog.show(); return self.background_dialog
    def select_scan(self,index):
        if self.thickness_dialog is not None: self.thickness_dialog.reject(); self.thickness_dialog.deleteLater(); self.thickness_dialog=None
        if self.background_dialog is not None: self.background_dialog.reject(); self.background_dialog.deleteLater(); self.background_dialog=None
        if self.peak_dialog is not None: self.peak_dialog.reject(); self.peak_dialog.deleteLater(); self.peak_dialog=None
        scan=self.scans[index]; self.plot.set_scan(scan); self.selector.setToolTip(scan.axis_label)
        self.thickness_button.setVisible(scan.template_name=='XRR')
        self.sync_background()
        self.kind_label.setText('AFM高度' if scan.data_kind=='AFM' else scan.template_name if scan.template_name!='global' else '数据')
        self.header.arrange()
        self.readout.setText(f'模板：{self.plot.template_name} · 单击曲线标点 · 拖动图例 · 双击轴标签编辑')
    def set_log(self,value):
        self.plot.set_axis_scale('left','log' if value else 'linear')
    def begin_manual_peaks(self):
        if self.manual_peaks_button.isChecked():
            if self.peak_dialog is not None: self.peak_dialog.hide()
            self.plot.start_peak_selection()
        else: self.plot.cancel_peak_selection()

    def open_file_info(self):
        from .file_info_dialog import FileInfoDialog
        if self.info_dialog is not None: self.info_dialog.close(); self.info_dialog.deleteLater()
        self.info_dialog=FileInfoDialog(self); self.info_dialog.show(); return self.info_dialog

    def open_thickness(self):
        if not self.plot.curves: return False
        from .thickness_dialog import ThicknessDialog
        if self.thickness_dialog is not None: self.thickness_dialog.close(); self.thickness_dialog.deleteLater()
        self.thickness_dialog=ThicknessDialog(self); self.thickness_dialog.show(); return self.thickness_dialog

    def open_peak_finding(self,run=False,region=None):
        if not self.plot.curves: return False
        from .peak_dialog import PeakFindingDialog
        self.plot.cancel_peak_selection()
        if self.peak_dialog is None:
            self.peak_dialog=PeakFindingDialog(self.plot,region)
        self.peak_dialog.curve.blockSignals(True)
        while self.peak_dialog.curve.count()>len(self.plot.curves): self.peak_dialog.curve.removeItem(self.peak_dialog.curve.count()-1)
        for i,curve in enumerate(self.plot.curves):
            text=f'{i+1} · {curve.label}'
            if i<self.peak_dialog.curve.count(): self.peak_dialog.curve.setItemText(i,text)
            else: self.peak_dialog.curve.addItem(text)
        self.peak_dialog.curve.blockSignals(False)
        if run:
            if self.plot.selected_curve is not None: self.peak_dialog.curve.setCurrentIndex(self.plot.selected_curve)
            self.peak_dialog.set_region(region); self.peak_dialog.run()
        self.peak_dialog.show(); self.peak_dialog.raise_(); return self.peak_dialog
    def update_history_actions(self):
        host=self.window()
        if hasattr(host,'update_actions'): host.update_actions()

    def undo(self):
        self.close_analysis(); return self.plot.restore_history()

    def redo(self):
        self.close_analysis(); return self.plot.restore_history(True)

    def close_analysis(self):
        for name in ('peak_dialog','thickness_dialog','background_dialog'):
            dialog=getattr(self,name,None)
            if dialog is not None: dialog.close(); dialog.deleteLater(); setattr(self,name,None)

    def save_file(self,save_as=False):
        path=self.path if self.path.suffix.lower()=='.cxplot' and not save_as else None
        if path is None:
            value,_=QFileDialog.getSaveFileName(self,'保存图文件',str(self.path.with_suffix('.cxplot')),'CrystalX 图文件 (*.cxplot)')
            if not value: return False
            path=Path(value)
            if path.suffix.lower()!='.cxplot': path=path.with_suffix('.cxplot')
        from .plot_document import write_document
        try: write_document(path,self)
        except (OSError,ValueError) as error: QMessageBox.warning(self,'保存失败',str(error)); return False
        self.path=path; self.update_history_actions(); return True

    def restore_document(self,states,active,name):
        self.plot.history_locked=True
        for scan,state in zip(self.scans,states):
            if state is not None:
                self.plot.scan_curves[id(scan)]=state['curves']
                self.plot.scan_states[id(scan)]=(state['style'],state.get('template_name',scan.template_name),None,state['legend_anchor'])
                self.plot.committed[id(scan)]=deepcopy(state)
        self.selector.blockSignals(True); self.selector.setCurrentIndex(active); self.selector.blockSignals(False)
        self.plot.scan=None
        self.select_scan(active)
        state=states[active]
        if state is not None:
            self.plot.history_locked=True
            for key,value in state.items(): setattr(self.plot,key,deepcopy(value))
            self.plot.name=name; self.plot.rebuild(); self.plot.history_locked=False; self.plot.committed[id(self.plot.scan)]=self.plot.snapshot()
        self.plot.history={}; self.plot.redo_history={}; self.update_history_actions()

    def confirm_changes(self): return True
