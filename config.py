import logging
import os

from datetime import datetime, timedelta

from dotenv import load_dotenv

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from aiologger import Logger
from aiologger.formatters.base import Formatter
from aiologger.handlers.files import AsyncFileHandler
from aiologger.handlers.streams import AsyncStreamHandler


load_dotenv()

TOKEN = os.getenv("TOKEN")

DB_URL = os.getenv("DB_URL")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
URL = os.getenv("URL")
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN")

NUMBERS = ('0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣')  # марки для чисел рейтинга

TRAINING_TYPES = ('🏐 Волейбол',
                  '🏀 Баскетбол',
                  '⚽️ Футбол',
                  '🏸 Бадминтон')

DEDLINE_TYPE = (
    # ("6 часов", "6"),
    ("12 часов", "12"),
    ("24 часа", "24"),
    ("48 часов", "48"),
    # ("3 дня", "72"),
    # ("5 дней", "120"),
)

SEASON_INDEX = [0]  # спец переменная, означающая начало летоисчисления сезона

DAYS = ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')

REPER_HOURS = (8, 13, 17, 22)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


# Функция для Настройки асинхронного логирования
def setup_logger(module):
    logger = Logger(name=module)
    logger.propagate = False
    for i in [('general', logging.INFO), ('error', logging.ERROR), ('bot', logging.CRITICAL)]:
        handler = AsyncFileHandler(f'logs/{i[0]}.log')
        handler.level = i[1]
        handler.formatter = Formatter('{asctime} - {name} - {levelname} - {message}', style='{')
        logger.add_handler(handler)
    return logger


# Дополнительный логер для синхронных функций для отлова в файлы
def setup_sync_logger(module):
    sync_logger = logging.getLogger(name=module)  # отдельный специальный логгер
    for i in [('general.log', 'INFO'), ('error.log', 'ERROR'), ('bot.log', 'CRITICAL')]:
        handler = logging.FileHandler(f'logs/{i[0]}')
        handler.setFormatter(logging.Formatter('{asctime} - {name} - {levelname} - {message}', style='{'))
        handler.setLevel(i[1])
        sync_logger.addHandler(handler)
    return sync_logger


# Конфигурация настроек базового логера для всего проекта
def setup_base_logger():
    # Форматтер для всех хендлеров
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Хендлер для INFO и выше (general.log)
    info_handler = logging.FileHandler('logs/general.log')
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    # Хендлер для ERROR и выше (error.log)
    error_handler = logging.FileHandler('logs/error.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # Хендлер для CRITICAL (bot.log)
    critical_handler = logging.FileHandler('logs/bot.log')
    critical_handler.setLevel(logging.CRITICAL)
    critical_handler.setFormatter(formatter)

    # Хендлер для консоли
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    # Настраиваем корневой логгер
    logging.basicConfig(
        level=logging.WARNING,
        handlers=[info_handler, error_handler, critical_handler, stream_handler]
    )


# config.py for MySQL

# TORTOISE_ORM = {
#     "connections": {
#         "default": {
#             "engine": "tortoise.backends.mysql",
#             "credentials": {
#                 "host": DB_HOST,
#                 "port": DB_PORT,
#                 "user": DB_USER,
#                 "password": DB_PASS,
#                 "database": DB_NAME,
#                 "minsize": 1,
#                 "maxsize": 5,
#                 "sql_mode": "STRICT_TRANS_TABLES",
#                 # "timezone": "Europe/Moscow",
#                 "charset": "utf8mb4"
#             },
#         }
#     },
#     "apps": {
#         "models": {
#             "models": ["app.database.models", "aerich.models"],
#             "default_connection": "default",
#         }
#     },
# }
#


# postgres
# TORTOISE_ORM = {
#     "connections": {
#         "default": {
#             "engine": "tortoise.backends.asyncpg",
#             "credentials": {
#                 "host": DB_HOST,
#                 "port": DB_PORT,
#                 "user": DB_USER,
#                 "password": DB_PASS,
#                 "database": DB_NAME,
#             },
#         }
#     },
#     "apps": {
#         "models": {
#             "models": ["app.database.models", "aerich.models"],
#             "default_connection": "default",
#         }
#     },
# }
#
#
#
# # TYPE_CHOICES = [
# #     ("OL", "OIL"),  # масло
# #     ("FL", "filter"),  # фильтр
# #     ("SP", "Support"),  # тормозные колодки
# #     ("FS", "Full Service"),  # полное ТО
# # ]
#
#
# # # sqlite
TORTOISE_ORM = {
    "connections": {
        "default": DB_URL,
    },
    "apps": {
        "models": {
            "models": ["app.database.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}


#
#

#

# Спец функция для считывания индекса сезона и перезаписи его
async def season_index(write_mode: bool = False):
    with open('season_index.txt', 'r') as f:
        global SEASON_INDEX
        SEASON_INDEX[0] = int(f.read().strip())
        if write_mode:
            SEASON_INDEX[0] += 1
            with open('season_index.txt', 'w') as f:
                f.write(str(SEASON_INDEX[0]))
    return SEASON_INDEX[0]


# Спец функция, определяющая реперный дедлайн для данного участника
def reper_dedline_definiton(real_dedline, now=None, event_datetime=None, is_string=True):
    real_dedline = real_dedline.replace(tzinfo=None)
    reper_dedline = datetime(real_dedline.year, real_dedline.month, real_dedline.day)
    dedline_type = 'init_dedline'
    if now and event_datetime:
        # Индивидуальный дедлайн для тех, кто записался после общего дедлайна
        individ_dedline, event_datetime = now + timedelta(hours=12), event_datetime.replace(tzinfo=None)
        if individ_dedline > real_dedline.replace(tzinfo=None) and individ_dedline < event_datetime.replace(tzinfo=None):
            real_dedline = individ_dedline
            reper_dedline = datetime(real_dedline.year, real_dedline.month, real_dedline.day)
            dedline_type = 'individ_dedline'
        elif individ_dedline >= event_datetime.replace(tzinfo=None):
            return (event_datetime.replace(tzinfo=None).strftime("%H:%M %d.%m.%Y"), 'individ_dedline')

    day = 0
    if reper_dedline < real_dedline:
        while reper_dedline < real_dedline:
            for hour in REPER_HOURS:
                reper_dedline = (datetime(real_dedline.year,
                                          real_dedline.month,
                                          real_dedline.day,
                                          hour)
                                 + timedelta(days=day))
                if reper_dedline > real_dedline:
                    break
            if reper_dedline < real_dedline:
                day += 1
    if is_string:
        return (reper_dedline.strftime("%H:%M %d.%m.%Y"), dedline_type)
    else:
        return (reper_dedline, 'not string')