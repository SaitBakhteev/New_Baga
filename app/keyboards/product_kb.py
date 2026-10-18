from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from ..keyboards.admin_keyboards.products_kb import manage_product_kb, change_position_product_kb
from ..keyboards.universal_keyboards import RETURN_TO_START_BUTTON


def show_products_kb(data: dict, is_admin: bool) -> InlineKeyboardMarkup:
    current_index = data["current_index"]
    left_index = data['left_index']
    right_index = data['right_index']

    buttons = []  # общий список кнопок
    nav_row = []  # верхний ряд кнопок навигации
    if left_index is not False:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"product_index:{left_index}"))
    nav_row.append(InlineKeyboardButton(text=" ", callback_data=f"None"))
    if right_index:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"product_index:{right_index}"))
    buttons.append(nav_row)
    if is_admin:  # нижний админский ряд кнопок редактирования и удаления текущего товара
        buttons.append(manage_product_kb(current_index))
        buttons.append(change_position_product_kb(current_index))
    buttons.append([want_announcement_kb(False)])
    buttons.append([RETURN_TO_START_BUTTON])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def want_announcement_kb(is_markup: bool=True):
    txt, call_data = "Разместить своё объявление 📌", "want_announcement"
    keyboard = InlineKeyboardButton(text=txt, callback_data=call_data)
    if is_markup:
        buttons = [[keyboard], [RETURN_TO_START_BUTTON]]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    else:
        return keyboard
