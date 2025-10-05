import os
from dotenv import load_dotenv

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
