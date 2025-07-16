import logging
from fastapi import APIRouter
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select

from asana.projects import ProjectsApi
from asana.client import asana_client

from ...templates import settings_template
from starlette.status import HTTP_303_SEE_OTHER
from config_manager import set, get
from database import Database
from database.models import TelegramConfig, TelegramConfigExtended
from tgbot import TgBot

telegram_settings_router = APIRouter(prefix='/settings/telegram')


@telegram_settings_router.get("/")
async def telegram_settings(request: Request):
    telegram_token = await get("telegram_token")

    notify_created = (await get("notify_created")) == "1"
    notify_created_full = (await get("notify_created_full")) == "1"
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

        chat_rules = (await session.execute(select(TelegramConfigExtended))).scalars().all()
        chat_ids = [cr.chat_id for cr in chat_rules]
        chat_titles = await TgBot.get_chats_titles(chat_ids)
        # for chat_rule in chat_rules:
        #     success, message = await TgBot.get_chat_title(chat_rule.chat_id)
        #     chat_titles.append([success, message])

    telegram_token_error = request.session.pop("telegram_token_error", None)
    telegram_token_error_message = request.session.pop(
        "telegram_token_error_message", None)
    saved = request.session.pop("saved", None)

    if telegram_token_error:
        saved = False

    if telegram_token is None:
        telegram_token = ""

    projects = await get_watched_projects()

    return settings_template("telegram.html",
                             {"request": request,
                              "telegram_token": telegram_token,
                              "users": users,
                              "chats": chats,
                              "notify_created": notify_created,
                              "notify_created_full": notify_created_full,
                              "notify_status_changed": notify_status_changed,
                              "notify_deleted": notify_deleted,
                              "notify_sub_tag_setted": notify_sub_tag_setted,
                              "notify_commented": notify_commented,
                              "saved": saved,
                              "telegram_token_error": telegram_token_error,
                              "telegram_token_error_message": telegram_token_error_message,
                              "chat_rules": chat_rules,
                              "chat_titles": chat_titles,
                              "projects": projects
                              })


@telegram_settings_router.post("/")
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
    notify_created_full = form.get("created_full") is not None
    notify_status_changed = form.get("status_changed") is not None
    notify_deleted = form.get("deleted") is not None
    notify_sub_tag_setted = form.get("sub_tag_setted") is not None
    notify_commented = form.get("commented") is not None

    await set("notify_created", "1" if notify_created else "0")
    await set("notify_created_full", "1" if notify_created_full else "0")
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

    return RedirectResponse(telegram_settings_router.prefix, status_code=HTTP_303_SEE_OTHER)


@telegram_settings_router.get("/new-chat-settings")
async def new_chat_settigns_page(request: Request):
    error_message = request.session.pop("new_tg_chat_error_message", None)
    success_message = request.session.pop("new_tg_chat_success_message", None)
    projects = await get_watched_projects()
    
    return settings_template("telegram/chat_settings.html", {"request": request,
                                                             "error_message": error_message,
                                                             "success_message": success_message,
                                                             "projects": projects
                                                             })

async def get_watched_projects() -> list[str]:
    result = []
    all_projects = await ProjectsApi(asana_client).get_projects()

    main_project = await get("main_project_gid")
    for p in all_projects:
        if p['gid'] == main_project:
            result.append(p)
            break
    
    listen_str = await get("listen_projects")
    if listen_str is not None:
        listen = listen_str.split(" ")
        if len(listen) > 0 and listen_str != "":
            for p in all_projects:
                if p['gid'] in listen:
                    result.append(p)

    return result

@telegram_settings_router.post("/new-chat-settings")
async def submit_new_chat_settigns_page(request: Request):
    form = await request.form()

    chat_id = form.get("chat_id")
    project_id = form.get("project")
    assert isinstance(chat_id, str)
    assert isinstance(project_id, str)

    created = form.get("created") is not None
    created_full = form.get("created_full") is not None
    status_changed = form.get("status_changed") is not None
    deleted = form.get("deleted") is not None
    sub_tag_setted = form.get("sub_tag_setted") is not None
    commented = form.get("commented") is not None

    success, message = await TgBot.get_chat_title(chat_id)

    if not success:
        request.session['new_tg_chat_error_message'] = message
    else:
        async with Database.make_session() as session:
            chat_rules = (await session.execute(select(TelegramConfigExtended).where(TelegramConfigExtended.chat_id == chat_id))).scalars().all()

            if len(chat_rules) != 0 and any([rule.additional == project_id for rule in chat_rules]):
                request.session[
                    'new_tg_chat_error_message'] = f"Для чата \"{message}\" (ID {chat_id}) уже настроены уведомления для этого проекта"
                return RedirectResponse(telegram_settings_router.prefix+f"/new-chat-settings", status_code=HTTP_303_SEE_OTHER)
            else:
                request.session[
                    'new_tg_chat_success_message'] = f"Успешно сохранена настройка уведомлений для чата '{message}'"

                setting = TelegramConfigExtended(
                    chat_id=chat_id,
                    created=created,
                    created_full=created_full,
                    status_changed=status_changed,
                    deleted=deleted,
                    sub_tag_setted=sub_tag_setted,
                    commented=commented,
                    additional=project_id
                )
                session.add(setting)

    return RedirectResponse(telegram_settings_router.prefix+f"/chat-settings/{setting.id}", status_code=HTTP_303_SEE_OTHER)


@telegram_settings_router.get("/chat-settings/{setting_id}")
async def show_chat_settings_page(request: Request, setting_id: int):
    success_message = request.session.pop("new_tg_chat_success_message", None)
    async with Database.make_session() as session:
        chat_setting = (await session.execute(select(TelegramConfigExtended).where(TelegramConfigExtended.id == setting_id))).scalars().one_or_none()
    projects = await get_watched_projects()
    return settings_template("telegram/chat_settings.html", {"request": request,
                                                             "chat_setting": chat_setting,
                                                             "success_message": success_message,
                                                             "selected_project": chat_setting.additional if chat_setting is not None else "",
                                                             "projects": projects})


@telegram_settings_router.post("/chat-settings/{setting_id}")
async def update_chat_settings_page(request: Request, setting_id: int):
    form = await request.form()

    created = form.get("created") is not None
    created_full = form.get("created_full") is not None
    status_changed = form.get("status_changed") is not None
    deleted = form.get("deleted") is not None
    sub_tag_setted = form.get("sub_tag_setted") is not None
    commented = form.get("commented") is not None

    project_id = form.get("project")
    assert isinstance(project_id, str)

    async with Database.make_session() as session:
        chat_setting = (await session.execute(select(TelegramConfigExtended).where(TelegramConfigExtended.id == setting_id))).scalars().one_or_none()

        if chat_setting is not None:
            chat_setting.created = created
            chat_setting.created_full = created_full
            chat_setting.status_changed = status_changed
            chat_setting.deleted = deleted
            chat_setting.sub_tag_setted = sub_tag_setted
            chat_setting.commented = commented
            chat_setting.additional = project_id

            session.add(chat_setting)
            request.session['new_tg_chat_success_message'] = "Сохранено"

    return RedirectResponse(telegram_settings_router.prefix+f"/chat-settings/{setting_id}", status_code=HTTP_303_SEE_OTHER)

@telegram_settings_router.post("/chat-settings/{setting_id}/delete")
async def delete_chat_settings_page(request: Request, setting_id: int):
    async with Database.make_session() as session:
        chat_setting = (await session.execute(select(TelegramConfigExtended).where(TelegramConfigExtended.id == setting_id))).scalars().one_or_none()

        if chat_setting is not None:
            await session.delete(chat_setting)
            await session.flush()

    return RedirectResponse(telegram_settings_router.prefix, status_code=HTTP_303_SEE_OTHER)