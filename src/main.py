import logging.config
from fastapi.responses import RedirectResponse
from database.models import Ticket, Status
from database import Database
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging
from sys import stdout
from lifespan import lifespan
import asana
import config_manager
import json
from core.receiver import receive_form
from sqlalchemy import select
import asyncio
from web import web_router
from starlette.status import HTTP_303_SEE_OTHER
from starlette.middleware.sessions import SessionMiddleware
import os
from log_config import logging_config

logging.config.dictConfig(logging_config)


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware,
                   secret_key="ZEfTgTOUTou8cpIlORwmU0fjiEc5j9LlP6Af6j3l4yA")
app.include_router(web_router)
app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.get("/")
def index():
    if not asana.initialized:
        return RedirectResponse("/settings", status_code=HTTP_303_SEE_OTHER)

    return RedirectResponse("/reports/all-managers", status_code=HTTP_303_SEE_OTHER)


@app.get("/status")
def status():
    return {"Im, ok"}


@app.get("/receive/{text}")
async def receive_yandex_form(text: str):
    data = json.loads(text)
    await receive_form(data)
    return {'Ok'}


@app.get("/receive-test/{text}")
async def receive_test(text: str):
    data = json.loads(text)
    logging.info(f"Получено в тестовый эндпоинт: {data}")
    return {'Ok'}
