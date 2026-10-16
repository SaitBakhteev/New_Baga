import asyncio
import traceback

from aiogram.types import FSInputFile, CallbackQuery
from aiogram.exceptions import TelegramNetworkError

from ..operations.often_ops_and_classes import ParentClassForTrainingOperations, delete_bkg, cmd_start
from ..keyboards.product_kb import show_products_kb
from config.constants import products, user_cache


class ShowProducts(ParentClassForTrainingOperations):
    def __init__(self, handler, state, is_admin, current_index=None):
        super().__init__(handler, state, is_admin)
        self._current_index = current_index

    async def dispatch(self):
        if self._handler.data == "show_products":
            await self.show_product(begin_show_products=True)
        elif self._handler.data.startswith("product_index"):
            await self.show_product()

    # Счетчик индексов кнопок
    def product_index_counter(self, begin_show_products=False):
        if self._current_index is None:
            current_index = int(self._handler.data.split(":")[1]) if not begin_show_products else 0
        else:
            current_index = self._current_index
        left_index = current_index - 1 if current_index > 0 else False
        right_index = current_index + 1 if current_index < len(products) - 1 else False
        return {"current_index": current_index, "left_index": left_index, "right_index": right_index}

    async def show_product(self, begin_show_products=False):
        try:
            data = self.product_index_counter(begin_show_products)
            product = products[int(data["current_index"])]
            keyboard = show_products_kb(data, self._is_admin)

            caption = ""
            if product.title:
                caption += f"📌 <b>{product.title}</b>\n"
            if product.sale:
                caption += f"💵 <b><i>{product.sale}</i></b>\n\n"
            caption += f"{product.description}\n"

            handler = self._handler.message if isinstance(self._handler, CallbackQuery) else self._handler
            await handler.answer_photo(photo=FSInputFile(product.photo),
                                       caption=caption, parse_mode="HTML",
                                       reply_markup=keyboard)
            asyncio.create_task(delete_bkg(self._handler))
        except TelegramNetworkError as e:
            await self._state.clear()
            await cmd_start(self._handler, self._state, self._is_admin, user_cache)
            await self._handler.message.answer("🚫 Возникла ошибка при загрузке фото")
