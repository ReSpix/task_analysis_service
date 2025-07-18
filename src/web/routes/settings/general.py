from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select

from core.events_handler import schedule_refresh
from ...templates import settings_template
import asana
from asana.client import AsanaClient, AsanaApiError
from asana import asana_client, ProjectsApi, try_create_apis
import logging
from starlette.status import HTTP_303_SEE_OTHER
from config_manager import set, get
from database import Database
from database.models import TelegramConfig, TagRule
from tgbot import TgBot


settings_router = APIRouter(prefix='/settings')


@settings_router.get("/")
async def settings_index(request: Request):
    return RedirectResponse(settings_router.prefix+"/asana/", status_code=HTTP_303_SEE_OTHER)


@settings_router.get("/asana")
async def submit(request: Request):
    asana_token = asana_client.get_token()
    data = request.session.pop("data", None)
    projects = request.session.pop("projects", None)

    main_section_gid = ""
    main_project_gid = None

    main_project_gid = await get("main_project_gid")
    main_section_gid = await get("main_section")
    sub_project_gid = await get("sub_project_gid")

    if main_project_gid is not None:  # and sub_project_gid is not None:
        if data == None:
            data = {}
        data['project_set'] = True
        data['success'] = True
        data['selected_main'] = main_project_gid
        # data['selected_sub'] = sub_project_gid
        projects = await ProjectsApi(asana_client).get_projects()

    sections = {}
    if main_project_gid is not None:
        sections = await ProjectsApi(asana_client).get_sections(main_project_gid)

    return settings_template("asana_main.html",
                             {"request": request,
                              "asana_token": asana_token,
                              "data": data,
                              "projects": projects,
                              "sections": sections,
                              "selected_section": main_section_gid
                              })


@settings_router.post("/asana")
async def post_form(request: Request):
    data = {}
    form = await request.form()
    asana_token = form.get("asana_token")

    main_project = form.get("main_project")
    main_section = form.get("section")
    # sub_project = form.get("sub_project")

    # and sub_project is not None:
    if main_project is not None and main_section is not None:
        assert isinstance(main_project, str)
        # assert isinstance(sub_project, str)
        data['project_set'] = True

        main_res = await ProjectsApi(asana_client).is_project(main_project)
        # sub_res = await ProjectsApi(asana_client).is_project(sub_project)

        # if main_project == sub_project:
        #     data['project_message_1'] = "Выберите разные проекты"
        #     data['project_message_2'] = "Выберите разные проекты"

        if not main_res:
            data['project_message_1'] = "Выберите проект"

        if main_section is None:
            data['project_message_2'] = "Выберите колонку основного проекта"

        # if not sub_res:
        #     data['project_message_2'] = "Выберите проект"

        if main_res:  # and sub_res:
            data['project_success'] = True
            await set("main_project_gid", main_project)
            assert isinstance(main_section, str)
            data['project_message_1'] = "Сохранено"

            if main_section is not None:
                data['section_success'] = True
                await set("main_section", main_section)
                data['project_message_2'] = "Сохранено"
            else:
                data['project_success'] = False
                data['project_message_2'] = "Выберите колонку"
            # await set("sub_project_gid", sub_project)

            data['selected_main'] = main_project
            # data['selected_sub'] = sub_project
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
    return RedirectResponse(settings_router.prefix+"/asana/", status_code=HTTP_303_SEE_OTHER)


@settings_router.post("/asana/projects-listening")
async def post_ptojects_listening(request: Request):
    form = await request.form()
    listen = form.getlist("listen")
    assert isinstance(listen, list)
    assert all(isinstance(item, str) for item in listen)

    listen_str = " ".join(str(item) for item in listen)
    await set("listen_projects", listen_str)
    logging.info(f"Обновлены отслеживаемые проекты: {listen_str}")
    schedule_refresh()

    return RedirectResponse(settings_router.prefix+f"/asana/tag-rules/", status_code=HTTP_303_SEE_OTHER)


@settings_router.get("/asana/tag-rules")
async def tag_rules_list(request: Request):
    async with Database.make_session() as session:
        tag_rules = (await session.execute(select(TagRule))).scalars().all()

    try:
        avail_projects = await ProjectsApi(asana_client).get_projects()
        main_project_gid = await get("main_project_gid")

        listen = await get("listen_projects")
        listen_projects = []
        if listen is not None:
            listen_projects = listen.split(" ")

        return settings_template("tag_rules/list.html",
                             {"request": request,
                              "tag_rules": tag_rules,
                              "initialized": asana.initialized,
                              "avail_projects": avail_projects,
                              "listen_projects": listen_projects,
                              "main_project_gid": main_project_gid
                              })
    except AsanaApiError as e:
        if e.status == 401:
            return RedirectResponse(settings_router.prefix+f"/", status_code=HTTP_303_SEE_OTHER)


@settings_router.post("/asana/tag-rules/rule-delete/{id}")
async def delete_tag_rule(request: Request, id: int):
    logging.info(f"Запрос на удаление правила {id}")
    async with Database.make_session() as session:
        tag_rule = (await session.execute(select(TagRule).where(TagRule.id == id))).scalars().one_or_none()
        if tag_rule is not None:
            await session.delete(tag_rule)
            await session.flush()

    return RedirectResponse(settings_router.prefix+f"/asana/tag-rules/", status_code=HTTP_303_SEE_OTHER)


@settings_router.get("/asana/tag-rules/rule/new")
async def new_tag_rule(request: Request):
    data = {}
    tags = await ProjectsApi(asana_client).get_tags()
    async with Database.make_session() as session:
        used_tags = (await session.execute(select(TagRule))).scalars().all()
        used_tags = {t.tag for t in used_tags}

    tags = {tag['name'] for tag in tags if tag['name'] not in used_tags}

    projects = await ProjectsApi(asana_client).get_projects()

    return settings_template("tag_rules/rule.html",
                             {"request": request,
                              "tags": tags,
                              "data": data,
                              "projects": projects,
                              "tag_rule": None
                              })


@settings_router.post("/asana/tag-rules/rule/new")
async def new_tag_rule_submit(request: Request):
    form = await request.form()
    tag = form.get("tag")
    action = form.get("action")
    project = form.get("project")
    section = form.get("section")

    async with Database.make_session() as session:
        tag_rule = TagRule(tag=tag, action=action,
                           project_gid=project, section_gid=section)
        session.add(tag_rule)
        await tag_rule.update_names(ProjectsApi(asana_client), session)

    return RedirectResponse(settings_router.prefix+f"/asana/tag-rules/", status_code=HTTP_303_SEE_OTHER)


@settings_router.get("/asana/tag-rules/rule/{id}")
async def get_tag_rule(request: Request, id: int):
    data = {}
    tags = await ProjectsApi(asana_client).get_tags()
    # logging.info(tags)
    tags = {tag['name'] for tag in tags}

    projects = await ProjectsApi(asana_client).get_projects()

    async with Database.make_session() as session:
        tag_rule = (await session.execute(select(TagRule).where(TagRule.id == id))).scalars().one_or_none()
        if tag_rule is None:
            return RedirectResponse(settings_router.prefix+f"/asana/tag-rules", status_code=HTTP_303_SEE_OTHER)

    sections = await ProjectsApi(asana_client).get_sections(tag_rule.project_gid)

    return settings_template("tag_rules/rule.html",
                             {"request": request,
                              "tags": tags,
                              "data": data,
                              "projects": projects,
                              "tag_rule": tag_rule,
                              "sections": sections
                              })


@settings_router.post("/asana/tag-rules/rule/{id}")
async def update_tag_rule(request: Request, id: int):
    form = await request.form()

    tag = form.get("tag")
    assert isinstance(tag, str)

    action = form.get("action")
    assert isinstance(action, str)
    action = int(action)

    project = form.get("project")
    assert isinstance(project, str)

    section = form.get("section")
    assert isinstance(section, str)

    async with Database.make_session() as session:
        tag_rule = (await session.execute(select(TagRule).where(TagRule.id == id))).scalars().one_or_none()

        if tag_rule is None:
            return RedirectResponse(settings_router.prefix+f"/asana/tag-rules", status_code=HTTP_303_SEE_OTHER)

        tag_rule.tag = tag
        tag_rule.action = action
        tag_rule.project_gid = project
        tag_rule.section_gid = section
        session.add(tag_rule)
        await tag_rule.update_names(ProjectsApi(asana_client), session)

    return RedirectResponse(settings_router.prefix+f"/asana/tag-rules", status_code=HTTP_303_SEE_OTHER)


@settings_router.get("/asana/project_sections")
async def get_project_sections(request: Request, project: str = "", main_project: str = ""):
    if project == "":
        project = main_project
    sections = await ProjectsApi(asana_client).get_sections(project)
    return settings_template("tag_rules/section_select.html",
                             {"request": request,
                              "sections": sections
                              })


@settings_router.get("/asana/additional")
async def additional_asana_settings(request: Request):
    is_after_set = request.session.pop("data", None)

    main_gid = await get("main_project_gid")
    sub_gid = await get("sub_project_gid")

    projects_api = ProjectsApi(asana_client)

    main_sections = await projects_api.get_sections(main_gid)
    sub_sections = await projects_api.get_sections(sub_gid)

    tags_objs = await projects_api.get_tags()

    key = "name"
    tags = {d[key] for d in tags_objs if key in d}

    selected_main_section = await get("main_section")
    selected_sub_section = await get("sub_section")
    selected_tag = await get("tag")

    data = {}
    if selected_main_section is not None:
        data['selected_main_section'] = selected_main_section

    if selected_sub_section is not None:
        data['selected_sub_section'] = selected_sub_section

    if selected_tag is not None:
        data['selected_tag'] = selected_tag

    return settings_template("asana_additional.html",
                             {"request": request,
                              "main_sections": main_sections,
                              "sub_sections": sub_sections,
                              "tags": tags,
                              "data": data,
                              "is_after_set": is_after_set
                              })


@settings_router.post("/asana/additional")
async def additional_asana_submit(request: Request):
    form = await request.form()

    main_section = form.get("main_section")
    sub_section = form.get("sub_section")
    tag = form.get("tag")

    assert isinstance(main_section, str)
    assert isinstance(sub_section, str)
    assert isinstance(tag, str)

    await set("main_section", main_section)
    await set("sub_section", sub_section)
    await set("tag", tag)

    request.session['data'] = True

    return RedirectResponse(settings_router.prefix+"/asana/additional", status_code=HTTP_303_SEE_OTHER)


@settings_router.get("/yandex-forms")
async def yandex_hints(request: Request):
    return settings_template("yandex_forms_hint.html",
                             {"request": request, })


@settings_router.get("/app")
async def settings_app(request: Request):
    watch_field_changes = (await get("watch_field_changes")) == "1"
    saved = request.session.pop("saved", None)

    return settings_template("app.html",
                             {"request": request,
                              "watch_field_changes": watch_field_changes,
                              "saved": saved
                              })


@settings_router.post("/app")
async def settings_app_submit(request: Request):
    form = await request.form()
    watch_field_changes = form.get("watch_field_changes") is not None
    await set("watch_field_changes", "1" if watch_field_changes else "0")

    request.session['saved'] = True

    return RedirectResponse(settings_router.prefix+"/app", status_code=HTTP_303_SEE_OTHER)
