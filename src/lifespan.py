from contextlib import asynccontextmanager
from functools import wraps
from typing import Callable
from fastapi import FastAPI
import logging
from database import Database


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup()
    yield
    await shutdown()


def status_message(text: str):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logging.info("Начато: %s", text)
            await func(*args, **kwargs)
            logging.info("Завершено: %s", text)
        return wrapper
    return decorator


@status_message("Инициализация")
async def startup():
    await Database.create_all()


@status_message("выключение")
async def shutdown():
    pass
