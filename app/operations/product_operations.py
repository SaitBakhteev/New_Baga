import asyncio
import time
import traceback

from aiogram.types import FSInputFile, CallbackQuery
from aiogram.exceptions import TelegramNetworkError

from ..operations.often_ops_and_classes import ParentClassForTrainingOperations, delete_bkg, cmd_start
from ..keyboards.product_kb import show_products_kb, want_announcement_kb
from config.constants import products, user_cache, redis_client
from config.log_config import setup_logger

logger = setup_logger(__name__)


class ShowProducts(ParentClassForTrainingOperations):
    def __init__(self, handler, state, is_admin, current_index=None):
        super().__init__(handler, state, is_admin)
        self._current_index = current_index

    async def dispatch(self):
            await redis_client.hdel("promo", self._handler.from_user.id)
            if isinstance(self._handler, CallbackQuery):
                if self._handler.data == "show_products":
                    await self.show_product(begin_show_products=True)
                elif self._handler.data.startswith("product_index"):
                    await self.show_product()
                if self._handler.data == "want_announcement":
                    await self.want_announcement()
            else:
                await self.show_product(begin_show_products=True)

    # Счетчик индексов кнопок
    def product_index_counter(self, begin_show_products=False, **kwargs):
        if "start_index" in kwargs:
            current_index = kwargs["start_index"]
        else:
            if isinstance(self._handler, CallbackQuery):
                if self._current_index is None:
                    current_index = int(self._handler.data.split(":")[1]) if not begin_show_products else 0
                else:
                    current_index = self._current_index
            else:
                current_index = 0
        left_index = current_index - 1 if current_index > 0 else False
        right_index = current_index + 1 if current_index < len(products) - 1 else False
        last_index = len(products) - 1
        return {"current_index": current_index, "left_index": left_index,
                "right_index": right_index, "last_index": last_index}

    async def show_product(self, begin_show_products=False, **kwargs):
        try:
            handler = self._handler.message if isinstance(self._handler, CallbackQuery) else self._handler
            promo_txt = ("📌📌📌📌📌📌📌\n"
                         "По вопросам размещения объявления напишите "
                         "@Rustambagautdinov или @SaitBakhteev 😌")

            if products:                # спец фильтр, чтобы сразу проверить есть ли какие-нибудь объявления
                data = self.product_index_counter(begin_show_products, **kwargs)
                product = products[int(data["current_index"])]
                keyboard = show_products_kb(data, self._is_admin)

                caption = ""
                if product.title:
                    caption += f"📌 <b>{product.title}</b>\n"
                if product.sale:
                    caption += f"💵 <b><i>{product.sale}</i></b>\n\n"

                caption += f"{product.description}\n\n<b><i>{promo_txt}</i></b>"

                await handler.answer_photo(photo=FSInputFile(product.photo),
                                           caption=caption, parse_mode="HTML",
                                           reply_markup=keyboard)
                asyncio.create_task(delete_bkg(self._handler))
            else:
                await handler.answer(f"Список объявлений товаров/услуг пока пуст 📭"
                                     f"\n<b><i>{promo_txt}</i></b>")
        except TelegramNetworkError as e:
            await logger.critical(f"Error on photo_load {e}\n: {traceback.format_exc()}")
            await self._state.clear()
            await cmd_start(self._handler, self._state, self._is_admin, user_cache)
            await self._handler.message.answer("🚫 Возникла ошибка при загрузке фото")

    async def want_announcement(self):  # хочу объявление
        await self._handler.message.answer("По вопросам размещения объявления напишите "
                                           "@Rustambagautdinov или @SaitBakhteev 😌")

    # Специалдьная функция по регулировке кэша для демонстрации промо
    async def promo_managment(self, tg_id):
        if not products:
            return
        now, dedline = time.time(), await redis_client.hget("promo", tg_id)
        if dedline:
            if float(dedline) > now:
                return

            # Пытаемся удалить. Если вернулось 1 (успех) - мы "забронировали" показ.
            is_first_click = await redis_client.hdel("promo", tg_id)
            if not is_first_click:
                return  # 4. Если 0, значит другой клик уже удалил и запустил показ. Выходим.

            async def delayed_promo():
                # Находим элемент с максимальным created_at и возвращаем его индекс
                start_index, last_prod = max(
                    enumerate(products),
                    key=lambda item: item[1].created_at
                )
                await asyncio.sleep(3)
                handler = self._handler.message if isinstance(self._handler, CallbackQuery) else self._handler
                await handler.answer(
                    f"👋 Привет, <b>{self._handler.from_user.first_name}</b>!\n\n"
                    f"У нас появились <b>свежие объявления</b>. 🛍️\n"
                    f"Скорее загляните, чтобы ничего не пропустить! 👇",
                    parse_mode="HTML"
                )
                await self.show_product(start_index=start_index)
            asyncio.create_task(delayed_promo())
        else:
            return