from .client import AsanaClient
from .events import EventsApi
from .tasks import TaskApi
import config_manager

asana_client = AsanaClient(
    config_manager.TOKEN, config_manager.MAIN_PROJECT_GID)
events_api = EventsApi(asana_client)
task_api = TaskApi(asana_client)