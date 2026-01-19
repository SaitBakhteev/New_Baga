from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Union

from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.constants import TRAINING_TYPES

BACK_TEXT_KB = '⤴️ Назад'

# Универсальная кнопка прерываний различных действий, возврата назад, отмены и прочее
def interrupt_or_return_button(
        callback_data: str, text='⛔️ Прервать процесс', this_markup=True
) -> Union[InlineKeyboardMarkup, InlineKeyboardButton]:
    button = InlineKeyboardButton(text=text, callback_data=callback_data)
    return InlineKeyboardMarkup(inline_keyboard=[[button]]) if this_markup else button


RETURN_TO_START_BUTTON = interrupt_or_return_button(text='🏠 В начало', callback_data='to_start',
                                                    this_markup=False)


# Внутренняя функция формирования списка инлайн-кнопок типов тренировок
def training_types_list_kb(prefix: str) -> InlineKeyboardBuilder:
    '''Prefix определяет контекст работы кнопок'''
    keyboard = InlineKeyboardBuilder()
    for i, item in enumerate(TRAINING_TYPES):
        keyboard.add(InlineKeyboardButton(text=item, callback_data=f'{prefix}:{i}'))
    return keyboard
