import logging

from functools import reduce

from aiogram import Router, F, BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject, InlineQuery
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from typing import Callable, Dict, Any, Awaitable

import app.database.requests as db_req  # импортирование модуля запросов к БД

from app.calendar import NewCalendar

from app.schedule import update
from datetime import datetime, timedelta, time, date, timezone
from aiogram_calendar import SimpleCalendarCallback

import app.keyboards as kb
import app.states as st

from app.tutorial import TUTORIAL, ADMIN_TUTORIAL, SIGN_UP_FOR_TRAINING_TUTORIAL, MARKS_DESCRIPTION

from config import TRAINING_TYPES, DEDLINE_TYPE


logger = logging.getLogger(__name__)
user_router = Router()

# Кэш список пользователей и дедлайнов
user_cache, dedlines = dict(), []

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
async def cmd_start(message: CallbackQuery | Message, state: FSMContext, is_admin: bool):
    try:
        if message.from_user.id not in user_cache:
            await registration(message)
            return
        await state.clear()
        message = message.message if isinstance(message, CallbackQuery) else message
        await message.answer(
            f"Добро пожаловать 😊\n"
            f"Для пользования ботом внизу слева расположено меню, "
            f"где Вы можете выбрать интересующую Вас команду."
        )
        if message.from_user.username == "radik313":
            await message.answer("Эээйй!!! Щупряк!!")
        if message.from_user.username == "Rinat_Tranzit":
            await message.answer("Мансура на тебя нет!!")
    except Exception as e:
        logger.error(e)
        return


@user_router.callback_query(F.data=='return_to_start')
async def return_to_start(call: CallbackQuery, state: FSMContext, is_admin: bool):
    await cmd_start(call, state, is_admin)


''' КНОПКИ ДЛЯ ВЫВОДА ИНСТРУКЦИЙ '''

# Вызов TUTORIAL через инлайн-кнопку или команду '/help'
@user_router.message(Command('help'))
@user_router.callback_query(F.data=='tutorial')
async def tutorial(update: CallbackQuery | Message, state: FSMContext):
    await state.clear()
    message = update.message if isinstance(update, CallbackQuery) else update
    await message.answer(TUTORIAL, parse_mode='HTML', reply_markup=await kb.return_to_start_markup(False))


@user_router.message(Command('train'))
async def show_sign_up_for_training_tutorial(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(SIGN_UP_FOR_TRAINING_TUTORIAL, parse_mode='HTML', reply_markup=await kb.return_to_start_markup(False))


@user_router.message(Command('marks'))
async def marks_description(message: Message):
    await message.answer(MARKS_DESCRIPTION, parse_mode='HTML', reply_markup=await kb.return_to_start_markup(False))


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
                         reply_markup= await kb.return_to_start_markup())
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
                                   reply_markup=await kb.edit_admins(),
                                   parse_mode='HTML')
        else:
            await call_mess.answer('Кроме Вас больше нет админов', reply_markup=await kb.edit_admins())
    except Exception as e:
        logger.error(f'Error_on admin_list: {e}\n'
                     f'user_cache = {user_cache}')
        await call_mess.answer('Возникла неизвестная ошибка.')
        await state.clear()


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
                             reply_markup=await kb.return_to_start_markup(), parse_mode='HTML')
        await state.set_state(st.EditAdminFSM.edit_admin)
    except Exception as e:
        logger.error(f'Ошибка при редактировании списка админов: {e}')
        await state.clear()
        await call.message.delete()
        await admin_list(call, state)
        await call.message.answer('Неизвестная ошибка.')


@user_router.message(st.EditAdminFSM.edit_admin)
async def finish_edit_admin(message: Message, state: FSMContext):
    try:
        tg_username = message.text.replace('@', '').strip()
        data = await state.get_data()
        admin_permissions = data['admin_permissions']
        user, tg_id = await db_req.update_admin_and_get(tg_username, admin_permissions)
        user_cache[tg_id] = user
        await message.delete()
        await admin_list(message, state)
        await message.answer('Статус изменен.')
    except Exception as e:
        logger.error(e)
        await message.delete()
        await admin_list(message, state)
        await message.answer('Данный пользователь не зарегистрирован в боте.')
        pass
    await state.clear()

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
                                      f'и отправьте в сообщении боту.')
            await state.set_state(st.DeleteTemplateFSM.delete_template)
        else:
            await call.message.answer(f'У Вас нет сохраненных шаблонов.')
    except Exception as e:
        logger.error(f'ошибка в delete_template: {e}')


@user_router.message(st.DeleteTemplateFSM.delete_template)
async def delete_template_finish(message: Message, state: FSMContext):
    try:
        template_id = int(message.text.strip())
        delete_template = await db_req.delete_template(template_id)
        if delete_template == 'OK':
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
    await message.delete()
    await message.answer(text)
    await state.clear()


@user_router.message(Command('event'))
@user_router.callback_query(F.data=='show_trainings')
async def show_trainings(update: Message | CallbackQuery, state: FSMContext, is_admin: bool):
    await state.clear()
    message = update.message if isinstance(update, CallbackQuery) else update
    await message.delete()
    events = await db_req.get_event()
    user_id = update.from_user.id
    event_user = await db_req.get_event_user(user_tg_id=user_id)
    if not events:
        await message.answer('Запланированных тренировок пока нет.')
    else:
        await message.answer(
            'Выберите тренировку.\n'
            'Тренировки, на которые Вы уже записаны, отмечены 🟢.',
            reply_markup=kb.show_events_kb(
                event_user,*events
            ),
            parse_mode='HTML'
        )
        await state.update_data(events=events)


# После выбора тренировки отображается текущий список заявишихся участников
@user_router.callback_query(F.data.startswith('choose_event'))
async def choose_event(update: CallbackQuery | Message, state: FSMContext,
                       is_admin: bool):
    try:
        data = await state.get_data()
        events = data.get('events')
        this_call_query = None # специальный флаг, определяющий работу этой функции

        if isinstance(update, CallbackQuery):
            this_call_query = True if update.data.startswith('choose_event') else False
        event_id = int(update.data.split(':')[1]) if this_call_query else data.get('event_id')
        event = next(item for item in events if item['id'] == event_id) if this_call_query else data.get('event')
        event_user = await db_req.get_event_user(event_id=event_id)


        text = await kb.show_text_about_event(event, event_user,
                                              tg_id=update.from_user.id,
                                              is_admin=is_admin)
        call_id = update.from_user.id

        await state.update_data(event_id=event_id, event=event, event_user=event_user)

        # Определение параметров отображения инлайн-клавиатуры
        availible_pay, paid_check, payment_confirmed = False, None, None
        signed_up_for_training =True if any(item['user__tg_id'] == call_id for item in event_user)\
            else False

        availible_notify_by_payment = None
        # Если пользователь ранее записался на эту тренировку, то кнопка записи на тренировку не отображается
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

        keyboard = await kb.sign_up_for_training(signed_up_for_training,
                                                 availible_pay,
                                                 admin_permissions=is_admin,
                                                 payment_confirmed=payment_confirmed,
                                                 availible_notify_by_payment=availible_notify_by_payment)
        if isinstance(update, CallbackQuery):
            await update.message.delete()
            await update.answer()
            await update.message.answer(text, parse_mode='HTML', reply_markup=keyboard)
        else:
            await update.answer(text, parse_mode='HTML', reply_markup=keyboard)
    except Exception as e:
        logger.error(e)


# Записаться на тренировку
@user_router.callback_query(F.data=='sign_up_for_training')
async def sign_up_for_training(call: CallbackQuery, state: FSMContext, is_admin: bool):
    try:
        # await call.message.delete()
        await call.message.answer('Вы записались на тренировку.\n'
                                  'Если у вас уже оплачена эта тренировка, нажмите на кнопку'
                                  '<i>"✔️ Тренировка оплачена"</i>')
        data = await state.get_data()
        user = await db_req.get_or_create_user(call.from_user, True)
        data['user_id'] = user['id']
        await db_req.create_event_user(data)
        await choose_event(call, state, is_admin)
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
    data = await state.get_data()
    user_id, event_id = data.get('user_id'), data.get('event_id')
    await db_req.delete_event_user(user_id, event_id)
    # await call.message.delete()
    await state.clear()
    await call.message.delete()
    await call.message.answer('Вы удалились из записи на тренировку.')


''' ДОСТУПНЫЕ АДМИНУ ФУНКЦИИ  '''

# Админ-панель
@user_router.message(Command('admpan'))
async def admin_panel(message: Message, state: FSMContext, is_admin: bool):
    if is_admin == True:
        await message.answer('Панель администратора', reply_markup=await kb.admin_panel())
    else:
        await message.answer('У Вас нет прав администратора')

# Инструкция для админа
@user_router.message(Command('admin'))
@user_router.callback_query(F.data=='admin_tutorial')
async def admin_tutorial(update: CallbackQuery | Message, state: FSMContext):
    await state.clear()
    message = update.message if isinstance(update, CallbackQuery) else update
    await message.answer(ADMIN_TUTORIAL, parse_mode='HTML',
                              reply_markup=await kb.return_to_start_markup(False))

# СОЗДАНИЕ ТРЕНИРОВКИ

@user_router.callback_query(F.data=='add_event')
async def add_event(call: CallbackQuery, state: FSMContext):
    await state.clear()
    templates = await db_req.get_templates()
    await call.message.answer("Шаблоны для создания тренировки",
                              reply_markup=await kb.input_template(templates=templates))
    await state.set_state(st.CreateEventFSM.template)


@user_router.message(st.CreateEventFSM.template)
async def input_template(message: Message, state: FSMContext):
    text = message.text.replace("@Sport_Salavat_Kupere_Bot", "").strip()
    event_text = ""
    data = await state.get_data()
    try:
        for index, fragment in enumerate(text.split("\n")):
            reper_index = fragment.find(":")  # реперный индекс двоеточия
            key, value = fragment[:reper_index], fragment[reper_index + 1:].strip()

            # Некоторые строки шаблона, значения которых должны соответствовать строгим форматам
            match index:
                case 2:  # дата тренировки
                    day, month, year = value.replace(" ", "").replace(",", ".").split(".")
                    event_date = date(year=int(year), month=int(month), day=int(day))
                case 3:  # время тренировки и дальнейшее формирование datetime тренировки
                    hour, minute = value.replace(" ", "").split(":")
                    event_time = time(hour=int(hour), minute=int(minute))
                    print(f"event_time= {event_time}")
                    event_datetime = datetime.combine(date=event_date, time=event_time)
                    if (event_datetime < datetime.now() + timedelta(hours=13)
                            or event_datetime > datetime.now() + timedelta(days=90)):
                        raise ValueError("unreal date")
                case 5:
                    participants_count = int(value)
                case 7:
                    boss_val = None
                    if value.strip() != "":
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
            await add_dedline_and_finish(message, state)
    except ValueError as e:
        print(f"ОШИБКА!!!: {e}")
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
                             reply_markup=await kb.input_template(text),
                             parse_mode="HTML")


@user_router.message(Command('save'))
async def skip(message: Message, state: FSMContext):
    data = await state.get_data()
    await db_req.create_template(text=data['current_template'])
    await message.answer(f"Шаблон сохранен!")


@user_router.callback_query(F.data.startswith("dedline_"), st.CreateEventFSM.dedline_type)
async def add_dedline_and_finish(call: CallbackQuery | Message, state: FSMContext):
    call_mess = call.message if isinstance(call, CallbackQuery) else call
    try:
        data = await state.get_data()
        event_text = data["event_text"]
        if 'is_update' not in data:  # если создается новая тренировка (там работает CallbackQuery)
            dedline_hour = int(call.data.split("_")[1])
            now = datetime.now()
            data["created_at"] = now
            payment_dedline = now + timedelta(hours=dedline_hour) if dedline_hour else None
            if payment_dedline:  # если для тренировки устанавалиеватся общий дедлайн
                data["event_text"] = (f"{event_text}\n"
                                      f"<b><i>Срок оплаты</i></b>: до "
                                      f"{payment_dedline.strftime("%H:%M %d.%m.%Y")}\n")
            else:  # иначе для тренировки устанавливается индивидуальный для каждого участника посуточный дедлайн
                data["event_text"] = (f"{event_text}\n"
                                      f"<b><i>Срок оплаты</i></b>: в течение суток после запси на тренировку\n")
            data["payment_dedline"] = payment_dedline

            await call.message.answer(f"<b>Создана следующая тренировка</b>:\n\n"
                                      f"{data['event_text']}\n\n")

            # Два запроса в БД: запись новой тренировки и получение её данных
            await db_req.create_event(data)
            last_event = await db_req.get_event(for_schedule=True, last_record=True)
            payment_dedline, id = last_event['payment_dedline'], last_event['id']
            dedlines.append((payment_dedline.replace(tzinfo=None), id))
            dedlines.sort()
        else:
            event_text, end_fragment = str(data["event_text"]), str(data["end_fragment"])
            event_id = int(data["event_id"])
            data["event_text"] = f'{event_text.strip()}\n{end_fragment}'
            await db_req.update_event(event_id, data)
            await call_mess.delete()
            await call_mess.answer('Тренировка отредактирована')
        await state.clear()
    except Exception as e:
        await call_mess.answer("Возникла ошибка! Повторите создание тренировки")
        logger.error(f"Ошибка при добавлении тренировки: {e}")

#----------Конец по добавке тренировки --------------

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
        await call.message.answer(text, parse_mode='HTML', reply_markup=await kb.return_to_start_markup())
        await state.set_state(st.UpdateEventUserFSM.payment_confirmed)
    except Exception as e:
        logger.error(e)


@user_router.message(st.UpdateEventUserFSM.payment_confirmed)
async def confirm_payment(message: Message, state: FSMContext, is_admin: bool):
    try:
        data = await state.get_data()
        event, event_user, verify_type = (data.get('event'), data.get('event_user'),
                                          data.get('verify_type'))
        participants_count = event['participants_count']

        # Список порядковых номеров участников, которые введены админом для подтверждения оплаты
        number_list = message.text.replace(' ', '').split(',')
        number_list = list(map(int, number_list))

        # Если админ номера (в т.ч. 0), выходящие за пределы ОСНОВНОГО СПИСКА
        if any(num > participants_count or num==0 for num in number_list):
            raise IndexError
        index_list =  list(map(lambda x: x-1, number_list))
        print(f'index_list = {index_list}')

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

        await message.delete()
        await choose_event(message, state, is_admin)
        await message.answer(report, parse_mode='HTML')


    except ValueError:
        await message.answer('Нужно <i><u>через запятую</u></i> вводить только '
                             '<b>целочисленные значения</b>. Повторите ввод.',
                             parse_mode='HTML',
                             reply_markup=await kb.return_to_start_markup(process_interrupt=True))
        return
    except IndexError:
        await message.answer(f'Допустимы только порядковые номера из '
                             f'<u>ОСНОВНОГО СПИСКА</u>.\n'
                             f'Повторите ввод.',
                             parse_mode='HTML',
                             reply_markup=await kb.return_to_start_markup(process_interrupt=True))
    except Exception as e:
        logger.error(e)
# ---------- Конец верификации оплаты ---------------


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
    keyboard = await kb.return_to_start_markup()
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
        await message.answer('Вы подтверждаете выаолнение данного действия?',
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
    await message.delete()
    await choose_event(message, state, is_admin)
    await message.answer(f'{text}\nОперация отклонена')


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
        await message.answer('Удаление тренировки отменено.')
        await choose_event(message, state, is_admin)

''' ----------- КОНЕЦ АДМИНСКИХ ФУНКЦИЙ  ------------ '''

@user_router.message(Command('test'))
async def test(message: Message):
    print(await db_req.delete_template(85))
