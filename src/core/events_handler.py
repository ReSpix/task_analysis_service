from typing import List
from sqlalchemy import select
from asana.client import AsanaApiError
from asana.models import Event, ActionType
from database.models import Ticket, Status
from database import Database
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asana import events_api, task_api

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
        logging.info(e)
    for e in events:
        if e.is_status_change_event():
            await on_section_moved(e)
        elif e.is_new_task_added():
            await on_new_task_added(e)


async def on_section_moved(event: Event):
    async with Database.make_session() as session:
        query = select(Ticket).where(Ticket.gid == event.resource.gid)
        result = await session.execute(query)
        ticket = result.scalars().first()
        if ticket is None:
            await on_new_task_added(event)
            return
        assert event.parent is not None
        status = Status(text=event.parent.name, ticket=ticket)
        session.add(status)
        logging.info(f"Задача {ticket.title} перемещена в '{status.text}'")


async def on_new_task_added(event: Event):
    async with Database.make_session() as session:
        query = select(Ticket).where(Ticket.gid == event.resource.gid)
        result = await session.execute(query)
        ticket = result.scalars().first()

        if ticket is not None:
            return

        try:
            ticket_data = await task_api.get_task(event.resource.gid)
        except AsanaApiError as e:
            if e.status == 404:
                logging.warning("Задачи не существует")
                logging.warning(e.body['errors'][0]['message'])
                return

        ticket = Ticket(
            gid=ticket_data['gid'], title=ticket_data['name'], text=ticket_data['notes'])
        session.add(ticket)

        status = Status(
            text=ticket_data['memberships'][0]['section']['name'], ticket=ticket)
        session.add(status)
