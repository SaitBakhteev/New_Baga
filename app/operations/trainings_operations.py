from datetime import datetime, timedelta

from config import bot, user_cache
from app.operations.often_ops_and_classes import *
import app.states as st
import app.keyboards.universal_keyboards as kb

logger = setup_logger(__name__)


# Локальная инлайн-кнопка отмены действий
def _change_kb(event_id: int):
    keyboard = kb.interrupt_or_return_button('⛔️Отменить', f'return_to_event_{event_id}')
    return keyboard


# Записаться на тренировку
async def sign_up_for_training(call: CallbackQuery, is_admin: bool):
    try:
        user_id = user_cache[call.from_user.id].id
        event_id = int(call.data.split(':')[1])
        now = datetime.now().replace(tzinfo=None)
        data = {'user_id': user_id, 'event_id': event_id,
                'created_at': now, 'modified_at': now}
        await db_rq_event_user.create_event_user(data)
        await show_formed_info_about_event(call, is_admin, event_id, user_id)
        text = ('Вы записались на тренировку.\n'
                'Если у вас уже оплачена эта тренировка, нажмите на кнопку <i>"✔️ Тренировка оплачена"</i>')

        ### ----- !!  ЗДЕСЬ БУДЕТ ЕЩЁ КОД ПО ОТОБРАЖЕНИЮ СООБЩЕНИЯ ДЛЯ ПОЛЬЗЩОВТАЕЛЯ ПО ДЕДЛАЙНУ  !! --- #####

        await call.message.answer(text, parse_mode='HTML')
    except Exception as e:
        await logger.error(e)
        # stream_logger.error(e)


# Уведомить бот об оплате
class PaymentNotify(ParentClassForTrainingOperations):
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('payment_notify'):
                event_id = int(self._handler.data.split(':')[1])
                await self._show_payment_notify_message(event_id)
        elif self._state.get_state() == st.PaymenNotify.confirm:
            await self._payment_notify_confirm()

    async def _show_payment_notify_message(self, event_id):
        try:
            text = (
                'ВНИМАНИЕ❗️\n'
                'Уведомлять об оплате можно только ОДИН (!!) раз. '
                'Через сутки (или раньше) статус ✔️ переходит либо в статус ✅ (админ подтвердил оплату), либо в '
                '❌ (админ не подтвердил оплату).\n'
                'Если Вы подтверждаете факт оплаты и отправки скрина админу, отправьте в сообщении боту слово <i>"да"</i>?'
            )
            await self._handler.message.answer(text, reply_markup=_change_kb(event_id), parse_mode='HTML')
            await self._state.update_data(event_id=event_id)
            await self._state.set_state(st.PaymenNotify.confirm)
        except Exception as e:
            text, except_text = ('⭕️ Возникла ошибка. Возможно, что Вы ранее уже уведомляли бот об оплате',
                                 f'Ошибка _payment_notify_confirm: {e}')
            await self._exception_func(text, except_text)

    async def _payment_notify_confirm(self):
        try:
            message = self._handler.text
            data = await self._state.get_data()
            event_id, user_id = data['event_id'], user_cache[self._handler.from_user.id].id

            if message.replace('"', '').lower() == "да":
                await db_rq_event_user.update_event_user(user_id, event_id, True)
                text = '✔️ Вы успешно уведомили бот об оплате. Ожидайте в течение суток подтверждения оплаты админом.'
            else:
                text = '⚠️ Вы отменили уведомление бота об оплате.'
            await self._handler.message.answer(text, parse_mode='HTML')
            await self._state.clear()
            await show_formed_info_about_event(self._handler, self._is_admin, event_id, user_id)
        except Exception as e:
            text, except_text = '⭕️ Возникла ошибка.', f'Ошибка _payment_notify_confirm: {e}'
            await self._exception_func(text, except_text)
        asyncio.create_task(delete_bkg(self._handler))


class DeleteFromTraining(ParentClassForTrainingOperations):
    def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('delete_from_training'):
                self._delete_from_training()
        elif self._state.get_state() == st.DeleteFromTrainingFSM.delete_from_training:
            self._delete_from_training_confirm()

    async def _delete_from_training(self):
        text =('Если Вы уверены, что хотите удалиться из тренировки напишите в сообщении '
               '<i><b>да</b></i> и отправьте его.\n'
               'Если сомневаетесь, отмените действие нажатием на кнопку или отправьте любое другое сообщение')
        event_id, user_id = int(self._handler.data.split(':')[1]), user_cache[self._handler.from_user.id].id
        await self._handler.message.answer(text, reply_markup=_change_kb(event_id), parse_mode='HTML')
        await self._state.update_data(event_id=event_id, user_id=user_id)
        await self._state.set_state(st.DeleteFromTrainingFSM.delete_from_training)

    async def _delete_from_training_confirm(self):
        try:
            data = await self._state.get_data()
            event_id, user_id = data.get('event_id'), data.get('user_id')
            if self._handler.text.lower().strip() == 'да':
                await cmd_start(self._handler, self._state, self._is_admin, user_cache)
                current_event_user = await db_rq_event_user.get_event_user_before_delete(event_id=event_id)

                seconds, update_list = -1, []
                now = datetime.now().replace(tzinfo=None)
                participants_count = current_event_user[0].event.participants_count
                for _user in current_event_user[participants_count:]:
                    seconds += 1
                    _user.modified_at = now + timedelta(seconds=seconds)
                    update_list.append(_user)
                    await db_rq_event_user.update_event_user_after_delete(update_list)

                await self.__send_messages(current_event_user, now, data)
                await db_rq_event_user.delete_event_user(user_id, event_id)
                await self._handler.answer('Вы удалились из записи на тренировку.')
            else:
                await show_formed_info_about_event(self._handler, self._is_admin, event_id, user_id)
                await self._handler.answer('Удаление прервано')
        except Exception as e:
            text, except_text = ('⭕️ Возникла ошибка.', f'Ошибка _payment_notify_confirm: {e}')
            await self._exception_func(text, except_text)
        asyncio.create_task(delete_bkg(self._handler))

    # Рассылка уведомлений после удаления
    async def __send_messages(self, current_event_user, now,data):
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


class AddFriend(ParentClassForTrainingOperations):
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('add_friend_to_event'):
                await self._add_friend()
            elif (self._handler.data.startswith('add_friend_confirm') and
                  self._state.get_state() == st.AddFriendFSM.add_friend_confirm):
                await self._add_friend_confirm()
        elif self._state.get_state() == st.AddFriendFSM.add_friend:
            await self._add_friend_check_friend()

    async def _add_friend(self):
        event_id = int(self._handler.data.split(':')[1])
        text = 'Введите никнейм вашего друга.\n<i>Пример</i>: @ivanov1934'
        await self._handler.message.answer(text, parse_mode='HTML', reply_markup=_change_kb(event_id))
        await self._state.update_data(event_id=event_id)
        await self._state.set_state(st.AddFriendFSM.add_friend)

    async def _add_friend_check_friend(self):
        try:
            data = await self._state.get_data()
            event_id = data['event_id']
            text = self._handler.text.strip().replace('@', '')
            if text != self._handler.from_user.username:
                friend = None
                for k in user_cache:
                    if user_cache[k].tg_username == text:
                        friend_id, friend, friend_tg_id = user_cache[k].id, user_cache[k].tg_username, user_cache[k].tg_id
                        break
                if friend is not None:
                    friend_signed_up  = await db_rq_event_user.get_event_user_for_check_friend(event_id, friend_id=friend_id)
                    my_prev_friend = await db_rq_event_user.get_event_user_for_check_friend(
                        event_id, i_am_friend=self._handler.from_user.username
                    )
                    ''' Проверяем не записывался ли ранее мой друг (friend_signed_up) и не записывал ли 
                    я кого-нибудь до этого (my_prev_friend) '''

                    if not friend_signed_up and self._is_admin is not True and not my_prev_friend:
                        message_text = ('⚠️ Внимание! Записать друга на тренировку можно только <b>один раз</b>!\n'
                                        'Вы подтверждаете запись друга?')
                        await self._state.update_data(friend_id=friend_id, friend=friend, friend_tg_id=friend_tg_id)
                        await self._state.set_state(st.AddFriendFSM.add_friend_confirm)
                        return await self._handler.answer(message_text, reply_markup=kb.add_friend_confirm_kb,
                                                          parse_mode='HTML')
                    elif not friend_signed_up and self._is_admin is True:  # админы могут добавлять хоть сколько друзей
                        message_text = ('Вы подтверждаете запись друга?')
                        await self._state.update_data(friend_id=friend_id, friend=friend, friend_tg_id=friend_tg_id)
                        await self._state.set_state(st.AddFriendFSM.add_friend_confirm)
                        return await self._handler.answer(message_text, reply_markup=kb.add_friend_confirm_kb, parse_mode='HTML')
                    elif friend_signed_up:
                        message_text = f'☑️ Ваш друг с никнеймом <i>{friend}</i> уже состоит в записи на тренировку'
                    elif my_prev_friend and self._is_admin is not True:
                        message_text = f'⛔️ Вы ранее уже записали друга с никнеймом <i>{my_prev_friend}</i>'
                else:
                    message_text = f'🤷🏻‍♂️ Пользователь с никнеймом <i>{text}</i> не зарегистрирован в боте'
            else:
                message_text = '☝🏽Вы не можете добавить себя вместо друга'
            await self._handler.answer(message_text, parse_mode='HTML', reply_markup=kb.return_to_start_markup())
        except Exception as e:
            text, except_text = '⭕️ Возникла ошибка.', f'Ошибка _add_friend_check_friend: {e}'
            await self._exception_func(text, except_text)
        asyncio.create_task(delete_bkg(self._handler))

    async def _add_friend_confirm(self):
        try:
            call_data = self._handler.data.split(':')[1]
            if call_data == 'yes':
                data = await self._state.get_data()
                data['created_at'] = datetime.now()
                friend_id, friend, friend_tg_id, event_id = (data['friend_id'], data['friend'], data['friend_tg_id'],
                                                             data['event_id'])
                await db_rq_event_user.create_event_user(data, friend_id=friend_id, i_am_friend=self._handler.from_user.username)

                event = await db_req.get_event(id=event_id)
                training_type, event_text = event[0]['training_type'], event[0]['event_text']
                text = (f'️⚡️ ️⚡️ <b>ВАЖНАЯ ИНФОРМАЦИЯ</b>\n'
                        f'Вас записали на следующую тренировку\n'
                        f'<b>Тип тренировки</b>:{training_type}\n{event_text}')

                ''' ----------------------  ЗДЕСЬ НУЖНА ЗАМЕНА!!! ------------------------------ '''
                # reper_dedline, dedline_type = reper_dedline_definiton(
                #     real_dedline=event[0]['payment_dedline'].replace(tzinfo=None),
                #     now=data['created_at'], event_datetime=event[0]['event_datetime'].replace(tzinfo=None),
                # )
                # if dedline_type == 'individ_dedline':
                #     text += (f'\n\n <b>ВНИМАНИЕ❗️</b>\n'
                #              f' У Вас другой дедлайн оплаты, Вам необходимо оплатить '
                #              f'за тренировку до <b><i>{reper_dedline}</i></b>')

                await bot.send_message(chat_id=friend_tg_id, text=text, parse_mode='HTML')
                text = f'Вы успешно записали друга с никнеймом <i>{friend}</i> на тренировку 🖍'
                await self._handler.message.answer(text, parse_mode='HTML')
            else:
                await self._handler.message.answer(f'Вы отменили запись друга на тренировку🟡')
            await self._state.clear()  # выходим из состояния, чтобы кнопки дезактивировались
            user_id = user_cache[self._handler.from_user.id].id
            await show_formed_info_about_event(self._handler, self._is_admin, user_id)
        except Exception as e:
            text, except_text = '⭕️ Возникла ошибка.', f'Ошибка _add_friend_confirm: {e}'
            await self._exception_func(text, except_text)
        asyncio.create_task(delete_bkg(self._handler))


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

