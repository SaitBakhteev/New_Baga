from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.admin_keyboards.admin_keyboards import CANCEL_ADMIN_OPERATION_BUTTON


class CreateProductKeyboards():
    interrupt_kb = InlineKeyboardMarkup(inline_keyboard=[[CANCEL_ADMIN_OPERATION_BUTTON]])

    def __init__(self, edit_mode=False):
        self.edit_mode = edit_mode

    def _skip_kb(self, call_data: str) -> InlineKeyboardButton:
        button = InlineKeyboardButton(text="Пропустить этот шаг ➡️", callback_data=call_data)
        return button

    def interplace_kb(self, call_data: str) -> InlineKeyboardMarkup:
        buttons = [[self._skip_kb(call_data)], [CANCEL_ADMIN_OPERATION_BUTTON]]
        if self.edit_mode:
            buttons.append([InlineKeyboardButton(text="📥 Заменить", callback_data="add_new_product")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
        ])
        return keyboard


def manage_product_kb(current_index: int) -> list[InlineKeyboardButton]:
    buttons = [
        InlineKeyboardButton(text="Редактировать 📝", callback_data=f"edit_product:{current_index}"),
        InlineKeyboardButton(text="Удалить 🗑",  callback_data=f"delete_product:{current_index}")
    ]
    return buttons
