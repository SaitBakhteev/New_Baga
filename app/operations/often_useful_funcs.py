from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.database import requests as db_req
from app import keyboards as kb
from app import states as st
from config import setup_logger, DAYS
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
def show_text_about_event(event: dict, event_user: list,
                                tg_id: int,
                                is_admin: bool=False) -> str:
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
        name = item["user__tg_name"] if item["user__tg_name"] else ''

        if is_admin:  # в списке участников имя аккаунта выводится только для админов
            username = f"@{item['user__tg_username']}" if item['user__tg_username'] else ""
        else:
            username = ''
        star = "⭐️" if star_tpl is not None and item['user__id'] in star_tpl else ''

        # Чтобы пользователь видел себя выделенным шрифтом в списке на тренировку
        name = f'<b><i>{name}</i></b>' if item['user__tg_id'] == tg_id else name

        text+=f"{star}{i+1}. {name} {username}  {tag}\n"
        if i + 1 == participants_count:
            text += "\n 📌📌 <b><i>Резерв</i></b>: \n"

    text += '\n<b>❗️ВАЖНЫЕ РЕКОМЕНДАЦИИ</b> в <b>/rec</b>'

    return text



async def training_info_formation(call_mess: Message | CallbackQuery, is_admin: bool, **kwargs):
    try:
        # events, training_type = kwargs['events'], kwargs['training_type']
        event_id, event, event_user = kwargs['event_id'], kwargs['event'], kwargs['event_user']
        signed_up_for_training, payment_confirmed, availible_pay, availible_notify_by_payment = (
            kwargs['signed_up_for_training'], kwargs['payment_confirmed'],
            kwargs['availible_pay'], kwargs['availible_notify_by_payment']
        )

        text = await kb.show_text_about_event(event, event_user,
                                              tg_id=call_mess.from_user.id,
                                              is_admin=is_admin)
        text = f'<b>Тип тренировки</b>: {event['training_type']}\n' + text
        keyboard = kb.sign_up_for_training(
            signed_up_for_training,
            availible_pay,
            admin_permissions=is_admin,
            payment_confirmed=payment_confirmed,
            availible_notify_by_payment=availible_notify_by_payment,
            event_id=event_id
        )

        return {'text': text, 'keyboard': keyboard}
    except Exception as e:
        await logger.error(f'Error on /training_text: {e}')
        # stream_logger.error(f'Error on /training_text: {e}')
        pass


# После выбора тренировки отображается текущий список заявишихся участников

async def show_formed_info_about_event(
        call_mess: Message | CallbackQuery, is_admin: bool,
        event_id: int, event: list, event_user: list,
):
    try:
        user__tg_id = call_mess.from_user.id  # считываем tg_id данного пользователя

        # Определение параметров отображения инлайн-клавиатуры
        availible_pay, paid_check, payment_confirmed, availible_notify_by_payment = False, None, None, None
        signed_up_for_training = True if any(item['user__tg_id'] == user__tg_id for item in event_user) else False

        if signed_up_for_training:  # если пользователь записан на тренировку
            user_id, paid_check, payment_confirmed = (
                next((item['user__id'], item['paid_check'], item['payment_confirmed'])
                     for item in event_user if item['user__tg_id'] == user__tg_id))

            # Определение критериев доступности кнопки оповещения бота об оплате
            participants_count = int(event['participants_count'])
            user_place_on_list = next(i + 1 for i, item in enumerate(event_user)
                                      if item['user__tg_id'] == user__tg_id)
            availible_pay = True if (user_place_on_list <= participants_count
                                     and paid_check is None
                                     and payment_confirmed is None) else False
            availible_notify_by_payment = True if user_place_on_list <= participants_count else None

        trn_info = await training_info_formation(call_mess=call_mess, is_admin=is_admin,
                                           event=event, event_user=event_user,
                                           signed_up_for_training=signed_up_for_training,
                                           payment_confirmed=payment_confirmed,
                                           availible_pay=availible_pay,
                                           availible_notify_by_payment=availible_notify_by_payment)
        mess_handler = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
        await mess_handler.answer(trn_info['text'], parse_mode='HTML', reply_markup=trn_info['keyboard'])
        asyncio.create_task(delete_bkg(call_mess))
    except Exception as e:
        await logger.error(f'Ошибка в choose_event: {e}')
        # stream_logger.error(f'Ошибка в choose_event: {e}')
