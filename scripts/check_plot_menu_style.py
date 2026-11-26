"""Visible menu checks, scientific tick UI, transparent captions and menu order."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from tempfile import TemporaryDirectory
from PyQt6.QtCore import Qt,QPoint,QPointF,QTimer,QEvent
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication,QWidget,QHBoxLayout,QCheckBox
from crystalx.xrd_page import XrdPlot
from crystalx.xrd_io import XrdScan
from crystalx.plot_presets import PlotDefaults
from crystalx.theme import CONTROLS,DIALOG_BG

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
out=Path(__file__).resolve().parents[1]/'output'; suffix=os.environ.get('QT_SCALE_FACTOR','1')
with TemporaryDirectory() as directory:
    plot=XrdPlot(QCheckBox(),PlotDefaults(Path(directory)/'plot.json')); plot.resize(1100,700)
    plot.set_scan(XrdScan([1,2,3],[10,100,1000])); plot.show(); app.processEvents()
    dialog=plot.open_style('left'); app.processEvents()
    scale=dialog.fields[('axes','left','scale')][1]
    assert not scale.isVisible(); dialog.axis_categories[0].setCurrentIndex(1); app.processEvents(); assert scale.isVisible()
    number=dialog.fields[('axes','left','number_format')][1]; number.setCurrentIndex(number.findData('scientific'))
    assert dialog.apply(),dialog.error.text(); app.processEvents()
    assert any(r'\times10^{' in text.get_text() for text in plot.axis_artists['left'].get_yticklabels())
    dialog.grab().save(str(out/f'plot-ticks-{suffix}.png')); dialog.reject()
    def scale_popup():
        area=plot.area(); menu=plot.context_menu(QPointF(area.left()-5,area.center().y()))
        return menu,next(a.menu() for a in menu.actions() if a.text()=='刻度')
    for index,kind in enumerate(('linear','sqrt','log')):
        plot.set_axis_scale('left',kind); app.processEvents(); menu,submenu=scale_popup()
        assert [a.isChecked() for a in submenu.actions()]==[i==index for i in range(3)]
        assert all(a.isCheckable() and a.icon().isNull() for a in submenu.actions())
    submenu.popup(plot.mapToGlobal(QPoint(120,120))); app.processEvents()
    submenu.grab().save(str(out/f'plot-scale-checks-{suffix}.png')); submenu.close()
    captured=[]
    def capture_visibility():
        popup=app.activePopupWidget(); assert popup is not None
        assert popup.actions()[0].isCheckable() and popup.actions()[0].isChecked()
        captured.append(popup.grab()); popup.close()
    QTimer.singleShot(80,capture_visibility); plot.toolbar.visibility_menu(); assert captured
    captured[0].save(str(out/f'plot-visibility-checks-{suffix}.png'))
    for editor in (plot.edit_axis_label('left'),plot.edit_legend_label(0)):
        app.processEvents(); point=editor.caption.mapTo(editor,QPoint(editor.caption.width()-3,editor.caption.height()//2))
        assert editor.grab().toImage().pixelColor(point).name()==DIALOG_BG
        editor.grab().save(str(out/f'plot-text-editor-{suffix}.png')); editor.reject()
    area=plot.area()
    for x,y in ((.5,.9),(.8,.8),(.2,.2)):
        menu=plot.context_menu(QPointF(area.left()+area.width()*x,area.top()+area.height()*y))
        names=[a.text() for a in menu.actions()]
        if '添加曲线' in names: break
    assert names[names.index('添加曲线')+1:names.index('添加曲线')+3]==['图片样式','复制图片']
    panel=QWidget(); panel.setStyleSheet(CONTROLS); layout=QHBoxLayout(panel)
    for state in (Qt.CheckState.Unchecked,Qt.CheckState.Checked,Qt.CheckState.PartiallyChecked):
        box=QCheckBox(); box.setTristate(True); box.setCheckState(state); layout.addWidget(box)
    panel.show(); app.processEvents(); panel.grab().save(str(out/f'checkbox-states-{suffix}.png'))
    panel.close(); panel.deleteLater(); plot.close(); plot.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
print('Tick page, scientific format, checked menus, caption backgrounds and menu order passed')
