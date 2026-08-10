"""Event handlers for the bot."""

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from src.bot.calendar import get_calendar_keyboard, get_time_keyboard
from src.bot.keyboards import (
    get_confirm_delete_keyboard,
    get_edit_field_keyboard,
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


class EditEventStates(StatesGroup):
    """States for editing an event."""

    choosing_field = State()
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

    # Show calendar for current month
    now = datetime.now(ZoneInfo("Europe/Prague"))
    await message.answer(
        "📅 Выберите дату события:",
        reply_markup=get_calendar_keyboard(now.year, now.month),
    )


# Old text-based date handler removed - now using calendar only


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

    if remind_at <= datetime.now(ZoneInfo("Europe/Prague")):
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


@router.callback_query(F.data.startswith("reminder_action:done:"))
async def reminder_action_done(callback: CallbackQuery) -> None:
    """Handle 'Done' action from reminder - delete the event.

    Args:
        callback: Callback query
    """
    event_id = int(callback.data.split(":")[-1])

    async with db_manager.get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        result = await session.execute(
            select(Event).where(Event.id == event_id, Event.user_id == user.id)
        )
        event = result.scalar_one_or_none()

        if event:
            event_title = event.title
            await session.delete(event)
            await session.commit()

            await callback.message.edit_text(
                f"✅ Событие <b>{event_title}</b> отмечено как выполненное и удалено!",
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text("❌ Событие не найдено.")

    await callback.answer()


@router.callback_query(F.data.startswith("reminder_action:ack:"))
async def reminder_action_ack(callback: CallbackQuery) -> None:
    """Handle 'Acknowledge' action from reminder.

    Args:
        callback: Callback query
    """
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("👌 Принято к сведению!", show_alert=False)


@router.callback_query(F.data == "events:list")
async def show_events_list(callback: CallbackQuery) -> None:
    """Show list of events when Back button is clicked.

    Args:
        callback: Callback query
    """
    async with db_manager.get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
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
        await callback.message.edit_text(
            "У вас пока нет событий.\n\n"
            "Создайте первое событие с помощью кнопки \"➕ Создать событие\"!"
        )
        await callback.answer()
        return

    events_text = "📋 <b>Ваши события:</b>\n\n"
    for event in events:
        events_text += (
            f"📝 <b>{event.title}</b>\n"
            f"📅 {format_datetime(event.event_date)}\n"
            f"🆔 ID: {event.id}\n\n"
        )

    events_text += "\nОтправьте ID события, чтобы увидеть детали."

    await callback.message.edit_text(events_text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("event:edit:"))
async def start_edit_event(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing an event - show menu of fields to edit.

    Args:
        callback: Callback query
        state: FSM context
    """
    event_id = int(callback.data.split(":")[-1])

    async with db_manager.get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one()

        result = await session.execute(
            select(Event).where(Event.id == event_id, Event.user_id == user.id)
        )
        event = result.scalar_one_or_none()

    if not event:
        await callback.answer("❌ Событие не найдено")
        return

    # Store event ID in state
    await state.update_data(event_id=event.id)
    await state.set_state(EditEventStates.choosing_field)

    await callback.message.edit_text(
        "📝 <b>Редактирование события</b>\n\n"
        "Что вы хотите изменить?",
        parse_mode="HTML",
        reply_markup=get_edit_field_keyboard(event.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit:title:"))
async def edit_field_title(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing event title.

    Args:
        callback: Callback query
        state: FSM context
    """
    event_id = int(callback.data.split(":")[-1])

    async with db_manager.get_session() as session:
        result = await session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()

    if not event:
        await callback.answer("❌ Событие не найдено")
        return

    await state.update_data(event_id=event_id)
    await state.set_state(EditEventStates.waiting_for_title)

    await callback.message.edit_text(
        f"📝 <b>Изменение названия</b>\n\n"
        f"Текущее название: <b>{event.title}</b>\n\n"
        f"Введите новое название:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StateFilter(EditEventStates.waiting_for_title))
async def process_edit_title(message: Message, state: FSMContext) -> None:
    """Process edited event title.

    Args:
        message: Incoming message
        state: FSM context
    """
    data = await state.get_data()
    event_id = data["event_id"]

    async with db_manager.get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one()

        result = await session.execute(
            select(Event).where(Event.id == event_id, Event.user_id == user.id)
        )
        event = result.scalar_one_or_none()

        if event:
            event.title = message.text
            await session.commit()

            await message.answer(
                f"✅ Название обновлено!\n\n"
                f"📝 <b>{event.title}</b>",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard(),
            )
        else:
            await message.answer("❌ Событие не найдено.")

    await state.clear()


@router.callback_query(F.data.startswith("edit:description:"))
async def edit_field_description(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing event description.

    Args:
        callback: Callback query
        state: FSM context
    """
    event_id = int(callback.data.split(":")[-1])

    async with db_manager.get_session() as session:
        result = await session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()

    if not event:
        await callback.answer("❌ Событие не найдено")
        return

    await state.update_data(event_id=event_id)
    await state.set_state(EditEventStates.waiting_for_description)

    old_desc = event.description if event.description else "(не указано)"
    await callback.message.edit_text(
        f"📄 <b>Изменение описания</b>\n\n"
        f"Текущее описание: {old_desc}\n\n"
        f"Введите новое описание:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(StateFilter(EditEventStates.waiting_for_description))
async def process_edit_description(message: Message, state: FSMContext) -> None:
    """Process edited event description.

    Args:
        message: Incoming message
        state: FSM context
    """
    data = await state.get_data()
    event_id = data["event_id"]

    async with db_manager.get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one()

        result = await session.execute(
            select(Event).where(Event.id == event_id, Event.user_id == user.id)
        )
        event = result.scalar_one_or_none()

        if event:
            event.description = message.text
            await session.commit()

            await message.answer(
                f"✅ Описание обновлено!",
                reply_markup=get_main_menu_keyboard(),
            )
        else:
            await message.answer("❌ Событие не найдено.")

    await state.clear()


@router.callback_query(F.data.startswith("edit:date:"))
async def edit_field_date(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing event date.

    Args:
        callback: Callback query
        state: FSM context
    """
    event_id = int(callback.data.split(":")[-1])

    async with db_manager.get_session() as session:
        result = await session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()

    if not event:
        await callback.answer("❌ Событие не найдено")
        return

    await state.update_data(event_id=event_id)
    await state.set_state(EditEventStates.waiting_for_date)

    # Show calendar for current month
    now = datetime.now(ZoneInfo("Europe/Prague"))
    await callback.message.edit_text(
        f"📅 <b>Изменение даты</b>\n\n"
        f"Текущая дата: {format_datetime(event.event_date)}\n\n"
        f"Выберите новую дату:",
        parse_mode="HTML",
        reply_markup=get_calendar_keyboard(now.year, now.month),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit:reminders:"))
async def edit_field_reminders(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing event reminders.

    Args:
        callback: Callback query
        state: FSM context
    """
    event_id = int(callback.data.split(":")[-1])

    async with db_manager.get_session() as session:
        result = await session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            await callback.answer("❌ Событие не найдено")
            return

        # Delete all old reminders
        await session.execute(
            select(Reminder).where(Reminder.event_id == event_id)
        )
        reminders = (await session.execute(
            select(Reminder).where(Reminder.event_id == event_id)
        )).scalars().all()

        for reminder in reminders:
            await session.delete(reminder)
        await session.commit()

    await state.update_data(event_id=event_id, event_date=event.event_date)
    await state.set_state(EditEventStates.selecting_reminders)

    await callback.message.edit_text(
        f"🔔 <b>Изменение напоминаний</b>\n\n"
        f"Старые напоминания удалены.\n"
        f"Выберите новые периоды напоминаний:",
        parse_mode="HTML",
        reply_markup=get_reminder_periods_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    StateFilter(EditEventStates.selecting_reminders),
    F.data.startswith("reminder:")
)
async def process_edit_reminder_selection(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Process reminder period selection during edit.

    Args:
        callback: Callback query
        state: FSM context
    """
    data = await state.get_data()

    if callback.data == "reminder:done":
        await state.clear()
        await callback.message.edit_text(
            "✅ Напоминания успешно обновлены!",
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

    if remind_at <= datetime.now(ZoneInfo("Europe/Prague")):
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


@router.callback_query(F.data.startswith("edit:cancel:"))
async def edit_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel editing.

    Args:
        callback: Callback query
        state: FSM context
    """
    await state.clear()
    await callback.message.edit_text("❌ Редактирование отменено.")
    await callback.answer()


# Calendar handlers
@router.callback_query(
    StateFilter(CreateEventStates.waiting_for_date, EditEventStates.waiting_for_date),
    F.data == "calendar:ignore"
)
async def calendar_ignore(callback: CallbackQuery) -> None:
    """Ignore calendar button clicks (headers, empty cells).

    Args:
        callback: Callback query
    """
    await callback.answer()


@router.callback_query(
    StateFilter(CreateEventStates.waiting_for_date, EditEventStates.waiting_for_date),
    F.data.startswith("calendar:nav:")
)
async def calendar_navigate(callback: CallbackQuery) -> None:
    """Navigate to a different month in the calendar.

    Args:
        callback: Callback query
    """
    _, _, year, month = callback.data.split(":")
    year, month = int(year), int(month)

    await callback.message.edit_reply_markup(
        reply_markup=get_calendar_keyboard(year, month)
    )
    await callback.answer()


@router.callback_query(
    StateFilter(CreateEventStates.waiting_for_date, EditEventStates.waiting_for_date),
    F.data == "calendar:today"
)
async def calendar_today(callback: CallbackQuery) -> None:
    """Navigate to current month in the calendar.

    Args:
        callback: Callback query
    """
    now = datetime.now(ZoneInfo("Europe/Prague"))

    try:
        await callback.message.edit_reply_markup(
            reply_markup=get_calendar_keyboard(now.year, now.month)
        )
        await callback.answer()
    except TelegramBadRequest:
        # User is already on current month, just acknowledge
        await callback.answer("Вы уже на текущем месяце")


@router.callback_query(
    StateFilter(CreateEventStates.waiting_for_date, EditEventStates.waiting_for_date),
    F.data.startswith("calendar:day:")
)
async def calendar_day_selected(callback: CallbackQuery) -> None:
    """Handle day selection, show time picker.

    Args:
        callback: Callback query
    """
    _, _, year, month, day = callback.data.split(":")
    selected_date = datetime(int(year), int(month), int(day), tzinfo=ZoneInfo("Europe/Prague"))

    await callback.message.edit_text(
        f"📅 Выбрана дата: {selected_date.strftime('%d.%m.%Y')}\n\n"
        "⏰ Выберите время:",
        reply_markup=get_time_keyboard(selected_date),
    )
    await callback.answer()


@router.callback_query(
    StateFilter(CreateEventStates.waiting_for_date),
    F.data.startswith("calendar:time:")
)
async def calendar_time_selected_create(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle time selection for creating event.

    Args:
        callback: Callback query
        state: FSM context
    """
    _, _, year, month, day, hour, minute = callback.data.split(":")
    event_date = datetime(
        int(year), int(month), int(day), int(hour), int(minute),
        tzinfo=ZoneInfo("Europe/Prague")
    )

    if event_date <= datetime.now(ZoneInfo("Europe/Prague")):
        await callback.answer(
            "❌ Дата события должна быть в будущем!",
            show_alert=True
        )
        return

    # Save event to database
    async with db_manager.get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
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
    await callback.message.edit_text(
        f"✅ Событие создано!\n\n"
        f"📝 <b>{data['title']}</b>\n"
        f"📅 {format_datetime(event_date)}\n\n"
        f"Теперь выберите периоды напоминаний:",
        parse_mode="HTML",
        reply_markup=get_reminder_periods_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    StateFilter(EditEventStates.waiting_for_date),
    F.data.startswith("calendar:time:")
)
async def calendar_time_selected_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle time selection for editing event.

    Args:
        callback: Callback query
        state: FSM context
    """
    _, _, year, month, day, hour, minute = callback.data.split(":")
    new_date = datetime(
        int(year), int(month), int(day), int(hour), int(minute),
        tzinfo=ZoneInfo("Europe/Prague")
    )

    if new_date <= datetime.now(ZoneInfo("Europe/Prague")):
        await callback.answer(
            "❌ Дата события должна быть в будущем!",
            show_alert=True
        )
        return

    data = await state.get_data()
    event_id = data["event_id"]

    # Update event in database
    async with db_manager.get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one()

        result = await session.execute(
            select(Event).where(Event.id == event_id, Event.user_id == user.id)
        )
        event = result.scalar_one_or_none()

        if not event:
            await callback.message.edit_text("❌ Событие не найдено.")
            await callback.answer()
            await state.clear()
            return

        event.event_date = new_date
        await session.commit()

        event_title = event.title

    # Store updated event date for reminders editing
    await state.update_data(event_date=new_date)

    # Ask if user wants to update reminders
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, изменить напоминания",
                    callback_data=f"edit:reminders:{event_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Нет, оставить как есть",
                    callback_data="edit:reminders:skip"
                )
            ],
        ]
    )

    await callback.message.edit_text(
        f"✅ Дата успешно обновлена!\n\n"
        f"📝 <b>{event_title}</b>\n"
        f"📅 {format_datetime(new_date)}\n\n"
        f"⚠️ Хотите обновить напоминания для новой даты?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "edit:reminders:skip")
async def edit_reminders_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip updating reminders after date change.

    Args:
        callback: Callback query
        state: FSM context
    """
    await state.clear()
    await callback.message.edit_text(
        "✅ Дата обновлена! Напоминания остались без изменений."
    )
    await callback.message.answer(
        "Используйте меню для дальнейших действий:",
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    StateFilter(CreateEventStates.waiting_for_date, EditEventStates.waiting_for_date),
    F.data == "calendar:cancel"
)
async def calendar_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel calendar selection.

    Args:
        callback: Callback query
        state: FSM context
    """
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")
    await callback.answer()
