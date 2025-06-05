from datetime import datetime
from asana.events import EventsApi
from typing import List
from sqlalchemy import select
from asana.client import AsanaApiError
from asana.models import Event, ActionType
from database.models import Ticket, Status
from database import Database
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asana import get_task_api, asana_client, get_projects_api
from config_manager import get
from tgbot import TgBot
from zoneinfo import ZoneInfo


scheduler = AsyncIOScheduler()
update_interval = 5
logging.getLogger("apscheduler").setLevel(logging.WARNING)

events_api = None
sub_events_api = None


async def request_events():
    global events_api
    global sub_events_api

    if events_api is None or sub_events_api is None:
        main_project_gid = await get("main_project_gid")
        sub_project_gid = await get("sub_project_gid")

        logging.info(f"{main_project_gid} {sub_project_gid}")

        if main_project_gid is not None and sub_project_gid is not None:
            events_api = EventsApi(asana_client, main_project_gid)
            sub_events_api = EventsApi(asana_client, sub_project_gid)
        else:
            return

    events = await events_api.get_events()
    sub_events = await sub_events_api.get_events()
    await handle_events(events)
    await handle_events(sub_events)


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
        elif e.is_tag_add():
            await on_tag_add(e)
        elif e.is_tag_removed():
            await on_tag_remove(e)
        elif e.is_story_add():
            await on_story_add(e)


async def on_section_moved(event: Event):
    async with Database.make_session() as session:
        ticket = await Ticket.get_by_gid(session, event.resource.gid)
        if ticket is None:
            await on_new_task_added(event)
            return
        assert event.parent is not None

        status = Status(text=event.parent.name, ticket=ticket,
                        datetime=event.created_at_local_timezone)
        session.add(status)
        logging.info(f"Задача {ticket.title} перемещена в '{status.text}'")

        notify = (await get("notify_status_changed")) == "1"
        if notify:
            await TgBot.send_message(f"'{ticket.title}' перемещено в '{status.text}'")


async def on_new_task_added(event: Event):
    watch = (await get("watch_tasks")) == "1"

    if not watch:
        return

    async with Database.make_session() as session:
        ticket = await Ticket.get_by_gid(session, event.resource.gid)

        if ticket is not None:
            return

        task_api = get_task_api()
        assert task_api is not None
        try:
            ticket_data = await task_api.get_task(event.resource.gid)
        except AsanaApiError as e:
            if e.status == 404:
                logging.warning("Задачи не существует")
                logging.warning(e.body['errors'][0]['message'])
                return

        ticket = Ticket(
            gid=ticket_data['gid'], title=ticket_data['name'], text=ticket_data['notes'], created_at=event.created_at_local_timezone)
        session.add(ticket)

        status = Status(
            text=ticket_data['memberships'][0]['section']['name'], ticket=ticket, datetime=event.created_at_local_timezone)
        session.add(status)


async def on_field_changed(event: Event):
    watch = (await get("watch_field_changes")) == "1"

    if not watch:
        return

    async with Database.make_session() as session:
        ticket = await Ticket.get_by_gid(session, event.resource.gid)

        if ticket is None:
            logging.warning(
                f"Обновлено поле несущесвтующей задачи. gid={event.resource.gid}")
            return

        task_api = get_task_api()
        assert task_api is not None
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
        ticket.deleted_at = event.created_at_local_timezone
        session.add(ticket)

        status = Status(text='Удалено', ticket=ticket, datetime=event.created_at_local_timezone)
        session.add(status)

    notify = (await get("notify_deleted")) == "1"
    if notify:
        await TgBot.send_message(f"'{ticket.title}' удалено")


async def on_task_undelete(event: Event):
    async with Database.make_session() as session:
        ticket = await Ticket.get_by_gid(session, event.resource.gid)
        if ticket is None:
            logging.warning(
                f"Восстановлена несущесвтующая задачи. gid={event.resource.gid}")
            return
        ticket.deleted = False
        session.add(ticket)

        status = Status(text="Удаление отменено", ticket=ticket, datetime=event.created_at_local_timezone)
        session.add(status)


async def on_tag_add(event: Event):
    assert event.parent is not None
    assert event.parent.name is not None

    tag = await get("tag")

    if tag is not None and tag.lower() == event.parent.name.lower():
        ticket_gid = event.resource.gid

        assert sub_events_api is not None
        sub_project_gid = sub_events_api.get_resource()

        task_api = get_task_api()
        assert task_api is not None
        res = await task_api.add_to_project(ticket_gid, sub_project_gid)
        assert isinstance(res, dict)

        if 'data' not in res.keys():
            logging.warning(
                f"Не удалось установить задачу в проект {sub_project_gid}")
            return

        logging.info(
            f"Задача {ticket_gid} установлена в проект {sub_project_gid}")

        res = await task_api.remove_from_project(ticket_gid, task_api._client.main_project_gid)
        logging.info(
            f"Задача {ticket_gid} удалена из проекта в проект {task_api._client.main_project_gid}")

        async with Database.make_session() as session:
            ticket = await Ticket.get_by_gid(session, ticket_gid)
            if ticket is None:
                logging.warning(
                    f"Поставлен тег на неизвестную задачу gid={ticket_gid}")
                return
            ticket.sub_contract = True
            session.add(ticket)
            # status = Status(text='Перемещено в субподряд', ticket=ticket, datetime=event.created_at_local_timezone)
            # session.add(status)

    notify = (await get("notify_sub_tag_setted")) == "1"
    if notify:
        await TgBot.send_message(f"'{ticket.title}' отмечено как субподряд")


async def on_tag_remove(event: Event):
    assert event.parent is not None
    assert event.parent.name is not None

    tag = await get("tag")

    if tag is not None and tag.lower() == event.parent.name.lower():
        ticket_gid = event.resource.gid

        async with Database.make_session() as session:
            ticket = await Ticket.get_by_gid(session, ticket_gid)
            if ticket is None:
                logging.warning(
                    f"Удален тег с неизвестной задачи gid={ticket_gid}")
                return
            ticket.sub_contract = False
            session.add(ticket)


async def on_story_add(event: Event):
    projects_api = get_projects_api()

    if projects_api is None:
        return

    story = await projects_api.get_story(event.resource.gid)

    if story['type'] == "comment":

        notify = (await get("notify_commented")) == "1"

        if notify:
            assert event.parent is not None
            async with Database.make_session() as session:
                ticket_gid = event.parent.gid
                ticket = await Ticket.get_by_gid(session, ticket_gid)

                if ticket is None:
                    return

                await TgBot.send_message(f"На '{ticket.title}' добавлен комментарий '{story['text']}'")
