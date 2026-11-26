"""Real mouse interactions and content-driven template selection."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PyQt6.QtCore import Qt,QPointF,QEvent
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication,QPushButton
from PyQt6.QtTest import QTest
from crystalx.xrd_page import XrdPage
from crystalx.xrd_io import XrdScan,read_xrd
from crystalx.plot_presets import PlotTemplates,write_plot_config,read_plot_config
from crystalx.plot_style import default_style

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
errors=[]; sys.excepthook=lambda *error: errors.append(error)
scans=[XrdScan([10,20,30,40],[1,6,3,8],{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega'}),
       XrdScan([.1,1,3,6],[1000,100,10,1],{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega'}),
       XrdScan([20,20.1,20.2],[1,8,2],{'MEAS_SCAN_AXIS_X_INTERNAL':'Omega'}),XrdScan([1,2],[3,4])]
assert [s.template_name for s in scans]==['XRD','XRR','Rocking Curve','global']
page=XrdPage(Path('sample.ras'),scans); page.resize(1000,720); page.show(); app.processEvents(); plot=page.plot
assert plot.template_name=='XRD'
assert plot.toolbar.parentWidget() is page.header
assert plot.toolbar.mapTo(page,plot.toolbar.rect().bottomLeft()).y()<plot.mapTo(page,plot.rect().topLeft()).y()
point=plot.point(20,6); image=plot.export_image(scale=1)
QTest.mouseMove(plot.canvas,point.toPoint()); app.processEvents()
assert plot.hover_point==(0,1)
assert plot.export_image(scale=1)==image
QTest.mouseClick(plot.canvas,Qt.MouseButton.LeftButton,pos=point.toPoint()); app.processEvents()
assert plot.curves[0].points==[1] and plot.selected_curve==0
# Right-click construction selects even when the previously selected curve differs.
plot.select_curve(None); plot.context_menu(point); assert plot.selected_curve==0
legend=plot.data_axes.get_legend(); ratio=plot.canvas.figure.bbox.width/plot.width()
box=legend.get_window_extent(plot.canvas.get_renderer())
start=QPointF(box.x0/ratio+box.width/ratio/2,plot.height()-(box.y0+box.height/2)/ratio)
bounds=plot.bounds
QTest.mousePress(plot.canvas,Qt.MouseButton.LeftButton,pos=start.toPoint())
QTest.mouseMove(plot.canvas,(start+QPointF(-110,60)).toPoint())
QTest.mouseRelease(plot.canvas,Qt.MouseButton.LeftButton,pos=(start+QPointF(-110,60)).toPoint()); app.processEvents()
assert plot.legend_anchor is not None and plot.bounds==bounds
anchor=plot.legend_anchor; plot.rebuild(); app.processEvents()
assert plot.legend_anchor==anchor and tuple(plot.data_axes.get_legend()._loc)==anchor
label=plot.axis_artists['bottom'].xaxis.label
box=label.get_window_extent(plot.canvas.get_renderer()); ratio=plot.canvas.figure.bbox.width/plot.width()
position=QPointF((box.x0+box.x1)/2/ratio,plot.height()-(box.y0+box.y1)/2/ratio)
assert plot.label_at(position)=='bottom'
QTest.mouseDClick(plot.canvas,Qt.MouseButton.LeftButton,pos=position.toPoint()); app.processEvents()
editor=plot.label_editor; assert editor.isVisible()
editor.input.setText(r'$\theta_{sample}$'); QTest.keyClick(editor.input,Qt.Key.Key_Return); app.processEvents()
assert plot.style['axes']['bottom']['label']==r'$\theta_{sample}$' and not editor.isVisible()
with TemporaryDirectory() as directory:
    path=Path(directory)/'custom.json'; style=default_style(); style['general']['size']=15
    style['axes']['bottom']['label']='must not replace content'; write_plot_config(path,style)
    assert read_plot_config(path)[0]['axes']['bottom']['label'] is None
    dialog=plot.open_style(); app.processEvents()
    assert dialog.fields[('axes','bottom','label')][1].text()==r'$\theta_{sample}$'
    assert '设为默认' not in [b.text() for b in dialog.findChildren(QPushButton)]
    with patch('crystalx.plot_style_dialog.QFileDialog.getOpenFileName',return_value=(str(path),'图片模板 (*.json)')):
        dialog.template_button.click()
    assert plot.template_name=='XRD' and '待应用：custom' in dialog.template_label.text()
    assert dialog.apply(),dialog.error.text()
    assert plot.template_name=='custom' and plot.style['general']['size']==15
    assert plot.style['axes']['bottom']['label']==r'$\theta_{sample}$'
    assert dialog.template_label.text()=='当前应用模板：\ncustom'
    dialog.reject()
for index,name in enumerate(('custom','XRR','Rocking Curve','global')):
    page.selector.setCurrentIndex(index); app.processEvents()
    assert plot.template_name==name
    assert plot.logarithmic==(name=='XRR')
page.selector.setCurrentIndex(0); app.processEvents()
assert plot.legend_anchor==anchor and plot.style['axes']['bottom']['label']==r'$\theta_{sample}$'
# Native QMenu submenus must open on hover, with no click on the parent item.
area=plot.area(); menu=plot.context_menu(QPointF(area.left()-4,area.center().y()))
submenu=next(action.menu() for action in menu.actions() if action.text()=='刻度')
menu.popup(plot.canvas.mapToGlobal(area.center().toPoint())); app.processEvents()
QTest.mouseMove(menu,menu.actionGeometry(submenu.menuAction()).center()); QTest.qWait(450)
assert submenu.isVisible()
assert [a.text() for a in submenu.actions()]==['线性刻度','根号刻度','对数刻度']
submenu.actions()[1].trigger(); submenu.close(); menu.close(); app.processEvents()
assert plot.data_axes.get_yscale()=='sqrt' and plot.axis_artists['left'].get_yscale()=='sqrt'
view=plot.bounds; plot.move_bounds(.5,.5,factor=.8); assert plot.bounds!=view and plot.bounds[2]>=0
plot.set_axis_scale('left','linear'); app.processEvents()
out=Path(__file__).resolve().parents[1]/'output'
page.grab().save(str(out/'plot-interactions.png'))
dialog=plot.open_style(); app.processEvents(); dialog.grab().save(str(out/'plot-template-settings.png')); dialog.reject()
if len(sys.argv)>1:
    counts={}
    for path in Path(sys.argv[1]).rglob('*.ras'):
        for scan in read_xrd(path):
            expected='Rocking Curve' if 'Rocking curve' in path.parts else 'XRR' if 'XRR' in path.parts else 'XRD'
            assert scan.template_name==expected,(path,scan.template_name)
            counts[expected]=counts.get(expected,0)+1
    print('Actual RAS content identification:',counts)
page.close(); page.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
assert not errors,errors
print('Legend drag, external toolbar, hover/click points, label editor and templates passed')
