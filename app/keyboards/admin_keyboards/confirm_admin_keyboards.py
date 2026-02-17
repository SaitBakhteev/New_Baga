from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def give_stars_continue_kb(event_id: int) -> InlineKeyboardMarkup:
   keyboard = InlineKeyboardMarkup(inline_keyboard=[
       [InlineKeyboardButton(text='Да', callback_data='give_stars_continue: Yes')],
       [InlineKeyboardButton(text='Нет', callback_data=f'to_manage_of_event_is: {event_id}')]
])
   return keyboard