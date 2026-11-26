"""Mixed formula popup selection stays legible; inherited swatches are symmetric."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from tempfile import TemporaryDirectory
import sys,traceback
from PyQt6.QtCore import Qt,QEvent
from PyQt6.QtGui import QFont,QFontDatabase,QColor
from PyQt6.QtWidgets import QApplication,QWidget,QHBoxLayout
from crystalx.xrd_page import XrdPlot
from crystalx.xrd_io import XrdScan
from crystalx.plot_presets import PlotDefaults
from crystalx.math_ui import MathLabel
from crystalx.plot_color import PlotColorButton

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
errors=[]
def report(kind,value,tb): errors.append(value); traceback.print_exception(kind,value,tb)
sys.excepthook=report
out=Path(__file__).resolve().parents[1]/'output'; ratio=app.primaryScreen().devicePixelRatio(); suffix=f'{ratio:g}'
with TemporaryDirectory() as folder:
    plot=XrdPlot(MathLabel(),PlotDefaults(Path(folder)/'plot.json')); plot.resize(950,650)
    plot.set_scan(XrdScan([1,2,3],[2,5,2])); plot.add_scan(XrdScan([1,2,3],[1,3,1])); plot.show()
    plot.curves[0].label='As-grown'; plot.curves[1].label=r'$O_2$ annealed at $800^{\circ}\mathrm{C}$ for 30min'; plot.rebuild()
    dialog=plot.open_style(section='curve'); dialog.show(); app.processEvents()
    combo=dialog.curve_selector; combo.showPopup(); view=combo.view(); view.setCurrentIndex(combo.model().index(1,0)); app.processEvents()
    image=view.grab().toImage(); dpr=image.devicePixelRatio(); row=view.visualRect(combo.model().index(1,0))
    dark=green=0
    for y in range(round((row.top()+3)*dpr),round((row.bottom()-2)*dpr)):
        for x in range(round((row.left()+5)*dpr),round((row.right()-5)*dpr)):
            pixel=image.pixelColor(x,y)
            dark+=max(pixel.red(),pixel.green(),pixel.blue())<130
            green+=max(abs(a-b) for a,b in zip((pixel.red(),pixel.green(),pixel.blue()),(220,231,223)))<3
    assert dark>50 and green>100,(dark,green)
    view.window().grab().save(str(out/f'formula-popup-{suffix}.png')); combo.hidePopup()
    assert combo.currentText().startswith('2 · $O_2$')
    panel=QWidget(); panel.setStyleSheet('QWidget {background:white;}'); layout=QHBoxLayout(panel)
    buttons=[]
    for value in ('','auto','none','#332288'):
        button=PlotColorButton(marker=True); button.set_color(value); layout.addWidget(button); buttons.append(button)
    panel.show(); app.processEvents(); panel.grab().save(str(out/f'color-swatches-{suffix}.png'))
    # Mirror symmetry catches the broken one-sided dash distribution in the report.
    image=buttons[0].grab().toImage(); w,h=image.width(),image.height(); differences=[]
    for y in range(h):
        for x in range(w):
            left=image.pixelColor(x,y); right=image.pixelColor(w-1-x,y)
            differences.append(max(abs(a-b) for a,b in zip((left.red(),left.green(),left.blue()),(right.red(),right.green(),right.blue()))))
    assert sum(differences)/len(differences)<8
    buttons[0].set_color('#228822'); assert buttons[0].value=='#228822'; buttons[0].set_color(''); assert buttons[0].value==''
    combo.setCurrentIndex(0); assert dialog.curve_index==0
    panel.close(); panel.deleteLater(); dialog.close(); plot.close(); plot.deleteLater()
    QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
assert not errors,errors
print('Formula popup contrast, native text selection and symmetric color swatches passed at',ratio)
