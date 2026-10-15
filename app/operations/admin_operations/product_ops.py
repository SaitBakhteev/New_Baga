import asyncio
from aiogram.types import CallbackQuery

from ..often_ops_and_classes import ParentClassForTrainingOperations, delete_bkg
from ..admin_operations.admin_operations import show_admin_panel
import app.states as st
from app.database.product_requests import create_product
from config.constants import products, media_products_dir
from ...keyboards.admin_keyboards.products_kb import CreateProductKeyboards


class CreateProduct(ParentClassForTrainingOperations):
    _kb = CreateProductKeyboards()
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data == "add_new_product":
                await self._load_photo()
            elif self._handler.data == "add_description":
                await self._add_sale_and_wait_description(sale=False)
        else:
            if await self._state.get_state() == st.CreateProductFSM.photo:
                await self._upload_photo_to_server()
            elif await self._state.get_state() == st.CreateProductFSM.sale:
                await self._add_sale_and_wait_description()
            elif await self._state.get_state() == st.CreateProductFSM.description:
                await self._add_description()
            elif await self._state.get_state() == st.CreateProductFSM.position:
                await self._add_position_and_finish()

    async def _load_photo(self):
        msg = ("Загрузите фотографию товара или услуги строго в формате <b>.jpg</b>\n"
               "Название товара можете прописать в подписи к фото")
        await self._handler.message.answer(msg, reply_markup=self._kb.interrupt_kb, parse_mode="HTML")
        await self._state.set_state(st.CreateProductFSM.photo)
        asyncio.create_task(delete_bkg(self._handler))

    async def _upload_photo_to_server(self):
        if self._handler.photo:
            file_id = self._handler.photo[-1].file_id
            file_name = f"{media_products_dir}{file_id}.jpg"
            await self._handler.bot.download(file=file_id, destination=file_name)
            await self._state.update_data(photo=file_name, title = self._handler.caption)
            await self._state.set_state(st.CreateProductFSM.sale)
            await self._handler.answer("Введите цену товара/услуги или пропустите этот шаг",
                                       reply_markup=self._kb.interplace_kb("add_description"))
            await asyncio.create_task(delete_bkg(self._handler))
        else:
            await self._handler.answer('🚫 Ошибка загрузки!'
                                       'Загружать фото нужно <i><u>не как документ</u></i>')

    # async def _add_title_and_wait_sale(self, title=True):
    #     title = self._handler.text if title is True else None
    #     await self._state.set_state(st.CreateProductFSM.title)
    #     await self._state.update_data(title = title)
    #     await self._state.set_state(st.CreateProductFSM.sale)
    #     await self._handler.answer("Введите цену", reply_markup=self._kb.interplace_kb('add_description'))
    #     await asyncio.create_task(delete_bkg(self._handler))

    async def _add_sale_and_wait_description(self, sale=True):
        sale = self._handler.text if sale is True else None
        await self._state.update_data(sale = sale)
        await self._state.set_state(st.CreateProductFSM.description)
        handler = self._handler.message if isinstance(self._handler, CallbackQuery) else self._handler
        await handler.answer("Введите описание товара/услуги", reply_markup=self._kb.interrupt_kb)
        await asyncio.create_task(delete_bkg(self._handler))

    async def _add_description(self):
        await self._state.update_data(description = self._handler.text)
        await self._state.set_state(st.CreateProductFSM.position)
        await self._handler.answer("Введите приоритет отображения в списке товаров/услуг 📌",
                                   reply_markup=self._kb.interrupt_kb)
        await asyncio.create_task(delete_bkg(self._handler))

    async def _add_position_and_finish(self):
        try:
            position = int(self._handler.text.replace(" ", "")) - 1
            await self._state.update_data(position=position)
            data = await self._state.get_data()
            await create_product(data, products)
            await self._state.clear()
            await show_admin_panel(self._handler, self._state)
            await self._handler.answer("Новое объявление товара/услуги добавлено успешно 📍")
        except (TypeError, ValueError) as e:
            await self._handler.answer("🚫 Некорректный формат числа. Потворите ввод")


class UpdateProduct(CreateProduct):
    _kb = CreateProductKeyboards(edit_mode=True)
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith("edit_product"):
                self._current_index = int(self._handler.data.split(":")[1])
                await self._load_photo()
            elif self._handler.data == "add_description":
                await self._add_sale_and_wait_description(sale=False)

    # Меняем фото или пропускаем
    async def change_photo_or_skip(self):
        msg = "Если оставляете фото и название, то пропустите этот шаг."
        keyboard = self._kb.interplace_kb("add_sale")
        await self._handler.message.answer(msg, reply_markup=keyboard)
