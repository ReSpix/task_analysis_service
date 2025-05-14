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
        elif e.is_field_change():
            await on_field_changed(e)
        elif e.is_deleted_task():
            await on_task_delete(e)
        elif e.is_undeleted_task():
            await on_task_undelete(e)


async def on_section_moved(event: Event):
    async with Database.make_session() as session:
        ticket = await Ticket.get_by_gid(session, event.resource.gid)
        if ticket is None:
            await on_new_task_added(event)
            return
        assert event.parent is not None
        status = Status(text=event.parent.name, ticket=ticket)
        session.add(status)
        logging.info(f"Задача {ticket.title} перемещена в '{status.text}'")


async def on_new_task_added(event: Event):
    async with Database.make_session() as session:
        ticket = await Ticket.get_by_gid(session, event.resource.gid)

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


async def on_field_changed(event: Event):
    async with Database.make_session() as session:
        ticket = await Ticket.get_by_gid(session, event.resource.gid)

        if ticket is None:
            logging.warning(
                f"Обновлено поле несущесвтующей задачи. gid={event.resource.gid}")
            return

        ticket_data = await task_api.get_task(event.resource.gid)
        ticket.title = ticket_data['name']
        ticket.text = ticket_data['notes']
        ticket.completed = ticket_data['completed']

        session.add(ticket)


async def on_task_delete(event: Event):
    async with Database.make_session() as session:
        ticket = await Ticket.get_by_gid(session, event.resource.gid)
        if ticket is None:
            logging.warning(
                f"Удалена несущесвтующая задачи. gid={event.resource.gid}")
            return
        ticket.deleted = True
        session.add(ticket)


async def on_task_undelete(event: Event):
    async with Database.make_session() as session:
        ticket = await Ticket.get_by_gid(session, event.resource.gid)
        if ticket is None:
            logging.warning(
                f"Восстановлена несущесвтующая задачи. gid={event.resource.gid}")
            return
        ticket.deleted = False
        session.add(ticket)
