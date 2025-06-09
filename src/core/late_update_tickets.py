import logging
from database import Database
from database.models import Ticket, Status
from sqlalchemy import not_, select
from asana import get_projects_api
from config_manager import get

async def after_downtime_update():
    logging.info("Синхронизация статусов задач")

    main_project_gid = await get("main_project_gid")
    if main_project_gid is None:
        return

    projects_api = get_projects_api()
    if projects_api is None:
        return
    
    tasks = await projects_api.get_tasks(main_project_gid)

    assert isinstance(tasks, list)
    async with Database.make_session() as session:
        for task in tasks:
            query = select(Ticket).where(Ticket.gid == task['gid'])
            res = await session.execute(query)
            task_db = res.scalars().one_or_none()

            if task_db is None:
                continue

            assert isinstance(task, dict)
            logging.info(task)
            if task_db.last_status is None:
                return
            
            if task['memberships'][0]['section']['name'] != task_db.last_status.text:
                status = Status(text=task['memberships'][0]['section']['name'], ticket=task_db)
                session.add(status)