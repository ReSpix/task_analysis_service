import logging
import sys

LOG_LEVEL = logging.INFO  # или DEBUG / WARNING / ERROR

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,  # важно: чтобы uvicorn не отключался
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "stderr": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",  # <<< ключ: stderr
            "formatter": "default",
        },
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["stderr"],
    },
    "loggers": {
        "uvicorn": {
            "level": LOG_LEVEL,
            "handlers": ["stderr"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": LOG_LEVEL,
            "handlers": ["stderr"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": LOG_LEVEL,
            "handlers": ["stderr"],
            "propagate": False,
        },
        # Можно добавить свой логгер по имени
        "myapp": {
            "level": LOG_LEVEL,
            "handlers": ["stderr"],
            "propagate": False,
        },
    },
}
