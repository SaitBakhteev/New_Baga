from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.universal_keyboards import RETURN_TO_START_BUTTON


registration_kb = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='🖍 Регистрация', callback_data='registration')]]
)


profile_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='Редактировать имя 🖌', callback_data='profile_edit')],
        [InlineKeyboardButton(text='Редактировать подписку на уведомления 🔔', callback_data='subscription_edit')],
        [RETURN_TO_START_BUTTON]
    ],
)


def notify(receive_notifications: bool) -> InlineKeyboardMarkup:
    text = 'Отключить уведомления 🔕' if receive_notifications else 'Включить уведомления 🔔'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data='on_off_notify')]
    ])
    return keyboard
