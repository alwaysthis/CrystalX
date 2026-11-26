"""Real widget interactions for curve clipboard, contextual menus and presets."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from PyQt6.QtCore import Qt,QPointF,QEvent,QTimer
from PyQt6.QtGui import QFont,QFontDatabase,QContextMenuEvent
from PyQt6.QtWidgets import QApplication,QLabel
from PyQt6.QtTest import QTest
from crystalx.xrd_page import XrdPlot
from crystalx.xrd_io import XrdScan
from crystalx.plot_presets import PlotDefaults
from crystalx.plot_selection import curve_hit

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
root=Path(__file__).resolve().parents[1]; out=root/'output'; out.mkdir(exist_ok=True)
with TemporaryDirectory() as directory:
    defaults=PlotDefaults(Path(directory)/'plot.json')
    source=XrdPlot(QLabel(),defaults); source.resize(900,600); source.set_scan(XrdScan([1,2,3,4],[2,5,3,7],{'MEAS_SCAN_UNIT_Y':'counts'})); source.show()
    target=XrdPlot(QLabel(),defaults); target.resize(1000,650); target.set_scan(XrdScan([1,2,3,4],[1,3,4,6])); target.show(); app.processEvents()
    assert [t.get_text() for t in source.data_axes.get_legend().get_texts()]==['plot 1']
    style=deepcopy(source.style); style['general'].update(color='#cc2222',width=2.5)
    source.apply_style(style); source.curves[0].label='source legend'; source.curves[0].points=[1]; source.rebuild(); app.processEvents()
    point=source.point(3,3); assert curve_hit(source,point)==0
    QTest.mouseClick(source.canvas,Qt.MouseButton.LeftButton,pos=point.toPoint()); assert source.selected_curve==0
    unselected=source.export_image(scale=1); source.select_curve(None)
    assert source.export_image(scale=1)==unselected  # transient selection is not exported
    source.select_curve(0); source.canvas.setFocus(); QTest.keyClick(source.canvas,Qt.Key.Key_C,Qt.KeyboardModifier.ControlModifier)
    style=deepcopy(target.style); style['general'].update(color='#2244cc',background='#eeeeff'); target.apply_style(style)
    previous=deepcopy(target.style); bounds=target.bounds
    target.canvas.setFocus(); QTest.keyClick(target.canvas,Qt.Key.Key_V,Qt.KeyboardModifier.ControlModifier); app.processEvents()
    assert len(target.curves)==2 and target.style==previous and target.bounds==bounds
    assert target.curves[1].style['color']=='' and target.curves[1].style['width']==0
    assert target.data_axes.curve_artists[1].get_color()=='#2244cc'
    assert target.curves[1].label=='source legend' and target.curves[1].points==[1,2]
    point=target.point(3,3); menu=target.context_menu(point)
    names=[a.text() for a in menu.actions()]
    assert names[0]=='重置视图' and '复制曲线' in names and '导出图片' not in names
    assert all(not action.icon().isNull() for action in menu.actions())
    area=target.area(); axis_menu=target.context_menu(QPointF(area.left()-5,area.center().y()))
    axis_names=[a.text() for a in axis_menu.actions()]
    assert '刻度' in axis_names and '复制图片' not in axis_names
    scale_menu=next(a.menu() for a in axis_menu.actions() if a.text()=='刻度')
    assert [a.text() for a in scale_menu.actions()]==['线性刻度','根号刻度','对数刻度']
    curves_before=[c.settings() for c in target.curves]
    next(a for a in scale_menu.actions() if a.text()=='对数刻度').trigger()
    assert target.style['axes']['left']['log'] and [c.settings() for c in target.curves]==curves_before
    target.set_axis_scale('left',False); app.processEvents()
    legend=target.data_axes.get_legend().get_window_extent(target.canvas.get_renderer())
    ratio=target.canvas.figure.bbox.width/target.width()
    position=QPointF(legend.x0/ratio+legend.width/(2*ratio),target.height()-(legend.y0+legend.height/2)/ratio)
    assert target.legend_at(position)
    legend_names=[a.text() for a in target.context_menu(position).actions()]
    assert '复制图片' not in legend_names and '导出图片' not in legend_names
    # Find empty plot space away from curves/legend/axes, then inspect its menu.
    for fx,fy in ((.75,.2),(.3,.1),(.5,.8),(.2,.7)):
        point=QPointF(area.left()+area.width()*fx,area.top()+area.height()*fy)
        menu=target.context_menu(point)
        if '粘贴曲线' in [a.text() for a in menu.actions()]: break
    assert '粘贴曲线' in [a.text() for a in menu.actions()]
    # Send real context-menu events: unlike mouse events their position is QPoint.
    # Closing via the nested event loop verifies popup dispatch, not only construction.
    import sys
    errors=[]; original_hook=sys.excepthook
    sys.excepthook=lambda *error: errors.append(error)
    try:
        for position in (point,target.point(3,3),QPointF(area.left()-5,area.center().y())):
            popped=[]
            def dismiss():
                popup=QApplication.activePopupWidget()
                if popup is not None:
                    popped.append([a.text() for a in popup.actions()]); popup.close()
            QTimer.singleShot(50,dismiss)
            event=QContextMenuEvent(QContextMenuEvent.Reason.Mouse,position.toPoint(),target.canvas.mapToGlobal(position.toPoint()))
            QApplication.sendEvent(target.canvas,event)
            assert not errors,errors
            assert popped and popped[0][0]=='重置视图'
            assert event.isAccepted()
    finally: sys.excepthook=original_hook
    point=target.point(3,3); target.annotate_point(1,point); assert 2 in target.curves[1].points
    dialog=target.open_style(section='curve'); app.processEvents()
    assert dialog.curve_selector.count()==2
    dialog.curve_selector.setCurrentIndex(0)
    color=dialog.fields[('curve','color')][1]; color.set_color('#228822')
    dialog.curve_selector.setCurrentIndex(1); dialog.fields[('curve','label')][1].setText('renamed second')
    assert dialog.apply(),dialog.error.text()
    assert target.curves[0].style['color']=='#228822' and target.curves[1].style['color']==''
    assert target.curves[1].label=='renamed second' and source.curves[0].label=='source legend'
    assert 'tick_mode' not in [path[-1] for path in dialog.fields]
    ticks=dialog.fields[('axes','bottom','ticks')][1]; interval=dialog.fields[('axes','bottom','interval')][1]
    ticks.setText('[1 2 3 4]'); assert not interval.isEnabled()
    ticks.clear(); assert interval.isEnabled()
    assert dialog.fields[('axes','left','label')][1].text()=='Intensity'
    font=dialog.fields[('general','font')][1]; font.showPopup(); app.processEvents()
    assert font.view().window().width()<=260; font.hidePopup()
    assert dialog.navigation.visualItemRect(dialog.navigation.item(0)).height()<=32
    config=Path(directory)/'export.json'; dialog.export_to(config)
    dialog.fields[('general','size')][1].setValue(22); dialog.load_from(config)
    assert dialog.fields[('general','size')][1].value()==previous['general']['size']
    assert dialog.apply(),dialog.error.text()
    fresh=XrdPlot(QLabel(),PlotDefaults(defaults.path)); fresh.resize(900,600); fresh.set_scan(XrdScan([1,2],[3,4]))
    plain=XrdPlot(QLabel(),PlotDefaults(Path(directory)/'factory.json')); plain.set_scan(XrdScan([1,2],[3,4]))
    plain.add_scan(XrdScan([1,2],[5,6])); assert [c.label for c in plain.curves]==['plot 1','plot 2']
    dialog.navigation.setCurrentRow(1); dialog.axis_selector.setCurrentIndex(1); dialog.axis_categories[1].setCurrentIndex(1)
    dialog.grab().save(str(out/'plot-style-compact.png'))
    dialog.reject(); target.select_curve(None); app.processEvents(); target.grab().save(str(out/'plot-multiple-curves.png'))
    source.close(); target.close(); fresh.close(); plain.close()
    for widget in (source,target,fresh,plain): widget.deleteLater()
    QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
print('Multiple curves, contextual menus, clipboard, compact styling and presets passed')
