from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.universal_keyboards import RETURN_TO_START_BUTTON, training_types_list_kb


def choose_raiting_kb() -> InlineKeyboardMarkup:
    keyboard = training_types_list_kb('to_raiting_type_is')
    keyboard.add(InlineKeyboardButton(text='🔥ОБЩИЙ РЕЙТИНГ💫', callback_data='general_statistics'))
    keyboard.add(InlineKeyboardButton(text='🔥ОБЩИЙ РЕЙТИНГ СИМПАТИЙ 💚', callback_data='likes_statistics'))
    keyboard.add(RETURN_TO_START_BUTTON)
    keyboard.adjust(1)
    return keyboard.as_markup()
