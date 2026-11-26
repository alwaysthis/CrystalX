"""Local crash diagnostics and reporting of uncaught Qt callback exceptions."""
import faulthandler
import logging
import os
import sys
import threading
from datetime import datetime
from PyQt6.QtCore import QObject,QEvent,QTimer,Qt,qInstallMessageHandler,QtMsgType
from PyQt6.QtWidgets import QApplication,QAbstractButton,QDialog,QMessageBox,QWidget

class RuntimeDiagnostics(QObject):
    def __init__(self,app,logs,notify=True):
        super().__init__(app); self.app=app; self.notify=notify; self.notice=None; self.pending=False
        self.logger=logging.getLogger('crystalx.runtime'); self.previous_hook=sys.excepthook
        self.previous_thread_hook=threading.excepthook
        self.fault_file=open(logs/'crash.log','a',encoding='utf-8')
        self.fault_file.write(f'\n{datetime.now().astimezone().isoformat()} Process {os.getpid()} started\n'); self.fault_file.flush()
        faulthandler.enable(file=self.fault_file,all_threads=True)
        sys.excepthook=self.exception; threading.excepthook=self.thread_exception
        self.previous_qt=qInstallMessageHandler(self.qt_message); app.installEventFilter(self)

    def exception(self,kind,value,tb):
        if issubclass(kind,(KeyboardInterrupt,SystemExit)): return self.previous_hook(kind,value,tb)
        self.logger.error('Unhandled UI exception',exc_info=(kind,value,tb))
        self.flush()
        if self.notify and threading.current_thread() is threading.main_thread() and not self.pending and self.notice is None:
            self.pending=True; QTimer.singleShot(0,self.show_notice)

    def thread_exception(self,args):
        self.logger.error('Unhandled worker exception in %s',args.thread.name,exc_info=(args.exc_type,args.exc_value,args.exc_traceback)); self.flush()

    def qt_message(self,kind,context,message):
        level=logging.CRITICAL if kind==QtMsgType.QtFatalMsg else logging.WARNING if kind in (QtMsgType.QtWarningMsg,QtMsgType.QtCriticalMsg) else logging.DEBUG
        self.logger.log(level,'Qt: %s',message)
        if kind==QtMsgType.QtFatalMsg: self.flush()

    def flush(self):
        for handler in logging.getLogger().handlers: handler.flush()

    def show_notice(self):
        self.pending=False
        if self.app.closingDown(): return
        from .dialogs import prepare
        dialog=QMessageBox(QMessageBox.Icon.Warning,'操作未完成','本次操作发生错误，详情已记录到 logs/crystalx.log。',QMessageBox.StandardButton.Ok,QApplication.activeWindow())
        self.notice=dialog
        dialog.setTextFormat(Qt.TextFormat.PlainText); prepare(dialog); dialog.button(QMessageBox.StandardButton.Ok).setText('确定')
        dialog.finished.connect(self.clear_notice); dialog.show()

    def clear_notice(self,*args):
        notice=self.notice; self.notice=None
        if notice is not None: notice.deleteLater()

    def eventFilter(self,obj,event):
        kind=event.type()
        if kind==QEvent.Type.MouseButtonRelease and isinstance(obj,QAbstractButton):
            self.logger.info('Action: %s / %s',obj.window().windowTitle(),QAbstractButton.text(obj) or obj.toolTip())
        elif kind in (QEvent.Type.Show,QEvent.Type.Close) and isinstance(obj,QDialog):
            self.logger.info('Dialog %s: %s','opened' if kind==QEvent.Type.Show else 'closed',obj.windowTitle())
        elif kind==QEvent.Type.ContextMenu and isinstance(obj,QWidget):
            self.logger.info('Context menu: %s / %s',obj.window().windowTitle(),type(obj).__name__)
        return False

    def close(self):
        self.app.removeEventFilter(self); sys.excepthook=self.previous_hook; threading.excepthook=self.previous_thread_hook
        qInstallMessageHandler(self.previous_qt); faulthandler.disable(); self.fault_file.close()
