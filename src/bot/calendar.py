"""Inline calendar for date selection."""

import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_calendar_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    """Generate inline calendar keyboard for a specific month.

    Args:
        year: Year
        month: Month (1-12)

    Returns:
        InlineKeyboardMarkup: Calendar keyboard
    """
    # Month and year header
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]

    keyboard = []

    # Header with month and year
    keyboard.append([
        InlineKeyboardButton(
            text=f"{month_names[month - 1]} {year}",
            callback_data="calendar:ignore"
        )
    ])

    # Days of week header
    days_header = []
    for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
        days_header.append(
            InlineKeyboardButton(text=day, callback_data="calendar:ignore")
        )
    keyboard.append(days_header)

    # Get calendar for the month
    cal = calendar.monthcalendar(year, month)

    # Add day buttons
    for week in cal:
        week_buttons = []
        for day in week:
            if day == 0:
                # Empty cell
                week_buttons.append(
                    InlineKeyboardButton(text=" ", callback_data="calendar:ignore")
                )
            else:
                # Day button
                week_buttons.append(
                    InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"calendar:day:{year}:{month}:{day}"
                    )
                )
        keyboard.append(week_buttons)

    # Navigation buttons
    nav_buttons = []

    # Previous month
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1

    nav_buttons.append(
        InlineKeyboardButton(
            text="◀️",
            callback_data=f"calendar:nav:{prev_year}:{prev_month}"
        )
    )

    # Today button
    nav_buttons.append(
        InlineKeyboardButton(
            text="Сегодня",
            callback_data="calendar:today"
        )
    )

    # Next month
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1

    nav_buttons.append(
        InlineKeyboardButton(
            text="▶️",
            callback_data=f"calendar:nav:{next_year}:{next_month}"
        )
    )

    keyboard.append(nav_buttons)

    # Cancel button
    keyboard.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="calendar:cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_time_keyboard(selected_date: datetime) -> InlineKeyboardMarkup:
    """Generate inline keyboard for time selection.

    Args:
        selected_date: Selected date

    Returns:
        InlineKeyboardMarkup: Time selection keyboard
    """
    keyboard = []

    # Header
    keyboard.append([
        InlineKeyboardButton(
            text=f"Выберите время для {selected_date.strftime('%d.%m.%Y')}",
            callback_data="calendar:ignore"
        )
    ])

    # Time options in 4x6 grid (00:00 to 23:00)
    hours = list(range(24))
    for i in range(0, 24, 4):
        row = []
        for hour in hours[i:i+4]:
            row.append(
                InlineKeyboardButton(
                    text=f"{hour:02d}:00",
                    callback_data=f"calendar:time:{selected_date.year}:{selected_date.month}:{selected_date.day}:{hour}:00"
                )
            )
        keyboard.append(row)

    # Back and cancel buttons
    keyboard.append([
        InlineKeyboardButton(
            text="◀️ Назад к календарю",
            callback_data=f"calendar:nav:{selected_date.year}:{selected_date.month}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="calendar:cancel"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
