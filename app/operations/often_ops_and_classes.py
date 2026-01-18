import asyncio

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject, Message, CallbackQuery

from typing import Callable, Dict, Any, Awaitable

import app.keyboards.kb_registr_and_profile
import app.keyboards.kb_show_training
from app import states as st
from app.database import requests as db_req
from app.database import event_user_requests as db_rq_event_user

from app.keyboards import universal_keyboards as kb
from ..keyboards.kb_show_training import choose_training_type_kb

from ..operations.regisration_ops import registration
from config.log_config import setup_logger
from config.constants import *

logger = setup_logger(__name__)


# Мидлварь для проверки прав пользователя
class AdminMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        # Проверяем, является ли пользователь администратором
        data['user_cache'] = user_cache
        if isinstance(event, (Message, CallbackQuery)):
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
        return await handler(event, data)


# Родительский класс для разных операций (в основном для операций с тренировками)
class ParentClassForTrainingOperations:
    def __init__(self, handler: CallbackQuery | Message, state: FSMContext, is_admin: bool):
        self._handler, self._state, self._is_admin = handler, state, is_admin

    async def _exception_func(self, text, except_text):
        await self._handler.message.answer(text, parse_mode='HTML')
        await cmd_start(self._handler, self._state, self._is_admin, user_cache)
        await logger.error(except_text)


# Фоновая задача для очистки пользовательского окна переписки
async def delete_bkg(call_mess: Message | CallbackQuery):
    try:
        call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
        await call_mess.bot.delete_message(call_mess.chat.id, call_mess.message_id)
    except Exception:
        return


async def cmd_start(call_mess: CallbackQuery | Message, state: FSMContext, is_admin: bool, user_cache):
    try:
        if call_mess.from_user.id not in user_cache:
            await registration(call_mess)
            return
        await state.clear()
        call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
        await call_mess.answer(
            f"Для работы с ботом воспользуйтесь командами меню, расположенными "
            f"слева внизу (если у вас на устройстве стандатная раскладка).\n↙️"
        )
    except Exception as e:
        await logger.error(f'Ошибка в cmd_start: {e}')
        # stream_logger.error(log_message)
        return


# Обработчик кнопок назад, отмены и прочее
async def return_to(call: CallbackQuery, state: FSMContext, is_admin: bool):
    user_id = user_cache[call.from_user.id].id
    if call.data == RETURN_TO_START[1]:
        await cmd_start(call, state, is_admin, user_cache)
    elif call.data == RETURN_TO_TRAININIG_TYPE_FOR_CHOOSE_EVENT[1]:
        await choose_training_types(call.message, state)
    elif call.data.startswith(RETURN_TO_EVENT[1]):
        event_id = int(call.data.split(':')[1])
        await show_formed_info_about_event(call, is_admin, event_id, user_id)
    elif call.data.startswith(RETURN_TO_START[0]):


# БЛОК ФУНКЦИЙ ПО ОТОБРАЖЕНИЮ ТРЕНИРОВКИ
# =====================================

async def choose_training_types(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('Выберите тип тренировки', reply_markup=choose_training_type_kb())


async def show_events(call: CallbackQuery, state: FSMContext, is_admin: bool):
    training_type = call.data.split(':')
    events = await db_req.get_event(training_type=training_type, is_admin=is_admin)
    events = sorted(events, key=lambda x: x['event_datetime'].replace(tzinfo=None))
    event_ids = [i['id'] for i in events]
    event_user = await db_rq_event_user.get_event_user(user_tg_id=call.chat.id, event_ids=event_ids)

    if not events:
        message_text = 'Запланированных тренировок пока нет.'
        button_text, callback_data = '↩️ Назад', 'return_to_choose_training_type'
        keyboard = kb.interrupt_or_return_button(button_text, callback_data)
        await call.answer(message_text, reply_markup=keyboard)
    else:
        message_text = (f'Ближайшие тренировки по дисциплине <b><i>{training_type}</i></b>.\n'
                        f'Тренировки, на которые Вы уже записаны, отмечены 🟢.')
        keyboard = app.keyboards.kb_show_training.show_events_kb(event_user, *events)
        await call.answer(message_text, reply_markup=keyboard, parse_mode='HTML')
        await state.update_data(events=events)


# Формирование текста по тренировке со списком участников
def _show_text_about_event(event: dict, event_user: list, user_id: int) -> str:
    text, participants_count = event['event_text'], int(event['participants_count'])
        # Находим границы фрагмента по дате трени
    idx_0, idx_end = text.find('<b>Дата тренировки</b>:'), text.find('<b>Длительность</b>')
    ev_dt_info = text[idx_0:idx_end]
    # Находим день недели по индексу от datetime
    day_idx = event['event_datetime'].weekday()
    day = DAYS[day_idx]
    # Присваиваем фрагмент инфы по трени временной переменной и вставляем в новый фрагмент день недели
    new_info = ev_dt_info.replace('\n',f' ({day})\n')
    text = text.replace(ev_dt_info, new_info)

    if event['stars'] is not None:
        stars_text = event['stars'].replace(' ', '').split(',')  # переводим текстовый набор user_id в список
        star_tpl = tuple(map(lambda x: int(x), stars_text))  # преобразуем в кортеж целых чисел значений user_id
    else:
        star_tpl = None
    text += '\n\n<b>ОСНОВНОЙ СПИСОК</b>\n'
    for i, item in enumerate(event_user):
        if i + 1 <= participants_count:
            if item['payment_confirmed'] is False:
                tag = '❌'
            elif not item['payment_confirmed'] and item['paid_check']:
                tag = '✔️'
            elif item['payment_confirmed']:
                tag = '✅'
            else:
                tag = '⚠️'
        else:
            tag = ''
        fullname = f"{item["user__tg_name"]} @{item['user__tg_username']}"
        star = "⭐️" if star_tpl is not None and item['user__id'] in star_tpl else ''

        # Чтобы пользователь видел себя выделенным шрифтом в списке на тренировку
        fullname = f'<b><i>{fullname}</i></b>' if item['user__id'] == user_id else fullname

        text+=f"{star}{i+1}. {fullname} {tag}\n"
        if i + 1 == participants_count:
            text += "\n 📌📌 <b><i>Резерв</i></b>: \n"

    text += '\n<b>❗️ВАЖНЫЕ РЕКОМЕНДАЦИИ</b> в <b>/rec</b>'

    return text


# После выбора тренировки отображается текущий список заявишихся участников
async def show_formed_info_about_event(call_mess: Message | CallbackQuery,
                                       is_admin: bool,
                                       event_id: int,
                                       user_id: int):
    try:
        event = db_req.get_event(id=event_id)
        event_user = await db_rq_event_user.get_event_user(event_id=event_id)

        keyboard = app.keyboards.kb_show_training.training_interface_kb(event, event_user, user_id, is_admin)
        text = _show_text_about_event(event, event_user, user_id)
        mess_handler = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
        await mess_handler.answer(text, parse_mode='HTML', reply_markup=keyboard)
        asyncio.create_task(delete_bkg(call_mess))
    except Exception as e:
        await logger.error(f'Ошибка в choose_event: {e}')
        # stream_logger.error(f'Ошибка в choose_event: {e}')


