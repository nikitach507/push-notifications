"""Event handlers for the bot."""

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from src.bot.keyboards import (
    get_confirm_delete_keyboard,
    get_event_actions_keyboard,
    get_main_menu_keyboard,
    get_reminder_periods_keyboard,
)
from src.database.database import db_manager
from src.database.models import Event, Reminder, User
from src.utils.helpers import (
    calculate_reminder_time,
    format_datetime,
    format_period,
    parse_date_input,
)

router = Router()


class CreateEventStates(StatesGroup):
    """States for creating an event."""

    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_date = State()
    selecting_reminders = State()


@router.message(lambda message: message.text == "➕ Создать событие")
async def start_create_event(message: Message, state: FSMContext) -> None:
    """Start creating a new event.

    Args:
        message: Incoming message
        state: FSM context
    """
    await state.set_state(CreateEventStates.waiting_for_title)
    await message.answer(
        "📝 <b>Создание события</b>\n\n"
        "Введите название события:",
        parse_mode="HTML",
    )


@router.message(StateFilter(CreateEventStates.waiting_for_title))
async def process_event_title(message: Message, state: FSMContext) -> None:
    """Process event title.

    Args:
        message: Incoming message
        state: FSM context
    """
    await state.update_data(title=message.text)
    await state.set_state(CreateEventStates.waiting_for_description)
    await message.answer(
        "📄 Введите описание события (или отправьте \"-\" чтобы пропустить):",
    )


@router.message(StateFilter(CreateEventStates.waiting_for_description))
async def process_event_description(message: Message, state: FSMContext) -> None:
    """Process event description.

    Args:
        message: Incoming message
        state: FSM context
    """
    description = None if message.text == "-" else message.text
    await state.update_data(description=description)
    await state.set_state(CreateEventStates.waiting_for_date)
    await message.answer(
        "📅 Введите дату и время события в формате:\n"
        "<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
        "Например: <code>31.12.2025 23:59</code>",
        parse_mode="HTML",
    )


@router.message(StateFilter(CreateEventStates.waiting_for_date))
async def process_event_date(message: Message, state: FSMContext) -> None:
    """Process event date.

    Args:
        message: Incoming message
        state: FSM context
    """
    event_date = parse_date_input(message.text)

    if not event_date:
        await message.answer(
            "❌ Неверный формат даты.\n"
            "Используйте формат: <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
            "Например: <code>31.12.2025 23:59</code>",
            parse_mode="HTML",
        )
        return

    if event_date <= datetime.now():
        await message.answer(
            "❌ Дата события должна быть в будущем.\n"
            "Пожалуйста, введите корректную дату."
        )
        return

    # Save event to database
    async with db_manager.get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one()

        data = await state.get_data()
        event = Event(
            user_id=user.id,
            title=data["title"],
            description=data.get("description"),
            event_date=event_date,
        )
        session.add(event)
        await session.flush()

        # Store event_id in state
        await state.update_data(event_id=event.id, event_date=event_date)

    await state.set_state(CreateEventStates.selecting_reminders)
    await message.answer(
        f"✅ Событие создано!\n\n"
        f"📝 <b>{data['title']}</b>\n"
        f"📅 {format_datetime(event_date)}\n\n"
        f"Теперь выберите периоды напоминаний:",
        parse_mode="HTML",
        reply_markup=get_reminder_periods_keyboard(),
    )


@router.callback_query(
    StateFilter(CreateEventStates.selecting_reminders),
    F.data.startswith("reminder:"),
)
async def process_reminder_selection(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Process reminder period selection.

    Args:
        callback: Callback query
        state: FSM context
    """
    data = await state.get_data()

    if callback.data == "reminder:done":
        await state.clear()
        await callback.message.edit_text(
            "✅ Событие успешно создано с напоминаниями!",
        )
        await callback.message.answer(
            "Используйте меню для дальнейших действий:",
            reply_markup=get_main_menu_keyboard(),
        )
        await callback.answer()
        return

    # Parse callback data
    _, period_type, period_value = callback.data.split(":")
    period_value = int(period_value)

    event_date = data["event_date"]
    event_id = data["event_id"]

    # Calculate reminder time
    remind_at = calculate_reminder_time(event_date, period_type, period_value)

    if remind_at <= datetime.now():
        await callback.answer(
            "❌ Это напоминание уже в прошлом, выберите другое!",
            show_alert=True,
        )
        return

    # Save reminder to database
    async with db_manager.get_session() as session:
        reminder = Reminder(
            event_id=event_id,
            remind_at=remind_at,
        )
        session.add(reminder)
        await session.commit()

    await callback.answer(
        f"✅ Напоминание добавлено: за {format_period(period_type, period_value)}",
    )


@router.message(lambda message: message.text == "📋 Мои события")
async def show_my_events(message: Message) -> None:
    """Show user's events.

    Args:
        message: Incoming message
    """
    async with db_manager.get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one()

        # Get all user events
        result = await session.execute(
            select(Event)
            .where(Event.user_id == user.id)
            .order_by(Event.event_date)
        )
        events = result.scalars().all()

    if not events:
        await message.answer(
            "У вас пока нет событий.\n\n"
            "Создайте первое событие с помощью кнопки \"➕ Создать событие\"!",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    events_text = "📋 <b>Ваши события:</b>\n\n"
    for event in events:
        events_text += (
            f"📝 <b>{event.title}</b>\n"
            f"📅 {format_datetime(event.event_date)}\n"
            f"🆔 ID: {event.id}\n\n"
        )

    events_text += "\nОтправьте ID события, чтобы увидеть детали."

    await message.answer(events_text, parse_mode="HTML")


@router.message(F.text.isdigit())
async def show_event_details(message: Message) -> None:
    """Show event details.

    Args:
        message: Incoming message
    """
    event_id = int(message.text)

    async with db_manager.get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one()

        # Get event with reminders
        result = await session.execute(
            select(Event)
            .where(Event.id == event_id, Event.user_id == user.id)
        )
        event = result.scalar_one_or_none()

    if not event:
        await message.answer("❌ Событие не найдено.")
        return

    # Get reminders
    async with db_manager.get_session() as session:
        result = await session.execute(
            select(Reminder)
            .where(Reminder.event_id == event.id)
            .order_by(Reminder.remind_at)
        )
        reminders = result.scalars().all()

    event_text = (
        f"📝 <b>{event.title}</b>\n\n"
        f"📅 Дата: {format_datetime(event.event_date)}\n"
    )

    if event.description:
        event_text += f"📄 Описание: {event.description}\n"

    if reminders:
        event_text += "\n🔔 <b>Напоминания:</b>\n"
        for reminder in reminders:
            status = "✅" if reminder.is_sent else "⏳"
            event_text += f"{status} {format_datetime(reminder.remind_at)}\n"
    else:
        event_text += "\n🔔 Напоминаний нет"

    await message.answer(
        event_text,
        parse_mode="HTML",
        reply_markup=get_event_actions_keyboard(event.id),
    )


@router.callback_query(F.data.startswith("event:delete:"))
async def confirm_delete_event(callback: CallbackQuery) -> None:
    """Confirm event deletion.

    Args:
        callback: Callback query
    """
    event_id = int(callback.data.split(":")[-1])

    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите удалить это событие?\n"
        "Все напоминания тоже будут удалены.",
        reply_markup=get_confirm_delete_keyboard(event_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("event:confirm_delete:"))
async def delete_event(callback: CallbackQuery) -> None:
    """Delete event.

    Args:
        callback: Callback query
    """
    event_id = int(callback.data.split(":")[-1])

    async with db_manager.get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one()

        result = await session.execute(
            select(Event)
            .where(Event.id == event_id, Event.user_id == user.id)
        )
        event = result.scalar_one_or_none()

        if event:
            await session.delete(event)
            await session.commit()

    await callback.message.edit_text("✅ Событие успешно удалено!")
    await callback.answer()


@router.callback_query(F.data.startswith("event:cancel_delete:"))
async def cancel_delete_event(callback: CallbackQuery) -> None:
    """Cancel event deletion.

    Args:
        callback: Callback query
    """
    await callback.message.edit_text("❌ Удаление отменено.")
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel current action.

    Args:
        callback: Callback query
        state: FSM context
    """
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")
    await callback.answer()
