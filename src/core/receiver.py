from sqlalchemy import select
from database import Database
from database.models import TelegramConfigExtended, Ticket, Status
import logging
from asana import get_task_api
import asyncio
from tgbot import TgBot
from config_manager import get

async def receive_form(data: dict):
    logging.info("Received ticket")
    async with Database.make_session() as session:
        ticket = Ticket.full_ticket_from_dict(data)
        session.add(ticket)

        task_api = get_task_api()
        assert task_api is not None
        section = await get("main_section")

        publish_data = await task_api.publish_task(ticket, section)
        ticket.gid = publish_data['gid']

        section_text = publish_data['memberships'][0]['section']['name']
        status_create = Status(text=f"Создано", ticket=ticket)
        status_section = Status(text=section_text, ticket=ticket)

        session.add(status_create)
        session.add(status_section)
        session.add(ticket)
        
        chats_short = (await session.execute(select(TelegramConfigExtended).where(TelegramConfigExtended.status_changed == True))).scalars().all()
        for chat in chats_short:
            await TgBot.send_message(chat.chat_id, f"Получено '{ticket.title}'")

        chats_full = (await session.execute(select(TelegramConfigExtended).where(TelegramConfigExtended.status_changed == True))).scalars().all()
        for chat in chats_full:
            await TgBot.send_message(chat.chat_id, f"Получен челлендж:\n\n{str(ticket)}")
