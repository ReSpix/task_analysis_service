from .client import AsanaClient


class TaskApi:
    def __init__(self, client: AsanaClient):
        self._client: AsanaClient = client
    
    async def publish_task():
        pass
        