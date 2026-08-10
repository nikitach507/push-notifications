"""Helper utilities for the bot."""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def parse_date_input(date_str: str) -> datetime | None:
    """Parse date input from user.

    Supports formats:
    - DD.MM.YYYY HH:MM
    - DD/MM/YYYY HH:MM
    - DD-MM-YYYY HH:MM

    Args:
        date_str: Date string from user

    Returns:
        datetime | None: Parsed datetime or None if invalid
    """
    # Clean up the input
    date_str = date_str.strip()

    # Try different formats
    formats = [
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})",
        r"(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})",
        r"(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})",
    ]

    for fmt in formats:
        match = re.match(fmt, date_str)
        if match:
            day, month, year, hour, minute = map(int, match.groups())
            try:
                return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo("Europe/Prague"))
            except ValueError:
                return None

    return None


def calculate_reminder_time(event_date: datetime, period_type: str, period_value: int) -> datetime:
    """Calculate reminder time based on period.

    Args:
        event_date: Event date
        period_type: Type of period (week, days, hours)
        period_value: Value of period

    Returns:
        datetime: Reminder datetime
    """
    if period_type == "week":
        return event_date - timedelta(weeks=period_value)
    elif period_type == "days":
        return event_date - timedelta(days=period_value)
    elif period_type == "hours":
        return event_date - timedelta(hours=period_value)
    else:
        raise ValueError(f"Unknown period type: {period_type}")


def format_datetime(dt: datetime) -> str:
    """Format datetime for display.

    Args:
        dt: Datetime to format

    Returns:
        str: Formatted datetime string
    """
    # Ensure datetime is timezone-aware
    if dt.tzinfo is None:
        # If naive, assume it's UTC
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    # Convert to Prague timezone
    prague_tz = ZoneInfo("Europe/Prague")
    dt_prague = dt.astimezone(prague_tz)

    return dt_prague.strftime("%d.%m.%Y %H:%M")


def format_period(period_type: str, period_value: int) -> str:
    """Format period for display.

    Args:
        period_type: Type of period (week, days, hours)
        period_value: Value of period

    Returns:
        str: Formatted period string
    """
    if period_type == "week":
        return f"{period_value} нед."
    elif period_type == "days":
        if period_value == 1:
            return "1 день"
        elif period_value in [2, 3, 4]:
            return f"{period_value} дня"
        else:
            return f"{period_value} дней"
    elif period_type == "hours":
        if period_value == 1:
            return "1 час"
        elif period_value in [2, 3, 4]:
            return f"{period_value} часа"
        else:
            return f"{period_value} часов"
    else:
        return f"{period_value} {period_type}"


def format_time_remaining(event_date: datetime) -> str:
    """Format time remaining until event.

    Args:
        event_date: Event datetime

    Returns:
        str: Formatted string like "Осталось 7 дней" or "Осталось 2 часа"
    """
    now = datetime.now(ZoneInfo("Europe/Prague"))
    diff = event_date - now

    if diff.total_seconds() < 0:
        return "Событие прошло"

    # Вычисляем компоненты времени
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60

    if days > 0:
        if days == 1:
            return "Осталось 1 день"
        elif days in [2, 3, 4]:
            return f"Осталось {days} дня"
        elif days in range(5, 21) or days % 10 in [0, 5, 6, 7, 8, 9]:
            return f"Осталось {days} дней"
        elif days % 10 == 1:
            return f"Осталось {days} день"
        elif days % 10 in [2, 3, 4]:
            return f"Осталось {days} дня"
        else:
            return f"Осталось {days} дней"
    elif hours > 0:
        if hours == 1:
            return "Осталось 1 час"
        elif hours in [2, 3, 4]:
            return f"Осталось {hours} часа"
        else:
            return f"Осталось {hours} часов"
    elif minutes > 0:
        if minutes == 1:
            return "Осталось 1 минута"
        elif minutes in [2, 3, 4]:
            return f"Осталось {minutes} минуты"
        else:
            return f"Осталось {minutes} минут"
    else:
        return "Событие наступает прямо сейчас"
