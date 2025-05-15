from database import Database
from database.models import Ticket, Status
import logging
from asana import task_api
import asyncio
from tgbot import TgBot

async def receive_form(data: dict):
    logging.info("Received ticket")
    async with Database.make_session() as session:
        ticket = Ticket.full_ticket_from_dict(data)
        session.add(ticket)

        publish_data = await task_api.publish_task(ticket)
        ticket.gid = publish_data['gid']

        section_text = publish_data['memberships'][0]['section']['name']
        status = Status(text=section_text, ticket=ticket)

        session.add(status)
        session.add(ticket)
    await TgBot.send_message(f"Получен {ticket.title}")
