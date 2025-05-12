from typing import List

from ..models import Event
from ..client import AsanaClient, AsanaApiError
from .events_parser import parse_events, clear_events
import logging
from config_manager import get_sync_token, save_sync_token


class EventsApi:
    def __init__(self, client: AsanaClient):
        self._client: AsanaClient = client
        self.sync: str = ""

    async def get_events(self, resource: str = "") -> List[Event]:
        if self.sync == "":
            self.sync = await get_sync_token()
        if resource == "":
            resource = self._client.main_project_gid

        params = {'sync': self.sync, "resource": resource}
        url = f"events"
        try:
            data = await self._client.get(url, params)
            await self._update_sync_token(data)
        except AsanaApiError as e:
            if e.status == 412:
                await self._update_sync_token(e.body)
                logging.info("Sync token missing or expired. Fetched new")
                return []
            else:
                raise

        events = parse_events(data)
        return clear_events(events)

    async def _update_sync_token(self, source: dict):
        if 'sync' not in source:
            raise ValueError("Update_sync_token source mush have 'sync' key")
        self.sync = source['sync']
        await save_sync_token(self.sync)