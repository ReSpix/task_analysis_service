from database import Database
from database.models import Ticket, Status
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
    
    notify = (await get("notify_created")) == "1"
    notify_created_full = (await get("notify_created_full")) == "1"

    if notify:
        await TgBot.send_message(f"Получено '{ticket.title}'")

    if notify_created_full:
        await TgBot.send_message(f"Получен челлендж:\n\n{str(ticket)}")
