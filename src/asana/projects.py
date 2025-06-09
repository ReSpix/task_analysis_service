import logging
from .client import asana_client, AsanaClient, AsanaApiError


class ProjectsApi:
    def __init__(self, client: AsanaClient = asana_client):
        self._client: AsanaClient = client

    async def get_projects(self):
        url = 'projects'
        res = await self._client.get(url)
        return res['data']

    async def is_project(self, gid):
        url = "projects/" + gid
        try:
            res = await self._client.get(url)
        except AsanaApiError as e:
            if e.status == 400:
                return False
        return True

    async def get_sections(self, project_gid):
        url = "projects/" + project_gid + "/sections"

        res = await self._client.get(url)
        return res['data']

    async def get_tags(self):
        url = "tags"

        res = await self._client.get(url)
        return res['data']

    async def get_story(self, story_gid: str):
        url = f"stories/{story_gid}"

        res = await self._client.get(url)
        return res['data']
    
    async def get_tasks(self, project_gid):
        url = "projects/" + project_gid + "/tasks"

        opt_fields = {"opt_fields": ["memberships.section.name"]}

        res = await self._client.get(url, opt_fields)
        return res['data']