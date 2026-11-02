import json
import logging
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
        app = QApplication(sys.argv)
        from .ui import MainWindow
        window = MainWindow(config)
        window.show()
        logging.info("Application started")
        return app.exec()
    except Exception:
        logging.exception("Application failed")
        raise


if __name__ == "__main__":
    sys.exit(main())
