from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.universal_keyboards import RETURN_TO_START_BUTTON, training_types_list_kb


def choose_raiting () -> InlineKeyboardMarkup:
    keyboard = training_types_list_kb('to_raiting_type_is')
    keyboard.add(InlineKeyboardButton(text='🔥ОБЩИЙ РЕЙТИНГ💫', callback_data='show_general_statistics'))
    keyboard.add(RETURN_TO_START_BUTTON)
    return keyboard.as_markup()
