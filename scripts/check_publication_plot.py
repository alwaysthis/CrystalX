"""Scientific style dialog, file-location persistence and vector/raster exports."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PyQt6.QtCore import QEvent,Qt,QPointF
from PyQt6.QtGui import QFont,QFontDatabase,QImage
from PyQt6.QtWidgets import QApplication
from crystalx.ui import MainWindow
from crystalx.session_state import SessionState
from crystalx.xrd_page import QFileDialog

app=QApplication([]); QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc'); app.setFont(QFont('Microsoft YaHei',10))
root=Path(__file__).resolve().parents[1]; output=root/'output'; output.mkdir(exist_ok=True)
with TemporaryDirectory() as folder:
    directory=Path(folder); data=directory/'data'; data.mkdir(); source=data/'scan.csv'
    source.write_text('angle,intensity\n'+'\n'.join(f'{10+i} {10+3000/(1+((i-40)/3)**2)}' for i in range(101)))
    state=SessionState(directory/'session.json'); config={'window_width':1450,'window_height':1000}
    window=MainWindow(config,session_state=state); window.show()
    assert window.load_path(root/'examples/Si.vasp')
    assert SessionState(state.path).directory==str((root/'examples').resolve())
    assert window.load_path(source); page=window.current_page(); plot=page.plot; app.processEvents()
    assert SessionState(state.path).directory==str(data.resolve())
    from crystalx.ui import QMessageBox
    with patch.object(QMessageBox,'warning'):
        assert not window.load_path(data/'not-present.ras')
    assert SessionState(state.path).directory==str(data.resolve())
    with patch.object(QFileDialog,'getOpenFileNames',return_value=([],'')) as opener:
        window.open_file(); assert opener.call_args.args[2]==str(data.resolve())
    restored=MainWindow(config,session_state=SessionState(state.path))
    assert restored.session_state.directory==str(data.resolve()); restored.close(); restored.deleteLater()

    dialog=plot.open_style(); app.processEvents()
    assert dialog.navigation.currentRow()==0
    dialog.navigation.setCurrentRow(1); dialog.axis_selector.setCurrentIndex(1)
    assert dialog.pages.currentIndex()==1 and dialog.axis_pages.currentIndex()==1
    dialog.reject(); dialog=plot.open_style('bottom'); app.processEvents()
    assert dialog.navigation.currentRow()==1 and dialog.axis_selector.currentIndex()==1
    def field(*path): return dialog.fields[path][1]
    field('general','size').setValue(13); field('general','width').setValue(1.5)
    field('general','color').set_color('#173ea0'); field('general','box').setChecked(True)
    field('axes','bottom','ticks').setText('[10:20:110]')
    field('axes','bottom','labels').setText("{'A', 20, 'C', 40, 'E', 60}")
    field('axes','left','label').setText(r'$\rm{Intensity}\;\mathscr{I}_{\alpha}+\bf{B}$')
    field('axes','top','visible').setChecked(True); field('axes','top','label').setText(r'$\theta\;(\rm{degree})$')
    field('axes','right','visible').setChecked(True); field('axes','right','scale').setCurrentIndex(2)
    field('axes','right','interval').setValue(1)
    field('axes','right','direction').setCurrentIndex(1)
    field('legend','visible').setChecked(True); field('legend','frame').setChecked(True)
    field('curve','label').setText(r'$\mathscr{I}_{\rm sample}$')
    field('curve','style').setCurrentIndex(4); field('curve','marker').setCurrentIndex(1)
    field('curve','marker_size').setValue(3)
    assert dialog.apply(),dialog.error.text(); app.processEvents()
    assert plot.style['axes']['right']['log'] and plot.data_axes.lines[0].get_color()=='#173ea0'
    assert plot.data_axes.lines[0].get_marker()=='o'
    configuration=directory/'settings.json'; dialog.export_to(configuration); dialog.load_from(configuration)
    assert SessionState(state.path).directory==str(directory.resolve())
    current=deepcopy(plot.style)
    field('axes','bottom','ticks').setText('[1:0:10]')
    assert not dialog.apply(); assert plot.style==current; assert dialog.error.text()
    field('axes','bottom','ticks').setText('[10:20:110]')
    dialog.error.clear(); dialog.navigation.setCurrentRow(1); dialog.grab().save(str(output/'publication-style-dialog.png'))
    dialog.reject()
    before=plot.bounds; plot.move_bounds(.5,.5,.8); zoomed=plot.bounds
    modified=deepcopy(plot.style); modified['general']['background']='#ffdddd'; plot.apply_style(modified)
    assert plot.bounds==zoomed  # Styling does not discard a user's zoom.
    plot.reset(); app.processEvents(); plot.toolbar.reveal()
    page.grab().save(str(output/'publication-plot-screen.png'))
    for suffix in ('.png','.svg','.pdf'):
        destination=output/('publication-plot'+suffix)
        with patch.object(QFileDialog,'getSaveFileName',return_value=(str(destination),suffix)):
            plot.save_image()
        assert destination.exists() and destination.stat().st_size>100
    image=QImage(str(output/'publication-plot.png')); assert image.pixelColor(0,0).alpha()==0
    screen=plot.grab().toImage(); assert screen.pixelColor(2,2).name()=='#ffdddd'
    plot.toolbar.copy_image(); assert app.clipboard().image().pixelColor(0,0).alpha()==0
    legend_frame=plot.data_axes.get_legend().get_frame(); original_face=legend_frame.get_facecolor()
    with plot.export_context(): assert legend_frame.get_facecolor()[3]==0
    assert legend_frame.get_facecolor()==original_face
    opaque=deepcopy(plot.style); opaque['general']['transparent']=False; plot.apply_style(opaque)
    assert plot.export_image(scale=1).pixelColor(0,0).alpha()==255
    assert plot.axis_at(QPointF(plot.area().left()-15,plot.area().center().y()))=='left'
    assert plot.axis_at(plot.area().center()) is None
    window.close(); window.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
print('Publication style, persistence and export checks passed')
