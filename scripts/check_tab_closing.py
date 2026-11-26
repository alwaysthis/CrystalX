import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from tempfile import TemporaryDirectory
from pathlib import Path
from PyQt6.QtWidgets import QApplication,QTabBar
from PyQt6.QtGui import QFont,QFontDatabase
from PyQt6.QtCore import Qt,QEvent
from PyQt6.QtTest import QTest
from crystalx.ui import MainWindow
from crystalx.session_state import SessionState
from crystalx.workspace_tabs import TabCloseButton,StructureTabs,WorkspaceTabBar
app=QApplication([]);QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc');app.setFont(QFont('Microsoft YaHei',10))
with TemporaryDirectory() as folder:
    folder=Path(folder);window=MainWindow({'window_width':1300,'window_height':900},session_state=SessionState(folder/'session.json'));window.show();app.processEvents()
    root=Path(__file__).resolve().parents[1]
    curve=folder/'test.xy';curve.write_text('1 3\n2 5\n3 1\n')
    assert window.load_path(root/'examples/Si.vasp');assert window.load_path(curve);assert window.load_path(curve)
    bar=window.work_tabs.tabBar();app.processEvents()
    for selected in range(bar.count()):
        bar.setCurrentIndex(selected);app.processEvents()
        for i in range(bar.count()):
            button=bar.tabButton(i,QTabBar.ButtonPosition.RightSide);assert isinstance(button,TabCloseButton)
            assert button.isVisible() and bar.tabRect(i).contains(button.geometry())
            gap=bar.tabRect(i).right()-button.geometry().right();assert 8<=gap<=11,gap
            image=button.grab().toImage()
            assert sum(image.pixelColor(x,y).alpha()>0 and max(image.pixelColor(x,y).red(),image.pixelColor(x,y).green(),image.pixelColor(x,y).blue())<150 for x in range(image.width()) for y in range(image.height()))>8
    bar.moveTab(2,0);app.processEvents()
    window.grab().save(str(root/'output/tab-close-selected.png'))
    # Close by clicking real buttons, including the last remaining selected tab.
    while bar.count():
        before=bar.count();bar.setCurrentIndex(0);app.processEvents()
        button=bar.tabButton(0,QTabBar.ButtonPosition.RightSide)
        QTest.mouseClick(button,Qt.MouseButton.LeftButton);app.processEvents()
        assert bar.count()==before-1
    assert window.work_tabs.count()==0 and window.current_page() is None and window.welcome_logo.isVisible()
    assert not window.buttons['保存'].isEnabled()
    assert window.load_path(curve);app.processEvents()
    page=window.current_page();info=page.open_file_info();style=page.plot.open_style();app.processEvents()
    QTest.mouseClick(bar.tabButton(0,QTabBar.ButtonPosition.RightSide),Qt.MouseButton.LeftButton);app.processEvents()
    assert not info.isVisible() and not style.isVisible()
    assert bar.count()==0
    window.close();window.deleteLater();QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
from PyQt6.QtWidgets import QWidget
tabs=StructureTabs();tabs.setTabBar(WorkspaceTabBar());tabs.setTabsClosable(True);tabs.resize(460,200)
tabs.tabCloseRequested.connect(tabs.removeTab)
for i in range(7): tabs.addTab(QWidget(),'Long_structure_or_diffraction_filename_'+str(i)+'.rasx')
tabs.show();tabs.setCurrentIndex(6);app.processEvents()
bar=tabs.tabBar();button=bar.tabButton(6,QTabBar.ButtonPosition.RightSide)
assert bar.rect().contains(button.geometry().center())
QTest.mouseClick(button,Qt.MouseButton.LeftButton);app.processEvents();assert tabs.count()==6
tabs.close();tabs.deleteLater();QApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
print('Mixed tabs, selected and unselected close buttons, alignment, reorder, closing last tab and reopen passed')
