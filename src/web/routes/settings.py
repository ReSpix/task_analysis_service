from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from ..templates import settings_templates
from asana.client import AsanaClient, AsanaApiError
from asana import asana_client, ProjectsApi, try_create_apis
import logging
from starlette.status import HTTP_303_SEE_OTHER
from config_manager import set, get


settings_router = APIRouter(prefix='/settings')


@settings_router.get("/")
async def submit(request: Request):
    asana_token = asana_client.get_token()
    data = request.session.pop("data", None)
    projects = request.session.pop("projects", None)

    if projects == None:
        main_project_gid = await get("main_project_gid")
        sub_project_gid = await get("sub_project_gid")

        if main_project_gid is not None and sub_project_gid is not None:
            if data == None:
                data = {}
            data['project_set'] = True
            data['success'] = True
            data['selected_main'] = main_project_gid
            data['selected_sub'] = sub_project_gid
            projects = await ProjectsApi(asana_client).get_projects()

    return settings_templates.TemplateResponse("index.html", {"request": request, "asana_token": asana_token, "data": data, "projects": projects})


@settings_router.post("/")
async def post_form(request: Request):
    data = {}
    form = await request.form()
    asana_token = form.get("asana_token")


    main_project = form.get("main_project")
    sub_project = form.get("sub_project")


    if main_project is not None and sub_project is not None:
        assert isinstance(main_project, str)
        assert isinstance(sub_project, str)
        data['project_set'] = True

        main_res = await ProjectsApi(asana_client).is_project(main_project)
        sub_res = await ProjectsApi(asana_client).is_project(sub_project)

        if main_project == sub_project:
            data['project_message_1'] = "Выберите разные проекты"
            data['project_message_2'] = "Выберите разные проекты"

        if not main_res:
            data['project_message_1'] = "Выберите проект"

        if not sub_res:
            data['project_message_2'] = "Выберите проект"

        if main_res and sub_res:
            data['project_success'] = True
            await set("main_project_gid", main_project)
            await set("sub_project_gid", sub_project)
            data['project_message_1'] = "Сохранено"
            data['project_message_2'] = "Сохранено"

            data['selected_main'] = main_project
            data['selected_sub'] = sub_project
            await try_create_apis()

    try:
        res = await asana_client.set_token(asana_token)
        data['success'] = res
        if res:
            data['message'] = f'Токен сохранен'
            projects = await ProjectsApi(asana_client).get_projects()
            request.session['projects'] = projects
        else:
            data['message'] = f'Неверный токен'
    except AsanaApiError as e:
        data['message'] = f"Неизвестная ошибка:\n{e}"

    request.session['data'] = data
    return RedirectResponse(settings_router.prefix+"/", status_code=HTTP_303_SEE_OTHER)
