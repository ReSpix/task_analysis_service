from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from ..templates import settings_templates
from config_manager import TOKEN
from asana.client import AsanaClient, AsanaApiError
from asana import asana_client
import logging
from starlette.status import HTTP_303_SEE_OTHER


settings_router = APIRouter(prefix='/settings')


@settings_router.get("/")
async def submit(request: Request):
    asana_token = asana_client.get_token()
    data = request.session.pop("data", None)

    return settings_templates.TemplateResponse("index.html", {"request": request, "asana_token": asana_token, "data": data})


@settings_router.post("/")
async def post_form(request: Request):
    data = {}
    form = await request.form()
    asana_token = form.get("asana_token")

    try:
        res = await asana_client.set_token(asana_token)
        data['success'] = res
        if res:
            data['message'] = f'Токен сохранен'
        else:
            data['message'] = f'Неверный токен'
    except AsanaApiError as e:
        data['message'] = f"Неизвестная ошибка:\n{e}"

    request.session['data'] = data
    return RedirectResponse(settings_router.prefix+"/", status_code=HTTP_303_SEE_OTHER)
