from datetime import datetime
import asyncio
import logging
from datetime import timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from aiogram.webhook.aiohttp_server import SimpleRequestHandler  # для webhook

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from tortoise import Tortoise, connections
from tortoise.exceptions import DBConnectionError, OperationalError

from app.user import user_router, user_cache  #, dedlines, dedline_notifications
from app.database.requests import get_all_users, get_event

from config import REPER_HOURS, TOKEN, TORTOISE_ORM, season_index, setup_logger, setup_base_logger
from app.schedule import delete_events, check_payment_dedline, stat_raiting

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

        await stat_raiting()  # загрузка статистики для рейтинга текущего сезона

        await season_index()  # загрузка текущего индекса летоичсчисления сезона
        scheduler = AsyncIOScheduler()
        scheduler.add_job(delete_events, CronTrigger(hour=1, minute=00), id="work_by_stats_and_delete_events_at_2")
        scheduler.add_job(delete_events, CronTrigger(hour=4, minute=00), id="work_by_stats_and_delete_events_at_5")
        for i in REPER_HOURS:  # это планировщик по проверкам дедлайнов
            scheduler.add_job(check_payment_dedline,
                              CronTrigger(hour=i - 1, minute=0),
                              kwargs={'notify': True, 'bot': bot},
                              id=f"notify_by_{i}")
            scheduler.add_job(check_payment_dedline, CronTrigger(hour=i, minute=0), id=f"scan_by_{i}")

        # # Заглушки
        # test_now = datetime.now()
        # for i in range(test_now.minute+1, 60):
        #     scheduler.add_job(check_payment_dedline,
        #                       CronTrigger(hour=test_now.hour, minute=i),
        #                       kwargs={'notify': True, 'bot': bot},
        #                       id=f"notify_by_test_{i}")
        #     scheduler.add_job(check_payment_dedline,
        #                       CronTrigger(hour=test_now.hour, minute=i, second=10),
        #                       id=f"scan_by_test_{i}")

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


            # Эта часть пока не исползуется
            # events = await get_event(for_schedule=True)
            # for item in events:
            #     payment_dedline = item['payment_dedline']
            #     # local_dedline = payment_dedline.astimezone()  # ← автоматически в часовой пояс системы
            #     dedlines.append((payment_dedline.replace(tzinfo=None), item['id']))
            #     # dedlines.append((local_dedline.replace(tzinfo=None), item['id']))
            # for item in dedlines:
            #     dedline_notifications.append((item[0] - timedelta(hours=1), item[1]))
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
    dp.include_router(user_router)
    dp.startup.register(startup)
    dp.shutdown.register(shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


''' Функции. которые пока отложены в сторонку '''
# # Специальные функции перепланировщики
# async def replanner_creator(scheduler, notify=False):
#     max_attempts = 3
#     for attempt in range(max_attempts):
#         try:
#
#             if notify is False:  # создатель перепланировщика по дедлайну
#                 if dedlines:
#                     scheduler.add_job(replanner, CronTrigger(hour=dedlines[0][0].hour,
#                                                              minute=dedlines[0][0].minute,
#                                                              day=dedlines[0][0].day,
#                                                              month=dedlines[0][0].month),
#                                       args=[scheduler], id="replanner")
#                 else:
#                     scheduler.add_job(replanner, CronTrigger(hour=9, minute=24),
#                                       args=[scheduler], id="replanner", )
#             else:  # создатель перепланировщика по уведомлениям
#                 if dedline_notifications:
#                     scheduler.add_job(notify_replanner, CronTrigger(hour=dedline_notifications[0][0].hour,
#                                                                     minute=dedline_notifications[0][0].minute,
#                                                                     day=dedline_notifications[0][0].day,
#                                                                     month=dedline_notifications[0][0].month),
#                                       args=[scheduler], id="notify_replanner")
#                 else:
#                     scheduler.add_job(notify_replanner, CronTrigger(hour=9, minute=24),
#                                       args=[scheduler], id="notify_replanner", )
#             return
#         except Exception as e:
#             await logger.error(f'Ошибка (попытка {attempt + 1}): {e}')
#             if attempt < max_attempts - 1:
#                 await asyncio.sleep(5)
#     await logger.critical('Не удалось создать планировщик после 3 попыток')
#
#
# async def replanner(scheduler):  # перепланировщик для исполняемых функций
#     if dedlines:
#         await message(dedlines[0][1])
#         dedlines.pop(0)
#     scheduler.remove_job('replanner')
#     await replanner_creator(scheduler)
#
#
# async def notify_replanner(scheduler):  # перепланировщик для отправки уведомлений
#     if dedline_notifications:
#         await message(dedline_notifications[0][1], True, bot)
#         dedline_notifications.pop(0)
#     scheduler.remove_job('notify_replanner')
#     await replanner_creator(scheduler, True)