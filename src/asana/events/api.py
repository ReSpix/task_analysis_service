from typing import List

from ..models import Event
from ..client import AsanaClient, AsanaApiError
from .events_parser import parse_events, clear_events
import logging
from config_manager import get, set


class EventsApi:
    def __init__(self, client: AsanaClient, resource: str):
        self._client: AsanaClient = client
        self.sync: str = ""
        self.resource = resource

    def _get_sync_key(self) -> str:
        return self.resource + "_sync"

    def get_resource(self) -> str:
        return self.resource

    async def get_events(self) -> List[Event]:
        if self.sync == "":
            sync = await get(self._get_sync_key())
            if sync is not None:
                self.sync = sync
        all_events = []
        original_sync = self.sync
        while True:
            params = {'sync': original_sync, "resource": self.resource}
            url = f"events"
            try:
                data = await self._client.get(url, params)
            except AsanaApiError as e:
                if e.status == 412:
                    await self._update_sync_token(e.body)
                    logging.info("Sync token missing or expired. Fetched new")
                    return []
                else:
                    raise

            events = parse_events(data)
            all_events.extend(clear_events(events))

            if data['has_more']:
                continue
            else:
                await self._update_sync_token(data)
                break
        
        if len(all_events) > 0:
            logging.info(f"Получено {len(all_events)} событий с ресурса {self.resource}")
        return all_events

    async def _update_sync_token(self, source: dict):
        if 'sync' not in source:
            raise ValueError("Update_sync_token source must have 'sync' key")
        self.sync = source['sync']
        await set(self._get_sync_key(), self.sync)
