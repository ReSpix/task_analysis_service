from .client import AsanaClient
from database.models import Ticket
from config_manager import MAIN_PROJECT_GID
from .client import asana_client
import logging


class TaskApi:
    def __init__(self, client: AsanaClient = asana_client):
        self._client: AsanaClient = client

    async def publish_task(self, ticket: Ticket):
        url = 'tasks'

        body = {'data': {'name': ticket.title,
                         "notes": ticket.text,
                         "projects": [MAIN_PROJECT_GID]
                         }}

        res = await self._client.post(url, body)
        # logging.info(res)
        return res['data']

    async def get_task(self, gid: str):
        url = f'tasks/{gid}'

        res = await self._client.get(url)
        return res['data']