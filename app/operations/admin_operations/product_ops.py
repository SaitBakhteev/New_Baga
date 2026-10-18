import traceback

import asyncio
from aiogram.types import CallbackQuery

from ..often_ops_and_classes import ParentClassForTrainingOperations, delete_bkg, cmd_start
from ..admin_operations.admin_operations import show_admin_panel
import app.states as st
from app.database.product_requests import create_product, update_product, delete_product, update_position
from config.constants import products, media_products_dir, BOT_NAME, redis_client
from config.log_config import setup_logger
from ..product_operations import ShowProducts
from ...keyboards.admin_keyboards.products_kb import CreateProductKeyboards, UpdateProductKeyboards
from ...keyboards.universal_keyboards import interrupt_or_return_button

logger = setup_logger(__name__)


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
        await self._handler.message.answer(msg, reply_markup=self._kb.interrupt_kb(), parse_mode="HTML")
        await self._state.set_state(st.CreateProductFSM.photo)
        # asyncio.create_task(delete_bkg(self._handler))

    async def _upload_photo_to_server(self):
        if self._handler.photo:
            file_id = self._handler.photo[-1].file_id
            file_name = f"{media_products_dir}{file_id}.jpg"
            await self._handler.bot.download(file=file_id, destination=file_name)
            await self._state.update_data(photo=file_name, title = self._handler.caption)
            await self._state.set_state(st.CreateProductFSM.sale)
            await self._handler.answer("Введите цену товара/услуги или пропустите этот шаг",
                                       reply_markup=self._kb.interplace_kb("add_description"))
            # await asyncio.create_task(delete_bkg(self._handler))
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
        await handler.answer("Введите описание товара/услуги", reply_markup=self._kb.interrupt_kb())
        await asyncio.create_task(delete_bkg(self._handler))

    async def _add_description(self):
        await self._state.update_data(description = self._handler.text)
        await self._state.set_state(st.CreateProductFSM.position)
        await self._handler.answer("Введите приоритет отображения в списке товаров/услуг 📌",
                                   reply_markup=self._kb.interrupt_kb())
        await asyncio.create_task(delete_bkg(self._handler))

    async def _add_position_and_finish(self):
        try:
            position = int(self._handler.text.replace(" ", "")) - 1
            if position < 0:
                raise ValueError("less_1")
            await self._state.update_data(position=position)
            data = await self._state.get_data()
            await create_product(data, products)
            await self._state.clear()
            await show_admin_panel(self._handler, self._state)
            await self._handler.answer("Новое объявление товара/услуги добавлено успешно 📍")
        except (TypeError, ValueError) as e:
            msg = "☝🏼 Позиция не может быть меньше 1" if str(e) == "less_1" else ("🚫 Некорректный формат числа.")
            msg += "\nПоворите ввод"
            await self._handler.answer(msg)
            return


class UpdateProduct(ParentClassForTrainingOperations):
    _kb = UpdateProductKeyboards()
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith("edit_product"):
                await self._change_photo_or_skip()
            if self._handler.data == "edit_title":
                current_index = await self._get_current_index()
                await self._state.update_data(photo=products[current_index].photo)
                await self._wait_edit_title()
            elif self._handler.data.startswith("product_index"):
                await self._state.clear()
        else:
            if await self._state.get_state() == st.UpdateProductFSM.photo:
                await self._upload_photo_to_server()
            elif await self._state.get_state() == st.UpdateProductFSM.title:
                await self._edit_title_and_wait_sale()
            elif await self._state.get_state() == st.UpdateProductFSM.sale:
                await self._edit_sale_and_wait_description()
            elif await self._state.get_state() == st.UpdateProductFSM.description:
                await self._edit_description_and_wait_position()
            elif await self._state.get_state() == st.UpdateProductFSM.position:
                await self._edit_position_and_finish()

    async def _get_current_index(self):
        data = await self._state.get_data()
        return data["current_index"]

    def _erase_bot_name(self, value: str):
        transform_value = (value.replace(f"@{BOT_NAME}", "").
                           replace(f"{BOT_NAME[1:]}", ""))
        return transform_value

    # Меняем фото или пропускаем
    async def _change_photo_or_skip(self):
        current_index = int(self._handler.data.split(":")[1])
        self._product = products[current_index]
        await self._state.update_data(current_index=current_index, product=self._product)
        msg =("Загрузите новую фотографию товара или услуги строго "
              "в формате <b>.jpg</b> <i>или пропустите этот шаг.</i>")
        keyboard = self._kb.begin_edit_kb(current_index)
        await self._handler.message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
        await self._state.set_state(st.UpdateProductFSM.photo)

    async def _upload_photo_to_server(self):
        if self._handler.photo:
            file_id = self._handler.photo[-1].file_id
            file_name = f"{media_products_dir}{file_id}.jpg"
            await self._handler.bot.download(file=file_id, destination=file_name)
            await self._state.update_data(photo=file_name)
            await self._wait_edit_title()
        else:
            await self._handler.answer('🚫 Ошибка загрузки!'
                                       'Загружать фото нужно <i><u>не как документ</u></i>')

    async def _wait_edit_title(self):
        current_index = await self._get_current_index()
        msg = f"Редактирование названия товара/услуги. <i>Если название не предусмотрено, отправьте 0</i>"
        title, txt = "Текущее название товара/услуги", products[current_index].title
        if txt is None:
            txt = ""
        keyboard = self._kb.inter_kb(title, txt,  current_index)
        handler = self._handler.message if isinstance(self._handler, CallbackQuery) else self._handler
        await handler.answer(msg, reply_markup=keyboard, parse_mode="HTML")
        await self._state.set_state(st.UpdateProductFSM.title)
        asyncio.create_task(delete_bkg(self._handler))

    async def _edit_title_and_wait_sale(self):
        title = self._handler.text
        title = title if title.strip() != "0" else None
        title = self._erase_bot_name(title)
        await self._state.update_data(title = title)
        await self._state.set_state(st.UpdateProductFSM.sale)
        current_index = await self._get_current_index()
        msg = "Редактирование цены. <i>Если хотите убрать цену поставьте 0</i> "
        sale, txt = "Текущая стоимость 💵", products[current_index].sale
        if txt is None:
            txt = ""
        keyboard = self._kb.inter_kb(sale, txt, current_index)
        await self._handler.answer(msg, reply_markup=keyboard, parse_mode="HTML")

    async def _edit_sale_and_wait_description(self):
        sale = self._erase_bot_name(self._handler.text)
        sale = sale if sale.strip() != "0" else None
        await self._state.update_data(sale=sale)
        await self._state.set_state(st.UpdateProductFSM.description)
        current_index = await self._get_current_index()
        msg, description, txt = "Редактирование описания", "Текущее описание 🗒", products[current_index].description
        keyboard = self._kb.inter_kb(description, txt, current_index)
        await self._handler.answer(msg, reply_markup=keyboard, parse_mode="HTML")
        await asyncio.create_task(delete_bkg(self._handler))

    async def _edit_description_and_wait_position(self):
        description = self._erase_bot_name(self._handler.text)
        await self._state.update_data(description = description)
        await self._state.set_state(st.UpdateProductFSM.position)
        current_index = await self._get_current_index()
        msg = "Редактирование приоритета"
        position, txt = "Текущий приоритет 🔼🔽", str(products[current_index].position+1)
        keyboard = self._kb.inter_kb(position, txt, current_index)
        await self._handler.answer(msg, reply_markup=keyboard, parse_mode="HTML")
        await asyncio.create_task(delete_bkg(self._handler))

    async def _edit_position_and_finish(self):
        try:
            position = self._erase_bot_name(self._handler.text)
            position = int(position.strip()) - 1
            if position < 0:
                raise ValueError("less_1")
            await self._state.update_data(position=position)
            current_index = await self._get_current_index()
            await self._state.update_data(current_index=current_index)
            data = await self._state.get_data()
            await update_product(data, current_index, products)
            show_product = ShowProducts(self._handler, self._state, self._is_admin, current_index)
            await show_product.show_product()
            await self._handler.answer("Товар/услуга отредактирована успешно ✏️")
        except (TypeError, ValueError) as e:
            msg = "☝🏼 Позиция не может быть меньше 1" if str(e) == "less_1" else ("🚫 Некорректный формат числа.")
            msg += "\nПоворите ввод"
            await self._handler.answer(msg)
            return
        except Exception as e:
            await cmd_start(self._handler, self._state, self._is_admin)
            await self._handler.answer("🚫 Возникла неизвестная ошибка!")
            await logger.error(f"Error on _edit_position_and_finish: {e}\n{traceback.format_exc()}")
            pass
        await self._state.clear()
        asyncio.create_task(delete_bkg(self._handler))


class DeleteProduct(ParentClassForTrainingOperations):
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith("delete_product"):
                await self._begin()
        else:
            if await self._state.get_state() == st.DeleteProductFSM.confirm:
                await self._finish()

    async def _begin(self):
        current_index = int(self._handler.data.split(":")[1])
        await self._state.update_data(current_index=current_index)
        await self._state.set_state(st.DeleteProductFSM.confirm)
        await self._handler.message.answer(
            "Отправьте <b><i>да</i></b> для подтверждения удаления.\n"
            "Для отмены действия отправьте любое другое сообщение"
        )

    async def _finish(self):
        data = await self._state.get_data()
        current_index = data["current_index"]
        if self._handler.text.strip().lower() == "да":
            product_id = products[current_index].id
            await delete_product(product_id, products)
            msg = "Объявление удалено 🗑️"
            current_index = 0
            if not products:
                redis_client.delete("promo")
        else:
            msg = "⛔️ Операция удаления отменена"
        await asyncio.create_task(delete_bkg(self._handler))
        show_prod = ShowProducts(self._handler, self._state, self._is_admin, current_index)
        await show_prod.show_product()
        await self._handler.answer(msg)


class ChangePosition(ParentClassForTrainingOperations):
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('change_position'):
                await self._change_position()
        else:
            if await self._state.get_state() == st.ChangePositionFSM.finish:
                await self._finish()

    async def _change_position(self):
        current_index = int(self._handler.data.split(":")[1])
        await self._state.update_data(current_index=current_index)
        current_position = products[current_index].position
        msg = (f"<b>Текущая позиция в карусели</b>: {current_position+1}\n"
               f"Введите новый номер позиции и отправьте сообщение боту")
        await self._state.set_state(st.ChangePositionFSM.finish)
        keyboard = interrupt_or_return_button(callback_data=f"product_index:{current_index}")
        await self._handler.message.answer(msg, reply_markup=keyboard, parse_mode="HTML")

    async def _finish(self):
        try:
            data = await self._state.get_data()
            current_index = data["current_index"]
            products[current_index].position = int(self._handler.text.strip()) - 1
            await update_position(products, current_index)
            msg = "🔝 Приоритет изменен успешно"
        except (TypeError, ValueError):
            msg = "🚫 Неверный формат. Операция отклонена"
        await asyncio.create_task(delete_bkg(self._handler))
        show_product = ShowProducts(self._handler, self._state, self._is_admin, current_index)
        await show_product.show_product(start_index=current_index)
        await self._handler.answer(msg, parse_mode="HTML")

