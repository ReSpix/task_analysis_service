from database import Database
from database.models import Ticket
import logging
from asana.tasks import TaskApi
import asyncio

async def receive_form(data: dict):
    logging.info("Received ticket")
    async with Database.make_session() as session:
        ticket = Ticket.full_ticket_from_dict(data)
        session.add(ticket)

        api = TaskApi()
        gid = await api.publish_task(ticket)
        ticket.gid = gid
        session.add(ticket)
