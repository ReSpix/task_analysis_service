from datetime import datetime
from asana.events import EventsApi
from typing import List
from sqlalchemy import select
from asana.client import AsanaApiError
from asana.models import Event, ActionType
from database.models import Ticket, Status, TagRule, TelegramConfigExtended
from database import Database
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from asana import get_task_api, asana_client, get_projects_api
from config_manager import get
from tgbot import TgBot
from zoneinfo import ZoneInfo
from .late_update_tickets import after_downtime_update
from utils import calculate_safe_interval
import asyncio


scheduler = AsyncIOScheduler()
scheduler_job = None
default_update_interval = 5
logging.getLogger("apscheduler").setLevel(logging.WARNING)

events_api = None
events_apis: list[EventsApi] = []
__need_to_refresh = False


def schedule_refresh():
    global __need_to_refresh
    __need_to_refresh = True
# sub_events_api = None


async def request_events():
    global events_api
    global events_apis
    global __need_to_refresh
    # global sub_events_api

    if events_api is None or __need_to_refresh:  # or sub_events_api is None:
        __need_to_refresh = False
        main_project_gid = await get("main_project_gid")
        listen_str = await get("listen_projects")
        # sub_project_gid = await get("sub_project_gid")

        if main_project_gid is not None:  # and sub_project_gid is not None:
            # {sub_project_gid}")
            logging.info(
                f"Основной проект: {main_project_gid}. События будут отслеживаться")
            events_api = EventsApi(asana_client, main_project_gid)
            events_api.register_sync_callback(after_downtime_update)

            # sub_events_api = EventsApi(asana_client, sub_project_gid)
        else:
            return

        if listen_str is not None:
            listen = listen_str.split(" ")
            if len(listen) > 0 and listen_str != "":
                for gid in listen:
                    if main_project_gid is not None and main_project_gid != gid:
                        events_apis.append(EventsApi(asana_client, gid))
                        logging.info(
                            f"Будут отслеживаться события проекта {gid}")

                new_interval = calculate_safe_interval(len(listen) + 1)
                logging.info(
                    F"События будут запрашиваться для {len(listen)} дополнительных проектов каждые {new_interval} секунд")
                if scheduler_job is not None:
                    scheduler_job.reschedule(
                        trigger=IntervalTrigger(seconds=new_interval))
            else:
                logging.info("Доплонительных проектов для отслеживания нет")
        else:
            logging.info(
                "Нет информации для отслеживания дополнительных проектов")

    # events = await events_api.get_events()
    # await handle_events(events)

    # for api in events_apis:
    #     events = await api.get_events()
    #     await handle_events(events)
    logging.info("Начинаю запрос событий")
    all_apis = [events_api] + events_apis

    results = await asyncio.gather(*[api.get_events() for api in all_apis])
    await asyncio.gather(*[handle_events(events) for events in results])
    logging.info("Запрос событий завершен")

    # sub_events = await sub_events_api.get_events()
    # await handle_events(sub_events)


def activate_scheduler():
    global scheduler_job
    scheduler_job = scheduler.add_job(
        request_events, 'interval', seconds=default_update_interval)
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
            await on_tag_add_ruled(e)
        elif e.is_tag_removed():
            await on_tag_remove(e)
        elif e.is_story_add():
            await on_story_add(e)


async def on_section_moved(event: Event):
    async with Database.make_session() as session:
        ticket = await Ticket.get_by_gid(session, event.resource.gid)
        saved_ticket = True
        if ticket is None:
            await on_new_task_added(event)
            ticket = await get_asana_task(event.resource.gid)
            if ticket is None:
                return
            saved_ticket = False

        assert event.parent is not None

        chats = (await session.execute(select(TelegramConfigExtended).where(TelegramConfigExtended.status_changed == True))).scalars().all()
        for chat in chats:
            if chat.additional == event.project:
                await TgBot.send_message(chat.chat_id, f"'{ticket.title}' перемещено в '{event.parent.name}'")

        if not saved_ticket:
            return

        status = Status(text=event.parent.name, ticket=ticket,
                        datetime=event.created_at_local_timezone)
        session.add(status)
        logging.info(f"Задача {ticket.title} перемещена в '{status.text}'")

        # notify = (await get("notify_status_changed")) == "1"


async def get_asana_task(gid: str):
    task_api = get_task_api()
    assert task_api is not None
    try:
        ticket_data = await task_api.get_task(gid)
    except AsanaApiError as e:
        if e.status == 404:
            logging.warning(f"Задачи gid={gid} не существует")
            logging.warning(e.body['errors'][0]['message'])
            return None

    ticket = Ticket(
        gid=ticket_data['gid'], title=ticket_data['name'], text=ticket_data['notes'], created_at=datetime.now())
    return ticket


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
        saved_ticket = True
        if ticket is None:
            logging.warning(
                f"Удалена неотслеживаемая задача задачи. gid={event.resource.gid}")
            saved_ticket = False
            # ticket = await get_asana_task(event.resource.gid)
            # if ticket is None:
            #     return
        
        chats = (await session.execute(select(TelegramConfigExtended).where(TelegramConfigExtended.deleted == True))).scalars().all()
        for chat in chats:
            if chat.additional == event.project:
                if event.resource.name != "":
                    await TgBot.send_message(chat.chat_id, f"'{event.resource.name}' удалено")
        
        if not saved_ticket or ticket is None:
            return
        
        ticket.deleted = True
        ticket.deleted_at = event.created_at_local_timezone
        session.add(ticket)

        status = Status(text='Удалено', ticket=ticket,
                        datetime=event.created_at_local_timezone)
        session.add(status)



async def on_task_undelete(event: Event):
    async with Database.make_session() as session:
        ticket = await Ticket.get_by_gid(session, event.resource.gid)
        if ticket is None:
            logging.warning(
                f"Восстановлена несущесвтующая задачи. gid={event.resource.gid}")
            return
        ticket.deleted = False
        session.add(ticket)

        status = Status(text="Удаление отменено", ticket=ticket,
                        datetime=event.created_at_local_timezone)
        session.add(status)


async def on_tag_add_ruled(event: Event):
    assert event.parent is not None
    tag = event.parent.name

    async with Database.make_session() as session:
        query = select(TagRule).where(TagRule.tag == tag)
        res = await session.execute(query)
        tag_rule = res.scalar_one_or_none()

        chats = (await session.execute(select(TelegramConfigExtended).where(TelegramConfigExtended.sub_tag_setted == True))).scalars().all()

    if tag_rule is None:
        return

    task_api = get_task_api()
    assert task_api is not None

    ticket_gid = event.resource.gid
    res = await task_api.add_to_project(ticket_gid, tag_rule.project_gid, tag_rule.section_gid)
    assert isinstance(res, dict)

    if 'data' not in res.keys():
        logging.warning(
            f"Не удалось установить задачу в проект {tag_rule.project_gid}(gid={tag_rule.project_gid}) в колонку {tag_rule.section_name}(gid={tag_rule.section_gid})")
        return

    logging.info(
        f"Задача {ticket_gid} установлена в проект {tag_rule.project_gid}(gid={tag_rule.project_gid})")

    if tag_rule.action == 1:
        # TODO: удалять из всех проектов, кроме нужного
        task_info = await task_api.get_task(ticket_gid)
        for membership in task_info['memberships']:
            if membership['project']['gid'] == tag_rule.project_gid:
                continue
            res = await task_api.remove_from_project(ticket_gid, membership['project']['gid'])
            logging.info(
                f"Задача {ticket_gid} удалена из проекта {membership['project']['gid']}")

        async with Database.make_session() as session:
            ticket = await Ticket.get_by_gid(session, ticket_gid)
            if ticket is not None:
                status_move = Status(
                    text=f"Перемещено при установке тега '{tag_rule.tag}'", ticket=ticket)
                ticket.deleted = True
                session.add(ticket)
                session.add(status_move)
                status_delete = Status(text=f"Удалено", ticket=ticket)
                session.add(status_delete)



    task_api = get_task_api()
    if task_api is not None:
        task = await task_api.get_task(ticket_gid)

    for chat in chats:
        text = f"На задачу '{task['name']}' установлен тег '{tag_rule.tag}'"
        if tag_rule.project_name is not None:
            text += f". Задача {'перемещена' if tag_rule.action == 1 else 'добавлена'} в проект '{tag_rule.project_name}'"
        if chat.additional == event.project:
            await TgBot.send_message(chat.chat_id, text)


async def on_tag_add(event: Event):
    logging.warning(
        "'on_tag_add(event: Event)' function deprecated. Now using 'on_tag_add_ruled(event: Event)'")
    return
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

    try:
        story = await projects_api.get_story(event.resource.gid)
    except AsanaApiError as e:
        if e.status == 404:
            logging.info("Добавлена история к неотслеживаемой задаче")
            return
        raise

    if story['type'] == "comment":
        async with Database.make_session() as session:
            chats = (await session.execute(select(TelegramConfigExtended).where(TelegramConfigExtended.commented == True))).scalars().all()
            for chat in chats:
                assert event.parent is not None
                ticket_gid = event.parent.gid
                ticket = await Ticket.get_by_gid(session, ticket_gid)

                if ticket is None:
                    ticket = await get_asana_task(event.parent.gid)
                    if ticket is None:
                        return
                
                if chat.additional == event.project:
                    await TgBot.send_message(chat.chat_id, f"На '{ticket.title}' добавлен комментарий '{story['text']}'")
