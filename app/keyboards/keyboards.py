import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Union

from config import setup_logger, setup_sync_logger, TRAINING_TYPES, DAYS

logger, sync_logger = setup_logger(__name__), setup_sync_logger(__name__)


# Универсальная кнопка прерываний различных действий
def universal_interrupt_or_back_button(
        text='⛔️ Отменить действие', callback_data='interrupt', this_markup=True
) -> Union[InlineKeyboardMarkup, InlineKeyboardButton]:
    button = InlineKeyboardButton(text=text, callback_data=callback_data)
    return InlineKeyboardMarkup(inline_keyboard=[[button]]) if this_markup else button


RETURN_TO_START_BUTTON = universal_interrupt_or_back_button(text='🏠 В начало', callback_data='return_to_start',
                                                            this_markup=False)


# Кнопка возврата в список инструкций
tutorial_list_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='⤴️ В список инструкций', callback_data='tutorial_list'),]
])


# РЕГИСТРАЦИЯ, РЕДАКТИРОВАНИЕ ПРОФИЛЯ, НАСТРОЙКА УВЕДОМЛЕНИЙ
# ==========================================================

registration_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='🖍 Регистрация', callback_data='registration')]]
)


# Кнопка редактирования профиля
profile_edit_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Редактировать профиль 🖌', callback_data='profile_edit')],
        [RETURN_TO_START_BUTTON]
    ],
)


# Кнока включения/выключения уведомлений
async def notify(receive_notifications: bool) -> InlineKeyboardMarkup:
    text = 'Отключить уведомления 🔕' if receive_notifications else 'Включить уведомления 🔔'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data='on_off_notify')]
    ])
    return keyboard


# КНОПКИ ПО ТРЕНИРОВКАМ
# =====================

# Выбор типа тренировки
def training_types_kb(**kwargs) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    for i, item in enumerate(TRAINING_TYPES):
        keyboard.add(InlineKeyboardButton(text=item, callback_data=f'training_type:{i}'))
    if 'raiting' in kwargs:
        keyboard.add(InlineKeyboardButton(text='🔥ОБЩИЙ РЕЙТИНГ💫', callback_data='training_type:general'))
    if 'without_back' not in kwargs:
        keyboard.add(RETURN_TO_START_BUTTON)
    keyboard.adjust(1)
    return keyboard.as_markup()


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
        keyboard.add(universal_interrupt_or_back_button('↩️ Назад', 'return_to_choose_training_type',
                                                        False))
        keyboard.adjust(1)
        return keyboard.as_markup()
    except Exception as e:
        sync_logger.error(f'Ошибка строка 193 = {e}')
        # base_logger.error(f'Ошибка строка 193 = {e}')


# Кнопки под списком участников тренировки
def training_interface_kb(event: dict,
                          event_user: list,
                          user_id: int,
                          admin_permissions: bool) -> InlineKeyboardMarkup:
    try:
        # Условия по записи и доступности уведомления об оплате
        signed_up_for_training = True if any(item['user_id'] == user_id for item in event_user) else False
        availible_notify_by_payment = None
        if signed_up_for_training:  # если пользователь записан на тренировку
            paid_check, payment_confirmed = (next((item['paid_check'], item['payment_confirmed'])
                                                  for item in event_user if item['user_id'] == user_id))

            # Определение критериев доступности кнопки оповещения бота об оплате
            participants_count = int(event['participants_count'])
            user_place_on_list = next(i + 1 for i, item in enumerate(event_user)
                                      if item['user_id'] == user_id)
            availible_notify_by_payment = True if (
                    user_place_on_list <= participants_count
                    and paid_check is None and payment_confirmed is None)\
                else False
        ''' Находим критерии, которые определят интерфейс по кнопкам'''

        keyboard = InlineKeyboardBuilder()

        text = '🔴 Удалиться из тренировки' if signed_up_for_training else '🟢 Записаться на тренировку'
        callback_data = f'sign_up_for_training:{event['id']}' if signed_up_for_training \
            else f'delete_from_training:{event['id']}'
        keyboard.add(InlineKeyboardButton(text=text, callback_data=callback_data))

        # Кнопка уведомления об оплате или её отмена доступна, только если участник не в резерве
        if availible_notify_by_payment:
            text, call = '✔️ Оповестить бот об оплате', f'payment_notify:{event['id']}'
            keyboard.button(text=text, callback_data=call)

        keyboard.button(text='🤜🏽Записать друга🤛🏽', callback_data=f'add_friend_to_event:{event['id']}')

        if admin_permissions:
            keyboard.button(
                text='💠🤵🏻‍♂️ Администрирование тренировки',
                callback_data=f'training_manage:{event['id']}'
            )
        keyboard.add(universal_interrupt_or_back_button('↩️ Назад', f'return_to_event:{event["id"]}',
                                                        False))
        keyboard.adjust(1)
        return keyboard.as_markup()
    except Exception as e:
        sync_logger.error(f'Ошибка в training_interface: {e}')
        # base_logger.error(f'Ошибка в siggn_up_for_training: {e}')
