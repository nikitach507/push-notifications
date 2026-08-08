"""Reminder scheduler for sending notifications."""

import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from src.database.database import db_manager
from src.database.models import Event, Reminder, User
from src.utils.helpers import format_datetime

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Manages scheduled reminders."""

    def __init__(self, bot: Bot) -> None:
        """Initialize reminder scheduler.

        Args:
            bot: Bot instance for sending messages
        """
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    async def check_and_send_reminders(self) -> None:
        """Check for pending reminders and send them."""
        now = datetime.now()

        async with db_manager.get_session() as session:
            # Get all pending reminders that should be sent
            result = await session.execute(
                select(Reminder)
                .where(
                    Reminder.is_sent == False,  # noqa: E712
                    Reminder.remind_at <= now,
                )
            )
            reminders = result.scalars().all()

            for reminder in reminders:
                try:
                    # Get event details
                    event_result = await session.execute(
                        select(Event).where(Event.id == reminder.event_id)
                    )
                    event = event_result.scalar_one_or_none()

                    if not event:
                        logger.warning(f"Event not found for reminder {reminder.id}")
                        continue

                    # Get user details
                    user_result = await session.execute(
                        select(User).where(User.id == event.user_id)
                    )
                    user = user_result.scalar_one_or_none()

                    if not user:
                        logger.warning(f"User not found for event {event.id}")
                        continue

                    # Send reminder message
                    message_text = (
                        f"🔔 <b>Напоминание!</b>\n\n"
                        f"📝 <b>{event.title}</b>\n"
                        f"📅 {format_datetime(event.event_date)}\n"
                    )

                    if event.description:
                        message_text += f"\n📄 {event.description}"

                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message_text,
                        parse_mode="HTML",
                    )

                    # Mark reminder as sent
                    reminder.is_sent = True
                    await session.commit()

                    logger.info(
                        f"Sent reminder {reminder.id} for event {event.id} to user {user.telegram_id}"
                    )

                except Exception as e:
                    logger.error(
                        f"Error sending reminder {reminder.id}: {e}",
                        exc_info=True,
                    )
                    await session.rollback()

    def start(self) -> None:
        """Start the scheduler."""
        # Check for reminders every minute
        self.scheduler.add_job(
            self.check_and_send_reminders,
            trigger=IntervalTrigger(minutes=1),
            id="check_reminders",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Reminder scheduler started")

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        logger.info("Reminder scheduler stopped")
