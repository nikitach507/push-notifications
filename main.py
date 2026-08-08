"""Main entry point for the Telegram notification bot."""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.bot.handlers import common, events
from src.config.settings import settings
from src.database.database import db_manager
from src.scheduler.reminder_scheduler import ReminderScheduler

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot, scheduler: ReminderScheduler) -> None:
    """Execute actions on bot startup.

    Args:
        bot: Bot instance
        scheduler: Reminder scheduler instance
    """
    # Create database tables
    logger.info("Creating database tables...")
    await db_manager.create_tables()

    # Start reminder scheduler
    logger.info("Starting reminder scheduler...")
    scheduler.start()

    logger.info("Bot started successfully!")


async def on_shutdown(scheduler: ReminderScheduler) -> None:
    """Execute actions on bot shutdown.

    Args:
        scheduler: Reminder scheduler instance
    """
    # Stop scheduler
    logger.info("Stopping reminder scheduler...")
    scheduler.shutdown()

    # Close database connection
    logger.info("Closing database connection...")
    await db_manager.close()

    logger.info("Bot stopped successfully!")


async def main() -> None:
    """Main function to run the bot."""
    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Initialize reminder scheduler
    scheduler = ReminderScheduler(bot)

    # Register routers
    dp.include_router(common.router)
    dp.include_router(events.router)

    # Setup startup and shutdown hooks
    dp.startup.register(lambda: on_startup(bot, scheduler))
    dp.shutdown.register(lambda: on_shutdown(scheduler))

    try:
        # Start bot
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
