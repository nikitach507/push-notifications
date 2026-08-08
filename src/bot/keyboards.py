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
    """Get reminder periods selection keyboard.

    Returns:
        InlineKeyboardMarkup: Reminder periods keyboard
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔔 За 1 неделю", callback_data="reminder:week:1"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔔 За 3 дня", callback_data="reminder:days:3"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔔 За 2 дня", callback_data="reminder:days:2"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔔 За 1 день", callback_data="reminder:days:1"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔔 За 12 часов", callback_data="reminder:hours:12"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔔 За 2 часа", callback_data="reminder:hours:2"
                ),
            ],
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
