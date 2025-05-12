from typing import List
from sqlalchemy import select
from asana.models import Event, ActionType
from database.models import Ticket, Status
from database import Database
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asana import events_api

scheduler = AsyncIOScheduler()
update_interval = 5
logging.getLogger("apscheduler").setLevel(logging.WARNING)


async def request_events():
    events = await events_api.get_events()
    await handle_events(events)


def activate_scheduler():
    scheduler.add_job(request_events, 'interval', seconds=update_interval)
    scheduler.start()


def shutdown_scheduler():
    scheduler.shutdown()


async def handle_events(events: List[Event]):
    for e in events:
        if e.action == ActionType.MOVED and e.parent is not None and e.parent.type == 'section' and e.resource.type == 'task':
            async with Database.make_session() as session:
                query = select(Ticket).where(Ticket.gid == e.resource.gid)
                result = await session.execute(query)
                ticket = result.scalars().first()
                if ticket is None:
                    return # TODO:
                status = Status(text=e.parent.name, ticket=ticket)
                session.add(status)
                logging.info(f"Задача {ticket.title} перемещена в '{status.text}'")
