from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

tutorial_list_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='⤴️ В список инструкций', callback_data='tutorial_list'), ]
])
