from database import Database
from database.models import Ticket, Status
import logging
from asana.tasks import TaskApi
import asyncio

async def receive_form(data: dict):
    logging.info("Received ticket")
    async with Database.make_session() as session:
        ticket = Ticket.full_ticket_from_dict(data)
        session.add(ticket)

        api = TaskApi()
        publish_data = await api.publish_task(ticket)
        ticket.gid = publish_data['gid']

        section_text = publish_data['memberships'][0]['section']['name']
        status = Status(text=section_text, ticket=ticket)

        session.add(status)
        session.add(ticket)
