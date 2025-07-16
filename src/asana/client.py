import functools
import logging
from typing import Callable
import aiohttp
import config_manager


class AsanaApiError(Exception):
    def __init__(self, status: int, body: dict):
        self.status = status
        self.body = body
        super().__init__(f"Asana API Error {status}: {body}")

    def __str__(self):
        return f"""
Код: {self.status}
Описание: {self.body}
"""


class AsanaClient:
    base_url = "https://app.asana.com/api/1.0/"

    async def _check_token(self, token, params={}):
        async with aiohttp.ClientSession() as session:
            headers = {"authorization": f"Bearer {token}"}
            async with session.get(self.base_url + 'workspaces', headers=headers, params=params) as response:
                data = await response.json()
                if response.status != 200:
                    raise AsanaApiError(response.status, data)
                return data

    def get_token(self):
        return self.token

    async def set_token(self, new_token) -> bool:
        try:
            await self._check_token(new_token)
            self.token = new_token
            await config_manager.set("token", new_token)
            return True
        except AsanaApiError as e:
            if e.status == 401:
                logging.info(
                    "Введен неверный токен, отмена сохранения нового токена")
                return False
            else:
                raise

    def set_main_project_gid(self, gid: str) -> None:
        self.main_project_gid = gid

    def __init__(self, token: str = "", main_project_gid: str = ""):
        self.token = token
        self.main_project_gid = main_project_gid
        self.base_url = self.__class__.base_url

    async def get(self, url, params={}, timeout: aiohttp.ClientTimeout|None=None):
        async with aiohttp.ClientSession(timeout=timeout) as session:
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


asana_client = AsanaClient()


async def try_init():
    global asana_client

    token = await config_manager.get("token")
    main_project_gid = await config_manager.get("main_project_gid")

    if token is None:
        logging.info(
            "Не удалось инициализировать API клиент Asana - отсутствует токен")
        return False

    await asana_client.set_token(token)

    if main_project_gid is None:
        logging.info(
            "API клиент Asana инициализирован частично - отсутствует GID основного проекта")
        return False

    asana_client.set_main_project_gid(main_project_gid)
    logging.info("API клиент Asana успешно инициализирован")
    return True
