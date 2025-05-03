from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging
from sys import stdout
from lifespan import lifespan
import asana
import config_manager

logging.basicConfig(level=logging.INFO, stream=stdout,
                    format="%(asctime)s [%(levelname)s] %(message)s")

asana_client = asana.AsanaClient(config_manager.TOKEN, config_manager.MAIN_PROJECT_GID)
app = FastAPI(lifespan=lifespan)
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/status")
def status():
    return {"Im, ok"}


@app.get("/asana-status")
async def asana_status():
    return await asana_client.workspaces()