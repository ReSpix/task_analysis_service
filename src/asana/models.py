from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional


class Resource(BaseModel):
    gid: str
    type: str = Field(alias="resource_type")
    name: Optional[str] = ""


class ActionType(str, Enum):
    CHANGED = "changed"
    ADDED = "added"
    REMOVED = "removed"
    DELETED = "deleted"
    UNDELETED = "undeleted"
    MOVED = 'moved'


class Change(BaseModel):
    action: ActionType
    field: str


class Event(BaseModel):
    action: ActionType
    created_at: datetime
    resource: Resource
    parent: Optional[Resource] = None
    change: Optional[Change] = None
    project: Optional[str] = ""

    @property
    def created_at_local_timezone(self):
        return self.created_at.astimezone(datetime.now().astimezone().tzinfo)

    def is_status_change_event(self) -> bool:
        return \
            self.action == ActionType.MOVED \
            and self.parent is not None \
            and self.parent.type == 'section' \
            and self.resource.type == 'task'

    def is_new_task_added(self) -> bool:
        return \
            self.action == ActionType.ADDED \
            and self.parent is not None \
            and self.parent.type == 'project' \
            and self.resource.type == 'task'

    def is_field_change(self) -> bool:
        return \
            self.action == ActionType.CHANGED \
            and self.change is not None \
            and self.change.action == ActionType.CHANGED \
            and self.change.field in ["notes", "name", "completed"] \
            and self.resource.type == 'task'

    def is_deleted_task(self) -> bool:
        return \
            self.action == ActionType.DELETED \
            and self.resource.type == 'task'

    def is_undeleted_task(self) -> bool:
        return \
            self.action == ActionType.UNDELETED \
            and self.resource.type == 'task'

    def is_tag_add(self) -> bool:
        return \
            self.action == ActionType.ADDED \
            and self.resource.type == 'task' \
            and self.parent is not None \
            and self.parent.type == 'tag'

    def is_tag_removed(self) -> bool:
        return \
            self.action == ActionType.REMOVED \
            and self.resource.type == 'task' \
            and self.parent is not None \
            and self.parent.type == 'tag'

    def is_removed_from_project(self) -> bool:
        return \
            self.action == ActionType.REMOVED \
            and self.resource.type == 'task' \
            and self.parent is not None \
            and self.parent.type == 'project'

    def is_story_add(self) -> bool:
        return \
            self.action == ActionType.ADDED \
            and self.resource.type == 'story' \
            and self.parent is not None \
            and self.parent.type == 'task'
