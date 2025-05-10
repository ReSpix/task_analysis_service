from typing import List

from sqlalchemy import select
from asana.models import Event, ActionType
from database.models import Ticket, Status
from database import Database
import logging

async def handle_events(events: List[Event]):
    for e in events:
        if e.action == ActionType.MOVED and e.parent is not None and e.parent.type == 'section' and e.resource.type == 'task':
            async with Database.make_session() as session:
                query = select(Ticket).where(Ticket.gid == e.resource.gid)
                result = await session.execute(query)
                ticket = result.scalars().first()
                logging.info(ticket)
                status = Status(text=e.parent.name, ticket=ticket)
                logging.info(status)
                session.add(status)
