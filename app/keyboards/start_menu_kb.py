from aiogram.types.inline_keyboard_button import InlineKeyboardButton
from aiogram.types.inline_keyboard_markup import InlineKeyboardMarkup


start_menu_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📅 Выбрать тренировку 🏃🏼‍♂️", callback_data="/event")],
    [InlineKeyboardButton(text="⭐️ Рейтинг 🔥", callback_data="/rait")],
    [InlineKeyboardButton(text="📔 Мой профиль 🙍🏻", callback_data="/prof")],
    [InlineKeyboardButton(text="🏷️ Объявления 📌", callback_data="show_products")],
    [InlineKeyboardButton(text="👁 Админ панель 🔑", callback_data="/admpan")],
    [InlineKeyboardButton(text="🛠 Сведения о разработчике", callback_data="/dev")],
])