from fastapi import APIRouter, Request, Form
from ..templates import settings_templates
from config_manager import TOKEN
from asana.client import AsanaClient, AsanaApiError
from asana import asana_client
import logging


settings_router = APIRouter(prefix='/settings')


@settings_router.api_route("/", methods=["GET", "POST"])
async def submit(request: Request):
    data = {'type': '', 'message': ''}
    asana_token = asana_client.get_token()

    if request.method == "POST":
        form = await request.form()
        asana_token = form.get("asana_token")

        try:
            res = await asana_client.set_token(asana_token)
            if res:
                data['type'] = 'input-success'
            else:
                data['type'] = 'input-error'
                data['message'] = f'Неверный токен'
        except AsanaApiError as e:
            data['message'] = f"Неизвестная ошибка:\n{e}"

    return settings_templates.TemplateResponse("index.html", {"request": request, "asana_token": asana_token, "data": data})
