import logging

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


logger = logging.getLogger(__name__)


# Кнопка возврата в стартовое меню в виде переменной и функции в зависимости от контекста
return_to_start = InlineKeyboardButton(text='⤴️ В начало', callback_data='return_to_start')


async def return_to_start_markup(process_interrupt=True) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    caption = '⤴️ Прервать процесс' if process_interrupt else '⤴️ В начало'
    keyboard.button(text=caption, callback_data='return_to_start')
    return keyboard.as_markup()


# Просмотр доступных тренировок для дальнейшкей записи
show_trainings_kb = InlineKeyboardButton(text='📅 Выбрать тренировку 🖍', callback_data='show_trainings')
tutorial_kb = InlineKeyboardButton(text='💡 Инструкция по использованию бота📘', callback_data='tutorial')


''' КНОПКИ СТАРТОВОГО МЕНЮ АДМИН ПАНЕЛИ '''
add_event_admin_kb = InlineKeyboardButton(text='💠 Создать тренировку 🗓', callback_data='add_event')
delete_template_kb = InlineKeyboardButton(text='💠 Удалить шаблон 📃', callback_data='delete_template')
admin_list_admin_kb = InlineKeyboardButton(text='💠 Управление списком админов 😎', callback_data='admin_list')


# Отображает в поле ввода сообщения заготовку для создания тренировки
async def input_template(current_template: str = None,
                         save: bool = False,
                         templates: list = None) -> InlineKeyboardMarkup:

    keyboard = InlineKeyboardBuilder()

    if not save:
        if current_template is None:
            template = ("Тип тренировки: волейбол\n"
                        "Адрес зала: КЭК, Спартаковская 6\n"
                        "❗️Дата тренировки: 25.06.2025\n"
                        "❗️Время: 11:00\n"
                        "Длительность: 2 часа\n"
                        "❗️Число участников: 12\n"
                        "Стоимость тренировки: 350\n"
                        "Как оплатить: перевод на карту Сбер 1111 2222 3333 4744, Рустам Вагизович. Б")
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

    keyboard.adjust(1)
    return keyboard.as_markup()


# Кнопка выбора типа дедлайна оплаты для тренировки
async def admin_dedline_type(*dedline_type) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    for dedline in dedline_type:
        keyboard.add(InlineKeyboardButton(text=dedline[0], callback_data=f"dedline_{dedline[1]}"))
    keyboard.adjust(2)
    return keyboard.as_markup()


async def edit_admins() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text='Добавить админа', callback_data='edit_admin:add')
    keyboard.button(text='Удалить админа', callback_data='edit_admin:delete')
    keyboard.add(return_to_start)
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
    keyboard.add(show_trainings_kb)
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
        logger.error(f"err = {e}")


# Инлайн-клавиатура для отображения всех запланированных тренировок
def show_events_kb(event_user: list, *args) -> InlineKeyboardMarkup:
    try:
        keyboard = InlineKeyboardBuilder()
        events_id_list = [item['event__id'] for item in event_user]

        for arg in args:
            print('\n')
            tag = '🟢' if arg['id'] in events_id_list else ''
            for i, item in enumerate(arg['event_text'].split('\n')):
                if i > 2:
                    break
                fragment = item.split(':')[1].strip()
                match i:
                    case 0: training_type = fragment
                    case 1: gym = fragment
                    case 2: event_date = fragment
            text = tag + ' ' + training_type + '; ' + event_date + '; ' + gym
            keyboard.button(text=text, callback_data=f"choose_event:{arg['id']}")
        keyboard.add(return_to_start)
        keyboard.adjust(1)
        return keyboard.as_markup()
    except Exception as e:
        logger.error(f'err = {e}')


# Фрмирование текста по тренировке со списком участников
async def show_text_about_event(event: dict, event_user: list,
                                tg_id: int,
                                is_admin: bool=False) -> str:
    text, participants_count = event['event_text'], int(event['participants_count'])
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

        # Чтобы пользователь видел себя выделенным шрифтом в списке на тренировку
        name = f'<b><i>{name}</i></b>' if item['user__tg_id'] == tg_id else name

        text+=f"{i+1}. {name} {username}  {tag}\n"
        if i + 1 == participants_count:
            text += "\n 📌📌 <b><i>Резерв</i></b>: \n"

    text += '\n<b>❗️ВАЖНЫЕ РЕКОМЕНДАЦИИ</b> в <b>/rec</b>'

    return text


# Кнопки под списком участников тренировки
async def sign_up_for_training(
        signed_up_for_training: bool,
        availible_pay: bool,
        admin_permissions=False
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

        # Эта кнопка доступна при соблюдении 2 условий: участник в основном списке, поле 'payment_confirmed' в БД not True
        if availible_pay:
            keyboard.button(text='✔️ Тренировка оплачена', callback_data='i_payed_check')
        if admin_permissions:
            keyboard.button(text='💠 Отменить верификацию оплаты ✖️', callback_data='verify_payment:change')
            keyboard.button(text='💠 Подтвердить оплату ✅', callback_data='verify_payment:confirm')
            keyboard.button(text='💠 Опровергнуть оплату ❌', callback_data='verify_payment:refute')
            keyboard.button(text='💠 Удалить участника 🚷', callback_data='drop_or_chancel:participant')
            keyboard.button(text='💠 🚫 ОТМЕНИТЬ ТРЕНИРОВКУ 💥', callback_data='drop_or_chancel:chancel_training')
        keyboard.add(return_to_start)
        keyboard.adjust(1)
        return keyboard.as_markup()
    except Exception as e:
        logging.error(e)


''' Функция, возвращающая инлайновые кнопки по записи на спортивные тренировки. 
Состав отображемых кнопок зависит от входных условий. Например, кнопка добавления
чека будет доступна толдко после того, как пользователь запишется на тренировку '''
training_sign_up_kb = InlineKeyboardMarkup(inline_keyboard =[
    [InlineKeyboardButton(text='Записаться на тренировку', callback_data='sign_up_to_section')],
    [InlineKeyboardButton(text='Загрузить чек об оплате', callback_data='check_upload'),
     InlineKeyboardButton(text='Удалить чек об оплате', callback_data='check_delete')]])
