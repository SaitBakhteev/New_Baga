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

FORMATTER = logging.Formatter('{asctime} - {name} - {levelname} - {message}',
                              style='{')


# Функция для Настройки асинхронного логирования
def setup_logger():
    info_handler = AsyncFileHandler('logs/general.log')
    info_handler.level = logging.INFO

    error_handler = AsyncFileHandler('logs/error.log')
    error_handler.level = logging.ERROR

    crirical_handler = AsyncFileHandler('logs/bot.log')
    crirical_handler.level = logging.CRITICAL

    # Из-за несовместимости асинхронного стрим-хендлера с windows, применяем синхронный
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(FORMATTER)

    for i in [info_handler, error_handler, crirical_handler, stream_handler]:
        i.formatter  = FORMATTER

    logger = Logger()
    # Добавляем все обработчики
    logger.add_handler(info_handler)
    logger.add_handler(error_handler)
    logger.add_handler(crirical_handler)
    logger.add_handler(stream_handler)

    return logger

logger = setup_logger()


# Синхронный стрим-логер
stream_loger = logging.getLogger(__name__)


# Дополнительный синхронный логер
def setup_sync_logger():
    sync_logger = logging.getLogger(__name__)  # отдельный специальный логгер
    info_file_handler = logging.FileHandler('logs/general.log')
    info_file_handler.setLevel('INFO')
    info_file_handler.setFormatter(FORMATTER)

    error_file_handler = logging.FileHandler('logs/error.log')
    error_file_handler.setLevel('ERROR')
    error_file_handler.setFormatter(FORMATTER)

    # Нестандартное логирование, для записи жалоб на работу бота от пользователей
    msg_handler = logging.FileHandler('logs/bot.log')
    msg_handler.setLevel('CRITICAL')
    msg_handler.setFormatter(FORMATTER)

    logging.basicConfig(format=logging.BASIC_FORMAT,
                        level=logging.INFO,
                        handlers=[info_file_handler, error_file_handler, msg_handler,
                                  logging.StreamHandler()])

    return sync_logger

sync_logger = setup_sync_logger()


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
