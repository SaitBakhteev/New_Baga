import asyncio
from datetime import timedelta

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject, Message, CallbackQuery

from typing import Callable, Dict, Any, Awaitable

from config.constants import bot, user_cache
from ..keyboards.kb_show_training import training_interface_kb, show_events_kb

from ..database import requests as db_req
from ..database import event_user_requests as db_rq_event_user

from ..keyboards.universal_keyboards import interrupt_or_return_button
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
        self._user_id = user_cache[handler.from_user.id].id

    async def _exception_func(self, text, except_text):
        _handler = self._handler.message if isinstance(self._handler, CallbackQuery) else self._handler
        await _handler.answer(text, parse_mode='HTML')
        await cmd_start(self._handler, self._state, self._is_admin, user_cache)
        await logger.error(except_text)


# Фоновая задача для очистки пользовательского окна переписки
async def delete_bkg(call_mess: Message | CallbackQuery):
    try:
        call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
        await call_mess.bot.delete_message(call_mess.chat.id, call_mess.message_id)
    except Exception as e:
        await logger.error(f'Ошибка в delete_bkg: {e}')
        return


async def cmd_start(call_mess: CallbackQuery | Message, state: FSMContext, is_admin: bool, user_cache):
    try:
        if call_mess.from_user.id not in user_cache:
            await registration(call_mess)
            return
        await state.clear()
        call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
        await call_mess.answer(
            f"Для работы воспользуйтесь меню внизу слева \n↙️"
        )
    except Exception as e:
        await logger.error(f'Ошибка в cmd_start: {e}')
        # stream_logger.error(log_message)
        return



# БЛОК ФУНКЦИЙ ПО ОТОБРАЖЕНИЮ ТРЕНИРОВКИ
# =====================================

async def show_training_types(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('Выберите тип тренировки', reply_markup=choose_training_type_kb())


async def show_events(call: CallbackQuery, state: FSMContext, is_admin: bool):
    _index = int(call.data.split(':')[1])  # индекс тренировки
    training_type = TRAINING_TYPES[_index]
    events = await db_req.get_events_by_training_type(training_type=training_type, is_admin=is_admin)

    if not events:
        message_text = 'Запланированных тренировок пока нет.'
        button_text, callback_data = '↩️ Назад', '/event'
        keyboard = interrupt_or_return_button(text=button_text, callback_data=callback_data)
        await call.message.answer(message_text, reply_markup=keyboard)
    else:
        event_ids = [i['id'] for i in events]
        event_user = await db_rq_event_user.get_event_user(user_tg_id=call.from_user.id, event_ids=event_ids)
        message_text = (f'Ближайшие тренировки по дисциплине <b><i>{training_type}</i></b>.\n'
                        f'Тренировки, на которые Вы уже записаны, отмечены 🟢.')
        keyboard = show_events_kb(event_user, *events)
        await call.message.answer(message_text, reply_markup=keyboard, parse_mode='HTML')
        await state.update_data(events=events)


# Формирование текста по тренировке со списком участников
def show_text_about_event(event: dict, event_user: list, user_id: int) -> str:
    text = f"<b>{event['training_type']}</b>\n\n"
    text += event['event_text']
    participants_count = int(event['participants_count'])

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
    if event_user:
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
            if len(tag) > 0 and tag != '✅':
                _dedline = f": ⏳ <b><i>{item['individual_dedline'].strftime('%H:%M %d.%m.')}</i></b>"
            else:
                _dedline = ''
            fullname = f"{item["user__tg_name"]} @{item['user__tg_username']}"
            star = "⭐️" if star_tpl is not None and item['user__id'] in star_tpl else ''

            # Чтобы пользователь видел себя выделенным шрифтом в списке на тренировку
            fullname = f'<b><i>{fullname}</i></b>' if item['user__id'] == user_id else fullname

            text+=f"{star}{i+1}. {fullname} {tag}{_dedline}\n"
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
        event = await db_req.get_event(id=event_id)
        event_user = await db_rq_event_user.get_event_user(event_id=event_id)

        keyboard = training_interface_kb(event, event_user, user_id, is_admin)
        text = show_text_about_event(event, event_user, user_id)
        mess_handler = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
        await mess_handler.answer(text, parse_mode='HTML', reply_markup=keyboard)
        asyncio.create_task(delete_bkg(call_mess))
    except Exception as e:
        await logger.error(f'Ошибка в show_formed_info_about_event: {e}')
        # stream_logger.error(f'Ошибка в choose_event: {e}')


def set_individual_dedline(payment_dedline, event_datetime, now):
    payment_dedline, event_datetime = payment_dedline.replace(tzinfo=None), event_datetime.replace(tzinfo=None)
    delta_12, delta_3, delta_2, delta_1 = (timedelta(hours=12), timedelta(hours=3),
                                           timedelta(hours=2), timedelta(hours=1))
    delta_30m, delta_10m = timedelta(minutes=30), timedelta(minutes=10)
    if now + delta_12 < payment_dedline:
        individual_dedline = payment_dedline
    elif now + delta_12 <= event_datetime - delta_3:
        individual_dedline = now + delta_12
    else:
        _delta, = event_datetime - now
        if _delta > delta_3:
            individual_dedline = event_datetime - delta_2
        elif _delta > delta_2 and _delta <= delta_3:
            individual_dedline = now + delta_1
        elif _delta > delta_1 and _delta <= delta_2:
            individual_dedline = now + delta_30m
        elif _delta > delta_30m and _delta <= delta_1:
            individual_dedline = now + delta_10m
        elif _delta > delta_10m and _delta <= delta_30m:
            individual_dedline = now + timedelta(minutes=5)

    _lenght_of_dedline = (individual_dedline - now)
    if _lenght_of_dedline >= delta_2:
        text = f"Вам необходимо оплатить до <b><i>{individual_dedline.strftime('%H:%M %d.%m.%Y')}</i></b>.\n"
    else:
        text = (f"ВНИМАНИЕ ‼️🔥\n У Вас весьма ограниченный дедлайн на оплату⏳.\n"
                 f"Вам необходимов течение {_lenght_of_dedline.strftime('%M')} минут.\n")

    text += 'По истечении дедлайна есть риск оказаться в конце очереди при наличии резерва'
    return {'text': text, 'individual_dedline':individual_dedline}


# Класс с метолдами отправки уведомлений в зависимости от контекста
class SendMessages():
    # Метод применяется при записи, удалении, перемещении админом и прочее
    @classmethod
    async def to_one_receiver(cls, text, tg_id):
        await bot.send_message(tg_id, text, parse_mode='HTML')

    @classmethod
    async def to_several_receivers(cls, tg_ids: list, text):
        '''
        Метод предназначен для рассылки нескольким участникам при работе планировщика
        :param tg_ids: список tg_id получателдей уведомления
        '''
        for tg_id in tg_ids:
            await bot.send_message(tg_id, text, parse_mode='HTML')

    @classmethod
    async def to_admins(cls, text, now, event_datetime):
        '''
        Данная функция сработает, если сообщения будут по тренировке, до начала
        которой остаются считанные часы (менее 12)
        :param text:
        :param now:
        :param event_datetime:
        :return:
        '''
        if event_datetime - now < timedelta(hours=12):
            for k in user_cache:
                if user_cache[k].admin_permissions:
                    await bot.send_message(int(k), text, parse_mode='HTML')

    @classmethod
    async def to_admins_about_non_marked_events(cls, events: list):
        text = ' 🚫🖊 ВНИМАНИЕ админам❗️\nВы не указали звезд следующих <b>прошедших</b> тренировок:\n\n'
        for item in events:
            text += f'{item.event_text}\n\n'
        text += 'Если на тренировке звезд не было, то нужно отметить прочерком'
        for k in user_cache:
            if user_cache[k].admin_permissions:
                await bot.send_message(int(k), text, parse_mode='HTML')
