from .client import AsanaClient, AsanaApiError
import logging


class EventsApi:
    def __init__(self, client: AsanaClient):
        self._client: AsanaClient = client
        self.sync: str = ""

    async def get_events(self, resource: str = ""):
        if resource == "":
            resource = self._client.main_project_gid

        params = {'sync': self.sync, "resource": resource}
        url = f"events"
        try:
            data = await self._client.get(url, params)
            self._update_sync_token(data)
        except AsanaApiError as e:
            if e.status == 412:
                self._update_sync_token(e.body)
                data = e.body
                logging.info("Sync token missing or expired. Fetched new")
            else:
                raise

        return data

    def _update_sync_token(self, source: dict):
        if 'sync' not in source:
            raise ValueError("Update_sync_token source mush have 'sync' key")
        self.sync = source['sync']