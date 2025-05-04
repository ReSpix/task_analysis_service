from database import Database
from database.models import Ticket
import logging
from asana.tasks import TaskApi
import asyncio

async def receive_form(data: dict):
    logging.info("Received ticket")
    async with Database.make_session() as session:
        ticket = Ticket.from_dict(data)
        session.add(ticket)

        api = TaskApi()
        asyncio.create_task(api.publish_task(ticket))