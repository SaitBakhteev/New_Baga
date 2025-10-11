import logging
import os

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


TRAINING_TYPES = ('🏐 Волейбол',
                  '🏀 Баскетбол',
                  '⚽️ Футбол',
                  '🏸 Бадминтон')

DEDLINE_TYPE = [("12 часов", "12"), ("24 часа", "24"),
                ("Индивидуальный дедлайн", "0")]

SEASON_INDEX = [0]  # спец переменная, означающая начало летоисчисления сезона


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
    logger = logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logger


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
async def season_index(write_mode: bool=False):
    with open('season_index.txt', 'r') as f:
        global SEASON_INDEX
        SEASON_INDEX[0] = int(f.read().strip())
        if write_mode:
            SEASON_INDEX[0] += 1
            with open('season_index.txt', 'w') as f:
                f.write(str(SEASON_INDEX[0]))
    return SEASON_INDEX[0]
