from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from dateutil.relativedelta import relativedelta
import math


def plural_ru(n, one, few, many):
    if 11 <= (n % 100) <= 14:
        return many
    elif n % 10 == 1:
        return one
    elif 2 <= n % 10 <= 4:
        return few
    else:
        return many


def format_timedelta_pretty(delta: Optional[timedelta]) -> str:
    if delta is None:
        return ""

    total_seconds = int(delta.total_seconds())

    if total_seconds < 60:
        return f"{total_seconds} " + plural_ru(total_seconds, "секунду", "секунды", "секунд")

    total_minutes = total_seconds // 60
    days = total_minutes // (24 * 60)
    hours = (total_minutes % (24 * 60)) // 60
    minutes = total_minutes % 60

    parts = []

    if days > 0:
        parts.append(f"{days} " + plural_ru(days, "день", "дня", "дней"))
    if hours > 0 or days > 0:
        parts.append(f"{hours} " + plural_ru(hours, "час", "часа", "часов"))
    if minutes > 0 or (days == 0 and hours == 0):
        parts.append(f"{minutes} " + plural_ru(minutes,
                     "минуту", "минуты", "минут"))

    return " ".join(parts)


@dataclass
class TimePeroid:
    start: datetime
    end: datetime


def create_date_period() -> TimePeroid:
    end = datetime.now()
    start = end - relativedelta(months=1)
    return TimePeroid(start=start, end=end)


def calculate_safe_interval(num_objects: int, safety_margin: float = 1.2) -> int:
    """
    Рассчитывает безопасный интервал между запросами к API.

    :param num_objects: Количество объектов, каждый из которых делает 1 запрос.
    :param safety_margin: Коэффициент запаса (по умолчанию 20%).
    :return: Минимальный интервал в секундах.
    """
    if num_objects <= 0:
        raise ValueError(
            "Количество объектов должно быть положительным числом")

    requests_per_minute_limit = 110
    base_interval = (60 * num_objects) / requests_per_minute_limit
    safe_interval = base_interval * safety_margin

    return max(math.ceil(safe_interval), 5)
