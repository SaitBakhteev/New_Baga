import asyncio
import logging
from functools import partial

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession  # ← добавляем

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tortoise import Tortoise, connections
from tortoise.exceptions import DBConnectionError, OperationalError

from app.handlers.main import main_router
from app.database.requests import get_all_users
from config.constants import *
from config.db_config import TORTOISE_ORM
from config.log_config import setup_base_logger, setup_logger
from app.schedule import main_func, stat_execute_func, StatisticOps, msg_send

setup_base_logger()
logging.getLogger('apscheduler').setLevel(logging.WARNING)

stream_logger = logging.getLogger(__name__)
logger = setup_logger(__name__)


async def connect_to_db():
    retries = 5
    delay = 5
    for attempt in range(retries):
        try:
            await Tortoise.init(config=TORTOISE_ORM)
            await Tortoise.generate_schemas()
            await connections.get("default").execute_query("SELECT 1")
            stream_logger.info("Successfully connected to database")
            return True
        except (DBConnectionError, OperationalError) as e:
            print(f"Database connection failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                stream_logger.error(f"Retrying in {delay} seconds... Error: {e}")
                await asyncio.sleep(delay)
    stream_logger.error("Failed to connect to database after multiple attempts")
    return False


async def startup(dispatcher: Dispatcher, bot: Bot):
    try:
        if not await connect_to_db():
            raise RuntimeError

        users = await get_all_users()
        for user_ in users:
            user_cache[user_.tg_id] = user_
        print(user_cache)

        await season_index()
        await StatisticOps.stat_raiting_form()

        scheduler = AsyncIOScheduler()
        scheduler.add_job(main_func, CronTrigger(minute='*/2'),
                          kwargs={'is_move': True}, id="move_to_end")
        scheduler.add_job(main_func, CronTrigger(minute='1-59/2'),
                          kwargs={'is_move': False}, id="remind")
        scheduler.add_job(msg_send, CronTrigger(hour=8, minute=0, second=25), id='msg_send')
        scheduler.add_job(stat_execute_func, CronTrigger(hour=1, minute=00), id="stat_execute_1h")
        scheduler.add_job(stat_execute_func, CronTrigger(hour=4, minute=00), id="stat_execute_4h")
        scheduler.start()
        stream_logger.info("Starting Bot with polling...")

        logger.info("=== ЗАПЛАНИРОВАННЫЕ ЗАДАНИЯ ===")
        for job in scheduler.get_jobs():
            logger.info(f"• {job.id}: {job.trigger} (next: {job.next_run_time})")

    except Exception as e:
        stream_logger.error(f"Startup error: {e}")
        raise


async def shutdown(dispatcher: Dispatcher, session: AiohttpSession):
    await Tortoise.close_connections()
    await session.close()


async def main():
    session = AiohttpSession(proxy=PROXY_URL)  # ← используем AiohttpSession
    bot = Bot(token=TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # Удаляем вебхук, если он был установлен
    await bot.delete_webhook()

    dp = Dispatcher()
    dp.include_router(main_router)

    dp.startup.register(partial(startup, bot=bot))
    dp.shutdown.register(partial(shutdown, session=session))

    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass