from collections import defaultdict
from copy import deepcopy
from typing import Dict, List
import logging
from operator import attrgetter
from pydantic import ValidationError

from ..models import Event, ActionType


def parse_events(data: dict | List[dict]):
    if isinstance(data, dict) and 'data' in data.keys():
        data = data['data']

    try:
        return generate_event_list(data)
    except TypeError:
        logging.info("Unknown type for parse_events")
        return []


def generate_event_list(data):
    events = []
    for d in data:
        try:
            events.append(Event(**d))
        except ValidationError as e:
            logging.error(f"Ошибка валидации: {e}")
            logging.error(d)
            logging.error("")

    return events


def clear_add_remove_pairs(events: List[Event]) -> List[Event]:
    events_tasks: Dict[str, List[Event]] = defaultdict(list)
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


def clear_many_change(events: List[Event]) -> List[Event]:
    events_tasks: Dict[str, List[Event]] = defaultdict(list)
    for event in events:
        if event.is_field_change():
            events_tasks[event.resource.gid].append(event)

    for key in events_tasks:
        e_list = events_tasks[key]
        for e in e_list:
            events.remove(e)
        events.append(e_list[-1])

    return events


def clear_events(events: List[Event]) -> List[Event]:
    _events = deepcopy(events)
    _events = clear_add_remove_pairs(_events)
    _events = clear_many_change(_events)
    return _events
