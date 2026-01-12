from re import fullmatch

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.database import requests as db_req
from app import keyboards as kb
from app import states as st
from config import setup_logger, DAYS, user_cache
import asyncio

logger = setup_logger(__name__)


# Фоновая задача для очистки пользовательского окна переписки
async def delete_bkg(call_mess: Message | CallbackQuery):
    try:
        call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
        await call_mess.bot.delete_message(call_mess.chat.id, call_mess.message_id)
    except Exception:
        return


# Регистрация
async def registration(event: Message | CallbackQuery):
    username = event.from_user.username
    event_message = event.message if isinstance(event, CallbackQuery) else event
    if username:
        await event_message.answer(
            "Спорт у дома приветсвует Вас в нашем телеграмм-боте для записи на тренировки.😊\n"
            "Для того, чтобы воспользоваться этим ботом нажмите на кнопку регистрации.\n"
            "При этом нажимая на кнопку регистрации, Вы соглашаетесь со всеми условиями предоставления "
            'персональных данных своего телеграмм аккаунта и иных условий пользовательского соглашения, '
            'описанных <a href="https://disk.yandex.ru/i/J4i-dcxqrgKCPw"><b>здесь</b></a>.',
            reply_markup=kb.registration_kb)
    else:
        await event_message.answer(
            "Сожалеем, но у Вас отсутствует никнейм телеграмм 🥺\n"
            "ℹ️ Как установить никнейм (username):\n"
            "1. Откройте 'Настройки' Telegram\n"
            "2. Выберите 'Изменить профиль'\n"
            "3. В поле 'Username' укажите желаемый ник\n"
            "4. После этого возвращайтесь в бота!☺️"
        )


async def cmd_start(call_mess: CallbackQuery | Message, state: FSMContext, is_admin: bool, user_cache):
    try:
        if call_mess.from_user.id not in user_cache:
            await registration(call_mess)
            return
        await state.clear()
        call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
        await call_mess.answer(
            f"Для работы с ботом воспользуйтесь командами меню, расположенными "
            f"слева внизу (если у вас на устройстве стандатная раскладка).\n↙️"
        )
    except Exception as e:
        await logger.error(f'Ошибка в cmd_start: {e}')
        # stream_logger.error(log_message)
        return


''' ДАЛЕЕ ИДУТ ФУНКЦИИ ПО ОТОБРАЖЕНИЮ ТРЕНИРОВКИ '''

# Фрмирование текста по тренировке со списком участников
def show_text_about_event(event: dict, event_user: list, user_id: int) -> str:
    text, participants_count = event['event_text'], int(event['participants_count'])
        # Находим границы фрагмента по дате трени
    idx_0, idx_end = text.find('<b>Дата тренировки</b>:'), text.find('<b>Длительность</b>')
    ev_dt_info = text[idx_0:idx_end]
    # Находим день недели по индексу от datetime
    day_idx = event['event_datetime'].weekday()
    day = DAYS[day_idx]
    # Присваиваем фрагмент инфы по трени временной переменной и вставляем в новый фрагмент день недели
    new_info = ev_dt_info.replace('\n',f' ({day})\n')
    text = text.replace(ev_dt_info, new_info)

    if event['stars'] is not None:
        stars_text = event['stars'].replace(' ', '').split(',')  # переводим текстовый набор user_id в список
        star_tpl = tuple(map(lambda x: int(x), stars_text))  # преобразуем в кортеж целых чисел значений user_id
    else:
        star_tpl = None
    text += '\n\n<b>ОСНОВНОЙ СПИСОК</b>\n'
    for i, item in enumerate(event_user):
        if i + 1 <= participants_count:
            if item['payment_confirmed'] is False:
                tag = '❌'
            elif not item['payment_confirmed'] and item['paid_check']:
                tag = '✔️'
            elif item['payment_confirmed']:
                tag = '✅'
            else:
                tag = '⚠️'
        else:
            tag = ''
        fullname = f"{item["user__tg_name"]} @{item['user__tg_username']}"
        star = "⭐️" if star_tpl is not None and item['user__id'] in star_tpl else ''

        # Чтобы пользователь видел себя выделенным шрифтом в списке на тренировку
        fullname = f'<b><i>{fullname}</i></b>' if item['user__id'] == user_id else fullname

        text+=f"{star}{i+1}. {fullname} {tag}\n"
        if i + 1 == participants_count:
            text += "\n 📌📌 <b><i>Резерв</i></b>: \n"

    text += '\n<b>❗️ВАЖНЫЕ РЕКОМЕНДАЦИИ</b> в <b>/rec</b>'

    return text


# После выбора тренировки отображается текущий список заявишихся участников
async def show_formed_info_about_event(call_mess: Message | CallbackQuery,
                                       is_admin: bool,
                                       event_id: int,
                                       user_id: int):
    try:
        event = db_req.get_event(id=event_id)
        event_user = await db_req.get_event_user(event_id=event_id)
        ''' Подгружаем из БД все необходимые данные по тренировке '''

        keyboard = kb.training_interface_kb(event, event_user, user_id, is_admin)
        text = show_text_about_event(event, event_user, user_id)
        mess_handler = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
        await mess_handler.answer(text, parse_mode='HTML', reply_markup=keyboard)
        asyncio.create_task(delete_bkg(call_mess))
    except Exception as e:
        await logger.error(f'Ошибка в choose_event: {e}')
        # stream_logger.error(f'Ошибка в choose_event: {e}')
