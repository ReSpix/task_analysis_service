from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging
from sys import stdout
from lifespan import lifespan

logging.basicConfig(level=logging.INFO, stream=stdout,
                    format="%(asctime)s [%(levelname)s] %(message)s")


app = FastAPI(lifespan=lifespan)
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/status")
def status():
    return {"Im, ok"}
