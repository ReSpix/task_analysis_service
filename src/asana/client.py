import logging
import aiohttp
import config_manager

class AsanaApiError(Exception):
    def __init__(self, status: int, body: dict):
        self.status = status
        self.body = body
        super().__init__(f"Asana API Error {status}: {body}")


class AsanaClient:
    def __init__(self, token: str, main_project_gid: str):
        self.token = token
        self.main_project_gid = main_project_gid
        self.base_url = "https://app.asana.com/api/1.0/"

    async def get(self, url, params={}):
        async with aiohttp.ClientSession() as session:
            headers = {"authorization": f"Bearer {self.token}"}
            async with session.get(self.base_url + url, headers=headers, params=params) as response:
                data = await response.json()
                if response.status != 200:
                    raise AsanaApiError(response.status, data)
                return data
            
    async def post(self, url, body, params={}):
        async with aiohttp.ClientSession() as session:
            headers = {"authorization": f"Bearer {self.token}"}
            async with session.post(self.base_url + url, headers=headers, params=params, json=body) as response:
                data = await response.json()
                return data


    async def workspaces(self):
        data = await self.get("workspaces")
        return data

asana_client = AsanaClient(config_manager.TOKEN, config_manager.MAIN_PROJECT_GID)