import os

from datetime import datetime, timedelta

from dotenv import load_dotenv, find_dotenv

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

load_dotenv(find_dotenv())

TOKEN, WEBHOOK_TOKEN = os.getenv("TOKEN"), os.getenv("WEBHOOK_TOKEN")
BOT_NAME = os.getenv("BOT_NAME")
URL = os.getenv("URL")


# ---------- НАСТРОЙКА ПРОКСИ ----------

SOCK_LOGIN, SOCK_PASS, SOCK_IP, SOCK_PORT = os.getenv("SOCK_LOGIN"), os.getenv("SOCK_PASS"), os.getenv("SOCK_IP"), os.getenv("SOCK_PORT"),
# PROXY_URL = f"socks5://{SOCK_LOGIN}:{SOCK_PASS}@{SOCK_IP}:{SOCK_PORT}"
PROXY_URL = f"socks5://{SOCK_IP}:{SOCK_PORT}"

# ------------------------------------


bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

TRAINING_TYPES = ('🏐 Волейбол', '🏖 Пляжный волейбол', '❄️ Снежный волейбол',
                  '🏀 Баскетбол', '⚽️ Футбол', '🏸 Бадминтон')
NUMBERS = ('0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣')  # марки для чисел рейтинга
DEDLINE_TYPE = (("24 часа", "24"))
DAYS = ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')
REPER_HOURS = (8, 13, 17, 22)

# Кэш список пользователей и дедлайнов
user_cache, dedlines, dedline_notifications = dict(), [], []

SEASON_INDEX = [0]  # спец переменная, означающая начало летоисчисления сезона


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
