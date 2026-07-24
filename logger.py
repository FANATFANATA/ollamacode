import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

_LOG_DIR = Path.home() / ".ollamacode" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "ollamacode.log"

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def configure_logging(level=logging.INFO, enable_file=True, enable_console=False):
    global _configured
    if _configured:
        return
    root = logging.getLogger("ollamacode")
    root.setLevel(level)
    root.propagate = False
    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)
    if enable_file:
        try:
            file_handler = RotatingFileHandler(
                _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except Exception:
            pass
    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    if not _configured:
        configure_logging()
    return logging.getLogger(f"ollamacode.{name}")
