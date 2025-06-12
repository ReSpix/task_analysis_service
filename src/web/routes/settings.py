from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from ..templates import settings_template
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

    if projects == None:
        main_project_gid = await get("main_project_gid")
        sub_project_gid = await get("sub_project_gid")

        if main_project_gid is not None:  # and sub_project_gid is not None:
            if data == None:
                data = {}
            data['project_set'] = True
            data['success'] = True
            data['selected_main'] = main_project_gid
            # data['selected_sub'] = sub_project_gid
            projects = await ProjectsApi(asana_client).get_projects()

    return settings_template("asana_main.html",
                             {"request": request,
                              "asana_token": asana_token,
                              "data": data,
                              "projects": projects})


@settings_router.post("/asana")
async def post_form(request: Request):
    data = {}
    form = await request.form()
    asana_token = form.get("asana_token")

    main_project = form.get("main_project")
    # sub_project = form.get("sub_project")

    if main_project is not None:  # and sub_project is not None:
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

        # if not sub_res:
        #     data['project_message_2'] = "Выберите проект"

        if main_res:  # and sub_res:
            data['project_success'] = True
            await set("main_project_gid", main_project)
            # await set("sub_project_gid", sub_project)
            data['project_message_1'] = "Сохранено"
            data['project_message_2'] = "Сохранено"

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


@settings_router.get("/asana/tag-rules")
async def tag_rules_list(request: Request):
    async with Database.make_session() as session:
        tag_rules = (await session.execute(select(TagRule))).scalars().all()

    return settings_template("tag_rules/list.html",
                             {"request": request,
                              "tag_rules": tag_rules,
                              "initialized": asana.initialized
                              })


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
    logging.info(tags)
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
async def get_project_sections(request: Request, project: str):
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


@settings_router.get("/telegram")
async def telegram_settings(request: Request):
    telegram_token = await get("telegram_token")

    notify_created = (await get("notify_created")) == "1"
    notify_status_changed = (await get("notify_status_changed")) == "1"
    notify_deleted = (await get("notify_deleted")) == "1"
    notify_sub_tag_setted = (await get("notify_sub_tag_setted")) == "1"
    notify_commented = (await get("notify_commented")) == "1"

    async with Database.make_session() as session:
        query_chats = select(TelegramConfig).where(
            TelegramConfig.destination_type == 'chat')
        res_chats = await session.execute(query_chats)
        chats = res_chats.scalars().all()

        query_users = select(TelegramConfig).where(
            TelegramConfig.destination_type == 'user')
        res_users = await session.execute(query_users)
        users = res_users.scalars().all()

        chats = "\n".join([d.destination_id for d in chats])
        users = "\n".join([d.destination_id for d in users])

    telegram_token_error = request.session.pop("telegram_token_error", None)
    telegram_token_error_message = request.session.pop(
        "telegram_token_error_message", None)
    saved = request.session.pop("saved", None)

    if telegram_token_error:
        saved = False

    if telegram_token is None:
        telegram_token = ""

    return settings_template("telegram.html",
                             {"request": request,
                              "telegram_token": telegram_token,
                              "users": users,
                              "chats": chats,
                              "notify_created": notify_created,
                              "notify_status_changed": notify_status_changed,
                              "notify_deleted": notify_deleted,
                              "notify_sub_tag_setted": notify_sub_tag_setted,
                              "notify_commented": notify_commented,
                              "saved": saved,
                              "telegram_token_error": telegram_token_error,
                              "telegram_token_error_message": telegram_token_error_message
                              })


@settings_router.post("/telegram")
async def telegram_settings_submit(request: Request):
    form = await request.form()

    bot_token = form.get("telegram_token")
    if bot_token is not None:
        assert isinstance(bot_token, str)
        is_token_correct, token_message = await TgBot.check_token(bot_token)

        if is_token_correct:
            await set("telegram_token", bot_token)
        else:
            request.session['telegram_token_error'] = True
            request.session['telegram_token_error_message'] = token_message

    notify_created = form.get("created") is not None
    notify_status_changed = form.get("status_changed") is not None
    notify_deleted = form.get("deleted") is not None
    notify_sub_tag_setted = form.get("sub_tag_setted") is not None
    notify_commented = form.get("commented") is not None

    await set("notify_created", "1" if notify_created else "0")
    await set("notify_status_changed", "1" if notify_status_changed else "0")
    await set("notify_deleted", "1" if notify_deleted else "0")
    await set("notify_sub_tag_setted", "1" if notify_sub_tag_setted else "0")
    await set("notify_commented", "1" if notify_commented else "0")

    chats = form.get("chats")
    if chats is not None:
        assert isinstance(chats, str)
        chats = chats.split("\r\n")

    users = form.get("users")
    if users is not None:
        assert isinstance(users, str)
        users = users.split("\r\n")

    async with Database.make_session() as session:
        query = delete(TelegramConfig)
        await session.execute(query)

        if chats is not None:
            for chat in chats:
                if len(chat) == 0 or chat[0] != "-":
                    continue

                tg_conf = TelegramConfig(
                    destination_id=chat, destination_type='chat')
                session.add(tg_conf)

        if users is not None:
            for user in users:
                if len(user) == 0 or user[0] != "@":
                    continue

                tg_conf = TelegramConfig(
                    destination_id=user, destination_type='user')
                session.add(tg_conf)

    request.session['saved'] = True

    return RedirectResponse(settings_router.prefix+"/telegram", status_code=HTTP_303_SEE_OTHER)


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
