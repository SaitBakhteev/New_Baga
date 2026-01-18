from aiogram.types import Message, CallbackQuery

from app.keyboards.kb_registr_and_profile import registration_kb
from app.database import requests as db_req


async def registration(event: Message | CallbackQuery):
    username = event.from_user.username
    event_message = event.message if isinstance(event, CallbackQuery) else event
    if username:
        await event_message.answer(
            "Спорт у дома приветсвует Вас в нашем телеграмм-боте для записи на тренировки.😊\n"
            "Для того, чтобы воспользоваться этим ботом нажмите на кнопку регистрации.\n"
            "При этом нажимая на кнопку регистрации, Вы соглашаетесь со всеми условиями предоставления "
            'персональных данных своего телеграмм аккаунта и иных условий пользовательского соглашения, '
            'описанных <a href="https://disk.yandex.ru/i/J4i-dcxqrgKCPw"><b>здесь</b></a>.',
            reply_markup=registration_kb)
    else:
        await event_message.answer(
            "Сожалеем, но у Вас отсутствует никнейм телеграмм 🥺\n"
            "ℹ️ Как установить никнейм (username):\n"
            "1. Откройте 'Настройки' Telegram\n"
            "2. Выберите 'Изменить профиль'\n"
            "3. В поле 'Username' укажите желаемый ник\n"
            "4. После этого возвращайтесь в бота!☺️"
        )


async def registration_and_welcome(call: CallbackQuery):
    await db_req.get_or_create_user(from_user=call.from_user, create_user=True)
    await call.message.delete()

    # Приходится дублировать это сообющение, поскольку переход на cmd_start после первичной регистрации не работает
    await call.message.answer(
        f"Добро пожаловать 😊\n"
        f"Для пользования ботом внизу слева расположено меню, "
        f"где Вы можете выбрать интересующую Вас команду."
    )
