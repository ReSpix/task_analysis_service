from typing import Optional
from .client import AsanaClient, try_init, asana_client
from .events import EventsApi
from .tasks import TaskApi
from .projects import ProjectsApi
import config_manager
import logging

# asana_client = AsanaClient(
    # config_manager.TOKEN, config_manager.MAIN_PROJECT_GID)
# events_api = EventsApi(asana_client)

_task_api: Optional[TaskApi] = None
_projects_api: Optional[ProjectsApi] = None


def get_task_api() -> Optional[TaskApi]:
    return _task_api

def get_projects_api() -> Optional[ProjectsApi]:
    return _projects_api

async def try_create_apis():
    global asana_client
    global _task_api
    global _projects_api

    init_res = await try_init()

    if not init_res:
        return
    
    _task_api = TaskApi(asana_client)
    _projects_api = ProjectsApi(asana_client)
    logging.info("Дополнительные части API Asana успешно инициализированы")