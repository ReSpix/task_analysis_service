import logging
from logging.handlers import RotatingFileHandler
import sys
import os

LOG_LEVEL = logging.INFO  # или DEBUG / WARNING / ERROR
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5  # Хранить 5 архивных файлов

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RELATIVE_FILE_PATH = os.path.join(BASE_DIR, '..', 'data', 'main.log')
ABSOLUTE_FILE_PATH = os.path.abspath(RELATIVE_FILE_PATH)

os.makedirs(os.path.dirname(ABSOLUTE_FILE_PATH), exist_ok=True)

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "rotating_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": RELATIVE_FILE_PATH,
            "maxBytes": MAX_LOG_SIZE,
            "backupCount": BACKUP_COUNT,
            "encoding": "utf-8",
            "formatter": "default",
        },
        # Если хочешь сохранить вывод в консоль:
        "stderr": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "formatter": "default",
        },
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["rotating_file", "stderr"],
    },
    "loggers": {
        "uvicorn": {
            "level": LOG_LEVEL,
            "handlers": ["rotating_file"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": LOG_LEVEL,
            "handlers": ["rotating_file"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": LOG_LEVEL,
            "handlers": ["rotating_file"],
            "propagate": False,
        },
        "myapp": {
            "level": LOG_LEVEL,
            "handlers": ["rotating_file"],
            "propagate": False,
        },
    },
}
