import asyncio

from tortoise.exceptions import IntegrityError

from app.operations.often_ops_and_classes import *
import app.states as st
from .often_ops_and_classes import set_individual_dedline
from ..keyboards.kb_show_training import cancel_kb
from ..keyboards.kb_confirm import add_friend_confirm_kb
from config.constants import bot, user_cache

logger = setup_logger(__name__)


# Записаться на тренировку
async def sign_up_to_training(call: CallbackQuery, state: FSMContext, is_admin: bool):
    '''Данная функция реализована за счет следующих этапов:
    - считываем данные тренировки, на которую записываемся
    - проверяем, остается до начала трени более 10 минут'''
    try:
        await state.clear()
        user_id = user_cache[call.from_user.id].id
        event_id = int(call.data.split(':')[1])
        now = datetime.now().replace(tzinfo=None)
        event = await db_req.get_event(id=event_id)
        payment_dedline, event_datetime = event['payment_dedline'], event['event_datetime']
        payment_dedline, event_datetime = payment_dedline.replace(tzinfo=None), event_datetime.replace(tzinfo=None)
        if (event_datetime - now) > timedelta(minutes=10):
            dedline_info = set_individual_dedline(payment_dedline=payment_dedline,
                                                  event_datetime=event_datetime, now=now)
            data = {'user_id': user_id, 'event_id': event_id, 'created_at': now, 'modified_at': now,
                    'individual_dedline':dedline_info['individual_dedline']}
            await db_rq_event_user.create_event_user(data)
            text = ('Вы записались на тренировку.\n'
                    'Если у вас уже оплачена эта тренировка, нажмите на кнопку оповещения бота ✔️\n')
            text += dedline_info['text']
        else:
            text = 'Новых участников, менее, чем за 10 минут до начала тренировки, могут записывать только админы.'
    except IntegrityError:
        text = 'Вы уже ранее записались на тренировку'
        pass
    except Exception as e:
        await logger.error(e)
        # stream_logger.error(e)
        text = '📛 Возникла неизвестная ошибка'
        pass
    await show_formed_info_about_event(call, is_admin, event_id, user_id)
    await call.message.answer(text, parse_mode='HTML')


# Уведомить бот об оплате
class PaymentNotify(ParentClassForTrainingOperations):
    _add_text = 'Если Вы оплатили за тренировку, срочно ❗️ свяжитесь с админом для подтверждения оплаты!'

    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('payment_notify_by_event_is'):
                await self._show_payment_notify_message()
        elif await self._state.get_state() == st.PaymenNotify.confirm:
            await self._payment_notify_confirm()

    async def _show_payment_notify_message(self):
        try:
            event_id = int(self._handler.data.split(':')[1])
            _check_state = await self._check_availability(event_id)
            if isinstance(_check_state, str):
                text = _check_state
                await show_formed_info_about_event(self._handler, self._is_admin, event_id, self._user_id)
                await self._handler.message.answer(text, parse_mode='HTML')
            else:
                text = (
                    'ВНИМАНИЕ❗️\n'
                    '<b><i>Что нужно знать об этой функции</i></b>:\n'
                    '🔸 Уведомлять бот об оплате можно только <b>ОДИН (!!) раз</b>;\n'
                    '🔸 Продлевает дедлайн оплаты МАКСИМУМ на 1,5 сутки <i><u>с момента попадания '
                    'в ОСНОВНОЙ список </u></i>;\n'
                    '🔸 По истечении времени присваивается статус ✅ (админ подтвердил оплату) или '
                    '❌ (админ не подтвердил оплату);\n'
                    '🔸 Уведомлять нужно ТОЛЬКО, если Вы оплатили и <u>отправили админу скрин чека</u>.\n'
                    '\nЕсли Вы подтверждаете факт оплаты, отправьте в сообщении боту слово <b><i>да</i></b>?'
                )
                await self._handler.message.answer(text, reply_markup=cancel_kb(event_id), parse_mode='HTML')
                await self._state.update_data(event_id=event_id, event_user=_check_state)
                await self._state.set_state(st.PaymenNotify.confirm)
        except Exception as e:
            text, except_text = ('⭕️ Возникла ошибка. Возможно, что Вы ранее уже уведомляли бот об оплате',
                                 f'Ошибка _payment_notify_confirm: {e}')
            await self._exception_func(text, except_text)

    # Проверка доступности продления дедлайна
    async def _check_availability(self, event_id):
        event_user = await db_rq_event_user.get_event_user_by_current_user(event_id, self._user_id)
        if event_user.paid_check is False:
            return (f'🔴 Вы не можете воспользоваться данной функцией, поскольку Вы находились в ОСНОВНОМ '
                    f'списке <b><u>БЕЗ подтвержденной оплаты</u></b> более <i>1,5 суток</i>.\n'
                    f'{self._add_text}')
        elif event_user.paid_check is True:
            return f'🔴 Вы ранее уже пользовались этой функцией.\n{self._add_text}'
        new_individual_dedline = event_user.modified_at + timedelta(days=1, hours=12)
        event_user.individual_dedline, event_user.paid_check = new_individual_dedline, True
        return event_user

    async def _payment_notify_confirm(self):
        try:
            message = self._handler.text
            data = await self._state.get_data()
            event_id, event_user = data['event_id'], data['event_user']
            if message.replace('"', '').lower() == "да":
                await event_user.save()
                _new_dedl_txt = event_user.individual_dedline.strftime('%H:%M %d.%m')
                text = f'✔️ Вы успешно уведомили бот об оплате и продлили дедлайн до {_new_dedl_txt}'
            else:
                text = '⚠️ Вы отменили уведомление бота об оплате.'
            await self._handler.answer(text, parse_mode='HTML')
            await self._state.clear()
            await show_formed_info_about_event(self._handler, self._is_admin, event_id, self._user_id)
        except Exception as e:
            text, except_text = '⭕️ Возникла ошибка.', f'Ошибка _payment_notify_confirm: {e}'
            await self._exception_func(text, except_text)


class AddFriend(ParentClassForTrainingOperations):
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('add_friend_to_event'):
                await self._add_friend()
            elif (self._handler.data.startswith('add_friend_confirm_to_event_is') and
                  await self._state.get_state() == st.AddFriendFSM.add_friend_confirm):
                await self._add_friend_confirm()
        elif await self._state.get_state() == st.AddFriendFSM.add_friend:
            await self._add_friend_check()

    async def _add_friend(self):
        event_id = int(self._handler.data.split(':')[1])
        text = 'Введите никнейм вашего друга.\n<i>Пример</i>: @ivanov1934'
        await self._handler.message.answer(text, parse_mode='HTML', reply_markup=cancel_kb(event_id))
        await self._state.update_data(event_id=event_id)
        await self._state.set_state(st.AddFriendFSM.add_friend)

    async def _add_friend_check(self):
        try:
            data = await self._state.get_data()
            event_id = data['event_id']
            _init_data = await self._init_data_definition(event_id)
            if isinstance(_init_data, dict):  # если никнейм добавляемого друга прошел первичную проверку
                friend_id, friend, friend_tg_id = (_init_data['friend_id'], _init_data['friend'],
                                                   _init_data['friend_tg_id'])
                proc_check =  self._process_of_check(_init_data)
                if proc_check['available'] is True:
                    await self._state.update_data(friend_id=friend_id, friend=friend, friend_tg_id=friend_tg_id)
                    await self._state.set_state(st.AddFriendFSM.add_friend_confirm)
                    keyboard = add_friend_confirm_kb(event_id)
                elif proc_check['available'] is False:
                    keyboard = cancel_kb(event_id)
                elif proc_check['available'] is None:
                    await self._state.clear()
                    await self._handler.answer(proc_check['message_text'], parse_mode='HTML')
                    await show_formed_info_about_event(self._handler, self._is_admin, event_id, self._user_id)
                    return
                message_text = proc_check['message_text']
            else:
                message_text, keyboard = _init_data, cancel_kb(event_id)
            await self._handler.answer(message_text, parse_mode='HTML', reply_markup=keyboard)
        except Exception as e:
            text, except_text = '⭕️ Возникла ошибка.', f'Ошибка _add_friend_check_friend: {e}'
            await self._exception_func(text, except_text)
        asyncio.create_task(delete_bkg(self._handler))

    # Определяем необходимые данные для записи друга
    async def _init_data_definition(self, event_id: int):
        text = self._handler.text.strip().replace('@', '')
        if text != self._handler.from_user.username:
            for k in user_cache:
                if user_cache[k].tg_username == text:
                    friend_id = user_cache[k].id
                    friend_signed_up = await db_rq_event_user.get_event_user_for_check_friend(
                        event_id, friend_id=friend_id
                    )
                    my_prev_friend = await db_rq_event_user.get_event_user_for_check_friend(
                        event_id, i_am_friend=self._handler.from_user.username
                    )
                    return {'friend_id': friend_id,
                            'friend': user_cache[k].tg_username,
                            'friend_tg_id':user_cache[k].tg_id,
                            'friend_signed_up': friend_signed_up,
                            'my_prev_friend': my_prev_friend}

            return f'🤷🏻‍♂️ Пользователь с никнеймом <i>@{text}</i> не зарегистрирован в боте'
        else:
            return '☝🏽Вы не можете добавить себя как друга'

    # Проверяем далее, можно ли добавлять друга
    def _process_of_check(self, _init_data: dict):
        friend, friend_signed_up, my_prev_friend = (_init_data['friend'], _init_data['friend_signed_up'],
                                                    _init_data['my_prev_friend'])
        if not friend_signed_up and self._is_admin is not True and not my_prev_friend:
            message_text = ('⚠️ Внимание! Записать друга на тренировку можно только <b>один раз</b>!\n'
                            'Вы подтверждаете запись друга?')
            available = True
        elif not friend_signed_up and self._is_admin is True:  # админы могут добавлять хоть сколько друзей
            message_text, available = ('Вы подтверждаете запись друга?'), True
        elif friend_signed_up:
            message_text = f'☑️ Ваш друг с никнеймом <i>@{friend}</i> уже состоит в записи на тренировку'
            available = False
        elif my_prev_friend and self._is_admin is not True:
            message_text, available = f'⛔️ Вы ранее уже записали друга с никнеймом <i>@{my_prev_friend}</i>', None
        return {'message_text': message_text, 'available': available}

    async def _add_friend_confirm(self):
        try:
            call_data = self._handler.data.split(':')
            state, event_id = call_data[0], int(call_data[1])
            if state == 'add_friend_confirm_to_event_is':
                data = await self._state.get_data()
                friend_id, friend, friend_tg_id = (data['friend_id'], data['friend'], data['friend_tg_id'])
                event = await db_req.get_event(id=event_id)
                training_type, event_text = event['training_type'], event['event_text']
                payment_dedline, event_datetime, now = event['payment_dedline'], event['event_datetime'], datetime.now()
                dedline_info = set_individual_dedline(payment_dedline, event_datetime, now)
                data['created_at'] = data['modified_at'] = now
                data['individual_dedline'] = dedline_info['individual_dedline']
                await db_rq_event_user.create_event_user(data, friend_id=friend_id,
                                                         i_am_friend=self._handler.from_user.username)
                text = (f'️⚡️ ️⚡️ <b>ВАЖНАЯ ИНФОРМАЦИЯ</b>\n'
                        f'Вас записали на следующую тренировку\n'
                        f'<b>Тип тренировки</b>:{training_type}\n{event_text}\n\n')
                text += dedline_info['text']
                asyncio.create_task(SendMessages.to_one_receiver(text=text, tg_id=friend_tg_id))
                text = f'Вы успешно записали друга с никнеймом <i>{friend}</i> на тренировку 🖍'
                await self._handler.message.answer(text, parse_mode='HTML')
                await show_formed_info_about_event(self._handler, self._is_admin, event_id, self._user_id)
            else:
                await self._handler.message.answer(f'Вы отменили запись друга на тренировку🟡')
            await self._state.clear()  # выходим из состояния, чтобы кнопки дезактивировались
        except Exception as e:
            text, except_text = '⭕️ Возникла ошибка.', f'Ошибка _add_friend_confirm: {e}'
            await self._exception_func(text, except_text)
        asyncio.create_task(delete_bkg(self._handler))


class DeleteFromTraining(ParentClassForTrainingOperations):
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('delete_from_training'):
                await self._delete_from_training()
        elif await self._state.get_state() == st.DeleteFromTrainingFSM.delete_from_training:
            await self._delete_from_training_confirm()

    async def _delete_from_training(self):
        text =('Если Вы уверены, что хотите удалиться из тренировки напишите в сообщении '
               '<i><b>да</b></i> и отправьте его.\n'
               'Если сомневаетесь, отмените действие нажатием на кнопку или отправьте любое другое сообщение')
        event_id, user_id = int(self._handler.data.split(':')[1]), user_cache[self._handler.from_user.id].id
        await self._handler.message.answer(text, reply_markup=cancel_kb(event_id), parse_mode='HTML')
        await self._state.update_data(event_id=event_id, user_id=user_id)
        await self._state.set_state(st.DeleteFromTrainingFSM.delete_from_training)

    async def _delete_from_training_confirm(self):
        try:
            data = await self._state.get_data()
            event_id, user_id = data.get('event_id'), data.get('user_id')
            if self._handler.text.lower().strip() == 'да':
                current_event_user = await db_rq_event_user.get_event_user_before_delete(event_id=event_id)
                seconds, update_list = -1, []
                now = datetime.now().replace(tzinfo=None)
                participants_count = current_event_user[0].event.participants_count
                for _user in current_event_user[participants_count:]:
                    seconds += 1
                    _user.modified_at = now + timedelta(seconds=seconds)
                    update_list.append(_user)
                    await db_rq_event_user.update_event_user_after_delete(update_list)

                await self._send_messages(current_event_user, now, data)
                await db_rq_event_user.delete_event_user(user_id, event_id)
                await self._handler.answer('Вы удалились из записи на тренировку.')
                await cmd_start(self._handler, self._state, self._is_admin, user_cache)
            else:
                await show_formed_info_about_event(self._handler, self._is_admin, event_id, user_id)
                await self._handler.answer('Удаление прервано')
        except Exception as e:
            text, except_text = ('⭕️ Возникла ошибка.', f'Ошибка _delete_from_training_confirm: {e}')
            await self._exception_func(text, except_text)
        await self._state.clear()

    # Рассылка уведомлений после удаления
    async def _send_messages(self, current_event_user, now, data):
        res_prtcpt = None
        participants_count = current_event_user[0].event.participants_count
        if len(current_event_user) > participants_count:
            user_pos = next(
                i for i, item in enumerate(current_event_user) if item.user.tg_id == self._handler.from_user.id
            )
            res_prtcpt = current_event_user[participants_count] if user_pos < participants_count else None
            text = (f"❗️⚡️ <b>ВНИМАНИЕ АДМИНАМ</b>\n"
                    f"Пользователь с никнеймом @<i>{self._handler.from_user.username}</i> "
                    f"удалился из следующей тренировки\n\n"
                    f"Дисциплина: <b><i>{data['training_type']}</i></b>\n"
                    f"{current_event_user[0].event.event_text}")
        if res_prtcpt:
            res_tg_username, res_tg_id, res_id = (res_prtcpt.user.tg_username, res_prtcpt.user.tg_id,
                                                  res_prtcpt.user.id)
            text += (f'\n\n<b><i>🔆ВАЖНО!</i></b>\n'
                     f"Пользователь с никнеймом <i>@{res_tg_username}</i> поднялся из резерва в основной список "
                     f"и ему было выслано соответствующее уведомление")
            # Обновляем времена поднявшегося из резерева и других резервистов

            if now + timedelta(hours=5) > current_event_user[0].event.event_datetime:
                for k in user_cache:  # Информирование админов
                    if user_cache[k].admin_permissions == True:
                        tg_id = user_cache[k].tg_id
                        await bot.send_message(chat_id=tg_id, text=text, parse_mode='HTML')

            # Информаривание пользователя, поднявшегося из резерва
            text = (f'⚡️⚡️<b>ВАЖНАЯ ИНФОРМАЦИЯ ДЛЯ ВАС</b>\n'
                    f'Вы перешли из резерва в основной список следующей тренировки:\n\n'
                    f"Дисциплина: <b><i>{data['training_type']}</i></b>\n"
                    f"{current_event_user[0].event.event_text}")

            # < ---------- ЗДЕСЬ БУДЕТ УСТАНОВКА ДЕДЛАЙНА ОПЛАТЫ ---------------- >

            text += (f'\n\n <b>ВНИМАНИЕ❗️</b> \n'
                     f'<i>У Вас другой дедлайн оплаты.\n'
                     f' Вам необходимо оплатить за тренировку до</i>'
                     f' <b><i> ... </i></b>')
            await bot.send_message(chat_id=res_tg_id, text=text, parse_mode='HTML')


# НЕИСПОЛЬЗУЕМЫЕ ФИЧИ
# ======================

# # Оповестить бот об оплате кнопкой '✔️ Тренировка оплачена'
# @add_router.callback_query(F.data.startswith('payment_notify'))
# @add_router.message(SendCheckFSM.send_check)
# async def payment_notify(call: CallbackQuery | Message, state: FSMContext, is_admin: bool):
#     try:
#         sendCheck = SendCheck(call, state)
#         await sendCheck.dispatch()
#         # call_data = call.data.split(':')[1]
#         # data = await state.get_data()
#         # user_id, event_id = data['user_id'], data['event_id']
#         # payment_notify = True if call_data == "i_payed_check" else False
#         # await db_req.update_event_user(user_id, event_id, payment_notify)
#         # await choose_event(call, state, is_admin)
#         # if payment_notify is not True:
#         #     await call.message.answer('❗️<b>ВНИМАНИЕ</b>❗️\n'
#         #                               'Вы отменили уведомление об оплате. Но это не '
#         #                               'означает автоматический возврат денежных средств, если '
#         #                               'Вы уже оплатили. Поэтому для возврата денежных средств обратитесь '
#         #                               'к админу тренировки.')
#     except Exception as e:
#         await logger.error(e)
#         # stream_logger.error(e)
#
#
#
# @add_router.message(Command('add'))
# async def add_command(message: Message, is_admin: bool):
#     await bot.send_document()
#     await message.answer(f'Значение составляет {is_admin} ')
# #
#
# # Оповестить бот об оплате кнопкой '✔️ Тренировка оплачена'
# @add_router.callback_query(F.data.startswith('payment_notify'))
# async def payment_notify(call: CallbackQuery, state: FSMContext, is_admin: bool):
#     try:
#         call_data = call.data.split(':')[1]
#         data = await state.get_data()
#         user_id, event_id = data['user_id'], data['event_id']
#         payment_notify = True if call_data == "i_payed_check" else False
#         await db_req.update_event_user(user_id, event_id, payment_notify)
#         await choose_event(call, state, is_admin)
#         if payment_notify is not True:
#             await call.message.answer('❗️<b>ВНИМАНИЕ</b>❗️\n'
#                                       'Вы отменили уведомление об оплате. Но это не '
#                                       'означает автоматический возврат денежных средств, если '
#                                       'Вы уже оплатили. Поэтому для возврата денежных средств обратитесь '
#                                       'к админу тренировки.')
#     except Exception as e:
#         await logger.error(e)
#         # stream_logger.error(e)


# Класс отправки чека об оплате
# class SendCheck():
#     def __init__(self, call: Message | CallbackQuery,
#                  state: FSMContext,
#                  id: int,
#                  is_admin: bool):
#         self._call, self._state, self._is_admin = call, state, is_admin
#         if isinstance(call, CallbackQuery):
#             self._call_data = 'upload_check'
#         else:
#             self._call_data = 'send_check'
#
#     async def dispatch(self):
#         match self._call_data:
#             case 'upload_check':
#                 await self._upload_check()
#             case 'send_check':
#                 await self._send_check()
#
#     async def _upload_check(self):
#         await self._call.message.answer('Загрузите чек об оплате', reply_markup=return_to_start_markup())
#         await self._state.set_state(SendCheckFSM.send_check)
#
#     async def _send_check(self):
#         file_id = self._call.photo[-1].file_id
#         event_user_id = int(self._call.data.split(':')[1])
#         event_user = await EventUser.get(id=event_user_id)
#         await event_user.upload_cjeck()
#         await bot.send_photo(chat_id=1933865493,
#                              photo=file_id,  caption='Чек об оплате',
#                              reply_markup=kb.payment_verify_kb(event_user_id))
#         await choose_event(self._call, self._state, self._is_admin)
#         if payment_notify is not True:
#             await self._call.message.answer('❗️<b>ВНИМАНИЕ</b>❗️\n'
#                                       'Вы отменили уведомление об оплате. Но это не '
#                                       'означает автоматический возврат денежных средств, если '
#                                       'Вы уже оплатили. Поэтому для возврата денежных средств обратитесь '
#                                       'к админу тренировки.')
#
#         # self._state.update_data(file_id = file_id)

