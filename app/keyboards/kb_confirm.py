from aiogram.types import InlineKeyboardMarkup

from .universal_keyboards import interrupt_or_return_button



def add_friend_confirm_kb(event_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [interrupt_or_return_button('Да', f'add_friend_confirm:{event_id}', False)],
        [interrupt_or_return_button('Нет', f'to_event:{event_id}', False)],
    ])
    return keyboard


def payment_notify_confirm_kb(event_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [interrupt_or_return_button('Да', f'add_friend_confirm:{event_id}', False)],
        [interrupt_or_return_button('Нет', f'{EVENT[1]}:{event_id}', False)],
    ])
    return keyboard
