from collections import defaultdict
from copy import deepcopy
from typing import Dict, List
import logging
from operator import attrgetter

from ..models import Event, ActionType


def parse_events(data: dict | List[dict]):
    if isinstance(data, dict) and 'data' in data.keys():
        data = data['data']

    try:
        return [Event(**data) for data in data]
    except TypeError:
        logging.info("Unknown type for parse_events")
        return []


def clear_events(events: List[Event]):
    events_tasks: Dict[str, List[Event]] = defaultdict(list)
    events = deepcopy(events)
    for event in events:
        if event.resource.type == 'task':
            events_tasks[event.resource.gid].append(event)

    to_remove = []
    for key in events_tasks:
        event_list = sorted(events_tasks[key], key=attrgetter('created_at'))
        for e1, e2 in zip(event_list, event_list[1:]):
            if e1.action == ActionType.ADDED and e2.action == ActionType.REMOVED:
                to_remove.append(e2)
                e1.action = ActionType.MOVED

    return [event for event in events if event not in to_remove]
