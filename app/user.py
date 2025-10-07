import logging
import os

import asyncio
from functools import reduce

from aiogram import Router, F, BaseMiddleware, Bot
from aiogram.types import Message, CallbackQuery, TelegramObject, BufferedInputFile
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from typing import Callable, Dict, Any, Awaitable

import app.database.requests as db_req  # импортирование модуля запросов к БД

from app.schedule import message, delete_events
from datetime import datetime, timedelta, time, date, timezone

import app.keyboards as kb
import app.states as st

from app.tutorial import TUTORIAL, ADMIN_TUTORIAL, SIGN_UP_FOR_TRAINING_TUTORIAL, MARKS_DESCRIPTION, VIDEO_TUTORIAL, VIDEO_ADMIN_TUTORIAL

from config import TRAINING_TYPES, DEDLINE_TYPE

from config import SEASON_INDEX, season_index

BOT_NAME = os.getenv('BOT_NAME')

logger = logging.getLogger(__name__)
user_router = Router()

# Кэш список пользователей и дедлайнов
user_cache, dedlines, dedline_notifications = dict(), [], []

# Мидлварь для проверки прав пользователя
class AdminMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        # Проверяем, является ли пользователь администратором
        if isinstance(event, (Message, CallbackQuery)):
            user_tg_id = event.from_user.id

            ''' Здесь несеольео нелогичный код, он чисто для перестраховки, если вдруг
            при первом входе что-то пойдет не так при создании пользователя в БД.
            Также перестраховка по поводжу перезапускасервера  '''

            if user_tg_id not in user_cache:
                # Вот это обращение к БД после первой регистарции
                user = await db_req.get_or_create_user(event.from_user)
                if not user:
                    if isinstance(event, CallbackQuery) and event.data == "registration":
                        return await handler(event, data)
                    else:
                        await registration(event)
                        return
                user_cache[user_tg_id] = user
                data["is_admin"] = None

                # Здесь возвращаем при первом входе пользователя или перезапуске сервера
                return await handler(event, data)
            else:
                if user_cache[user_tg_id] is None:  # вот это скорее лишний запрос к БД на всякий случай
                    user_cache[user_tg_id] = await db_req.get_or_create_user(event.from_user)

            user = user_cache[user_tg_id]

            if user:
                data["is_admin"] = True if (event.from_user.username=='Rustambagautdinov'
                                            or event.from_user.username=='2SaitBakhteev') \
                    else user.admin_permissions
            else:
                data["is_admin"] = False
        # data["is_admin"] = False
        logger.info(f'event.from_user.username={event.from_user.username}')
        # Передаем управление следующему обработчику
        # print(f'user_cache[e] = {user_cache[tg_id]}')
        return await handler(event, data)

user_router.message.middleware(AdminMiddleware())
user_router.callback_query.middleware(AdminMiddleware())


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


@user_router.callback_query(F.data=='registration')
async def registration_callback_query(call: CallbackQuery, state: FSMContext):
    await db_req.get_or_create_user(from_user=call.from_user, create_user=True)
    await call.message.delete()

    # Прихожится дублировать это сообющение, поскольку переход на cmd_start после первичной регистрации не работает
    await call.message.answer(
        f"Добро пожаловать 😊\n"
        f"Для пользования ботом внизу слева расположено меню, "
        f"где Вы можете выбрать интересующую Вас команду."
    )


# ----- ОБРАБОТКА /start -----------
@user_router.message(CommandStart())
async def cmd_start(call_mess: CallbackQuery | Message, state: FSMContext, is_admin: bool):
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
        if call_mess.from_user.username == "radik313":
            await call_mess.answer("Эээйй!!! Щупряк!!")
        if call_mess.from_user.username == "Rinat_Tranzit":
            await call_mess.answer("Мансура на тебя нет!!")
    except Exception as e:
        logger.error(e)
        return


# Кнопка прерывания
@user_router.callback_query(F.data=='process_interrupt')
async def process_interrupt(call: CallbackQuery, state: FSMContext,  is_admin: bool):
    if is_admin:
        current_state = await state.get_state()
        match current_state:
            case st.CreateEventFSM.dedline_type | st.CreateEventFSM.training_type | st.CreateEventFSM.template:
                await state.clear()
                await admin_panel(call, state, is_admin)
            case st.ChooseEventFSM.training_type:
                await state.clear()
                await show_training_types(call.message, state, is_admin)
    else:
        pass
    asyncio.create_task(delete_bkg(call))


@user_router.callback_query(F.data=='return_to_start')
async def return_to_start(call: CallbackQuery, state: FSMContext, is_admin: bool):
    current_state = await state.get_state()
    match current_state:
        case st.AddFriendFSM.add_friend | st.DeleteFromTrainingFSM.delete_from_training | st.ChooseEventFSM.give_star:
            await choose_event(call.message, state, is_admin)
        case st.CreateEventFSM.dedline_type | st.EditAdminFSM.edit_admin | st.DeleteTemplateFSM.delete_template:
            await state.clear()
            await admin_panel(call, state, is_admin)

    if current_state != st.DeleteFromTrainingFSM.delete_from_training:
        asyncio.create_task(delete_bkg(call))


@user_router.callback_query(F.data=='back')
async def back(call: CallbackQuery, state: FSMContext, is_admin: bool):
    current_state = await state.get_state()
    match current_state:
        case st.ChooseEventFSM.training_type:
            await show_training_types(call.message, state)
        case st.ChooseEventFSM.choose_event:
            await state.set_state(st.ChooseEventFSM.training_type)
            await show_events(call.message, state)
        case st.CreateEventFSM.training_type | st.EditAdminFSM.show_list:
            await admin_panel(call, state, is_admin)
        case st.ChooseEventFSM.admin_management:
            await state.set_state(st.ChooseEventFSM.training_type)
            await show_events(call.message, state)
    asyncio.create_task(delete_bkg(call))


''' КНОПКИ ДЛЯ ВЫВОДА ИНСТРУКЦИЙ '''

# Вызов TUTORIAL через инлайн-кнопку или команду '/help'
@user_router.message(Command('help'))
@user_router.callback_query(F.data=='tutorial')
async def tutorial(call_mess: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    message = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
    await message.answer(VIDEO_TUTORIAL, parse_mode='HTML',
                         reply_markup=kb.back_kb_markup)


async def load_video(message: Message, bot: Bot, file_name: str):
    await message.answer('Подождите, загружается видеоинструкция ...')
    file_path = f'media/{file_name}.mp4'
    with open(file_path, 'rb') as video_file:
        await bot.send_video(
            chat_id=message.from_user.id,
            video=BufferedInputFile(video_file.read(),
                                    filename=file_path)
        )


@user_router.message(Command('gen'))
async def general_tut(message: Message, bot: Bot):
    await load_video(message, bot, 'general_new_render')


@user_router.message(Command('sign'))
async def general_tut(message: Message, bot: Bot):
    await load_video(message, bot, 'sign_rend')


@user_router.message(Command('met'))
async def general_tut(message: Message, bot: Bot):
    await load_video(message, bot, 'tags_rend')


@user_router.message(Command('train'))
async def show_sign_up_for_training_tutorial(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(SIGN_UP_FOR_TRAINING_TUTORIAL, parse_mode='HTML',
                         reply_markup= kb.return_to_start_markup(False))


@user_router.message(Command('marks'))
async def marks_description(message: Message):
    await message.answer(MARKS_DESCRIPTION, parse_mode='HTML', reply_markup=kb.return_to_start_markup(False))


# Важные рекомендации о действиях после записи
@user_router.message(Command('rec'))
async def queue(message: Message):
    text = ('🔹\n'
            'Если вы оплатили за тренировку, настоятельно рекомендуется оповестить об этом бот. '
            'Для этого нажмите <i>"✔️ Тренировка оплачена"</i>.\n'
            '\n🔹\n'
            'Кнопка <i>"✔️ Тренировка оплачена"</i> доступна <u>ТОЛЬКО</u> участникам со статусом ⚠️;\n'
            '\n🔹\n'
            'Участники со статусами ⚠️ и ❌ при наступлении <i>ДЕДЛАЙНА</i> перемещаются ботом '
            'в конец очереди.\n\n'
            'Более подробную информацию читайте в <b>/train</b> и <b>/marks</b>.\n\n')
    await message.answer(text, parse_mode='HTML')


# Сообщения о багах от пользователей
@user_router.message(Command('bug'))
async def bug(message: Message, state:FSMContext):
    await message.answer('Напишите о проблеме работы бота и отправьте сообщение.',
                         reply_markup= kb.return_to_start_markup())
    await state.set_state(st.WrightBugsFSM.wright_bug)

@user_router.message(st.WrightBugsFSM.wright_bug)
async def send_bugs_message(message: Message, state: FSMContext, is_admin:bool):
    try:
        text = message.text
        if '0' not in text:
            logger.critical(text, extra={'username': message.from_user.username})
            await message.answer('Благодарим Вас за обратную связь.')
        else:
            raise Exception
    except Exception as e:
        await message.answer('Извините возникла ошибка.\n'
                             'Возможно причина в отстуствии имени аккаунта телеграмм.')
        logger.error('Error on /bugs')
        pass
    await state.clear()


# Включение/выключение получения уведомлений
@user_router.message(Command('ntf'))
async def ntf(message: Message, state: FSMContext):
    await state.clear()
    user = await db_req.get_or_create_user(message.from_user, for_telegramm=True)
    receive_notifications = user['receive_notifications']
    await message.answer('Изменение настроек уведомлений',
                         reply_markup= await kb.notify(receive_notifications))
    await state.update_data(receive_notifications=receive_notifications)

@user_router.callback_query(F.data=='on_off_notify')
async def on_off_notify(call: CallbackQuery, state: FSMContext):
    receive_notifications = await db_req.update_user_receive_notificcations(call.from_user.id)
    await call.message.delete()
    text = 'Уведомления включены 🔔' if receive_notifications else 'Уведомления отключены 🔕'
    await call.message.answer(text)


@user_router.message(Command('event'))
@user_router.callback_query(F.data=='show_training_types')
async def show_training_types(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('Выберите тип тренировки', reply_markup=kb.training_types_kb(without_back=True))
    await state.set_state(st.ChooseEventFSM.training_type)


async def show_events(message: Message, state: FSMContext):
    data = await state.get_data()
    training_type = data['training_type']
    events = await db_req.get_event(training_type=training_type)
    event_ids = [i['id'] for i in events]
    event_user = await db_req.get_event_user(user_tg_id=message.chat.id, event_ids=event_ids)

    if not events:
        await message.answer('Запланированных тренировок пока нет.')
        await state.clear()
    else:
        await message.answer(
            f'Ближайшие тренировки по дисциплине <b><i>{training_type}</i></b>.\n'
            'Тренировки, на которые Вы уже записаны, отмечены 🟢.',
            reply_markup=kb.show_events_kb(
                event_user,*events
            ),
            parse_mode='HTML'
        )
        await state.update_data(events=events)

async def training_info(call_mess: Message | CallbackQuery, state: FSMContext, is_admin: bool):
    try:
        data = await state.get_data()
        events, training_type = data.get('events'), data['training_type']
        this_call_query = None  # специальный флаг, определяющий работу этой функции

        if isinstance(call_mess, CallbackQuery):
            this_call_query = True if call_mess.data.startswith('choose_event') else False
        event_id = int(call_mess.data.split(':')[1]) if this_call_query else data.get('event_id')
        event = next(item for item in events if item['id'] == event_id) if this_call_query else data.get('event')
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
        logger.error('Error on /training_text')
        pass

# После выбора тренировки отображается текущий список заявишихся участников
@user_router.callback_query(F.data.startswith('choose_event'))
async def choose_event(call_mess: Message | CallbackQuery, state: FSMContext,
                       is_admin: bool):
    try:
        trn_info = await training_info(call_mess, state, is_admin)
        event, events, event_id, event_user = trn_info['event'], trn_info['events'], trn_info['event_id'], trn_info['event_user']
        this_call_query = None  # специальный флаг, определяющий работу этой функции
        if isinstance(call_mess, CallbackQuery):
            this_call_query = True if call_mess.data.startswith('choose_event') else False

        call_id = call_mess.from_user.id

        await state.update_data(event_id=event_id, event=event, event_user=event_user)

        # Определение параметров отображения инлайн-клавиатуры
        availible_pay, paid_check, payment_confirmed = False, None, None
        signed_up_for_training =True if any(item['user__tg_id'] == call_id for item in event_user)\
            else False

        availible_notify_by_payment = None

        # Если пользователь ранее записался на эту тренировку, то кнопка записи на тренировку не отображается
        friend = None
        if signed_up_for_training:
            user_id, paid_check, payment_confirmed = (
                next((item['user__id'], item['paid_check'], item['payment_confirmed'])
                     for item in event_user if item['user__tg_id'] == call_id))
            await state.update_data(user_id = user_id)

            # Определение критериев доступности кнопки оповещения бота об оплате
            participants_count = int(event['participants_count'])
            user_place_on_list = next(i+1 for i, item in enumerate(event_user)
                                      if item['user__tg_id']==call_id)
            availible_pay = True if (user_place_on_list <= participants_count
                                     and paid_check is None
                                     and payment_confirmed is None ) else False
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
        logger.error(e)


# Записаться на тренировку
@user_router.callback_query(F.data=='sign_up_for_training')
async def sign_up_for_training(call: CallbackQuery, state: FSMContext, is_admin: bool):
    try:
        await call.message.answer('Вы записались на тренировку.\n'
                                  'Если у вас уже оплачена эта тренировка, нажмите на кнопку'
                                  '<i>"✔️ Тренировка оплачена"</i>')
        data = await state.get_data()
        user = await db_req.get_or_create_user(call.from_user, True)
        data['user_id'] = user['id']
        await db_req.create_event_user(data)
        await choose_event(call, state, is_admin)
        await state.set_state(st.ChooseEventFSM.sign_up_for_training)
    except Exception as e:
        logger.error(e)


# Оповестить бот об оплате кнопкой '✔️ Тренировка оплачена'
@user_router.callback_query(F.data.startswith('payment_notify'))
async def payment_notify(call: CallbackQuery, state: FSMContext, is_admin: bool):
    try:
        call_data = call.data.split(':')[1]
        data = await state.get_data()
        user_id, event_id = data['user_id'], data['event_id']
        payment_notify = True if call_data == "i_payed_check" else False
        await db_req.update_event_user(user_id, event_id, payment_notify)
        await choose_event(call, state, is_admin)
        if payment_notify is not True:
            await call.message.answer('❗️<b>ВНИМАНИЕ</b>❗️\n'
                                      'Вы отменили уведомление об оплате. Но это не '
                                      'означает автоматический возврат денежных средств, если '
                                      'Вы уже оплатили. Поэтому для возврата денежных средств обратитесь '
                                      'к админу тренировки.')
    except Exception as e:
        logger.error(e)


# Удалиться из тренировки
@user_router.callback_query(F.data=='delete_from_training')
async def delete_from_training(call: CallbackQuery, state: FSMContext, is_admin: bool):
    await call.message.answer('Если Вы уверены, что хотите удалиться из тренировки '
                              'напишите в сообщении <i><b>да</b></i> и отправьте его.\n'
                              'Если сомневаетесь, прервите процесс или отправьте любое слово',
                              reply_markup=kb.return_to_start_markup(),
                              parse_mode='HTML')
    await state.set_state(st.DeleteFromTrainingFSM.delete_from_training)


@user_router.message(st.DeleteFromTrainingFSM.delete_from_training)
async def delete_from_training_confirm(message: Message, state: FSMContext, is_admin: bool):
    if message.text.lower().strip() == 'да':
        data = await state.get_data()
        user_id, event_id = data.get('user_id'), data.get('event_id')

        await db_req.delete_event_user(user_id, event_id)
        await message.answer('Вы удалились из записи на тренировку.')
        asyncio.create_task(delete_bkg(message))
        await cmd_start(message, state, is_admin)
    else:
        await message.answer('Удаление прервано')
        await choose_event(message, state, is_admin)


# Записать друга на тренировку
@user_router.callback_query(F.data=='add_friend')
async def add_friend(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введите никнейм вашего друга.\n'
                              '<i>Пример</i>: @ivanov1934',
                              parse_mode='HTML', reply_markup=kb.return_to_start_markup())
    await state.set_state(st.AddFriendFSM.add_friend)


@user_router.message(st.AddFriendFSM.add_friend)
async def add_friend(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        event_id = data.get('event_id')
        text = message.text.strip().replace('@', '')
        if text != message.from_user.username:
            friend = None
            for k in user_cache:
                if user_cache[k].tg_username == text:
                    friend_id, friend = user_cache[k].id, user_cache[k].tg_username
                    break
            if friend is not None:
                ''' Проверяем не записывался ли ранее мой друг (friend_signed_up) и не
                записывал ли я кого-нибудь жо этого (my_prev_friend) '''
                friend_signed_up = await db_req.get_event_user_for_check_friend(event_id, friend_id=friend_id)
                my_prev_friend = await db_req.get_event_user_for_check_friend(
                    event_id, i_am_friend=message.from_user.username
                )

                if not friend_signed_up and not my_prev_friend:
                    message_text = ('⚠️ Внимание! Записать друга на тренировку можно только <b>один раз</b>!\n'
                                    'Вы подтверждаете запись друга?')
                    await state.update_data(friend_id=friend_id, friend=friend)
                    await state.set_state(st.AddFriendFSM.add_friend_confirm)
                    return await message.answer(message_text, reply_markup=kb.add_friend_confirm_kb, parse_mode='HTML')
                elif friend_signed_up:
                    message_text = f'☑️ Ваш друг с никнеймом <i>{friend}</i> уже состоит в записи на тренировку'
                elif my_prev_friend:
                    message_text = f'⛔️ Вы ранее уже записали друга с никнеймом <i>{my_prev_friend}</i>'
            else:
                message_text = f'🤷🏻‍♂️ Пользователь с никнеймом <i>{text}</i> не зарегистрирован в боте'
        else:
            message_text = '☝🏽Вы не можете добавить себя вместо друга'
        await message.answer(message_text, parse_mode='HTML', reply_markup=kb.return_to_start_markup())
    except Exception as e:
        logger.error(f'Add+friend: {e}')


@user_router.callback_query(F.data.startswith('add_friend') and st.AddFriendFSM.add_friend_confirm)
async def add_friend_confirm(call: CallbackQuery, state: FSMContext, is_admin: bool):
    call_data = call.data.split(':')[1]
    data = await state.get_data()
    friend_id, friend = data['friend_id'], data['friend']
    if call_data == 'yes':
        await db_req.create_event_user(data, friend_id=friend_id, i_am_friend=call.from_user.username)
        await call.message.answer(f'Вы успешно записали друга с никнеймом <i>{friend}</i> на тренировку 🖍')
    else:
        await call.message.answer(f'Вы отменили запись друга на тренировку🟡')
    await state.set_state(None)  # выходим из состояния, чтобы кнопки дезактивировались
    await choose_event(call, state, is_admin)


''' ДОСТУПНЫЕ АДМИНУ ФУНКЦИИ  '''

# Функция, которая определяет из БД учатников по веденным порядковым номерам
async def participant_list_formation(call_mess: Message | CallbackQuery, state: FSMContext, is_admin: bool):
    try:
        data = await state.get_data()
        event = data.get('event')

        call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
        participants_count = event['participants_count']

        # Список порядковых номеров участников, которые введены админом для подтверждения оплаты
        number_list = call_mess.text.replace(' ', '').split(',')
        number_list = list(map(int, number_list))

        # Если админ ввел номера (в т.ч. 0), выходящие за пределы ОСНОВНОГО СПИСКА
        if any(num > participants_count or num == 0 for num in number_list):
            raise IndexError
        index_list = list(map(lambda x: x - 1, number_list))
        asyncio.create_task(delete_bkg(call_mess))
        return index_list
    except ValueError:
        await call_mess.answer('Нужно <i><u>через запятую</u></i> вводить только '
                             '<b>целочисленные значения</b>. Повторите ввод.',
                             parse_mode='HTML',
                             reply_markup=kb.return_to_start_markup(process_interrupt=True))
        raise
    except IndexError:
        await call_mess.answer(f'Допустимы только порядковые номера из '
                             f'<u>ОСНОВНОГО СПИСКА</u>.\n'
                             f'Повторите ввод.',
                             parse_mode='HTML',
                             reply_markup=kb.return_to_start_markup(process_interrupt=True))
        raise


# -------------- Список админов ----------------
@user_router.callback_query(F.data=='admin_list')
async def admin_list(call_mess: CallbackQuery | Message, state: FSMContext):
    call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
    try:
        text = ''
        for k in user_cache:
            if user_cache[k].admin_permissions == True:
                text += f'{user_cache[k].tg_username}\n'
        if len(text) > 0:
            await call_mess.answer(f'<b><i>Текущий список админов</i></b>:\n{text}',
                                   reply_markup=kb.edit_admins(),
                                   parse_mode='HTML')
            await state.set_state(st.EditAdminFSM.show_list)
        else:
            await call_mess.answer('Кроме Вас больше нет админов', reply_markup=kb.edit_admins())
    except Exception as e:
        logger.error(f'Error_on admin_list: {e}\n'
                     f'user_cache = {user_cache}')
        await call_mess.answer('Возникла неизвестная ошибка.')
        await state.clear()
        await admin_panel(call_mess, state, True)
        asyncio.create_task(delete_bkg(call_mess))


@user_router.callback_query(F.data.startswith('edit_admin:'))
async def edit_admin(call: CallbackQuery, state: FSMContext):
    try:
        call_data = call.data.split(':')[1]
        admin_permissions = True if call_data == 'add' else False
        await state.update_data(admin_permissions=admin_permissions)
        await state.set_state(st.EditAdminFSM.edit_admin)
        await call.message.answer('Введите никнейм телеграмм-аккаунта ❗️<i>без "@"</i>❗️, '
                                  'для которого хотите установить или отменить админский статус.\n '
                                  '<i>Например, если у пользователя аккаунт <u>"@Ivanov_79"</u>, то '
                             'нужно ввести <u>"Ivanov_79"</u></i>.',
                             reply_markup=kb.return_to_start_markup(), parse_mode='HTML')
        await state.set_state(st.EditAdminFSM.edit_admin)
    except Exception as e:
        logger.error(f'Ошибка при редактировании списка админов: {e}')
        await call.message.answer('Неизвестная ошибка.')
        await state.clear()
        await admin_panel(call, state, True)
        asyncio.create_task(delete_bkg(call))


@user_router.message(st.EditAdminFSM.edit_admin)
async def finish_edit_admin(message: Message, state: FSMContext):
    try:
        tg_username = message.text.replace('@', '').strip()
        data = await state.get_data()
        admin_permissions = data['admin_permissions']
        user, tg_id = await db_req.update_admin_and_get(tg_username, admin_permissions)
        user_cache[tg_id] = user
        await message.answer('Статус изменен.')
    except Exception as e:
        logger.error(e)
        await message.answer('Данный пользователь не зарегистрирован в боте.')
        pass
    await state.clear()
    await admin_list(message, state)
    asyncio.create_task(delete_bkg(message))

# ---------- Конец редактирования списка админов ---------------

# ----------- Удаление шаблонов ---------------
@user_router.callback_query(F.data == 'delete_template')
async def delete_template(call: CallbackQuery, state: FSMContext):
    try:
        templates = await db_req.get_templates()
        tempale_list_text = ''
        if templates:
            for template in templates:
                id, text = template['id'], template['text']
                tempale_list_text += f'<b>{id}</b>. {text}\n\n'
            await call.message.answer(f'{tempale_list_text}\n\n'
                                      f'Введите id шаблона (выделен жирным шрифтом), который хотите удалить '
                                      f'и отправьте в сообщении боту.',
                                      reply_markup=kb.return_to_start_markup())
            await state.set_state(st.DeleteTemplateFSM.delete_template)
        else:
            await call.message.answer(f'У Вас нет сохраненных шаблонов.')
    except Exception as e:
        logger.error(f'ошибка в delete_template: {e}')
        await admin_panel(message, state, True)
        asyncio.create_task(delete_bkg(call))


@user_router.message(st.DeleteTemplateFSM.delete_template)
async def delete_template_finish(message: Message, state: FSMContext):
    try:
        template_id = int(message.text.strip())
        var_delete_template = await db_req.delete_template(template_id)
        if var_delete_template == 'OK':
            text = 'Шаблон удален'
        else:
            text = 'Возможно Вы ввели несуществующий id шаблона. Операция отменена'
    except ValueError:
        text = 'Значение id шаблона должно быть в формате целого числа. Операция отменена'
        pass
    except Exception as e:
        logger.error(f'unknown error on delete_template_finish: {e}')
        text = 'Возникла неизвестная ошибка. Операция отклонена'
        pass
    await message.answer(text)
    await state.clear()
    await admin_panel(message, state, True)


# Админ-панель
@user_router.message(Command('admpan'))
async def admin_panel(call_mess: Message | CallbackQuery, state: FSMContext, is_admin: bool):
    call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
    if is_admin == True:
        await call_mess.answer('Панель администратора', reply_markup=await kb.admin_panel())
    else:
        await call_mess.answer('У Вас нет прав администратора')


# Видео-Инструкция для админа
@user_router.message(Command('admin'))
@user_router.callback_query(F.data=='admin_tutorial')
async def admin_tutorial(call_mess: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    message = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
    await message.answer(VIDEO_ADMIN_TUTORIAL, parse_mode='HTML')


@user_router.message(Command('adm_cre'))
async def general_tut(message: Message, bot: Bot):
    await load_video(message, bot, 'create_event')


@user_router.message(Command('adm_nts'))
async def general_tut(message: Message, bot: Bot):
    await load_video(message, bot, 'main_notes')


@user_router.message(Command('adm_vrf'))
async def general_tut(message: Message, bot: Bot):
    await load_video(message, bot, 'verify')


@user_router.message(Command('adm_trs'))  # сдвинуть участников, удалить тренровку
async def general_tut(message: Message, bot: Bot):
    await load_video(message, bot, 'transfer')    


@user_router.message(Command('adm_edt'))  # редактировать тренровку
async def general_tut(message: Message, bot: Bot):
    await load_video(message, bot, 'edit_event')    


# СОЗДАНИЕ ТРЕНИРОВКИ

@user_router.callback_query(F.data=='add_event')
async def add_event(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("Выберите тип создаваемой тренировки",
                              reply_markup=kb.training_types_kb())
    await state.set_state(st.CreateEventFSM.training_type)
    asyncio.create_task(delete_bkg(call))


@user_router.callback_query(F.data.startswith('training_type'), st.ChooseEventFSM.training_type)
@user_router.callback_query(F.data.startswith('training_type'), st.CreateEventFSM.training_type)
async def choose_training_type(call: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    training_index = int(call.data.split(':')[1])
    training_type = TRAINING_TYPES[training_index]
    await state.update_data(training_type=training_type)
    if current_state == st.ChooseEventFSM.training_type:
        await show_events(call.message, state)
    else:
        templates = await db_req.get_templates()
        await call.message.answer('Выберите шаблон',
                                  reply_markup=kb.input_template(templates=templates))
        await state.set_state(st.CreateEventFSM.template)
    asyncio.create_task(delete_bkg(call))


@user_router.message(st.CreateEventFSM.template)
async def input_template(message: Message, state: FSMContext):
    text = message.text.replace(f"{BOT_NAME}", "").strip()
    event_text = ""
    data = await state.get_data()
    try:
        for index, fragment in enumerate(text.split("\n")):
            reper_index = fragment.find(":")  # реперный индекс двоеточия
            key, value = fragment[:reper_index], fragment[reper_index + 1:].strip()

            # Некоторые строки шаблона, значения которых должны соответствовать строгим форматам
            match index:
                case 1:  # дата тренировки
                    day, month, year = value.replace(" ", "").replace(",", ".").split(".")
                    event_date = date(year=int(year), month=int(month), day=int(day))
                case 2:  # время тренировки и дальнейшее формирование datetime тренировки
                    hour, minute = value.replace(" ", "").split(":")
                    event_time = time(hour=int(hour), minute=int(minute))
                    event_datetime = datetime.combine(date=event_date, time=event_time)
                    if (event_datetime < datetime.now() + timedelta(hours=13)
                            or event_datetime > datetime.now() + timedelta(days=90)):
                        raise ValueError("unreal date")
                case 4:
                    participants_count = int(value)
                case 6:
                    boss_val = None  # на всякий случай, поскольку дебаггер показал непонятки
                    if value.strip() != "" and value.strip() != "-":
                        boss_val = value.strip().replace('@', '')
                        boss = await db_req.get_user_by_username(boss_val)
                        if boss:
                            boss_id = boss
                        else:
                            raise ValueError(f"User does not exist")
                    else:  # если никнейм босса не вводить, то None
                        boss_id = None
            # Формирование текста о создаваемой тренировке
            if index < len(text.split("\n")) - 1:
                if 'Босс тренировки' not in key:
                    event_text += f"<b>{key}</b>: {value}\n"
                else:
                    value = f'@{value}' if boss_id is not None else '-'
                    value.replace('@@', '@')  # ещё одна перестраховка
                    event_text += f"<b>{key}</b>: {value}\n"
            else:
                event_text += (f"\n<b>ИНФОРМАЦИЯ ОБ ОПЛАТЕ</b>:\n"
                              f"{value}")
        event_text = event_text.replace("❗️", "")
        await state.update_data(event_text=event_text,
                                event_datetime=event_datetime,
                                participants_count=participants_count,
                                current_template=text,
                                boss_id=boss_id)
        if 'is_update' not in data:
            await message.answer("Если хотите сохранить шаблон, нажмите на /save\n"
                                 "Выберите дедлайн оплаты за тренировку",
                                 reply_markup=await kb.admin_dedline_type(*DEDLINE_TYPE))
            await state.set_state(st.CreateEventFSM.dedline_type)
        else:
            await add_dedline_and_finish(message, state, True)

    except ValueError as e:
        if str(e) == "month must be in 1..12":
                error_message = "Некорректно введен месяц"
        elif str(e) == "unreal date":
            error_message = ("Тренировка не может быть запланирована менее, чем за <u>13 часов</u> "
                             "и более, чем за <u>90 дней</u>.")
        elif str(e) == "minute must be in 0..59":
            error_message = ("Некорректное значение минут")
        elif str(e) == "hour must be in 0..23":
            error_message = ("Некорректное значение часов")
        elif str(e).startswith("invalid literal for int() with base 10"):
            error_message = ("Строка со знаком ❗️ содержит некорректное значение")
        elif str(e) == "day is out of range for month":
            error_message = "Введен несуществующий день месяца."
        elif str(e) == "User does not exist":
            error_message = "Для босса тренировки такой никнейм пользователя в боте не зарегистрирован."
        else:
            error_message = "Ошибка в формате иного плана, проверьте внимательно"

        await message.answer(f"{error_message}.\n"
                             f"Повторите действия, начиная со вставки шаблона.",
                             reply_markup=kb.input_template(text),
                             parse_mode="HTML")
        asyncio.create_task(delete_bkg(message))


@user_router.message(Command('save'))
async def skip(message: Message, state: FSMContext):
    data = await state.get_data()
    await db_req.create_template(text=data['current_template'])
    await message.answer(f"Шаблон сохранен!")
    asyncio.create_task(delete_bkg(message))


@user_router.callback_query(F.data.startswith("dedline_"), st.CreateEventFSM.dedline_type)
async def add_dedline_and_finish(call_mess: CallbackQuery | Message, state: FSMContext, is_admin: bool):
    call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
    try:
        data = await state.get_data()
        event_text = data["event_text"]
        if 'is_update' not in data:  # если создается новая тренировка (там работает CallbackQuery)
            dedline_hour = int(call_mess.data.split("_")[1]) if isinstance(call_mess, CallbackQuery) \
                else None
            now = datetime.now()
            data["created_at"] = now
            payment_dedline = now + timedelta(hours=dedline_hour) if dedline_hour else None
            if payment_dedline:  # если для тренировки устанавалиеватся общий дедлайн
                data["event_text"] = (f"{event_text}\n"
                                      f"<b><i>Срок оплаты</i></b>: до "
                                      f"{payment_dedline.strftime('%H:%M %d.%m.%Y')}\n")
            else:  # иначе для тренировки устанавливается индивидуальный для каждого участника посуточный дедлайн
                data["event_text"] = (f"{event_text}\n"
                                      f"<b><i>Срок оплаты</i></b>: в течение суток после записи на тренировку\n")
            data["payment_dedline"] = payment_dedline

            await call_mess.answer(f"<b>Создана следующая тренировка</b>:\n\n"
                                      f"<b>Тип тренировки</b>: {data['training_type']}\n"
                                      f"{data['event_text']}\n\n")

            # Два запроса в БД: запись новой тренировки и получение её данных
            await db_req.create_event(data)
            last_event = await db_req.get_event(for_schedule=True, last_record=True)
            payment_dedline, id = last_event['payment_dedline'], last_event['id']

            # Обновление списка дедлайнов
            dedlines.append((payment_dedline.replace(tzinfo=None), id))
            dedlines.sort()
            notificate_datetime = payment_dedline.replace(tzinfo=None) - timedelta(hours=1)
            dedline_notifications.append((notificate_datetime, id))
            dedline_notifications.sort()
            await state.clear()
        else:
            event_text, end_fragment = str(data["event_text"]), str(data["end_fragment"])
            event_id = int(data["event_id"])
            data["event_text"] = f'{event_text.strip()}\n{end_fragment}'
            await db_req.update_event(event_id, data)
            event = await db_req.get_event(id=event_id)
            await call_mess.answer('Тренировка отредактирована')
            await state.update_data(event=event[0])
            await choose_event (call_mess, state, is_admin)
    except Exception as e:
        await call_mess.answer("Возникла ошибка! Повторите создание тренировки")
        logger.error(f"Ошибка при добавлении тренировки: {e}")
    asyncio.create_task(delete_bkg(call_mess))

#----------Конец по добавке тренировки --------------

@user_router.callback_query(F.data.startswith("training_manage"))
async def training_manage(call: CallbackQuery, state: FSMContext):
    try:
        await state.set_state(st.ChooseEventFSM.admin_management)
        trn_info = await training_info(call, state, True)
        await call.message.answer(trn_info['text'],
                                  parse_mode="HTML",
                                  reply_markup=kb.admin_train_manag_kb)
        asyncio.create_task(delete_bkg(call))
    except Exception:
        pass

# --------- Редактирование тренировки -----------
@user_router.callback_query(F.data == 'edit_event')
async def edit_event(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    template = data['event']['event_text']
    end_fragment = template[template.find('<b><i>Срок оплаты'):]
    print(f'sours: {template}')

    # Более приемлемый способ для множественной замены в большой строке
    replacements = {"<b>": "", "</b>": "", "<i>": "", "</i>": "",
                    "Дата тренировки": "❗️Дата тренировки",
                    "Время": "❗️Время",
                    "Число участников": "❗️Число участников",
                    'Босс тренировки': '❗️Босс тренировки',
                    "ИНФОРМАЦИЯ ОБ ОПЛАТЕ:\n": "Как оплатить: ",
                    "\n\n": "\n"}

    # Переделка текущего текста тренировки под шаблон для создания
    template = reduce(lambda fragment, kv: fragment.replace(*kv), replacements.items(), template)
    template = template[:template.find('Срок оплаты')]  # урезаем до фразы срок оплаты

    await state.update_data(is_update=True, end_fragment=end_fragment)
    await state.set_state(st.CreateEventFSM.template)
    await call.message.answer('Вставьте текущий шаблон этой тренировки, '
                              'после чего отредактируйте и отправьте в сообщении боту',
                              reply_markup=await kb.insert_template_on_edit_admin(template))

# ------------ Конец редактирования тренировки ----------

@user_router.callback_query(F.data.startswith('verify_payment:'))
async def payment_verification(call: CallbackQuery, state: FSMContext):
    try:
        # Нажата кнопка '✅ Подтвердить оплату' или '❌ Опровергнуть оплату'
        verify_type = call.data.split(':')[1]
        await state.update_data(verify_type=verify_type)

        if verify_type == 'change':
            text = ("Вы выбрали тип верификации <i>'✖️ Отменить верификацию оплаты'</i>. "
                    "Данное действие вы можете осуществить для участников с <u>любым</u> статусом.\n")

        elif verify_type == 'confirm':
            text = ("Вы выбрали тип верификации <i>'✅ Подтвердить оплату'</i>. "
                    "Данное действие вы можете осуществить только для участников со статусами ✔️, ⚠️ и ❌.\n")

        else:
            text = ("Вы выбрали тип верификации <i>'❌ Опровергнуть оплату'</i>. "
                    "Данное действие вы можете осуществить только для участников со статусом ✔️. "
                    "Если ни один из выбранных вами участников не будет соответствовать данному критерию, "
                    "то бот отменит операцию.\n")

        text += ('\n Чтобы выполнить соответсвующую верификацию, наберите <i><u>через запятую</u></i> порядковые '
                 'номера участников в вышеприведенном списке👆🏻 в виде <u>сообщения</u>, после чего отправьте его боту.\n'
                 'Например, для верификации 3-го, 5-го и 8-го участников в списке наберите сообщение так:\n'
                 '<i><b>3, 5, 8</b></i>\n\n'
                 "<i>Примечание</i>: статусы могут быть обновлены <u>частично</u> или вовсе <u>не обновлены</u>.\n"
                 'С более подробной иформацией можете ознакомиться в <b>/admin</b>')
        await call.message.answer(text, parse_mode='HTML', reply_markup=kb.return_to_start_markup())
        await state.set_state(st.UpdateEventUserFSM.payment_confirmed)
    except Exception as e:
        logger.error(e)


@user_router.message(st.UpdateEventUserFSM.payment_confirmed)
async def confirm_payment(message: Message, state: FSMContext, is_admin: bool):
    try:
        data = await state.get_data()
        event, event_user, verify_type = (data.get('event'), data.get('event_user'),
                                          data.get('verify_type'))
        index_list = await participant_list_formation(message, state, is_admin)

        # Формирование списка id объектов EventUser для обновления в БД значений поля 'payment_confirmed'
        if verify_type == 'change':  # Отменить верификацию оплаты ✖️
            id_list = [event_user[i]['id'] for i in index_list]
        elif verify_type == 'confirm':  # Подтвердить платеж можно только, если поле 'payment_confirmed' не True
            id_list = [event_user[i]['id'] for i in index_list if event_user[i]['payment_confirmed'] is not True]
        else: # Опровергнуть платеж можно, если 'payment_confirmed' пустое и 'paid_check' не пустое
            id_list = [event_user[i]['id'] for i in index_list if event_user[i]['payment_confirmed'] is None
                       and event_user[i]['paid_check'] is not None]

        # Обновление в БД
        if len(id_list) > 0:
            if verify_type=='change':
                await db_req.update_event_user_for_payment_verify(id_list, is_confirm=None)
            elif verify_type=='refute':
                await db_req.update_event_user_for_payment_verify(id_list, is_confirm=False)
            else:
                await db_req.update_event_user_for_payment_verify(id_list)
            report = ('👁‍🗨 Обновление статусов проведено <i>частично</i>. '
                      'Причины описаны в <b>/admin</b>.') if len(id_list)<len(number_list)\
                else '🔷 Статусы всех указанных участников обновлены.'
        else:
            report = '🛑 Статусы <b>не обновлены</b>. Причины описаны в <b>/admin</b>.'

        await message.answer(report, parse_mode='HTML')
        await choose_event(message, state, is_admin)
        asyncio.create_task(delete_bkg(message))

    except Exception as e:
        logger.error(e)
# ---------- Конец верификации оплаты ---------------


# --------- Присвоить звезду. Начало -------------

@user_router.callback_query(F.data=='give_star')
async def give_star(call: CallbackQuery, state: FSMContext):
    await state.set_state(st.ChooseEventFSM.give_star)
    await call.message.answer('Введите через запятую порядковые номера игроков, которым хотите присвоить звезду',
                              reply_markup=kb.return_to_start_markup())


@user_router.message(st.ChooseEventFSM.give_star)
async def give_star_confirm(message: Message, state: FSMContext, is_admin: bool):
    try:
        index_list = await participant_list_formation(message, state, is_admin)
        await message.answer('Суперстар')
    except Exception:
        return
# --------- Присвоить звезду. Конец -------------


# ---------- Исключение участников или перемещение в конец очереди, отмена тренировки ---------------
@user_router.callback_query(F.data.startswith('drop_or_chancel'))
async def drop_or_chancel(call: CallbackQuery, state: FSMContext):
    call_data = call.data.split(':')[1]
    if call_data != 'chancel_training':
        await state.update_data(call_data=call_data)
        fragment = 'исключить из тренировки' if call_data == 'participant' else 'переместить в конец очереди'
        text = (f'Укажите в сообщении боту порядковый номер участника, которого '
                f'хотите <b><i><u>{fragment}</u></i></b> и отправьте это сообщение.')
        await state.set_state(st.DropParticipantFromTrainFSM.waiting)
    else:
        text = ('Если точно хотите отменить эту тренировку, введите "да" '
                'в сообщении боту, иначе операция будет отменена.')
        await state.set_state(st.ChancelTraininigFSM.chancel_training)
    keyboard = kb.return_to_start_markup()
    await call.message.answer(text, reply_markup=keyboard, parse_mode='HTML')


# Промежуточное состояние, требующее подтверждения операции удаления или перемещения в конец очереди участника

@user_router.message(st.DropParticipantFromTrainFSM.waiting)
async def drop_participant_middlware_state(message: Message, state: FSMContext, is_admin: bool):
    try:
        data = await state.get_data()
        event_user, event_id = data.get('event_user'), data.get('event_id')
        index = int(message.text) # порядковый номер участника

        if index > len(event_user) or index == 0:
            raise IndexError

        user_id = next(item['user__id'] for i, item in enumerate(event_user) if i==index-1)
        await state.update_data(user_id=user_id)
        await message.answer('Вы подтверждаете выполнение данного действия?',
                             reply_markup=kb.drop_participant_kb)
        return

    except ValueError:
        text = 'Допустим ввод только одного целого числа.'
        pass
    except IndexError:
        text = 'Таких порядковых номеров нет в списке.'

        pass
    except Exception as e:
        logger.error(e)
        text = 'Возникла неизвестная ошибка.'
        pass

    await state.set_state(None)
    await choose_event(message, state, is_admin)
    await message.answer(f'{text}\nОперация отклонена')
    asyncio.create_task(delete_bkg(message))


@user_router.callback_query(F.data.startswith('drop_paricipant'))
async def drop_participant(call: CallbackQuery, state: FSMContext, is_admin: bool):
    if call.data.split(':')[1] == 'yes':
        data = await state.get_data()
        call_data = data['call_data']  # удаляем или перемещаем в конец очереди
        user_id, event_id = data['user_id'], data['event_id']
        if call_data == 'participant':  # удаление участника из тренировки
            await db_req.delete_event_user(user_id, event_id=event_id)
            text = 'Участник удален.'
        else:  # перемещение участника в конец очереди
            await db_req.update_event_user(user_id, event_id, replace_to_end=True)
            text = 'Участник перемещен в конец очереди.'
    else:
        text = 'Операция отменена.'
    await call.message.delete()
    await choose_event(call.message, state, is_admin)
    await call.message.answer(text)

@user_router.message(st.ChancelTraininigFSM.chancel_training)
async def chancel_training_state(message: Message, state: FSMContext, is_admin: bool):
    await state.set_state(None)
    if message.text.lower() == 'да':
        data = await state.get_data()
        event_id = data.get('event_id')
        await db_req.delete_event(event_id)
        await message.answer('Тренировка удалена.')
    else:
        await message.delete()
        await message.answer('Удаление тренировки отменено.')
        await state.set_state(None)

''' ----------- КОНЕЦ АДМИНСКИХ ФУНКЦИЙ  ------------ '''

@user_router.message(Command('test'))
async def test(message: Message):
    await delete_events()


    # await season_index(True)
    # print(f'SEASON_INDEX = {SEASON_INDEX[0]}')