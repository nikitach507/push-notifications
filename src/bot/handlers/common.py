"""Common handlers for the bot."""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy import select

from src.bot.keyboards import get_main_menu_keyboard
from src.database.database import db_manager
from src.database.models import User

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command.

    Args:
        message: Incoming message
    """
    async with db_manager.get_session() as session:
        # Check if user exists
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        # Create user if doesn't exist
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            session.add(user)
            await session.commit()

    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        "Я помогу тебе не забыть о важных событиях.\n\n"
        "Создавай события и настраивай напоминания — я буду присылать уведомления в Telegram, "
        "чтобы ты точно не пропустил важный момент!\n\n"
        "Используй меню ниже для навигации:",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(Command("help"))
@router.message(lambda message: message.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    """Handle /help command.

    Args:
        message: Incoming message
    """
    help_text = (
        "📚 <b>Как пользоваться ботом:</b>\n\n"
        "<b>➕ Создать событие</b>\n"
        "Создай новое событие, указав название, описание и дату.\n"
        "После создания ты сможешь настроить напоминания.\n\n"
        "<b>📋 Мои события</b>\n"
        "Посмотри список всех твоих событий.\n"
        "Можно редактировать или удалять события.\n\n"
        "<b>🔔 Напоминания</b>\n"
        "Настрой напоминания для каждого события:\n"
        "• За 1 неделю\n"
        "• За 3 дня\n"
        "• За 2 дня\n"
        "• За 1 день\n"
        "• За 12 часов\n"
        "• За 2 часа\n\n"
        "<b>📅 Формат даты</b>\n"
        "При создании события указывай дату в формате:\n"
        "<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
        "Например: <code>31.12.2025 23:59</code>\n\n"
        "❓ Если возникли вопросы — пиши /help"
    )

    await message.answer(help_text, parse_mode="HTML")
