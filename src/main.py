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
from core.events_handler import handle_events
import asyncio

logging.basicConfig(level=logging.INFO, stream=stdout,
                    format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(lifespan=lifespan)
asana_client = asana.AsanaClient(
    config_manager.TOKEN, config_manager.MAIN_PROJECT_GID)
events_api = asana.EventsApi(asana_client)
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/status")
def status():
    return {"Im, ok"}


@app.get("/receive/{text}")
async def asana_events(text: str):
    data = json.loads(text)
    await receive_form(data)
    return {'Ok'}


@app.get("/tickets")
async def tickets():
    async with Database.make_session() as session:
        query = select(Ticket)

        result = await session.execute(query)
        tickets = result.scalars().all()

        return tickets
    

@app.get("/statuses")
async def statuses():
    async with Database.make_session() as session:
        query = select(Status)

        result = await session.execute(query)
        tickets = result.scalars().all()

        return tickets


@app.get("/events")
async def events():
    events = await events_api.get_events()
    asyncio.create_task(handle_events(events))
    return events