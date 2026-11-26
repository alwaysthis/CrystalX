"""Capture real current Qt interfaces using only public/synthetic demo data."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtCore import QEvent,QEventLoop,QTimer
from crystalx.ui import MainWindow
from crystalx.session_state import SessionState
from crystalx.xrd_page import XrdPage
from crystalx.curve_data import XYScan
from crystalx.afm_io import read_unit_xy
from crystalx import operations

root=Path(__file__).resolve().parents[1];out=root/'docs/screenshots';out.mkdir(exist_ok=True,parents=True)
app=QApplication([])
for font in ('C:/Windows/Fonts/segoeui.ttf','C:/Windows/Fonts/msyh.ttc'): QFontDatabase.addApplicationFont(font)
app.setFont(QFont('Microsoft YaHei',10))
def settle():
    app.processEvents();loop=QEventLoop();QTimer.singleShot(100,loop.quit);loop.exec();app.processEvents()
def capture(widget,name):
    settle();assert widget.grab().save(str(out/name))
with TemporaryDirectory() as folder:
    window=MainWindow({'window_width':1440,'window_height':960},session_state=SessionState(Path(folder)/'session.json'));window.show();settle()
    window.load_path(root/'examples/Si.vasp');structure=window.current_page()
    structure.run_operation(operations.supercell,[2,2,2],clear_selection=True);structure.reset_view();settle()
    window.messages.setPlainText('演示：examples/Si.vasp · 2 × 2 × 2 硅超胞')
    capture(window,'structure-workspace.png')
    structure.show_coordinates();capture(structure.coordinate_dialog,'structure-editor.png');structure.coordinate_dialog.close()
    rng=np.random.default_rng(17)
    def page(name,scan):
        item=XrdPage(Path(name),[scan]);window.work_tabs.addTab(item,name);window.work_tabs.setCurrentWidget(item);settle()
        window.messages.setPlainText('界面演示：模拟数据，不代表实验测量结果。');return item
    x=np.linspace(20,80,2401)
    y=15+8000*np.exp(-.5*((x-45.2)/.12)**2)+3500*np.exp(-.5*((x-65.8)/.18)**2)
    metadata=dict(MEAS_SCAN_AXIS_X_INTERNAL='TwoThetaOmega',MEAS_SCAN_UNIT_X='deg',MEAS_SCAN_UNIT_Y='counts',MEAS_SCAN_STEP='.025',MEAS_SCAN_SPEED='2',MEAS_SCAN_SPEED_UNIT='deg/min')
    xrd=page('Demo_XRD.ras',XYScan(x.tolist(),rng.poisson(y).astype(float).tolist(),metadata))
    xrd.plot.set_legend_label(0,r'Demo $\mathrm{XRD}$');capture(window,'xrd-workspace.png')
    style=xrd.plot.open_style();style.resize(1000,760);capture(style,'plot-style.png');style.close()
    angles=np.linspace(.3,5,3001);q=4*np.pi*np.sin(np.deg2rad(angles/2))/1.540593
    y=1e6*(.35/(angles+.1))**4*(1+.45*np.cos(250*q))
    metadata=dict(MEAS_SCAN_AXIS_X_INTERNAL='TwoThetaOmega',MEAS_SCAN_UNIT_X='deg',MEAS_SCAN_UNIT_Y='counts',HW_XG_WAVE_LENGTH_ALPHA1='1.540593',HW_XG_WAVE_LENGTH_UNIT='angstrom')
    xrr=page('Demo_XRR.rasx',XYScan(angles.tolist(),y.tolist(),metadata));xrr.plot.set_legend_label(0,'Simulated film')
    capture(window,'xrr-workspace.png')
    peaks=xrr.open_peak_finding(run=True);capture(peaks,'xrr-fringes.png');peaks.close()
    thickness=xrr.open_thickness();thickness.detect();thickness.calculate();capture(thickness,'xrr-thickness.png');thickness.close()
    x=np.linspace(0,5,256);y=250*np.sin(2*np.pi*x/1.7)+rng.normal(0,45,len(x))
    text='X Unit: MicroMeter\nY Unit: PicoMeter\nX Y\n'+'\n'.join(f'{a:.8g} {b:.8g}' for a,b in zip(x,y))
    profile=page('Demo_AFM_Line.txt',read_unit_xy(text));profile.plot.set_legend_label(0,'Height profile');capture(window,'afm-profile.png')
    x=np.linspace(-1.5,1.5,128);y=np.round(3000*np.exp(-.5*((x-.1)/.32)**2))
    text='X Unit: NanoMeter\nY Unit: Pixel\nX Y\n'+'\n'.join(f'{a:.8g} {b:.8g}' for a,b in zip(x,y))
    histogram=page('Demo_AFM_Region.txt',read_unit_xy(text));histogram.plot.set_legend_label(0,'Height distribution');capture(window,'afm-distribution.png')
    # Dispose this demonstration session without prompting about synthetic edits.
    while window.work_tabs.count():
        widget=window.work_tabs.widget(0)
        if hasattr(widget,'close_analysis'):widget.close_analysis();widget.plot.close_editors()
        window.work_tabs.removeTab(0);widget.deleteLater()
    window.close();window.deleteLater();QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
print('Captured 9 current UI screenshots using Si and synthetic datasets:',out)
