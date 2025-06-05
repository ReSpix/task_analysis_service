from .client import AsanaClient
from database.models import Ticket
from .client import asana_client
import logging
from config_manager import get


class TaskApi:
    def __init__(self, client: AsanaClient = asana_client):
        self._client: AsanaClient = client

    async def publish_task(self, ticket: Ticket, section: str | None):
        url = 'tasks'

        body = {'data': {'name': ticket.title,
                         "notes": ticket.text,
                         "projects": [asana_client.main_project_gid],
                         }}

        if section is not None:
            body['data']['memberships'] = [
                {
                    "project": asana_client.main_project_gid,
                    "section": section
                }
            ]

        res = await self._client.post(url, body)
        # logging.info(res)
        return res['data']

    async def get_task(self, gid: str):
        url = f'tasks/{gid}'

        res = await self._client.get(url)
        return res['data']

    async def add_to_project(self, task_gid: str, project_gid: str):
        url = f'tasks/{task_gid}/addProject'

        body = {'data': {'project': project_gid}}

        section = await get("sub_section")
        if section is not None:
            body['data']['section'] = section

        res = await self._client.post(url, body)
        return res

    async def remove_from_project(self, task_gid: str, project_gid: str):
        url = f'tasks/{task_gid}/removeProject'

        body = {'data': {'project': project_gid}}

        res = await self._client.post(url, body)
        return res
