from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.universal_keyboards import RETURN_TO_START_BUTTON


registration_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='🖍 Регистрация', callback_data='registration')]]
)
profile_edit_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Редактировать профиль 🖌', callback_data='profile_edit')],
        [RETURN_TO_START_BUTTON]
    ],
)


async def notify(receive_notifications: bool) -> InlineKeyboardMarkup:
    text = 'Отключить уведомления 🔕' if receive_notifications else 'Включить уведомления 🔔'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data='on_off_notify')]
    ])
    return keyboard
