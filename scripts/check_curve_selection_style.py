"""Selected curve edits must remain visible and match their legend handles."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,traceback
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import numpy as np
from matplotlib.colors import to_hex
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtWidgets import QApplication,QLabel
from PyQt6.QtCore import Qt,QPointF
from PyQt6.QtTest import QTest
from crystalx.xrd_page import XrdPlot
from crystalx.xrd_io import XrdScan
from crystalx.plot_presets import PlotDefaults

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
errors=[]
def report(kind,value,tb): errors.append(value); traceback.print_exception(kind,value,tb)
sys.excepthook=report
with TemporaryDirectory() as directory:
    plot=XrdPlot(QLabel(),PlotDefaults(Path(directory)/'plot.json')); plot.resize(1000,650)
    x=np.linspace(0,10,301).tolist()
    plot.set_scan(XrdScan(x,[7+.2*np.sin(v) for v in x])); plot.show(); app.processEvents()
    style=deepcopy(plot.style); style['curve'].update(color='#d62728',width=1.25); plot.apply_style(style)
    plot.add_scan(XrdScan(x,[3+np.sin(v) for v in x])); plot.reset(); app.processEvents()
    assert plot.selected_curve==1
    assert plot.data_axes.curve_artists[1].get_color()=='#d62728'
    assert to_hex(plot.data_axes.get_legend().legend_handles[1].get_color())=='#d62728'
    dialog=plot.open_style(section='curve'); app.processEvents()
    color=dialog.fields[('curve','color')][1]
    color.set_color('#332288')
    assert dialog.apply(),dialog.error.text()
    assert plot.selected_curve==1 and plot.curves[0].style['color']=='#d62728'
    line=plot.data_axes.curve_artists[1]; legend=plot.data_axes.get_legend()
    assert line.get_color()=='#332288' and to_hex(legend.legend_handles[1].get_color())=='#332288'
    # Legend text intentionally has an independent (black) text-color setting.
    assert to_hex(legend.get_texts()[1].get_color())=='#000000'
    dialog.hide(); app.processEvents()
    selected=plot.grab().toImage(); ratio=selected.devicePixelRatio()
    hits=0
    for i in range(10,290):
        point=plot.point(x[i],plot.curves[1].y[i]); px,py=round(point.x()*ratio),round(point.y()*ratio)
        near=[]
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                pixel=selected.pixelColor(px+dx,py+dy)
                near.append(max(abs(a-b) for a,b in zip((pixel.red(),pixel.green(),pixel.blue()),(51,34,136))))
        hits+=min(near)<65
    plot.grab().save(str(Path(__file__).resolve().parents[1]/'output/selected-curve-style.png'))
    assert hits/280>.9,(hits,280)
    exported=plot.export_image(scale=1); plot.select_curve(None); app.processEvents()
    assert plot.export_image(scale=1)==exported
    plot.select_curve(1); app.processEvents()
    plot.grab().save(str(Path(__file__).resolve().parents[1]/'output/selected-curve-style.png'))
    dialog.show(); color.set_color('#117733'); dialog.fields[('curve','width')][1].setValue(2)
    assert dialog.apply(),dialog.error.text()
    assert plot.data_axes.curve_artists[1].get_color()=='#117733'
    assert plot.data_axes.curve_artists[1].get_linewidth()==2
    assert to_hex(plot.data_axes.get_legend().legend_handles[1].get_color())=='#117733'
    dialog.hide(); app.processEvents(); bounds=plot.bounds
    area=plot.area(); blank=QPointF(area.center().x(),area.top()+area.height()*.4)
    QTest.mouseClick(plot.canvas,Qt.MouseButton.LeftButton,pos=blank.toPoint())
    assert plot.selected_curve is None and plot.bounds==bounds
    plot.select_curve(1); plot.canvas.setFocus(); QTest.keyClick(plot.canvas,Qt.Key.Key_Escape)
    assert plot.selected_curve is None and plot.bounds==bounds
    assert plot.curves[1].style['color']=='#117733'
    plot.set_series_visible(1,False); app.processEvents(); plot.set_series_visible(1,True)
    dialog.close(); plot.close(); plot.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
assert not errors,errors
print('Selected curve screen color, repeated style edits, legend handles and transparent export passed')
