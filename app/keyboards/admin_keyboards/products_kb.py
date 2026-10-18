from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.admin_keyboards.admin_keyboards import CANCEL_ADMIN_OPERATION_BUTTON
from app.keyboards.universal_keyboards import interrupt_or_return_button


class CreateProductKeyboards():
    def interrupt_kb(self) -> InlineKeyboardMarkup:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[CANCEL_ADMIN_OPERATION_BUTTON]])
        return keyboard

    def __init__(self, edit_mode=False):
        self.edit_mode = edit_mode

    def _skip_kb(self, call_data: str) -> InlineKeyboardButton:
        button = InlineKeyboardButton(text="Пропустить этот шаг ➡️", callback_data=call_data)
        return button

    def interplace_kb(self, call_data: str) -> InlineKeyboardMarkup:
        buttons = [[self._skip_kb(call_data)], [CANCEL_ADMIN_OPERATION_BUTTON]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        return keyboard


class UpdateProductKeyboards():
    def _interrupt_kb(self, current_index: int) -> InlineKeyboardButton:
        return interrupt_or_return_button(f"product_index:{current_index}", this_markup=False)

    def __init__(self, edit_mode=False):
        self.edit_mode = edit_mode

    def begin_edit_kb(self, current_index:int) -> InlineKeyboardMarkup:
        buttons = [[InlineKeyboardButton(text="Пропустить этот шаг ➡️", callback_data="edit_title")],
                   [self._interrupt_kb(current_index)]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        return keyboard

    # Клавиатура промежуточных шагов
    def inter_kb(self, title, txt, current_index:int) -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton(text=f"{title}", switch_inline_query_current_chat=txt)],
            [self._interrupt_kb(current_index)]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        return keyboard


def manage_product_kb(current_index: int) -> list[InlineKeyboardButton]:
    buttons = [InlineKeyboardButton(text="Редактировать 📝", callback_data=f"edit_product:{current_index}"),
            InlineKeyboardButton(text="Удалить 🗑",  callback_data=f"delete_product:{current_index}"),]
    return buttons

def change_position_product_kb(current_index: int) -> list[InlineKeyboardButton]:
    buttons = [InlineKeyboardButton(text="Сменить приоритет 🔝", callback_data=f"change_position:{current_index}"),]
    return buttons
