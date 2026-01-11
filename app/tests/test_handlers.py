from aiogram import Dispatcher
from aiogram.types import CallbackQuery, User
from aiogram.fsm.context import FSMContext

from unittest.mock import AsyncMock

from app.handlers.user import user_router, registration_callback_query


async def test_registration_callback_query():
    dp = Dispatcher()
    dp.include_router(user_router)
    user = User(id=1, is_bot=False, name='<NAME>')
    call = CallbackQuery(from_user=user, data="registration")
    state = AsyncMock(spec=FSMContext)
    # mock = AsyncMock(call=call, state=state)
    await registration_callback_query(call, state)
    call.message.answer.assert_called_once_with(
        f"Добро пожаловать 😊\n"
        f"Для пользования ботом внизу слева расположено меню, "
        f"где Вы можете выбрать интересующую Вас команду."
    )
    # call.message.answer.assert_called_once()

