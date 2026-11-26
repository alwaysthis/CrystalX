import json
import logging
import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(filename=ROOT / "logs" / "crystalx.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8")
    try:
        config = json.loads((ROOT / "config/default/app.json").read_text(encoding="utf-8"))
        custom = ROOT / "config/custom/app.json"
        if custom.exists():
            config.update(json.loads(custom.read_text(encoding="utf-8")))
        if sys.platform=='win32':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('CrystalX.Desktop')
        app = QApplication(sys.argv)
        from .runtime import RuntimeDiagnostics
        diagnostics=RuntimeDiagnostics(app,ROOT/'logs')
        from .ui import MainWindow
        window = MainWindow(config)
        window.show()
        logging.info("Application started (PID %s, Python %s)",os.getpid(),sys.version.split()[0])
        try:
            code=app.exec(); logging.info('Application exited normally: %s',code); return code
        finally: diagnostics.close()
    except Exception:
        logging.exception("Application failed")
        raise


if __name__ == "__main__":
    sys.exit(main())
