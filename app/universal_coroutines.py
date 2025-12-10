from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.database import requests as db_req
from app import keyboards as kb
from app import states as st
from config import setup_logger
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


async def training_info(call_mess: Message | CallbackQuery, is_admin: bool, **kwargs):
    try:
        events, training_type = kwargs['events'], kwargs['training_type']
        this_call_query = None  # специальный флаг, определяющий работу этой функции

        if isinstance(call_mess, CallbackQuery):
            this_call_query = True if call_mess.data.startswith('choose_event') else False
        event_id = int(call_mess.data.split(':')[1]) if this_call_query else kwargs['event_id']
        event = next(item for item in events if item['id'] == event_id) if this_call_query else kwargs['event']
        event_user = await db_req.get_event_user(event_id=event_id)
        text = await kb.show_text_about_event(event, event_user,
                                              tg_id=call_mess.from_user.id,
                                              is_admin=is_admin)
        text = f'<b>Тип тренировки</b>: {training_type}\n' + text
        return {
            'event': event,
            'events': events,
            'event_id': event_id,
            'event_user': event_user,
            'text': text}
    except Exception as e:
        await logger.error(f'Error on /training_text: {e}')
        # stream_logger.error(f'Error on /training_text: {e}')
        pass


# После выбора тренировки отображается текущий список заявишихся участников

async def choose_event(call_mess: Message | CallbackQuery, state: FSMContext,
                       is_admin: bool):
    try:
        data = await state.get_data()
        events, training_type = data['events'], data['training_type']

        # Дурацкий с event_id, но пока ничего лучше не получилось. Тупая перестраховкас условиями
        if 'event_id' in data and 'event' in data:
            event_id, event, events, event_user = data['event_id'], data['event'], data['events'], data['event_user']
            trn_info = await training_info(call_mess, is_admin,
                                           training_type=training_type,
                                           events=events,
                                           event_id=event_id,
                                           event=event,
                                           event_user=event_user)
        else:
            if isinstance(call_mess, CallbackQuery):
                trn_info = await training_info(call_mess, is_admin,
                                               training_type=training_type,
                                               events=events)

        event, events, event_id, event_user = (
            trn_info['event'], trn_info['events'], trn_info['event_id'], trn_info['event_user']
        )
        this_call_query = None  # специальный флаг, определяющий работу этой функции
        if isinstance(call_mess, CallbackQuery):
            this_call_query = True if call_mess.data.startswith('choose_event') else False
        call_id = call_mess.from_user.id
        await state.update_data(event_id=event_id, event=event, event_user=event_user)

        # Определение параметров отображения инлайн-клавиатуры
        availible_pay, paid_check, payment_confirmed = False, None, None
        signed_up_for_training = True if any(item['user__tg_id'] == call_id for item in event_user) \
            else False

        availible_notify_by_payment = None

        # Если пользователь ранее записался на эту тренировку, то кнопка записи на тренировку не отображается
        friend = None
        if signed_up_for_training:
            user_id, paid_check, payment_confirmed = (
                next((item['user__id'], item['paid_check'], item['payment_confirmed'])
                     for item in event_user if item['user__tg_id'] == call_id))
            await state.update_data(user_id=user_id)

            # Определение критериев доступности кнопки оповещения бота об оплате
            participants_count = int(event['participants_count'])
            user_place_on_list = next(i + 1 for i, item in enumerate(event_user)
                                      if item['user__tg_id'] == call_id)
            availible_pay = True if (user_place_on_list <= participants_count
                                     and paid_check is None
                                     and payment_confirmed is None) else False
            availible_notify_by_payment = True if user_place_on_list <= participants_count else None
            friend = next(item['friend'] for item in event_user if item['user__tg_id'] == call_id)

        keyboard = kb.sign_up_for_training(
            signed_up_for_training,
            availible_pay,
            admin_permissions=is_admin,
            payment_confirmed=payment_confirmed,
            availible_notify_by_payment=availible_notify_by_payment,
            friend=friend,
            event_id=event_id
        )
        text = trn_info['text']
        if isinstance(call_mess, CallbackQuery):
            await call_mess.message.answer(text, parse_mode='HTML', reply_markup=keyboard)
        else:
            await call_mess.answer(text, parse_mode='HTML', reply_markup=keyboard)

        await state.set_state(st.ChooseEventFSM.choose_event)

        # Специальная переделка call_mess наоборот (может это избыточно!)
        call_mess = call_mess.message if this_call_query else call_mess
        asyncio.create_task(delete_bkg(call_mess))
    except Exception as e:
        await logger.error(f'Ошибка в choose_event: {e}')
        # stream_logger.error(f'Ошибка в choose_event: {e}')
