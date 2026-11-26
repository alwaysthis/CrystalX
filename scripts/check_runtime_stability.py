"""Qt callback diagnostics, delayed painting and dialog/tab lifecycle stress."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys,logging,faulthandler
from pathlib import Path
from tempfile import TemporaryDirectory
from PyQt6.QtCore import QTimer,QEvent,QEventLoop,Qt,QPointF,QObject
from PyQt6.QtGui import QContextMenuEvent
from PyQt6.QtWidgets import QApplication
from crystalx.runtime import RuntimeDiagnostics
from crystalx.ui import MainWindow
from crystalx.session_state import SessionState
from crystalx.xrd_page import XrdPage
from crystalx.xrd_io import XrdScan

app=QApplication([])
with TemporaryDirectory() as directory:
    folder=Path(directory); log=folder/'crystalx.log'; handler=logging.FileHandler(log,encoding='utf-8'); logging.getLogger().addHandler(handler); logging.getLogger().setLevel(logging.INFO)
    diagnostics=RuntimeDiagnostics(app,folder)
    window=MainWindow({'window_width':1400,'window_height':950},session_state=SessionState(folder/'session.json')); window.show(); app.processEvents()
    # A genuine Qt callback exception must be logged and reported without abort.
    def failed_callback(): raise ValueError('intentional callback verification')
    QTimer.singleShot(0,failed_callback); app.processEvents(); app.processEvents()
    assert diagnostics.notice is not None and 'intentional callback verification' in log.read_text(encoding='utf-8')
    diagnostics.notice.accept(); app.processEvents(); assert diagnostics.notice is None
    handler.flush(); boundary=log.stat().st_size
    for cycle in range(3):
        page=XrdPage(Path('XRR.ras'),[XrdScan([.5,.6,.7,.8,.9,1,1.1,1.2,1.3],[1,4,1,3,1,2,1,2,1],{'MEAS_SCAN_AXIS_X_INTERNAL':'TwoThetaOmega'})])
        window.work_tabs.addTab(page,'XRR'); window.work_tabs.setCurrentWidget(page); app.processEvents()
        dialog=page.open_thickness(); app.processEvents()
        for _ in range(3): dialog.add_row()
        dialog.consecutive.setChecked(False); dialog.consecutive.setChecked(True)
        dialog.table.selectRow(1); dialog.delete_rows(); dialog.load_rows([.6,.8,1.0]); assert dialog.calculate()
        dialog.show_marks.setChecked(True); assert len(page.plot.curves[0].thickness_marks)==3
        editor=page.plot.edit_legend_label(0); editor.input.setText(r'As-grown $I_1$'); editor.accept(); app.processEvents()
        editor=page.plot.edit_axis_label('bottom'); editor.input.setText(r'$2\theta$ (°)'); editor.accept(); app.processEvents()
        event=QContextMenuEvent(QContextMenuEvent.Reason.Mouse,window.rect().center())
        # Application filters also receive QWindow/QObject events, not just widgets.
        assert diagnostics.eventFilter(window.windowHandle(),event) is False
        assert diagnostics.eventFilter(QObject(),event) is False
        area=page.plot.area(); position=QPointF(area.center().x(),area.top()+area.height()*.2)
        menus=[]
        def close_popup():
            popup=QApplication.activePopupWidget()
            if popup is not None: menus.append([action.text() for action in popup.actions()]); popup.close()
        QTimer.singleShot(50,close_popup)
        context=QContextMenuEvent(QContextMenuEvent.Reason.Mouse,position.toPoint(),page.plot.canvas.mapToGlobal(position.toPoint()))
        QApplication.sendEvent(page.plot.canvas,context)
        assert menus and menus[0][0]=='重置视图' and diagnostics.notice is None
        window.outer.setSizes([1,900]); app.processEvents(); window.outer.setSizes([800,150]); app.processEvents()
        window.maximize_terminal(); app.processEvents(); window.maximize_terminal(); app.processEvents()
        page.open_file_info(); page.open_background_settings(); app.processEvents()
        page.selector.currentIndexChanged.emit(0); app.processEvents()
        page.open_thickness(); app.processEvents()
        window.close_tab(window.work_tabs.indexOf(page)); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        delay=QEventLoop(); QTimer.singleShot(80,delay.quit); delay.exec()
    handler.flush(); later=log.read_text(encoding='utf-8')[boundary:]
    assert 'Unhandled UI exception' not in later,later
    faulthandler.dump_traceback(file=diagnostics.fault_file); diagnostics.fault_file.flush()
    assert 'check_runtime_stability.py' in (folder/'crash.log').read_text(encoding='utf-8')
    window.close(); window.deleteLater(); QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete); app.processEvents()
    diagnostics.close(); logging.getLogger().removeHandler(handler); handler.close()
print('Qt error reporting, native trace output, tiny layout, dialogs and tab deletion passed')
