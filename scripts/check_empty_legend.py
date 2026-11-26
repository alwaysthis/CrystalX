import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from PyQt6.QtWidgets import QApplication,QLabel
from PyQt6.QtCore import Qt,QPoint,QEvent
from PyQt6.QtTest import QTest
from crystalx.xrd_page import XrdPlot
from crystalx.curve_data import XYScan
app=QApplication([])
plot=XrdPlot(QLabel());plot.resize(1000,650);plot.set_scan(XYScan([1,2,3],[1,3,2]));plot.show();app.processEvents()
dialog=plot.open_legend_entries()
for _,box in dialog.entries: box.setChecked(False)
dialog.apply();app.processEvents()
assert plot.data_axes.get_legend() is not None
position=plot.legend_rect().center();assert plot.legend_at(position)
assert '图例条目' in [a.text() for a in plot.context_menu(position).actions()]
image=plot.export_image()
QTest.mouseMove(plot.canvas,position.toPoint());app.processEvents()
assert plot.legend_hover and plot.canvas.cursor().shape()==Qt.CursorShape.OpenHandCursor
assert plot.export_image()==image
QTest.mousePress(plot.canvas,Qt.MouseButton.LeftButton,pos=position.toPoint())
QTest.mouseMove(plot.canvas,position.toPoint()-QPoint(80,50))
QTest.mouseRelease(plot.canvas,Qt.MouseButton.LeftButton,pos=position.toPoint()-QPoint(80,50));app.processEvents()
assert plot.legend_anchor is not None
dialog.close();dialog=plot.open_legend_entries();dialog.entries[0][1].setChecked(True);dialog.apply();app.processEvents()
assert len(plot.data_axes.get_legend().get_texts())==1
plot.close();plot.deleteLater();QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
print('Empty legend retained, hover, menu, dragging, export isolation and restoration passed')
