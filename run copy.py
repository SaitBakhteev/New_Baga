import asyncio
import logging

from aiogram import Dispatcher

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tortoise import Tortoise, connections
from tortoise.exceptions import DBConnectionError, OperationalError

from app.handlers.main import main_router
from app.database.requests import get_all_users

from config.constants import *
from config.db_config import TORTOISE_ORM
from config.log_config import setup_base_logger, setup_logger

from app.schedule import main_func, stat_execute_func, StatisticOps

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

setup_base_logger()  # запускаем настройки для стандартного логера

stream_logger = logging.getLogger(__name__)

logger = setup_logger(__name__)


async def connect_to_db():
    retries = 5
    delay = 5  # seconds

    for attempt in range(retries):
        try:
            await Tortoise.init(config=TORTOISE_ORM)
            await Tortoise.generate_schemas()

            # Проверка подключения
            await connections.get("default").execute_query("SELECT 1")
            stream_logger.info("Successfully connected to database")
            return True

        except (DBConnectionError, OperationalError) as e:
            print(f"Database connection failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                stream_logger.error(f"Retrying in {delay} seconds...; "
                                    f"Error_message: {e}")
                await asyncio.sleep(delay)
        stream_logger.error("Failed to connect to database after multiple attempts")
        return False


async def startup(dispatcher: Dispatcher):
    try:
        if not await connect_to_db():
            raise RuntimeError

        # Формирование user_cache и dedlines
        users = await get_all_users()
        for user_ in users:
            user_cache[user_.tg_id] = user_
        print(user_cache)

        await season_index()  # загрузка текущего индекса летоичсчисления сезона
        await StatisticOps.stat_raiting_form()

        scheduler = AsyncIOScheduler()
        # scheduler.add_job(main_func, CronTrigger(minute='*/2'),
        #                   kwargs={'is_move': True}, id="move_to_end")
        # scheduler.add_job(main_func, CronTrigger(minute='1-59/2'),
        #                   kwargs={'is_move': False}, id="remind")

        scheduler.add_job(stat_execute_func, CronTrigger(hour=1, minute=0), id="stat_execute_1h")
        scheduler.add_job(stat_execute_func, CronTrigger(hour=4, minute=0), id="stat_execute_4h")

        scheduler.start()
        stream_logger.info("Starting Bot...")

        # ЗАПИСЫВАЕМ В ЛОГИ ВСЕ ЗАДАНИЯ
        try:
            logger.info("=== ЗАПЛАНИРОВАННЫЕ ЗАДАНИЯ ===")
            jobs = scheduler.get_jobs()
            if not jobs:
                logger.info("Нет активных заданий")
            else:
                for job in jobs:
                    logger.info(f"• {job.id}: {job.trigger} (next: {job.next_run_time})")
        except Exception as e:
            await logger.error(f'Ошибка при попытке === ЗАПЛАНИРОВАННЫЕ ЗАДАНИЯ ===: {e}')

    except RuntimeError as e:
        stream_logger.error(f"On startup: {e}")
    except Exception as e:
        stream_logger.error(f"ERROR_on_Starting Bot...: {e}")


async def shutdown(dispatcher: Dispatcher):
    await Tortoise.close_connections()
    exit(0)


async def main():
    dp = Dispatcher()
    dp.include_router(main_router)
    dp.startup.register(startup)
    dp.shutdown.register(shutdown)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
