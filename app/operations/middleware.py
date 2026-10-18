from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.database import requests as db_req
from app.operations.regisration_ops import registration
from config.constants import user_cache
from ..operations.product_operations import ShowProducts


# Мидлварь для проверки прав пользователя
class AdminMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:

        # Проверяем, является ли пользователь администратором
        if isinstance(event, (Message, CallbackQuery)):
            # Самый первый фильтр — есть ли username вообще
            if not event.from_user.username:
                text = (
                    "Сожалеем, но у вас отсутствует никнейм телеграмм, "
                    "поэтому Вам функции бота пока недоступны 🥺.\n"
                    "Заведите никнейм и возвращайтесь к нам 🤗"
                )
                if isinstance(event, CallbackQuery):
                    await event.answer(text, show_alert=True)
                else:
                    await event.answer(text)
                return

            user_tg_id = event.from_user.id

            ''' Здесь несеольео нелогичный код, он чисто для перестраховки, если вдруг
            при первом входе что-то пойдет не так при создании пользователя в БД.
            Также перестраховка по поводжу перезапускасервера  '''

            if user_tg_id not in user_cache:
                # Вот это обращение к БД после первой регистарции
                user = await db_req.get_or_create_user(event.from_user)
                if not user:
                    if isinstance(event, CallbackQuery) and event.data == "registration":
                        return await handler(event, data)
                    else:
                        await registration(event)
                        return
                user_cache[user_tg_id] = user
                data["is_admin"] = None

                # Здесь возвращаем при первом входе пользователя или перезапуске сервера
                return await handler(event, data)
            else:
                if user_cache[user_tg_id] is None:  # вот это скорее лишний запрос к БД на всякий случай
                    user_cache[user_tg_id] = await db_req.get_or_create_user(event.from_user)

            user = user_cache[user_tg_id]

            # Если вдруг пользователь поменял свой никнейм,то бот автоматически обновляет запись в БД и кэше
            if event.from_user.username != user_cache[user_tg_id].tg_username:
                user_cache[user_tg_id].tg_username = event.from_user.username
                user_id, new_username = user_cache[user_tg_id].id, user_cache[user_tg_id].tg_username
                await db_req.update_user(user_id=user_id, new_username=new_username)
            if user:
                data["is_admin"] = True if (event.from_user.username == 'Rustambagautdinov'
                                            or event.from_user.username == '2SaitBakhteev') \
                    else user.admin_permissions
            else:
                data["is_admin"] = False
            state = data["state"]
            show_prod = ShowProducts(event, state, data["is_admin"])
            await show_prod.promo_managment(event.from_user.id)
        return await handler(event, data)
