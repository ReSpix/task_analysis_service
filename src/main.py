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

logging.basicConfig(level=logging.INFO, stream=stdout,
                    format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(lifespan=lifespan)
app.include_router(web_router)
app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.get("/status")
def status():
    return {"Im, ok"}


@app.get("/receive/{text}")
async def asana_events(text: str):
    data = json.loads(text)
    await receive_form(data)
    return {'Ok'}
