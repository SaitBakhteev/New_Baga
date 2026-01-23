with open("/tmp/bot_debug.log", "a") as f:
    f.write("=== STARTING BOT новая отладка ===\n")

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
with open("/tmp/bot_debug.log", "a") as f:
    f.write("=== line 14 ===\n")


from aiogram.webhook.aiohttp_server import SimpleRequestHandler  # для webhook
from aiohttp import web

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
with open("/tmp/bot_debug.log", "a") as f:
    f.write("=== line 22 ===\n")

from tortoise import Tortoise, connections
from tortoise.exceptions import DBConnectionError, OperationalError


from app.handlers.main_handler import main_router, user_cache  #, dedlines, dedline_notifications
from app.database.requests import get_all_users

with open("/tmp/bot_debug.log", "a") as f:
    f.write("=== line 32 ===\n")

from config.log_config import *
from config.constants import *
from config.db_config import *

with open("/tmp/bot_debug.log", "a") as f:
    f.write("=== line 36 ===\n")

from app.schedule import delete_events, check_payment_dedline, stat_raiting
with open("/tmp/bot_debug.log", "a") as f:
    f.write("=== line 41 ===\n")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
with open("/tmp/bot_debug.log", "a") as f:
    f.write("=== BOT INIT OK ===")
print("=== BOT INIT OK ===")  # ← ДОБАВЬ ПОСЛЕ ИНИЦИАЛИЗАЦИИ БОТА

with open("/tmp/bot_debug.log", "a") as f:
    f.write("=== до setup_base_logger ===")
setup_base_logger()  # запускаем настройки для стандартного логера
with open("/tmp/bot_debug.log", "a") as f:
    f.write("=== после setup_base_logger ===")

stream_logger = logging.getLogger(__name__)

logger = setup_logger(__name__)
with open("/tmp/bot_debug.log", "a") as f:
    f.write("=== 58 ===")


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


async def webhook_setup(bot: Bot):
    with open("/tmp/bot_debug.log", "a") as f:
        f.write("=== line 78 ===\n")
    
    try:
        with open("/tmp/bot_debug.log", "a") as f:
            f.write(f"=== URL: {URL} ===\n")
            f.write(f"=== WEBHOOK_TOKEN: {WEBHOOK_TOKEN} ===\n")
        
        # Удаляем старый вебхук перед установкой нового
        await bot.delete_webhook()
        
        await bot.set_webhook(
            url=f"{URL}/webhook",
            secret_token=f"{WEBHOOK_TOKEN}"
        )
        
        # Проверяем установку
        webhook_info = await bot.get_webhook_info()
        with open("/tmp/bot_debug.log", "a") as f:
            f.write(f"=== line 84 - webhook SUCCESS: {webhook_info.url} ===\n")
            f.write(f"=== Webhook pending updates: {webhook_info.pending_update_count} ===\n")
            
    except Exception as e:
        with open("/tmp/bot_debug.log", "a") as f:
            f.write(f"=== webhook_setup ERROR: {e} ===\n")
        raise


async def startup(dispatcher: Dispatcher):
    try:
        if not await connect_to_db():
            raise RuntimeError

        with open("/tmp/bot_debug.log", "a") as f:
            f.write("=== 120 ===\n")        
        # Вызываем установку webhook
        await webhook_setup(bot)

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
    print(f"DEBUG: URL = {URL}")
    print(f"DEBUG: WEBHOOK_TOKEN = {WEBHOOK_TOKEN}")

    dp = Dispatcher()
    dp.include_router(main_router)
    
    # РЕГИСТРИРУЕМ startup/shutdown
    dp.startup.register(startup)
    dp.shutdown.register(shutdown)
    with open("/tmp/bot_debug.log", "a") as f:
        f.write("=== 200 ===\n")
    try:
        # НАСТРОЙКА WEBHOOK СЕРВЕРА
        app = web.Application()
        with open("/tmp/bot_debug.log", "a") as f:
            f.write("=== line 205 ===\n")
        
        # Регистрируем обработчик вебхука
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=f"{WEBHOOK_TOKEN}",
        )
        webhook_requests_handler.register(app, path="/webhook")
        with open("/tmp/bot_debug.log", "a") as f:
            f.write("=== line 213 ===\n")
        # Запускаем сервер
        runner = web.AppRunner(app)
        await runner.setup()
        with open("/tmp/bot_debug.log", "a") as f:
            f.write("=== 216: afterawait runner.setup()"  ===")
        
        site = web.TCPSite(runner, host="0.0.0.0", port=3000)
        await site.start()
        
        
        print("Webhook server started on port 3000")
        with open("/tmp/bot_debug.log", "a") as f:
            f.write("=== 221: Webhook server started on port 3000"  ===")
        # БЕСКОНЕЧНЫЙ ЦИКЛ
        await asyncio.Event().wait()
        
    except Exception as e:
        print(f"ERROR in main: {e}")
        raise
    

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