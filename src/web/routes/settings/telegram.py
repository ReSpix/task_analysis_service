import logging
from fastapi import APIRouter
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select

from ...templates import settings_template
from starlette.status import HTTP_303_SEE_OTHER
from config_manager import set, get
from database import Database
from database.models import TelegramConfig
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
                              "notify_created_full": notify_created_full,
                              "notify_status_changed": notify_status_changed,
                              "notify_deleted": notify_deleted,
                              "notify_sub_tag_setted": notify_sub_tag_setted,
                              "notify_commented": notify_commented,
                              "saved": saved,
                              "telegram_token_error": telegram_token_error,
                              "telegram_token_error_message": telegram_token_error_message
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
    return settings_template("telegram/chat_settings.html", {"request": request,
                                                             "error_message": error_message,
                                                             "success_message": success_message
                                                             })

@telegram_settings_router.post("/new-chat-settings")
async def submit_new_chat_settigns_page(request: Request):
    form = await request.form()

    chat_id = form.get("chat_id")
    assert isinstance(chat_id, str)

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
        request.session['new_tg_chat_success_message'] = f"Успешно сохранена настройка уведомлений для чата '{message}'"
    return RedirectResponse(telegram_settings_router.prefix+"/new-chat-settings", status_code=HTTP_303_SEE_OTHER)