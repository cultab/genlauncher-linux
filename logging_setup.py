from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from platformdirs import user_log_dir


def setup_logging() -> str:
    log_dir = user_log_dir("genlauncher", ensure_exists=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"genlauncher_{timestamp}.log")

    handler = RotatingFileHandler(
        log_path,
        maxBytes=1_048_576,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(logging.WARNING)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
    ))

    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    root.addHandler(handler)

    def excepthook(exc_type, exc_value, exc_traceback):
        logging.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = excepthook

    return log_path
