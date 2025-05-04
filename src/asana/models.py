from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional


class Resource(BaseModel):
    gid: str
    type: str = Field(alias="resource_type")


class ActionType(str, Enum):
    CHANGED = "changed"
    ADDED = "added"
    REMOVED = "removed"
    DELETED = "deleted"
    UNDELETED = "undeleted"
    MOVED = 'moved'


class Event(BaseModel):
    action: ActionType
    created_at: datetime
    resource: Resource
    parent: Optional[Resource]
