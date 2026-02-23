import asyncio

from aiogram.types import InlineKeyboardMarkup
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
                await self._state.clear()
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

        # Если кнопка оповещения бота доступна, двигаемся дальше
        new_individual_dedline = event_user.modified_at + timedelta(days=1, hours=12)
        if new_individual_dedline > event_user.event.event_datetime:
            new_individual_dedline = event_user.event.event_datetime
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
        if not self._is_admin:  # проверим, не простой ли это пользователь и не добавлял ли он ранее
            my_prev_friend = await db_rq_event_user.get_event_user_for_check_friend(
                event_id, i_am_friend=self._handler.from_user.username)
            if my_prev_friend:
                await self._state.clear()
                text = f'⛔️ Вы ранее уже записали друга с никнеймом <i>@{my_prev_friend}</i>'
                await self._handler.message.answer(text, parse_mode='HTML')
                await self._handler.answer()  # чтобы кнопка сразу стала активной
                return

        # Если ранее друга не добавляли или это админ, то продолжаем
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
                _available, message_text = proc_check['available'], proc_check['message_text']
                if _available is True:
                    await self._state.update_data(friend_id=friend_id, friend=friend, friend_tg_id=friend_tg_id)
                    await self._state.set_state(st.AddFriendFSM.add_friend_confirm)
                keyboard = add_friend_confirm_kb(event_id) if _available is True else cancel_kb(event_id)
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
                    return {'friend_id': friend_id,
                            'friend': user_cache[k].tg_username,
                            'friend_tg_id':user_cache[k].tg_id,
                            'friend_signed_up': friend_signed_up}
            return f'🤷🏻‍♂️ Пользователь с никнеймом <i>@{text}</i> не зарегистрирован в боте'
        else:
            return '☝🏽Вы не можете добавить себя как друга'

    # Проверяем далее, можно ли добавлять друга
    def _process_of_check(self, _init_data: dict):
        friend, friend_signed_up = (_init_data['friend'], _init_data['friend_signed_up'])
        if not friend_signed_up:
            message_text = ('⚠️ Внимание! Записать друга на тренировку можно только <b>один раз</b>!\n'
                            'Вы подтверждаете запись друга?\n')
            available = True
        else:
            message_text = f'☑️ Ваш друг с никнеймом <i>@{friend}</i> уже состоит в записи на тренировку'
            available = False
        return {'message_text': message_text, 'available': available}

    async def _add_friend_confirm(self):
        try:
            call_data = self._handler.data.split(':')
            state, event_id = call_data[0], int(call_data[1])
            if state == 'add_friend_confirm_to_event_is':
                data = await self._state.get_data()
                friend_id, friend, friend_tg_id = data['friend_id'], data['friend'], data['friend_tg_id']
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


class AddLike(ParentClassForTrainingOperations):
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('add_like_of_event_is'):
                await self._begin()
        elif await self._state.get_state() == st.AddLike.input_prtcp:
            await self._input()
        elif  await self._state.get_state() == st.AddLike.confirm:
            await self._confirm()

    async def _begin(self):
        event_id = int(self._handler.data.split(':')[1])
        event_user = await db_rq_event_user.get_event_user(event_id=event_id)

        check = await self._check_avlblty_on_begin(event_user)
        if check is True:
            await self._state.update_data(event_id=event_id, event_user=event_user)
            await self._state.set_state(st.AddLike.input_prtcp)
            msg = 'Имейте ввиду, голосовать можно только ОДИН раз!\nВведите порядковый номер игрока из основного списка'
            await self._handler.message.answer(msg, parse_mode='HTML', reply_markup=cancel_kb(event_id))
        else:
            await self._state.clear()
            await show_formed_info_about_event(self._handler, self._is_admin, event_id, self._user_id)
            await self._handler.message.answer(check, parse_mode='HTML')
            asyncio.create_task(delete_bkg(self._handler))

    # Проверяем доступность голосования для дальнейших действий
    async def _check_avlblty_on_begin(self, event_user: list):
        question, event_datetime = event_user[0]['event__question'], event_user[0]['event__event_datetime']
        if not question:
            return 'К сожалению админ не добавил вопрос для голосования 🥺'
        elif len(event_user) == 0:
            return 'Увы, но никого нет в списке на тренировку 🤷🏼‍♂️'
        elif datetime.now() + timedelta(hours=1) < event_datetime.replace(tzinfo=None):
            return 'Голосование открывается через час после начала тренировки ⏱️️'

        # Конечная проверка, есть ли Вы в основном списке и не голосовали ли ранее
        prtcpts_count = event_user[0]['event__participants_count']
        main_lst = event_user[:prtcpts_count]  # отсекаем резерв
        await self._state.update_data(main_lst=main_lst)
        i_am = next((item for item in main_lst if item['user__id']==self._user_id), None)
        if not i_am:
            return 'Вы отсутствуете в основном списке 🙅🏻'
        if i_am['me_liked']:
            return 'Вы уже ранее отдали свой голос ☝🏼'
        return True

    async def _input(self):
        data = await self._state.get_data()
        main_lst = data['main_lst']
        try:
            num = int(self._handler.text.strip())
            if num > len(main_lst) or num <= 0:
                raise ValueError('out of range')
            user_id =main_lst[num-1]['user__id']
            if user_id == self._user_id:
                await self._handler.answer('Нельзя голосовать за самого себя ☝🏼',
                                           reply_markup=cancel_kb(data['event_id']))
                return
            await self._state.update_data(user_id=user_id)
            msg = 'Для подтверждения, отправьте <b><i>да</i></b>'
            await self._state.set_state(st.AddLike.confirm)
        except ValueError as e:
            if str(e).startswith('out of range'):
                msg = 'Вы ввели номер за пределами ОСНОВНОГО списка'
            else:
                msg = 'Некорретный формат. Вводить нужно только одно целое число.'
        await self._handler.answer(msg, reply_markup=cancel_kb(data['event_id']), parse_mode='HTML')
        asyncio.create_task(delete_bkg(self._handler))

    async def _confirm(self):
        '''
        Здесь мы сначала должны получит из БД текущее полодение вещей по игроку
        :return:
        '''
        data = await self._state.get_data()
        event_id, user_id = data['event_id'], data['user_id']
        if self._handler.text.strip() == 'да':
            await db_rq_event_user.update_for_like(event_id, user_id, self._user_id)
            msg = 'Ваш голос зачтен 💚👍🏼'
        else:
            msg = '🚫 Голосование отменено'
        await self._state.clear()
        await show_formed_info_about_event(self._handler, self._is_admin, event_id, self._user_id)
        await self._handler.answer(msg, parse_mode='HTML')
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
        event_id = int(self._handler.data.split(':')[1])
        await self._handler.message.answer(text, reply_markup=cancel_kb(event_id), parse_mode='HTML')
        await self._state.update_data(event_id=event_id)
        await self._state.set_state(st.DeleteFromTrainingFSM.delete_from_training)

    async def _delete_from_training_confirm(self):
        try:
            data = await self._state.get_data()
            event_id = data['event_id']
            if self._handler.text.lower().strip() == 'да':
                self._now = datetime.now()
                important_params = await self._important_params()
                await db_rq_event_user.delete_event_user(self._user_id, event_id)
                await self._send_messages(important_params)
                msg = '🗑 Вы удалились из записи на тренировку.'
                await cmd_start(self._handler, self._state, self._is_admin, user_cache)
            else:
                msg = '🟠 Удаление прервано.'
                await show_formed_info_about_event(self._handler, self._is_admin, event_id, self._user_id)
            await self._handler.answer(msg)
        except Exception as e:
            text, except_text = ('⭕️ Возникла ошибка.', f'Ошибка _delete_from_training_confirm: {e}')
            await self._exception_func(text, except_text)
        await self._state.clear()

    async def _important_params(self):
        '''
        Метод устанавливает важные параметры:
         - поднимется ли кто-нибудь из резерва после удаления;
         - параметры тренировки
        Здесь определяем позицию удаляющегося. Важны два критерия:
        - есть ли резерв;
        - находится ли удаляемый в основном списке.
        Если выполняются оба критерия, то фиксируется tg_id первого участника резерва, который поднимется из резерва
        '''
        data = await self._state.get_data()
        event_id = data.get('event_id')
        current_event_user = await db_rq_event_user.get_event_user_before_delete(event_id=event_id)
        participants_count = current_event_user[0].event.participants_count
        event_datetime = current_event_user[0].event.event_datetime
        payment_dedline = current_event_user[0].event.payment_dedline
        training_type = current_event_user[0].event.training_type
        event_text = current_event_user[participants_count].event.event_text

        idx_pos = next(i for i, item in enumerate(current_event_user) if item.user.id == self._user_id)
        if idx_pos < participants_count and len(current_event_user) > participants_count:
            rsrv_tg_id = current_event_user[participants_count].user.tg_id
            rsrv_tg_username = current_event_user[participants_count].user.tg_username
            await self._update_params(current_event_user, participants_count, payment_dedline, event_datetime)
        else:
            rsrv_tg_id = rsrv_tg_username = None

        return {'rsrv_tg_id': rsrv_tg_id, 'rsrv_tg_username': rsrv_tg_username, 'training_type': training_type,
                'event_datetime': event_datetime.replace(tzinfo=None), 'event_text': event_text}

    async def _update_params(self, current_event_user:list, participants_count:int, payment_dedline, event_datetime):
        '''
        Метод:
        - обновляет поля modified_at всем резервникам
        - обновляет individual_dedline резервнику, который поднялся в основной список
        - записывает обновления в БД
        return: текст индвидуального девлайна для информирования, чтобы информировать резревника,
                поднявшегося в основной список
        '''
        seconds, update_list = -1, []
        for i, obj in enumerate(current_event_user[participants_count:]):
            if i == 0:
                ind_dline = set_individual_dedline(payment_dedline, event_datetime, self._now)
                obj.individual_dedline = ind_dline['individual_dedline'].replace(tzinfo=None)
                self._ind_dline_txt = ind_dline['text']
            seconds += 1
            obj.modified_at = self._now + timedelta(seconds=seconds)
            update_list.append(obj)
        await db_rq_event_user.update_event_user_on_delete(update_list)

    async def _send_messages(self, impnt_params:dict):
        '''
        Метод делает рассылку админам и тому, кто поднялся из резерва.
        Текст для админов может дополниться, если есть резервник, поднявшийся в основной список, поэтому
         SendMessages.to_admins идет как бы после блока с условием
        '''
        rsrv_tg_id, rsrv_tg_username = impnt_params['rsrv_tg_id'], impnt_params['rsrv_tg_username']
        event_datetime, event_text = impnt_params['event_datetime'], impnt_params['event_text']
        training_type = impnt_params['training_type']
        tg_id, tg_username = self._handler.from_user.id, self._handler.from_user.username
        adm_txt = (f"❗️⚡️ <b>ВНИМАНИЕ АДМИНАМ</b>\n"
                f"Пользователь с никнеймом @<i>{tg_username}</i> "
                f"удалился из следующей тренировки\n\n"
                f"Дисциплина: <b><i>{training_type}</i></b>\n"
                f"{event_text}")

        if rsrv_tg_id:
            adm_txt += (f'\n\n<b><i>🔆ВАЖНО!</i></b>\n'
                     f"Пользователь с никнеймом <i>@{rsrv_tg_username}</i> поднялся из резерва в основной список "
                     f"и ему было выслано соответствующее уведомление")

            # Информаривание пользователя, поднявшегося из резерва
            text = (f'⚡️⚡️<b>ВАЖНАЯ ИНФОРМАЦИЯ ДЛЯ ВАС</b>\n'
                    f'Вы перешли из резерва в основной список следующей тренировки:\n\n'
                    f"Дисциплина: <b><i>{training_type}</i></b>\n"
                    f"{event_text}"
                    f"\n\n{self._ind_dline_txt}")
            await SendMessages.to_one_receiver(text, rsrv_tg_id)
        await SendMessages.to_admins(adm_txt, self._now, event_datetime)


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

