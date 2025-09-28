import asyncio
import logging
from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tortoise import Tortoise, connections
from tortoise.exceptions import DBConnectionError, OperationalError

from app.user import user_router, user_cache, dedlines, dedline_notifications
from app.database.requests import get_all_users, get_event

from config import TOKEN, TORTOISE_ORM
from app.schedule import delete_events, update

logger = logging.getLogger(__name__)

# Общий для всех обработчиков формат вывода сообщений в лог-файлы
FORMATTER = logging.Formatter('{asctime} - {name} - {levelname} - {message}',
                              style='{')

info_file_handler = logging.FileHandler('logs/general.log')
info_file_handler.setLevel('INFO')
info_file_handler.setFormatter(FORMATTER)

error_file_handler = logging.FileHandler('logs/error.log')
error_file_handler.setLevel('ERROR')
error_file_handler.setFormatter(FORMATTER)

# Нестандартное логирование, для записи жалоб на работу бота от пользователей
msg_handler = logging.FileHandler('logs/bot.log')
msg_handler.setLevel('CRITICAL')
msg_formatter = logging.Formatter('{asctime}:{username} -- {message}',
                                  style='{')
msg_handler.setFormatter(msg_formatter)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

logging.basicConfig(format=logging.BASIC_FORMAT,
                    level=logging.INFO,
                    handlers=[info_file_handler, error_file_handler, msg_handler,
                              logging.StreamHandler()])


async def connect_to_db():
    retries = 5
    delay = 5  # seconds

    for attempt in range(retries):
        try:
            await Tortoise.init(config=TORTOISE_ORM)
            await Tortoise.generate_schemas()

            # Проверка подключения
            await connections.get("default").execute_query("SELECT 1")
            logger.info("Successfully connected to database")
            return True

        except (DBConnectionError, OperationalError) as e:
            print(f"Database connection failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                logger.error(f"Retrying in {delay} seconds...; "
                             f"Error_message: {e}")
                await asyncio.sleep(delay)
        logger.error("Failed to connect to database after multiple attempts")
        return False


# Специальные функции перепланировщики
async def replanner_creator(scheduler, notify=False):
    if notify is False:  # создатель перепланировщика по дедлайну
        if dedlines:
            scheduler.add_job(replanner, CronTrigger(hour=dedlines[0][0].hour,
                                                     minute=dedlines[0][0].minute,
                                                     day=dedlines[0][0].day,
                                                     month=dedlines[0][0].month),
                              args=[scheduler], id="replanner")
        else:
            scheduler.add_job(replanner, CronTrigger(hour=9, minute=24),
                              args=[scheduler], id="replanner", )
    else:  # создатель перепланировщика по уведомлениям
        if dedline_notifications:
            scheduler.add_job(notify_replanner, CronTrigger(hour=dedline_notifications[0][0].hour,
                                                     minute=dedline_notifications[0][0].minute,
                                                     day=dedline_notifications[0][0].day,
                                                     month=dedline_notifications[0][0].month),
                              args=[scheduler], id="notify_replanner")
        else:
            scheduler.add_job(notify_replanner, CronTrigger(hour=9, minute=24),
                              args=[scheduler], id="notify_replanner", )


async def replanner(scheduler):  # перепланировщик для исполняемых функций
    if dedlines:
        await update(dedlines[0][1])
        dedlines.pop(0)
    scheduler.remove_job('replanner')
    await replanner_creator(scheduler)


async def notify_replanner(scheduler):  # перепланировщик для отправки уведомлений
    if dedline_notifications:
        await update(dedline_notifications[0][1], True, bot)
        dedline_notifications.pop(0)
    scheduler.remove_job('notify_replanner')
    await replanner_creator(scheduler, True)


async def startup(dispatcher: Dispatcher):
    try:
        if not await connect_to_db():
            raise RuntimeError
        
        # Формирование user_cache и dedlines
        users = await get_all_users()
        for user_ in users:
            user_cache[user_.tg_id] = user_
        print(user_cache)
        events = await get_event(for_schedule=True)
        for item in events:
            payment_dedline = item['payment_dedline']
            dedlines.append((payment_dedline.replace(tzinfo=None), item['id']))
        for item in dedlines:
            dedline_notifications.append((item[0] - timedelta(hours=1), item[1]))
        print(f'dedlines = {dedlines}\n'
              f'dedline_notifications = {dedline_notifications}')
        scheduler = AsyncIOScheduler()
        scheduler.add_job(delete_events, CronTrigger(hour=23, minute=58))
        scheduler.add_job(update, CronTrigger(hour=0, minute=0))
        scheduler.add_job(delete_events, CronTrigger(hour=11, minute=58))
        scheduler.add_job(update, CronTrigger(hour=12, minute=0))
        await replanner_creator(scheduler)
        await replanner_creator(scheduler, True)
        scheduler.start()
        logger.info("Starting Bot...")
    except RuntimeError as e:
        logger.error(f"On startup: {e}")
    except Exception as e:
        logger.error(f"ERROR_on_Starting Bot...: {e}")


async def shutdown(dispatcher: Dispatcher):
    await Tortoise.close_connections()
    exit(0)


async def main():
    dp = Dispatcher()
    dp.include_router(user_router)
    dp.startup.register(startup)
    dp.shutdown.register(shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
