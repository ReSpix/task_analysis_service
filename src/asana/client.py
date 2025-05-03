import aiohttp


class AsanaClient:
    def __init__(self, token: str, main_project_gid: str):
        self.token = token
        self.main_project_gid = main_project_gid
        self.base_url = "https://app.asana.com/api/1.0/"

    async def get(self, url, params={}):
        async with aiohttp.ClientSession() as session:
            headers = {"authorization": f"Bearer {self.token}"}
            async with session.get(self.base_url + url, headers=headers, params=params) as response:
                return await response.json()

    async def workspaces(self):
        data = await self.get("workspaces")
        return data
