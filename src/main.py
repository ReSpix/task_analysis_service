from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging
from sys import stdout
from lifespan import lifespan
import asana
import config_manager
import json
from core.receiver import receive_form

logging.basicConfig(level=logging.INFO, stream=stdout,
                    format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(lifespan=lifespan)
asana_client = asana.AsanaClient(config_manager.TOKEN, config_manager.MAIN_PROJECT_GID)
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


from database import Database
from database.models import Ticket
@app.get("/tickets")
async def tickets():
    async with Database.make_session() as session:
        from sqlalchemy import select

        result = await session.execute(select(Ticket))
        tickets = result.scalars().all()
    
    return tickets