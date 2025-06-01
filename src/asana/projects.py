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
