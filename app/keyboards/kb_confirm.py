from aiogram.types import InlineKeyboardMarkup

from .universal_keyboards import interrupt_or_return_button


def add_friend_confirm_kb(event_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [interrupt_or_return_button(text='Да',
                                    callback_data=f'add_friend_confirm_to_event_is:{event_id}',
                                    this_markup=False)],
        [interrupt_or_return_button(text='Нет',
                                    callback_data= f'to_event_is:{event_id}',
                                    this_markup=False)],
    ])
    return keyboard


def payment_notify_confirm_kb(event_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [interrupt_or_return_button(text='Да',
                                    callback_data=f'add_friend_confirm:{event_id}',
                                    this_markup=False)],
        [interrupt_or_return_button(text='Нет',
                                    callback_data=f'to_event_is:{event_id}',
                                    this_markup=False)],
    ])
    return keyboard
