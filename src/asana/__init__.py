from .client import AsanaClient, asana_client
from .events import EventsApi
from .tasks import TaskApi
from .projects import ProjectsApi
import config_manager

# asana_client = AsanaClient(
    # config_manager.TOKEN, config_manager.MAIN_PROJECT_GID)
events_api = EventsApi(asana_client)
task_api = TaskApi(asana_client)
projects_api = ProjectsApi(asana_client)