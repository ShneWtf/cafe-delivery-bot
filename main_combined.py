"""
Combined entry point for Telegram Bot + FastAPI
Runs both services in one process for Render deployment
"""

import asyncio
import logging
import os
import sys
import threading
from pathlib import Path

# Add bot directory to path
sys.path.insert(0, str(Path(__file__).parent / "bot"))
sys.path.insert(0, str(Path(__file__).parent / "webapp"))

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_api_server():
    """Run FastAPI server in a separate thread"""
    import uvicorn
    from webapp.api import app
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🌐 Starting API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


async def run_bot():
    """Run Telegram bot"""
    from aiogram import Bot, Dispatcher
    from aiogram.enums import ParseMode
    from aiogram.client.default import DefaultBotProperties
    
    # Import after path is set
    from bot.handlers import user_router, admin_router, director_router, courier_router
    from bot.database import init_db, DIRECTOR_ID
    
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN not found!")
        return
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    logger.info(f"Database initialized. Director ID: {DIRECTOR_ID}")
    
    # Initialize bot
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    dp.include_router(director_router)
    dp.include_router(admin_router)
    dp.include_router(courier_router)
    dp.include_router(user_router)
    
    logger.info("🤖 Starting Telegram bot...")
    
    # Notify director
    try:
        await bot.send_message(
            DIRECTOR_ID,
            "🚀 <b>Бот запущен на Render!</b>\n\n"
            "👑 Вы директор.\n"
            "Используйте /director для управления."
        )
    except Exception as e:
        logger.warning(f"Could not notify director: {e}")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


def main():
    """Main entry point - runs both bot and API"""
    logger.info("=" * 50)
    logger.info("🚀 Starting Combined Bot + API Server")
    logger.info("=" * 50)
    
    # Start API server in a separate thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    
    # Give API time to start
    import time
    time.sleep(2)
    
    # Run bot in main thread (async)
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
