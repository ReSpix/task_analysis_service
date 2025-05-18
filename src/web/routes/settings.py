from fastapi import APIRouter, Request, Form
from ..templates import settings_templates
from config_manager import TOKEN
import aiohttp
from asana.client import AsanaClient, AsanaApiError


settings_router = APIRouter(prefix='/settings')


@settings_router.get("/")
def show(request: Request):
    return settings_templates.TemplateResponse("index.html", {"request": request})


@settings_router.post("/submit")
async def submit(request: Request, asana_token=Form(...)):
    try:
        data = await AsanaClient.check_token("workspaces", asana_token)
    except AsanaApiError as e:
        if e.status == 401:
            data = f'Неверный токен'
        else:
            data = f"Неизвестная ошибка:\n{e}"
    return settings_templates.TemplateResponse("index.html", {"request": request, "asana_token": asana_token, "data": data})
