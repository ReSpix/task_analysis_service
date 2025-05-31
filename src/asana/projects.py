from .client import asana_client, AsanaClient

class ProjectsApi:
    def __init__(self, client: AsanaClient = asana_client):
        self._client: AsanaClient = client

    async def get_projects(self):
        url = 'projects'
        res = await self._client.get(url)
        return res['data']
