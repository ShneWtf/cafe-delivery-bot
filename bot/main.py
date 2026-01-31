"""
Main entry point for Telegram Cafe Bot
Aiogram 3.x bot with Web App integration
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Load environment variables
load_dotenv()

# Import handlers
from handlers import user_router, admin_router, director_router, courier_router

# Import database initialization
from database import init_db, DIRECTOR_ID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main function to run the bot"""
    
    # Get bot token from environment
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN not found in environment variables!")
        logger.error("Please create .env file with BOT_TOKEN=your_token")
        sys.exit(1)
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    logger.info(f"Database initialized. Director ID: {DIRECTOR_ID}")
    
    # Initialize bot with default properties
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Initialize dispatcher
    dp = Dispatcher()
    
    # Register routers
    dp.include_router(director_router)  # Director first (highest priority)
    dp.include_router(admin_router)      # Admin second
    dp.include_router(courier_router)    # Courier third
    dp.include_router(user_router)       # User last (catch-all)
    
    logger.info("All routers registered")
    
    # Startup message
    logger.info("=" * 50)
    logger.info("🚀 Cafe Delivery Bot Starting...")
    logger.info(f"👑 Director ID: {DIRECTOR_ID}")
    logger.info(f"🌐 WebApp URL: {os.getenv('WEBAPP_URL', 'Not set')}")
    logger.info("=" * 50)
    
    # Notify director on startup (optional)
    try:
        await bot.send_message(
            DIRECTOR_ID,
            "🚀 <b>Бот запущен!</b>\n\n"
            "👑 Вы являетесь директором.\n"
            "Используйте /director для управления персоналом.\n"
            "Используйте /admin для админ-панели."
        )
    except Exception as e:
        logger.warning(f"Could not notify director: {e}")
    
    # Start polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped with error: {e}")
        raise
