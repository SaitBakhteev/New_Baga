from aiogram.filters import Command
from aiogram import Router, F

from datetime import datetime, timedelta

from config import bot, reper_dedline_definiton
from ..keyboards import return_to_start_markup
from ..database.models import *
from app.states import SendCheckFSM
from app.operations.often_useful_funcs import *
import app.states as st


logger = setup_logger(__name__)

add_router = Router()  # дополнительный роутер, чтобы разгрузить бизнес-логику


class TrainingsOperations():
    def __init__(self, handler: CallbackQuery | Message,
                 state: FSMContext,
                 is_admin: bool,
                 user_cache):
        self._handler, self._state, self._is_admin, self._user_cache = handler, state, is_admin, user_cache

    def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('choose_event'):
                self._call_choose_event(self._handler, self._state, self._is_admin)
            elif self._handler.data.startswith('sign_up_for_training'):
                self._sign_up_for_training()
            # elif self._handler.startswith('sign_up_for_training'):
        elif self._state.get_state() == st.DeleteFromTrainingFSM.delete_from_training:
            self._delete_from_training_confirm(self._handler, self._state, self._is_admin, self._user_cache)
        else:
            if self._state.get_state() == st.DeleteFromTrainingFSM.delete_from_training:
                self._delete_from_training_confirm(self._handler, self._state, self._is_admin, self._user_cache)

    async def _call_choose_event(self, call: CallbackQuery, state: FSMContext, is_admin: bool):
        await show_formed_info_about_event(call, state, is_admin)

    # Записаться на тренировку
    async def _sign_up_for_training(self):
        try:
            event_id = int(self._handler.data.split(':')[1])
            event = db_req.get_event(id=event_id)
            event_user = await db_req.get_event_user(event_id=event_id)
            ''' Подгружаем из БД все необходимые данные по тренировке '''

            user_id = self._user_cache[self._handler.from_user.id].id
            now = datetime.now().replace(tzinfo=None)
            data = {'user_id': user_id,
                    'event_id': event_id,
                    'created_at': now,
                    'modified_at': now}
            text = show_text_about_event(event=event,
                                         event_user=event_user,
                                         tg_id=self._handler.from_user.id,
                                         is_admin=self._is_admin,)
            await db_req.create_event_user(data)
            await show_formed_info_about_event(call, is_admin)
            text = ('Вы записались на тренировку.\n'
                    'Если у вас уже оплачена эта тренировка, нажмите на кнопку <i>"✔️ Тренировка оплачена"</i>')
            reper_dedline, dedline_type = reper_dedline_definiton(
                real_dedline=event['payment_dedline'].replace(tzinfo=None),
                now=now, event_datetime=event['event_datetime'].replace(tzinfo=None),
            )
            if dedline_type == 'individ_dedline':
                text += (f'\n\n <b>ВНИМАНИЕ❗️</b>\n'
                         f' У Вас другой дедлайн оплаты, Вам необходимо оплатить '
                         f'за тренировку до <b><i>{reper_dedline}</i></b>')
            await call.message.answer(text, parse_mode='HTML')
        except Exception as e:
            await logger.error(e)
            # stream_logger.error(e)

    # # Удалиться из тренировки
    # @add_router.callback_query(F.data == 'delete_from_training')
    async def _delete_from_training(self, call: CallbackQuery, state: FSMContext, is_admin: bool):
        await call.message.answer('Если Вы уверены, что хотите удалиться из тренировки '
                                  'напишите в сообщении <i><b>да</b></i> и отправьте его.\n'
                                  'Если сомневаетесь, прервите процесс или отправьте любое слово',
                                  reply_markup=kb.return_to_start_markup(),
                                  parse_mode='HTML')
        await state.set_state(st.DeleteFromTrainingFSM.delete_from_training)

    # @add_router.message(st.DeleteFromTrainingFSM.delete_from_training)
    async def _delete_from_training_confirm(self, message: Message, state: FSMContext, is_admin: bool, user_cache):
        try:
            if message.text.lower().strip() == 'да':
                data = await state.get_data()
                user_id, event_id, event = data.get('user_id'), data.get('event_id'), data.get('event')
                await cmd_start(message, state, is_admin)
                current_event_user = await db_req.get_event_user_after_delete(event_id=event_id)
                participants_count = current_event_user[0].event.participants_count
                res_prtcpt = None
                if len(current_event_user) > participants_count:
                    user_pos = next(
                        i for i, item in enumerate(current_event_user) if item.user.tg_id == message.from_user.id)
                    res_prtcpt = current_event_user[participants_count] if user_pos < participants_count else None
                await db_req.delete_event_user(user_id, event_id)
                await message.answer('Вы удалились из записи на тренировку.')

                text = (f"❗️⚡️ <b>ВНИМАНИЕ АДМИНАМ</b>\n"
                        f"Пользователь с никнеймом @<i>{message.from_user.username}</i> удалился из следующей тренировки\n\n"
                        f"Дисциплина: <b><i>{data['training_type']}</i></b>\n"
                        f"{data['event']['event_text']}")
                if res_prtcpt:
                    res_tg_username, res_tg_id, res_id = (res_prtcpt.user.tg_username, res_prtcpt.user.tg_id,
                                                          res_prtcpt.user.id)
                    text += (f'\n\n<b><i>🔆ВАЖНО!</i></b>\n'
                             f"Пользователь с никнеймом <i>@{res_tg_username}</i> поднялся из резерва в основной список "
                             f"и ему было выслано соответствующее уведомление")
                    # Обновляем времена поднявшегося из резерева и других резервистов
                    seconds, update_list = -1, []
                    now = datetime.now().replace(tzinfo=None)
                    for _user in current_event_user[participants_count:]:
                        seconds += 1
                        _user.created_at = now + timedelta(seconds=seconds)
                        update_list.append(_user)
                    await db_req.update_event_user_after_delete(update_list)

                for k in user_cache:  # Информаривание админов
                    if user_cache[k].admin_permissions == True:
                        tg_id = user_cache[k].tg_id
                        await bot.send_message(chat_id=tg_id, text=text, parse_mode='HTML')
                if res_prtcpt:  # Информаривание пользователя, поднявшегося из резерва
                    text = (f'⚡️⚡️<b>ВАЖНАЯ ИНФОРМАЦИЯ ДЛЯ ВАС</b>\n'
                            f'Вы перешли из резерва в основной список следующей тренировки:\n\n'
                            f"Дисциплина: <b><i>{data['training_type']}</i></b>\n"
                            f"{data['event']['event_text']}")
                    reper_dedline, dedline_type = reper_dedline_definiton(
                        real_dedline=event['payment_dedline'],
                        now=now, event_datetime=event['event_datetime'],
                    )
                    if dedline_type == 'individ_dedline':
                        text += (f'\n\n <b>ВНИМАНИЕ❗️</b> \n'
                                 f'<i>У Вас другой дедлайн оплаты.\n'
                                 f' Вам необходимо оплатить за тренировку до</i>'
                                 f' <b><i>{reper_dedline}</i></b>')
                    await bot.send_message(chat_id=res_tg_id, text=text, parse_mode='HTML')
            else:
                await message.answer('Удаление прервано')
                await show_formed_info_about_event(message, state, is_admin)
        except Exception as e:
            await logger.error(f'ошибка в delete_from_training_confirm: {e}')
            await cmd_start(message, state, is_admin)
        asyncio.create_task(delete_bkg(message))

    # Записать друга на тренировку
    # @add_router.callback_query(F.data == 'add_friend')
    async def add_friend(call: CallbackQuery, state: FSMContext):
        await call.message.answer('Введите никнейм вашего друга.\n'
                                  '<i>Пример</i>: @ivanov1934',
                                  parse_mode='HTML', reply_markup=kb.return_to_start_markup())
        await state.set_state(st.AddFriendFSM.add_friend)


@add_router.message(st.AddFriendFSM.add_friend)
async def add_friend(message: Message, state: FSMContext, is_admin: bool, user_cache):
    try:
        data = await state.get_data()
        event_id = data.get('event_id')
        text = message.text.strip().replace('@', '')
        if text != message.from_user.username:
            friend = None
            for k in user_cache:
                if user_cache[k].tg_username == text:
                    friend_id, friend, friend_tg_id = user_cache[k].id, user_cache[k].tg_username, user_cache[k].tg_id
                    break
            if friend is not None:
                ''' Проверяем не записывался ли ранее мой друг (friend_signed_up) и не
                записывал ли я кого-нибудь жо этого (my_prev_friend) '''
                friend_signed_up = await db_req.get_event_user_for_check_friend(event_id, friend_id=friend_id)
                my_prev_friend = await db_req.get_event_user_for_check_friend(
                    event_id, i_am_friend=message.from_user.username
                )

                if not friend_signed_up and is_admin is not True and not my_prev_friend:
                    message_text = ('⚠️ Внимание! Записать друга на тренировку можно только <b>один раз</b>!\n'
                                    'Вы подтверждаете запись друга?')
                    await state.update_data(friend_id=friend_id, friend=friend, friend_tg_id=friend_tg_id)
                    await state.set_state(st.AddFriendFSM.add_friend_confirm)
                    return await message.answer(message_text, reply_markup=kb.add_friend_confirm_kb, parse_mode='HTML')
                elif not friend_signed_up and is_admin is True:  # админы могут добавлять хоть сколько друзей
                    message_text = ('Вы подтверждаете запись друга?')
                    await state.update_data(friend_id=friend_id, friend=friend, friend_tg_id=friend_tg_id)
                    await state.set_state(st.AddFriendFSM.add_friend_confirm)
                    return await message.answer(message_text, reply_markup=kb.add_friend_confirm_kb, parse_mode='HTML')
                elif friend_signed_up:
                    message_text = f'☑️ Ваш друг с никнеймом <i>{friend}</i> уже состоит в записи на тренировку'
                elif my_prev_friend and is_admin is not True:
                    message_text = f'⛔️ Вы ранее уже записали друга с никнеймом <i>{my_prev_friend}</i>'
            else:
                message_text = f'🤷🏻‍♂️ Пользователь с никнеймом <i>{text}</i> не зарегистрирован в боте'
        else:
            message_text = '☝🏽Вы не можете добавить себя вместо друга'
        await message.answer(message_text, parse_mode='HTML', reply_markup=kb.return_to_start_markup())
    except Exception as e:
        await logger.error(f'Add+friend: {e}')
        await cmd_start(message, state, is_admin)
        asyncio.create_task(delete_bkg(message))
        # stream_logger.error(f'Add+friend: {e}')


@add_router.callback_query(F.data.startswith('add_friend') and st.AddFriendFSM.add_friend_confirm)
async def add_friend_confirm(call: CallbackQuery, state: FSMContext, is_admin: bool, user_cache):
    try:
        call_data = call.data.split(':')[1]
        if call_data == 'yes':
            data = await state.get_data()
            data['created_at'] = datetime.now()
            friend_id, friend, friend_tg_id = data['friend_id'], data['friend'], data['friend_tg_id']
            await db_req.create_event_user(data, friend_id=friend_id, i_am_friend=call.from_user.username)
            event_id = data.get('event_id')
            event = await db_req.get_event(id=event_id)
            training_type, event_text = event[0]['training_type'], event[0]['event_text']
            text = (f'️⚡️ ️⚡️ <b>ВАЖНАЯ ИНФОРМАЦИЯ</b>\n'
                    f'Вас записали на следующую тренировку\n'
                    f'<b>Тип тренировки</b>:{training_type}\n{event_text}')
            reper_dedline, dedline_type = reper_dedline_definiton(
                real_dedline=event[0]['payment_dedline'].replace(tzinfo=None),
                now=data['created_at'], event_datetime=event[0]['event_datetime'].replace(tzinfo=None),
            )
            if dedline_type == 'individ_dedline':
                text += (f'\n\n <b>ВНИМАНИЕ❗️</b>\n'
                         f' У Вас другой дедлайн оплаты, Вам необходимо оплатить '
                         f'за тренировку до <b><i>{reper_dedline}</i></b>')

            await bot.send_message(chat_id=friend_tg_id, text=text, parse_mode='HTML')
            await call.message.answer(f'Вы успешно записали друга с никнеймом <i>{friend}</i> на тренировку 🖍')
        else:
            await call.message.answer(f'Вы отменили запись друга на тренировку🟡')
        await state.set_state(None)  # выходим из состояния, чтобы кнопки дезактивировались
        await show_formed_info_about_event(call, state, is_admin)
    except Exception as e:
        await call.message.answer(f'Возникла ошибка')
        await logger.error(f'add_friend_confirm: {e}\n'
                           f'user_cache = {user_cache}')
        await cmd_start(call, state, is_admin)
        asyncio.create_task(delete_bkg(call))


# Оповестить бот об оплате кнопкой '✔️ Тренировка оплачена'
@add_router.callback_query(F.data.startswith('payment_notify'))
@add_router.message(SendCheckFSM.send_check)
async def payment_notify(call: CallbackQuery | Message, state: FSMContext, is_admin: bool):
    try:
        sendCheck = SendCheck(call, state)
        await sendCheck.dispatch()
        # call_data = call.data.split(':')[1]
        # data = await state.get_data()
        # user_id, event_id = data['user_id'], data['event_id']
        # payment_notify = True if call_data == "i_payed_check" else False
        # await db_req.update_event_user(user_id, event_id, payment_notify)
        # await choose_event(call, state, is_admin)
        # if payment_notify is not True:
        #     await call.message.answer('❗️<b>ВНИМАНИЕ</b>❗️\n'
        #                               'Вы отменили уведомление об оплате. Но это не '
        #                               'означает автоматический возврат денежных средств, если '
        #                               'Вы уже оплатили. Поэтому для возврата денежных средств обратитесь '
        #                               'к админу тренировки.')
    except Exception as e:
        await logger.error(e)
        # stream_logger.error(e)



@add_router.message(Command('add'))
async def add_command(message: Message, is_admin: bool):
    await bot.send_document()
    await message.answer(f'Значение составляет {is_admin} ')
#
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


''' Неиспользумые фичи, но потенциально могут пригодиться '''

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

