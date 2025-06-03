from datetime import timedelta
from typing import Optional


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
