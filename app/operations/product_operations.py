import asyncio
from string import capwords

from aiogram.types import CallbackQuery, FSInputFile

from ..operations.often_ops_and_classes import ParentClassForTrainingOperations, delete_bkg, cmd_start
from ..keyboards.admin_keyboards.products_kb import manage_product_kb
from ..keyboards.product_kb import show_products_kb
from config.constants import products


class ShowProducts(ParentClassForTrainingOperations):
    async def dispatch(self):
        if self._handler.data == "show_products":
            await self.show_product(begin_show_products=True)
        elif self._handler.data.startswith("product_index"):
            await self.show_product()

    # Счетчик индексов кнопок
    def product_index_counter(self, begin_show_products=False):
        current_index = int(self._handler.data.split(":")[1]) if not begin_show_products else 0
        left_index = current_index - 1 if current_index > 0 else False
        right_index = current_index + 1 if current_index < len(products) - 1 else False
        return {"current_index": current_index, "left_index": left_index, "right_index": right_index}

    async def show_product(self, begin_show_products=False):
        data = self.product_index_counter(begin_show_products)
        product = products[data["current_index"]]
        keyboard = show_products_kb(data, self._is_admin)

        caption = ""
        if product.title:
            caption += f"📌 <b>{product.title}</b>\n"
        if product.sale:
            caption += f"💵 <b><i>{product.sale}</i></b>\n\n"
        caption += f"{product.description}\n"

        await self._handler.message.answer_photo(photo=FSInputFile(product.photo),
                                         caption=caption, parse_mode="HTML",
                                         reply_markup=keyboard)
        await self._handler.answer()
        asyncio.create_task(delete_bkg(self._handler))
