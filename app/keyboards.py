import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import setup_logger, setup_sync_logger, TRAINING_TYPES, DAYS

logger, sync_logger = setup_logger(__name__), setup_sync_logger(__name__)


# Кнопка возврата в список инструкций
tutorial_list_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='⤴️ В список инструкций',
                          callback_data='tutorial_list'),]
])

# Кнока включения/выключения уведомлений
async def notify(receive_notifications: bool) -> InlineKeyboardMarkup:
    text = 'Отключить уведомления 🔕' if receive_notifications else 'Включить уведомления 🔔'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data='on_off_notify')]
    ])
    return keyboard

process_interrupt_kb = InlineKeyboardButton(text='⛔️ Прервать процесс', callback_data='process_interrupt')

# Кнопка возврата в стартовое меню в виде переменной и функции в зависимости от контекста
return_to_start = InlineKeyboardButton(text='⤴️ В начало', callback_data='return_to_start')


# Кнопка редактирования профиля
profile_edit_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Редактировать профиль 🖌', callback_data='profile_edit')],
        [return_to_start]
    ],
)


registration_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(
        text='🖍 Регистрация', callback_data='registration'
    )
    ]]
)


def return_to_start_markup(process_interrupt=True) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    caption = '⛔️ Прервать процесс' if process_interrupt else '⤴️ В начало'
    keyboard.button(text=caption, callback_data='return_to_start')
    return keyboard.as_markup()


# Кнопка назад
back_kb = InlineKeyboardButton(text='↩️Назад', callback_data='back')
back_kb_markup = InlineKeyboardMarkup(inline_keyboard=[[back_kb]])

show_training_types_kb = InlineKeyboardButton(text='📅 Выбрать тренировку 🖍', callback_data='show_training_types')

tutorial_kb = InlineKeyboardButton(text='💡 Инструкция по использованию бота📘', callback_data='tutorial')

''' КНОПКИ СТАРТОВОГО МЕНЮ АДМИН ПАНЕЛИ '''
add_event_admin_kb = InlineKeyboardButton(text='💠 Создать тренировку 🗓', callback_data='add_event')
delete_template_kb = InlineKeyboardButton(text='💠 Удалить шаблон 🗑', callback_data='delete_template')
admin_list_admin_kb = InlineKeyboardButton(text='💠 Управление списком админов 😎', callback_data='admin_list')
admin_tutorial_kb = InlineKeyboardButton(text='💠 Иструкция для админа 📕', callback_data='admin_tutorial')

async def admin_panel():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(add_event_admin_kb)
    keyboard.add(delete_template_kb)
    keyboard.add(admin_list_admin_kb)
    keyboard.add(admin_tutorial_kb)
    keyboard.adjust(1)
    return keyboard.as_markup()


# Отображает в поле ввода сообщения заготовку для создания тренировки
def input_template(current_template: str = None,
                   save: bool = False,
                   templates: list = None) -> InlineKeyboardMarkup:

    keyboard = InlineKeyboardBuilder()

    if not save:
        if current_template is None:
            template = ("Адрес зала: КЭК, Спартаковская 6\n"
                        "❗️Дата тренировки: 01.11.2025\n"
                        "❗️Время: 06:00\n"
                        "Длительность: 2 часа\n"
                        "❗️Квота участников: 12\n"
                        "Стоимость тренировки: 350\n"
                        "❗️Босс тренировки:\n"
                        "ИНФОРМАЦИЯ ОБ ОПЛАТЕ:  карта ТИНЬКОФФ 💳📍4377 7237 4025 3178📍💳. "
                        "После кидаем скрин чека @Rustambagautdinov")
            title = "Чистый шаблон"
        else:
            template, title = current_template, "Текущий шаблон"
        keyboard.add(InlineKeyboardButton(text=title,
                                          switch_inline_query_current_chat=template))

        # Формирование заголовка кнопок из загружаемых из БД шаблонгов
        if templates:
            for dct in templates:
                title = ""
                for i, item in enumerate(dct["text"].split("\n")):
                    if i < 3:
                        title += f"{item.split(':')[1].strip()}; "
                    else:
                        break
                keyboard.add(InlineKeyboardButton(text=title,
                                                  switch_inline_query_current_chat=dct["text"]))

    else:
        keyboard.button(text="Сохранить шаблон", callback_data='save_template')

    keyboard.add(process_interrupt_kb)
    keyboard.adjust(1)
    return keyboard.as_markup()


# Кнопка выбора типа дедлайна оплаты для тренировки
async def admin_dedline_type(*dedline_type) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    for dedline in dedline_type:
        keyboard.add(InlineKeyboardButton(text=dedline[0], callback_data=f"dedline_{dedline[1]}"))
    keyboard.adjust(2)
    keyboard.add(process_interrupt_kb)
    keyboard.adjust(1)
    return keyboard.as_markup()


def edit_admins() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text='Добавить админа', callback_data='edit_admin:add')
    keyboard.button(text='Удалить админа', callback_data='edit_admin:delete')
    keyboard.add(back_kb)
    keyboard.adjust(1)
    return keyboard.as_markup()


# Кнопки админа не в стартовом меню
async def admin_kb_markup(is_any_process=True) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    if not is_any_process:
        keyboard.button(text='💠 Удалить зал ❌', callback_data='delete_gym')
    caption = '⤴️ Прервать процесс' if is_any_process else '⤴️ В начало'
    keyboard.button(text=caption, callback_data='return_to_start')
    return keyboard.as_markup()


async def start_menu(admin_perm=False) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.add(show_training_types_kb)
    keyboard.add(tutorial_kb)
    if admin_perm:
        keyboard.add(add_event_admin_kb)
        keyboard.add(admin_list_admin_kb)
        keyboard.add(delete_template_kb)
    keyboard.adjust(1)
    return keyboard.as_markup()


async def keyboard_builder(prefix: str, lst: list,
                           return_to_start_for_interrupt=True
                           ) -> InlineKeyboardMarkup:

    try:
        keyboard = InlineKeyboardBuilder()
        for i, item in enumerate(lst):
            text, index = item, i  # Если итерируемый элемент не кортеж
            if isinstance(item, tuple):
                text = f"{item[1]} {item[0]}"
            if isinstance(item, dict):
                index = item['id']
                text = item['info']
            keyboard.button(text=text, callback_data=f"{prefix}:{index}")
        if return_to_start_for_interrupt:
            keyboard.add(InlineKeyboardButton(text='⤴️ Прервать процесс', callback_data="return_to_start"))
        else:
            keyboard.add(return_to_start)
        keyboard.adjust(1)
        return keyboard.as_markup()
    except Exception as e:
        await logger.error(f"err = {e}")
        # base_logger.error(f"err = {e}")


# Инлайн-клавиатура для отображения всех запланированных тренировок
def show_events_kb(event_user: list, *args) -> InlineKeyboardMarkup:
    try:
        keyboard = InlineKeyboardBuilder()
        events_id_list = [item['event__id'] for item in event_user]

        for arg in args:
            tag = '🟢' if arg['id'] in events_id_list else ''
            for i, item in enumerate(arg['event_text'].split('\n')):
                if i > 2:
                    break
                fragment = item.split(':')[1].strip() if i < 2 else f"{item.split(':')[1]}:{item.split(':')[2]}"
                match i:
                    case 0: gym = fragment
                    case 1: event_date = fragment
                    case 2: event_time = fragment
            # Добавляем день недели к кнопкам
            day_idx = arg['event_datetime'].weekday()
            day = DAYS[day_idx]
            text = tag + ' (' + day + ') ' + event_date + ', ' + event_time + '; ' + gym
            keyboard.button(text=text, callback_data=f"choose_event:{arg['id']}")
        keyboard.add(back_kb)
        keyboard.adjust(1)
        return keyboard.as_markup()
    except Exception as e:
        sync_logger.error(f'Ошибка строка 193 = {e}')
        # base_logger.error(f'Ошибка строка 193 = {e}')


# Фрмирование текста по тренировке со списком участников
async def show_text_about_event(event: dict, event_user: list,
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


# Кнопки под списком участников тренировки
def sign_up_for_training(
        signed_up_for_training: bool,
        availible_pay: bool,
        admin_permissions=False, payment_confirmed=False,
        availible_notify_by_payment: bool = None,
        **kwargs
) -> InlineKeyboardMarkup:
    try:
        keyboard = InlineKeyboardBuilder()
        if signed_up_for_training is False:
            keyboard.add(InlineKeyboardButton(
                text='🟢 Записаться на тренировку',
                callback_data='sign_up_for_training'
            ))
        else:
            keyboard.add(InlineKeyboardButton(
                text='🔴 Удалиться из тренировки',
                callback_data='delete_from_training'
            ))

        ''' Эта кнопка доступна при соблюдении 2 условий: участник в основном списке, поле 'payment_confirmed'
        в БД not True. Пока не подтвердил оплату, кнопки уведомдления или отмены уведомсления об оплате доступны '''
        if payment_confirmed is not True and signed_up_for_training:
            if availible_pay:
                text, call = '✔️ Тренировка оплачена', 'payment_notify:i_payed_check'
            else:
                text, call = '✖️ Отменить оповещение об оплате', 'payment_notify:i_chancelled_check'

            # Кнопка уведомления об оплате или её отмена доступна, только если участник не в резерве
            if availible_notify_by_payment:
                keyboard.button(text=text, callback_data=call)

        keyboard.button(text='🤜🏽Записать друга🤛🏽', callback_data='add_friend')

        if admin_permissions:
            if 'event_id' in kwargs:
                event_id = int(kwargs['event_id'])
                keyboard.button(
                    text='💠🤵🏻‍♂️ Администрирование тренировки',
                    callback_data=f'training_manage:{event_id}'
                )
        keyboard.add(back_kb)
        keyboard.adjust(1)
        return keyboard.as_markup()
    except Exception as e:
        sync_logger.error(f'Ошибка в siggn_up_for_training: {e}')
        # base_logger.error(f'Ошибка в siggn_up_for_training: {e}')


# Кнопки администрирования тренировки
admin_train_manag_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='💠 Отмена верификации 🔘', callback_data='verify_payment:change')],
    [InlineKeyboardButton(text='💠 Подтвердить оплату ✅', callback_data='verify_payment:confirm')],
    [InlineKeyboardButton(text='💠 Опровергнуть оплату ❌', callback_data='verify_payment:refute')],
    [InlineKeyboardButton(text='💠 Присвоить звезду ⭐️', callback_data='give_star')],
    [InlineKeyboardButton(text='💠 Сдвинуть в конец очереди ⬇️', callback_data='drop_or_chancel:replace_to_end')],
    [InlineKeyboardButton(text='💠 Удалить участника 🚷', callback_data='drop_or_chancel:participant')],
    [InlineKeyboardButton(text='💠 Редактировать тренировку ✏️', callback_data=f'edit_event')],
    [InlineKeyboardButton(text='💠 🚫 ОТМЕНИТЬ ТРЕНИРОВКУ 💥', callback_data='drop_or_chancel:chancel_training')],
    [back_kb],
])


# Клавиатура подтверждения удаления или перемещения в конец очереди участника
drop_participant_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Да', callback_data='drop_paricipant:yes'),
     InlineKeyboardButton(text='Нет', callback_data='drop_paricipant:No')]
])


# Клавиатура подтверждения добавления друга
add_friend_confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Да', callback_data='add_friend:yes'),
     InlineKeyboardButton(text='Нет', callback_data='add_friend:No')]
])


# Клавиатура для вставки текущего шаблона редактируемой тренировки
async def insert_template_on_edit_admin(template: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Вставить текущий шаблон тренировки',
                              switch_inline_query_current_chat=template)]
    ])
    return keyboard


# Выбор типа тренировки
def training_types_kb(**kwargs) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    for i, item in enumerate(TRAINING_TYPES):
        keyboard.add(InlineKeyboardButton(text=item, callback_data=f'training_type:{i}'))
    if 'raiting' in kwargs:
        keyboard.add(InlineKeyboardButton(text='🔥ОБЩИЙ РЕЙТИНГ💫', callback_data='training_type:general'))
    if 'without_back' not in kwargs:
        keyboard.add(back_kb)
    keyboard.adjust(1)
    return keyboard.as_markup()

''' Функция, возвращающая инлайновые кнопки по записи на спортивные тренировки. 
Состав отображемых кнопок зависит от входных условий. Например, кнопка добавления
чека будет доступна толдко после того, как пользователь запишется на тренировку '''
training_sign_up_kb = InlineKeyboardMarkup(inline_keyboard =[
    [InlineKeyboardButton(text='Записаться на тренировку', callback_data='sign_up_to_section')],
    [InlineKeyboardButton(text='Загрузить чек об оплате', callback_data='check_upload'),
     InlineKeyboardButton(text='Удалить чек об оплате', callback_data='check_delete')]])
