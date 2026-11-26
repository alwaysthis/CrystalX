"""Compact light controls inspired by x_rheed studio theme/constants.py."""
from PyQt6.QtCore import QObject,QEvent
from PyQt6.QtWidgets import QAbstractSpinBox,QComboBox

class WheelGuard(QObject):
    def eventFilter(self,obj,event):
        if event.type()==QEvent.Type.Wheel and isinstance(obj,(QAbstractSpinBox,QComboBox)):
            event.ignore(); return True
        return False

CONTROLS = """
QPushButton,QToolButton {background:#fff;color:#252525;border:1px solid #e0e0e0;border-radius:4px;padding:4px 8px;}
QToolButton {padding:2px;}
QPushButton:hover,QToolButton:hover {background:#f3f3f3;border-color:#b8b8b8;}
QPushButton:pressed,QToolButton:pressed,QToolButton:checked {background:#e3e8e6;border-color:#8fa69b;}
QPushButton:disabled,QToolButton:disabled {color:#aaa;border-color:#eee;}
QAbstractSpinBox,QComboBox {background:#fff;color:#252525;border:1px solid #ddd;border-radius:4px;padding:3px 8px;min-height:22px;}
QAbstractSpinBox:hover,QComboBox:hover,QAbstractSpinBox:focus,QComboBox:focus {border-color:#91aa9c;background:#fcfcfc;}
QComboBox::drop-down {border:0;width:22px;}
QMenu {background:white;border:1px solid #ddd;padding:4px;}
QMenu::item {padding:3px 16px 3px 8px;min-width:90px;}
QMenu::item:selected {background:#ecefed;border-radius:3px;}
QMenuBar {border:0;background:transparent;}
QMenuBar::item {padding:6px 14px;background:transparent;}
QMenuBar::item:selected {background:#ecefed;}
QScrollBar:vertical {background:transparent;width:10px;margin:0;}
QScrollBar::handle:vertical {background:#cbd0cd;min-height:28px;border-radius:4px;margin:1px;}
QScrollBar::handle:vertical:hover {background:#aab5af;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical {background:transparent;}
QScrollArea {border:0;}
"""

# Shared window, workspace-tab and spin-stepper style library.
TITLE_BAR_HEIGHT=32
PANEL_RADIUS=9
DIALOG_BG='#f1f3f2'
PAGE_BG='#ffffff'
AXIS_COLORS = ['#b51d24','#087d32','#163fb4']
WORKSPACE_TABS = """
QWidget#workspaceTabs {background:transparent;border:0;}
QWidget#workspacePage {background:transparent;border:0;}
QWidget#workspacePage QLabel,QWidget#workspacePage QCheckBox {background:transparent;}
QTabBar {background:transparent;border:0;}
QTabBar::tab {border:0;padding:0;margin:0;}
"""


def stepper_css():
    from pathlib import Path
    assets=Path(__file__).resolve().parents[2]/'assets'
    css=''
    for direction,position in [('up','top right'),('down','bottom right')]:
        names=','.join(f'{kind}::{direction}-button' for kind in ['QSpinBox','QDoubleSpinBox'])
        css+=names+'{subcontrol-origin:border;subcontrol-position:'+position+';width:20px;border:0;border-left:1px solid #ddd;background:transparent;margin:1px;}'
        css+=','.join(f'{kind}::{direction}-button:hover' for kind in ['QSpinBox','QDoubleSpinBox'])+'{background:#ececec;}'
        css+=','.join(f'{kind}::{direction}-button:pressed' for kind in ['QSpinBox','QDoubleSpinBox'])+'{background:#ddd;}'
        css+=','.join(f'{kind}::{direction}-arrow' for kind in ['QSpinBox','QDoubleSpinBox'])+'{image:url("'+(assets/f'spin-{direction}.svg').as_posix()+'");width:8px;height:5px;}'
    css+='QSpinBox::up-button,QDoubleSpinBox::up-button {border-bottom:1px solid #ddd;margin-top:1px;margin-bottom:0;}'
    return css

ICON_BUTTONS = """
QToolButton {background:transparent;border:1px solid #d7ddd9;border-radius:4px;padding:2px;}
QToolButton:hover {background:rgba(100,130,115,25);}
QToolButton:pressed,QToolButton:checked {background:rgba(100,130,115,45);}
QToolButton::menu-indicator {image:none;width:0;height:0;}
"""

BASE_STYLE = """
QWidget { background:#fdfefd; color:#29352f; font-family:'Segoe UI','Microsoft YaHei'; font-size:13px; }
QMainWindow,QMenuBar,QToolBar { background:#fafcfb; }
QToolBar { border-bottom:1px solid #dce3dd; spacing:12px; padding:12px; }
QPushButton { border:1px solid #dce3dd; border-radius:5px; padding:9px 14px; background:#fff; }
QPushButton:disabled { color:#a4ada7; background:#f1f4f0; }
QPushButton:hover { background:#e3eee7; border-color:#94b49f; }
QPushButton:checked { background:#dbece1; color:#286345; }
QTreeWidget,QTableWidget { border:0; background:transparent; alternate-background-color:#f7faf8; }
QTreeWidget::item { padding:9px; }
QTreeWidget::item:selected { background:#deece2; color:#286345; }
QGroupBox { border:0; margin-top:18px; padding-top:22px; font-weight:600; }
QGroupBox::title { subcontrol-origin:margin; top:4px; font-weight:bold; }
QDoubleSpinBox,QComboBox { background:white; border:1px solid #dce3dd; border-radius:4px; padding:6px; }
QHeaderView::section { background:transparent; padding:6px; border:0; }
QStatusBar { border:0; color:#4f6258; background:#e0e6e2; }
QStatusBar QWidget {background:#e0e6e2;}
QSplitter::handle { background:#e0e6e0; width:1px; height:1px; }
"""

SLIDERS = """
QSlider::groove:horizontal {height:5px;background:#c6cfca;border-radius:2px;}
QSlider::sub-page:horizontal {background:#5c8c79;border-radius:2px;}
QSlider::handle:horizontal {background:#fff;border:1px solid #719482;width:12px;margin:-4px 0;border-radius:6px;}
QWidget#titleChrome {border:0;}
QWidget#viewportHost,QWidget#viewportTools {background:#fff;}
"""


def window_control_css(close=False):
    """Window controls always use square hit/hover/pressed surfaces."""
    hover='#e95c58' if close else '#e8eeeb'
    pressed='#cc4541' if close else '#d3ddd7'
    return (
        'QToolButton {background:transparent;border:0;border-radius:0px;padding:0;margin:0;}'
        f'QToolButton:hover {{background:{hover};border:0;border-radius:0px;}}'
        f'QToolButton:pressed {{background:{pressed};border:0;border-radius:0px;}}'
    )

PANELS = """
QTreeWidget,QTableWidget,QListWidget {background:transparent;}
QTreeWidget::item:selected {background:#dfe9e4;}
QToolButton[moreButton="true"] {border:0;background:transparent;}
QMenuBar::item {padding:10px 14px;border-radius:0;background:transparent;}
QMenuBar::item:selected,QMenuBar::item:pressed {background:#e0e8e3;}
QTabWidget#structureTabs {background:transparent;border:0;}
QTabWidget#structureTabs::pane {border:0;background:#fff;}
QTabWidget#terminalTabs::pane {border:0;background:transparent;}
QTabWidget#terminalTabs QTabBar::tab {border:0;border-radius:5px;padding:4px 12px;margin:4px;background:transparent;}
QTabWidget#terminalTabs QTabBar::tab:selected {background:#dfe7e2;}
QTabWidget#terminalTabs QTabBar::tab:hover {background:#e8eeeb;}
"""

PANE_FRAMES = """
QFrame#workPanel,QFrame#terminalPanel {border:0;background:transparent;}
QSplitter#workspaceSplit {background:#f1f3f2;}
QSplitter#workspaceSplit::handle {background:#f1f3f2;}
QToolButton[paneControl="true"] {border:0;background:transparent;border-radius:0;padding:3px;}
QToolButton[paneControl="true"]:hover {background:#e3ebe6;}
QToolButton[paneControl="true"]:pressed {background:#cfded4;}
"""


MENU_STYLE = """
QMenu {background-color:#ffffff;color:#29352f;border:1px solid #d5ddd8;padding:4px;}
QMenu::item {background:transparent;color:#29352f;padding:3px 16px 3px 8px;min-width:90px;}
QMenu::item:selected {background:#e8eeeb;color:#29352f;border-radius:3px;}
QMenu::item:disabled {color:#9aa39e;}
QMenu::separator {height:1px;background:#dfe5e1;margin:4px 6px;}
"""

def apply_menu_theme(menu):
    """Keep popup surfaces opaque even beneath transparent title/tool containers."""
    from PyQt6.QtGui import QColor,QPalette
    menu.setStyleSheet(MENU_STYLE)
    palette=menu.palette()
    for role,color in [(QPalette.ColorRole.Window,'#ffffff'),(QPalette.ColorRole.Base,'#ffffff'),(QPalette.ColorRole.WindowText,'#29352f'),(QPalette.ColorRole.Text,'#29352f')]:
        palette.setColor(role,QColor(color))
    menu.setPalette(palette)
    for action in menu.actions():
        if action.menu(): apply_menu_theme(action.menu())
    return menu


from pathlib import Path as _Path
_assets=(_Path(__file__).resolve().parents[2]/'assets').as_posix()
CHECKBOX_SIZE=16
CHECKBOX_STYLE = """
QCheckBox::indicator,QAbstractItemView::indicator,QMenu::indicator {width:16px;height:16px;border:1px solid #344f3f;border-radius:3px;background:#fff;image:none;}
QCheckBox::indicator:hover,QAbstractItemView::indicator:hover {border-color:#173d28;background:#edf3ef;}
QCheckBox::indicator:checked,QAbstractItemView::indicator:checked,QMenu::indicator:checked {image:url("""+_assets+"""/check.svg);background:#e0ebe4;}
QCheckBox::indicator:indeterminate,QAbstractItemView::indicator:indeterminate,QMenu::indicator:indeterminate {image:url("""+_assets+"""/partial.svg);background:#fff;}
QCheckBox::indicator:disabled,QAbstractItemView::indicator:disabled,QMenu::indicator:disabled {border-color:#9ba99f;background:#f0f3f1;}
"""
CONTROLS += CHECKBOX_STYLE
MENU_STYLE += CHECKBOX_STYLE
CONTROLS += """
QAbstractSpinBox[pendingEdit="true"],QAbstractSpinBox[pendingEdit="true"]:focus {background:#fde5e5;}
"""

CONTROLS += """
QAbstractSpinBox:disabled,QComboBox:disabled {background:#f0f3f1;color:#9ba69f;border-color:#dfe5e1;}
QCheckBox:disabled {color:#9ba69f;}
"""

CONTROLS += 'QComboBox {padding-right:25px;} QComboBox::drop-down {subcontrol-origin:border;subcontrol-position:top right;width:23px;border:0;background:transparent;} QComboBox::down-arrow {image:url("'+_assets+'/combo-arrow.svg");width:12px;height:8px;}'
