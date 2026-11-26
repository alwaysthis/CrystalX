"""Axis-only wheel events, inline range menus, aspect and template persistence."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,traceback
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from PyQt6.QtCore import Qt,QPoint,QPointF,QEvent
from PyQt6.QtGui import QWheelEvent,QFontDatabase,QFont
from PyQt6.QtWidgets import QApplication,QPushButton
from PyQt6.QtTest import QTest
from crystalx.xrd_page import XrdPage
from crystalx.xrd_io import XrdScan
from crystalx.plot_presets import PlotTemplates,write_plot_config,read_plot_config
from crystalx.plot_style import default_style,aspect_ratio

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
errors=[]
def record(kind,value,tb):
    errors.append(value); traceback.print_exception(kind,value,tb)
sys.excepthook=record
page=XrdPage(Path('scan.ras'),[XrdScan([1,2,3,4],[1,4,9,16],{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega'})])
page.resize(1100,800); page.show(); app.processEvents(); plot=page.plot
assert plot.style['general']['size']==25 and plot.style['general']['box'] and plot.style['general']['font']=='Times New Roman'
def wheel(position):
    event=QWheelEvent(position,plot.canvas.mapToGlobal(position.toPoint()).toPointF(),QPoint(),QPoint(0,120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
    QApplication.sendEvent(plot.canvas,event); app.processEvents(); assert event.isAccepted()
for scale in ('linear','sqrt','log'):
    plot.set_axis_scale('left',scale); app.processEvents()
    plot.set_axis_range('left','1','25'); before=plot.bounds; area=plot.area()
    wheel(QPointF(area.left()-8,area.center().y()))
    assert plot.bounds[:2]==before[:2] and plot.bounds[2:]!=before[2:]
    before=plot.bounds; area=plot.area(); wheel(QPointF(area.center().x(),area.bottom()+8))
    assert plot.bounds[:2]!=before[:2] and plot.bounds[2:]==before[2:]
    # Top/right frame edges also zoom the corresponding visible data axis.
    before=plot.bounds; area=plot.area(); wheel(QPointF(area.center().x(),area.top()-2))
    assert plot.bounds[:2]!=before[:2] and plot.bounds[2:]==before[2:]
plot.set_axis_scale('left','linear'); plot.set_axis_range('left','0','20')
area=plot.area(); menu=plot.context_menu(QPointF(area.left()-4,area.center().y()))
ranges=next(action.menu() for action in menu.actions() if action.text()=='范围')
controls=ranges.actions()[0].defaultWidget(); xbounds=plot.bounds[:2]
menu.popup(plot.canvas.mapToGlobal(area.center().toPoint())); app.processEvents()
QTest.mouseMove(menu,menu.actionGeometry(ranges.menuAction()).center()); QTest.qWait(450); assert ranges.isVisible()
ranges.grab().save(str(Path(__file__).resolve().parents[1]/'output/plot-range-menu.png'))
controls.minimum.setText('2'); controls.maximum.setText('12'); assert controls.apply(); assert plot.bounds==(xbounds+(2.,12.))
before=plot.bounds; controls.minimum.setText('20'); assert not controls.apply() and controls.error.text(); assert plot.bounds==before
dialog=plot.open_style(); app.processEvents()
assert not any(path[-1] in ('minimum','maximum') for path in dialog.fields)
dialog.fields[('general','size')][1].setValue(22); assert dialog.apply(); assert plot.bounds==before
aspect=dialog.fields[('general','aspect')][1]
for choice in ('4:3','1:1','16:9','3:2','自适应'):
    aspect.setCurrentText(choice); assert dialog.apply(),dialog.error.text(); app.processEvents()
    if choice=='自适应': assert plot.geometry()==page.plot_host.rect()
    else:
        expected=aspect_ratio(choice); assert abs(plot.width()/plot.height()-expected)<.01
        image=plot.export_image(scale=1); assert abs(image.width()/image.height()-expected)<.01
    assert plot.bounds==before
aspect.setCurrentText('0:1'); assert not dialog.apply(); aspect.setCurrentText('1:1')
with TemporaryDirectory() as folder:
    templates=PlotTemplates(Path(folder)/'config'); source=templates.root/'default/plot-templates/XRD.json'
    write_plot_config(source,default_style()); original=source.read_bytes()
    plot.templates=templates; plot.template_name=dialog.template_name='XRD'; plot.template_path=dialog.template_path=source
    assert dialog.apply(); assert not (templates.root/'custom/plot-templates/XRD.json').exists()
    assert dialog.apply_to_template(),dialog.error.text()
    target=templates.root/'custom/plot-templates/XRD.json'
    assert target.exists() and source.read_bytes()==original
    style,curves=read_plot_config(target)
    assert style['general']['size']==22 and style['general']['aspect']=='1:1'
    assert not style['axes']['left']['minimum'] and not style['axes']['left']['maximum']
    scan=XrdScan([10,110],[1,2],{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega'})
    assert templates.resolve(scan)[0]['general']['size']==22
out=Path(__file__).resolve().parents[1]/'output'
dialog.grab().save(str(out/'plot-aspect-general.png'))
dialog.navigation.setCurrentRow(1); app.processEvents(); dialog.grab().save(str(out/'plot-axis-header.png'))
assert dialog.axis_selector.parentWidget() is dialog.axis_header
assert [b.text() for b in dialog.findChildren(QPushButton)].count('应用于模板')==1
dialog.reject(); app.processEvents(); page.grab().save(str(out/'plot-square.png'))
page.close(); page.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
assert not errors,errors
print('Axis wheel, inline ranges, appearance isolation, ratios and template application passed')
