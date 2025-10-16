import logging
import os

from datetime import timedelta, datetime, time
from dotenv import load_dotenv

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

NUMBERS = ('0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣')  # марки для чисел рейтинга

TRAINING_TYPES = ('🏐 Волейбол',
                  '🏀 Баскетбол',
                  '⚽️ Футбол',
                  '🏸 Бадминтон')

DEDLINE_TYPE = [
    # ("12 часов", "12"), ("24 часа", "24"),
    # ("Индивидуальный дедлайн", "0"),
    ("Автодедлайн", "-1")
]

SEASON_INDEX = [0]  # спец переменная, означающая начало летоисчисления сезона

DAYS = ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')

SCAN_TIMES = (
    time(1,7),
    time(6,0),
    time(10, 0),
    time(14, 0),
    time(18, 0),
    time(22, 0),
)


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
        level=logging.INFO,
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
