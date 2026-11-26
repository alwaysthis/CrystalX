"""Curve ownership, history, expression, native file and menu integration."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest.mock import patch
import sys,traceback,json
import numpy as np
from PyQt6.QtCore import QEvent,QPointF
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication
from crystalx.ui import MainWindow
from crystalx.xrd_page import XrdPage
from crystalx.curve_data import XYScan
from crystalx.plot_presets import PlotTemplates,write_plot_config
from crystalx.plot_document import write_document,read_document
from crystalx.session_state import SessionState

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10)); errors=[]
def report(kind,value,tb): errors.append(value); traceback.print_exception(kind,value,tb)
sys.excepthook=report
with TemporaryDirectory() as directory:
    folder=Path(directory)
    window=MainWindow({'window_width':1450,'window_height':1000},session_state=SessionState(folder/'session.json')); window.show()
    x=np.linspace(.5,2.5,701); y=5+100*np.exp(-.5*((x-1.5)/.08)**2)
    scan=XYScan(x.tolist(),y.tolist(),{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega','HW_XG_WAVE_LENGTH_ALPHA1':'1.540593'})
    page=XrdPage(folder/'XRR.ras',[scan,deepcopy(scan)]); window.work_tabs.addTab(page,'XRR.ras'); window.work_tabs.setCurrentWidget(page); app.processEvents()
    plot=page.plot
    plot.set_axis_scale('left','linear')
    plot.set_axis_label('left',r'$I$ (counts)'); assert plot.can_undo
    page.undo(); assert plot.style['axes']['left']['label']!=r'$I$ (counts)'
    page.redo(); assert plot.style['axes']['left']['label']==r'$I$ (counts)'
    plot.canvas.setFocus(); QTest.keyClick(plot.canvas,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier)
    assert plot.style['axes']['left']['label']!=r'$I$ (counts)'
    QTest.keyClick(plot.canvas,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.ShiftModifier)
    assert plot.style['axes']['left']['label']==r'$I$ (counts)'
    dialog=page.open_peak_finding(); dialog.method.setCurrentIndex(dialog.method.findData("fit")); page.open_peak_finding(run=True); app.processEvents(); assert dialog.result.peaks
    dialog.show_smooth.setChecked(True); app.processEvents()
    assert len(plot.curves)==2 and plot.curves[1].role=='fit'
    fit=plot.curves[1]; fit_id=fit.uid; assert fit.source_id==plot.curves[0].uid
    assert len(plot.data_axes.get_legend().get_texts())==2
    dialog.show_contours.setChecked(True)
    profile=next(c for c in plot.curves if c.role.startswith('profile:'))
    assert profile.visible and profile.fill_baseline
    profile.style['color']='#228822'; plot.rebuild()
    assert plot.data_axes.curve_artists[plot.curves.index(profile)].get_color()=='#228822'
    dialog.show_contours.setChecked(False)
    entries=plot.open_legend_entries(); entries.entries[0][1].setChecked(False); entries.apply()
    assert len(plot.data_axes.get_legend().get_texts())==1
    page.undo(); assert plot.curves[0].legend_visible
    plot.select_curve(1); assert plot.copy_curve(); assert plot.paste_curve()
    pasted=len(plot.curves)-1
    assert plot.curves[pasted].uid!=fit_id and plot.curves[pasted].source_id==''
    plot.select_curve(pasted); dialog=page.open_peak_finding(); dialog.method.setCurrentIndex(dialog.method.findData("fit")); page.open_peak_finding(run=True); assert dialog.result_index==pasted and dialog.result.peaks
    assert plot.curves[0].uid!=plot.curves[pasted].uid
    page.open_thickness(); app.processEvents(); assert page.thickness_dialog.curve.currentIndex()==pasted
    page.thickness_dialog.load_rows([.8,1,1.2]); assert page.thickness_dialog.calculate()
    page.thickness_dialog.show_marks.setChecked(True)
    assert plot.curves[pasted].thickness_marks and not plot.curves[0].thickness_marks
    count=len(plot.curves); plot.select_curve(1); plot.delete_curve(); assert len(plot.curves)==count-1
    assert page.peak_dialog is None and page.thickness_dialog is None
    assert page.undo() and len(plot.curves)==count; assert page.redo() and len(plot.curves)==count-1
    count=len(plot.curves); expression=plot.open_expression(); expression.expression.setText('t^2, {t,-1,1}'); assert expression.add()
    assert len(plot.curves)==count+1 and plot.curves[-1].expression=='t^2, {t,-1,1}'
    plot.add_expression('x=1','0,2'); assert all(abs(value-1)<1e-10 for value in plot.curves[-1].x)
    plot.set_axis_label('bottom',r'$q_z$')
    document=folder/'study.cxplot'; expected=plot.snapshot(); write_document(document,page)
    scans,states,active,name=read_document(document); assert len(scans)==2
    assert states[active]['curves']==expected['curves']; assert states[active]['style']==expected['style']
    assert window.load_path(document); restored=window.current_page(); app.processEvents()
    assert restored.plot.curves==expected['curves'] and restored.plot.bounds==expected['bounds']
    restored.select_scan(1); restored.plot.add_expression('u','-1,1'); restored.select_scan(0)
    assert restored.plot.curves==expected['curves']
    destination=folder/'second.cxplot'
    with patch('crystalx.xrd_page.QFileDialog.getSaveFileName',return_value=(str(destination),'')):
        assert restored.save_file(True)
    assert destination.exists()
    assert not restored.plot.can_undo
    assert window.buttons['保存'].isEnabled()
    restored.select_scan(1)
    with patch('crystalx.xrd_page.QFileDialog.getSaveFileName',return_value=(str(folder/'active-second.cxplot'),'')):
        assert restored.save_file(True)
    assert read_document(folder/'active-second.cxplot')[2]==1
    while restored.plot.curves: restored.plot.delete_curve(0)
    assert not restored.manual_peaks_button.isEnabled()
    assert restored.undo() and restored.plot.curves
    restored.redo(); assert not restored.plot.curves
    plot.templates=PlotTemplates(folder); plot.template_path=None; plot.template_name='XRR'
    style=plot.open_style(); assert style.apply_to_template()
    next_plot=XrdPage(folder/'other.ras',[deepcopy(scan)]); next_plot.plot.templates=PlotTemplates(folder)
    next_plot.plot.scan=None; next_plot.plot.scan_curves={}; next_plot.plot.set_scan(next_plot.scans[0])
    assert next_plot.plot.style['axes']['bottom']['label']==r'$q_z$'
    # Context exports are grouped, and vectors are real SVG rather than screenshots.
    menu=plot.context_menu(QPointF(plot.area().right()-15,plot.area().center().y()))
    actions={action.text():action for action in menu.actions()}; assert '新增曲线' in actions and '导出图片' in actions
    assert [a.text() for a in actions['新增曲线'].menu().actions()]==['表达式','文件']
    vector=folder/'plot.svg'
    with patch('crystalx.xrd_page.QFileDialog.getSaveFileName',return_value=(str(vector),'SVG 矢量图 (*.svg)')): plot.save_image(True)
    assert '<svg' in vector.read_text(encoding='utf-8')
    app.processEvents()
    root=Path(__file__).resolve().parents[1]
    expression=plot.open_expression(); expression.expression.setText('Sin[t]^2, {t,-Pi,Pi}'); app.processEvents()
    expression.grab().save(str(root/'output/expression-curve-dialog.png')); expression.close()
    legend=plot.open_legend_entries(); app.processEvents(); legend.grab().save(str(root/'output/legend-entries-dialog.png')); legend.close()
    assert window.load_path(root/'examples/Si.vasp'); app.processEvents()
    for is_vector,name in ((True,'structure-vector'),(False,'structure-image')):
        destination=folder/name
        with patch('crystalx.ui.QFileDialog.getSaveFileName',return_value=(str(destination),'')): window.export_current(is_vector)
        actual=Path(str(destination)+('.svg' if is_vector else '.png')); assert actual.exists() and actual.stat().st_size>100
    # Native window/context logging must tolerate QWindow (the original crash trigger).
    from crystalx.runtime import RuntimeDiagnostics
    from PyQt6.QtGui import QContextMenuEvent
    diagnostics=RuntimeDiagnostics(app,folder)
    assert diagnostics.eventFilter(window.windowHandle(),QContextMenuEvent(QContextMenuEvent.Reason.Mouse,window.rect().center())) is False
    diagnostics.close()
    for widget in (next_plot,window): widget.close(); widget.deleteLater()
    QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
    assert not errors,errors
print('Native plot round-trip, history, fit curves, pasted analysis, expressions, templates and SVG passed')
