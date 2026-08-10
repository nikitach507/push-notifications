"""Keyboard layouts for the bot."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Get main menu keyboard.

    Returns:
        ReplyKeyboardMarkup: Main menu keyboard
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Создать событие")],
            [KeyboardButton(text="📋 Мои события")],
            [KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_reminder_periods_keyboard() -> InlineKeyboardMarkup:
    """Get reminder periods selection keyboard (3x3 grid).

    Returns:
        InlineKeyboardMarkup: Reminder periods keyboard
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            # Первая строка: 30д, 14д, 7д
            [
                InlineKeyboardButton(text="30д", callback_data="reminder:days:30"),
                InlineKeyboardButton(text="14д", callback_data="reminder:days:14"),
                InlineKeyboardButton(text="7д", callback_data="reminder:days:7"),
            ],
            # Вторая строка: 5д, 2д, 1д
            [
                InlineKeyboardButton(text="5д", callback_data="reminder:days:5"),
                InlineKeyboardButton(text="2д", callback_data="reminder:days:2"),
                InlineKeyboardButton(text="1д", callback_data="reminder:days:1"),
            ],
            # Третья строка: 12ч, 3ч, 1ч
            [
                InlineKeyboardButton(text="12ч", callback_data="reminder:hours:12"),
                InlineKeyboardButton(text="3ч", callback_data="reminder:hours:3"),
                InlineKeyboardButton(text="1ч", callback_data="reminder:hours:1"),
            ],
            # Кнопка завершения
            [
                InlineKeyboardButton(
                    text="✅ Завершить выбор", callback_data="reminder:done"
                ),
            ],
        ]
    )
    return keyboard


def get_event_actions_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Get event actions keyboard.

    Args:
        event_id: Event ID

    Returns:
        InlineKeyboardMarkup: Event actions keyboard
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Редактировать", callback_data=f"event:edit:{event_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить", callback_data=f"event:delete:{event_id}"
                ),
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="events:list"),
            ],
        ]
    )
    return keyboard


def get_confirm_delete_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Get confirmation keyboard for event deletion.

    Args:
        event_id: Event ID

    Returns:
        InlineKeyboardMarkup: Confirmation keyboard
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить", callback_data=f"event:confirm_delete:{event_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data=f"event:cancel_delete:{event_id}"
                ),
            ],
        ]
    )
    return keyboard


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Get cancel keyboard.

    Returns:
        InlineKeyboardMarkup: Cancel keyboard
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
            ],
        ]
    )
    return keyboard


def get_reminder_action_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Get reminder action keyboard with Done and Acknowledge buttons.

    Args:
        event_id: Event ID

    Returns:
        InlineKeyboardMarkup: Reminder action keyboard
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Выполнено", callback_data=f"reminder_action:done:{event_id}"
                ),
                InlineKeyboardButton(
                    text="👌 Ack", callback_data=f"reminder_action:ack:{event_id}"
                ),
            ],
        ]
    )
    return keyboard


def get_edit_field_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Get edit field selection keyboard.

    Args:
        event_id: Event ID

    Returns:
        InlineKeyboardMarkup: Edit field selection keyboard
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Название", callback_data=f"edit:title:{event_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📄 Описание", callback_data=f"edit:description:{event_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📅 Дата", callback_data=f"edit:date:{event_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔔 Напоминания", callback_data=f"edit:reminders:{event_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data=f"edit:cancel:{event_id}"
                ),
            ],
        ]
    )
    return keyboard
