import logging
import json
from logging import Logger
from pathlib import Path
import sys


class JSONFormatter(logging.Formatter):
    """Форматтер для структурного (JSON) логирования с указанием файла и строки."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "filename": record.filename,
            "pathname": record.pathname,
            "funcName": record.funcName,
            "line": record.lineno,
        }
        if record.args:
            log_entry["args"] = [str(a) for a in record.args]
        return json.dumps(log_entry, ensure_ascii=False, default=str)


def setup_logger() -> Logger:
    log_dir = Path("logger")
    log_file = log_dir / "app.json"
    log_dir.mkdir(parents=True, exist_ok=True)

    my_logger = logging.getLogger("my_logger")
    my_logger.setLevel(logging.DEBUG)

    json_fmt = JSONFormatter()
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(json_fmt)
    my_logger.addHandler(file_handler)

    console_fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)-5s [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(console_fmt)
    my_logger.addHandler(console_handler)

    return my_logger


logger = setup_logger()
