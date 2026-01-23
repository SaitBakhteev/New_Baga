from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.universal_keyboards import interrupt_or_return_button, training_types_list_kb, RETURN_TO_START_BUTTON

from config.log_config import setup_sync_logger
from config.constants import DAYS, TRAINING_TYPES

from .universal_keyboards import BACK_TEXT_KB

sync_logger = setup_sync_logger(__name__)


# КНОПКИ ПО ВЫБОРУ ТИПА ТРЕНИРОВОК В ЗАВИСИМОСТИ ОТ КОНТЕКСТА
# ===========================================================

def choose_training_type_kb() -> InlineKeyboardMarkup:
    keyboard = training_types_list_kb('to_training_type_is')
    keyboard.add(RETURN_TO_START_BUTTON)
    keyboard.adjust(1)
    return keyboard.as_markup()


# ОТОБРАЖЕНИЕ ТРЕНИРОВОК
# =====================

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
            keyboard.button(text=text, callback_data=f"to_event_is:{arg['id']}")
        _text, _callback_data = BACK_TEXT_KB, '/event'
        keyboard.add(interrupt_or_return_button(text=BACK_TEXT_KB, callback_data=_callback_data, this_markup=False))
        keyboard.adjust(1)
        return keyboard.as_markup()
    except Exception as e:
        sync_logger.error(f'Ошибка show_events_kb = {e}')
        # base_logger.error(f'Ошибка строка 193 = {e}')


def training_interface_kb(event: dict, event_user: list, user_id: int, admin_permissions: bool) -> InlineKeyboardMarkup:
    try:
        # Условия по записи и доступности уведомления об оплате
        signed_up_for_training = True if any(item['user__id'] == user_id for item in event_user) else False
        availible_notify_by_payment = None
        if signed_up_for_training:  # если пользователь записан на тренировку
            paid_check, payment_confirmed = (next((item['paid_check'], item['payment_confirmed'])
                                                  for item in event_user if item['user__id'] == user_id))
            # Определение критериев доступности кнопки оповещения бота об оплате
            participants_count = int(event['participants_count'])
            user_place_on_list = next(i + 1 for i, item in enumerate(event_user)
                                      if item['user__id'] == user_id)
            availible_notify_by_payment = True if (
                    user_place_on_list <= participants_count
                    and paid_check is None and payment_confirmed is None)\
                else False

        # БЛОК ФОРМИРОВАНИЯ ИНТЕРФЕЙСА ТРЕНИРОВКИ
        # =======================================

        keyboard = InlineKeyboardBuilder()
        if signed_up_for_training:
            text = '🔴 Удалиться из тренировки'
            callback_data = f'delete_from_training_is:{event['id']}'
        else:
            text = '🟢 Записаться на тренировку'
            callback_data = f'sign_up_to_training_is:{event['id']}'
        keyboard.add(InlineKeyboardButton(text=text, callback_data=callback_data))

        # Кнопка уведомления об оплате или её отмена доступна, только если участник не в резерве
        if availible_notify_by_payment:
            text, call = '✔️ Оповестить бот об оплате', f'payment_notify_by_event_is:{event['id']}'
            keyboard.button(text=text, callback_data=call)

        keyboard.button(text='🤜🏽Записать друга🤛🏽', callback_data=f'add_friend_to_event_is:{event['id']}')

        if admin_permissions:
            keyboard.button(
                text='💠🤵🏻‍♂️ Администрирование тренировки',
                callback_data=f'training_manage_of_event_is:{event['id']}'
            )
        _index = TRAINING_TYPES.index(event["training_type"])
        callback_data = f'to_training_type_is:{_index}'
        keyboard.add(interrupt_or_return_button(text=BACK_TEXT_KB, callback_data=callback_data, this_markup=False))
        keyboard.adjust(1)
        return keyboard.as_markup()
    except Exception as e:
        sync_logger.error(f'Ошибка в training_interface: {e}')
        # base_logger.error(f'Ошибка в siggn_up_for_training: {e}')
