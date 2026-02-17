import asyncio
from datetime import datetime, date, time, timedelta

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from cryptography.hazmat.primitives.keywrap import aes_key_wrap

from app import states as st
from app.database import requests as db_rq
from app.database import event_user_requests as db_event_user_rq
from ..often_ops_and_classes import show_text_about_event

from config.constants import *

from ..often_ops_and_classes import delete_bkg, ParentClassForTrainingOperations, show_formed_info_about_event
from ...keyboards.admin_keyboards.admin_keyboards import *
from ...keyboards.admin_keyboards.confirm_admin_keyboards import give_stars_continue_kb

from config.log_config import setup_logger

logger = setup_logger(__name__)


_verification_text = (
    "Чтобы выполнить это действие, наберите <i><u>через запятую</u></i> порядковые номера "
    "участников в вышеприведенном списке👆🏻 в виде <u>сообщения</u>, после чего отправьте его боту.\n"
    "Например, для верификации 3-го, 5-го и 8-го участников в списке наберите сообщение так:\n"
    "<i><b>3, 5, 8</b></i>"
)


async def show_event_with_manage_interface(call: CallbackQuery | Message, state: FSMContext,
                                           event_id = None):
    try:
        await state.clear()
        event_id = int(call.data.split(':')[1]) if isinstance(call, CallbackQuery) else event_id
        _call = call.message if isinstance(call, CallbackQuery) else call
        user_id = user_cache[call.from_user.id].id
        event, event_user = await db_rq.get_event(id=event_id), await db_event_user_rq.get_event_user(event_id=event_id)
        keyboard = admin_train_manag_kb(event_id)
        text = show_text_about_event(event, event_user, user_id)
        await _call.answer(text, parse_mode='HTML', reply_markup=keyboard)
        asyncio.create_task(delete_bkg(call))
    except Exception as e:
        await logger.error(f'Ошибка в show_event_with_manage_interface: {e}')


# Подтверждение оплаты
class PaymentVerification(ParentClassForTrainingOperations):
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith("confirm_payment_of_event_is"):
                await self._show_interface(verification_mode='confirm')
            elif self._handler.data.startswith("refute_payment_of_event_is"):
                await self._show_interface(verification_mode='refute')
            elif self._handler.data.startswith("cancel_verify_payment_of_event_is"):
                await self._show_interface(verification_mode='cancel')
        elif await self._state.get_state() == st.PayConfirmationFSM.write_participants:
            await self._write_participants()

    async def _show_interface(self, verification_mode):
        try:
            await self._state.clear()
            match verification_mode:
                case "confirm": _verif_mode_text = '✅ Подтвердить оплату'
                case "refute": _verif_mode_text = '❌ Опровергнуть оплату'
                case "cancel": _verif_mode_text = '✖️ Отменить верификацию оплаты'
            text =  f"Вы выбрали тип верификации <i>{_verif_mode_text}</i>.\n{_verification_text}"
            event_id = int(self._handler.data.split(':')[1])
            await self._handler.message.answer(
                text, parse_mode='HTML',
                reply_markup=interrupt_or_return_button(
                    callback_data=f'to_manage_of_event_is:{event_id}'
                )
            )
            event, event_user = await db_rq.get_event(event_id), await db_event_user_rq.get_event_user(event_id)
            await self._state.update_data(event=event, event_user=event_user, verification_mode=verification_mode)
            await self._state.set_state(st.PayConfirmationFSM.write_participants)
        except Exception as e:
            await logger.error(f'Ошибка в _show_interface: {e}')

    # Собрать список участников на проведение операции
    async def _write_participants(self):

        try:
            data = await self._state.get_data()
            event, event_user, verification_mode = data['event'], data['event_user'], data['verification_mode']
            prtcp_lst_form = await self._participant_list_formation()
            if 'error_msg' in prtcp_lst_form:
                error_msg, keyboard = prtcp_lst_form['error_msg'], prtcp_lst_form['keyboard']
                await self._handler.answer(error_msg, reply_markup=keyboard, parse_mode='HTML')
                return

            # Формирование списка id объектов EventUser для обновления в БД значений поля 'payment_confirmed'
            index_list, number_list = prtcp_lst_form['index_list'], prtcp_lst_form['number_list']
            match verification_mode:
                case 'confirm': id_list = [event_user[i]['id'] for i in index_list]
                case 'refute': id_list = [event_user[i]['id'] for i in index_list if event_user[i]['paid_check']
                                          is True and event_user[i]['payment_confirmed'] is None]
                case 'cancel': id_list = [event_user[i]['id'] for i in index_list if event_user[i]['payment_confirmed']
                                          is not None]
            # Обновление в БД
            if len(id_list) > 0:
                await db_event_user_rq.update_event_user_for_payment_verify(id_list, verification_mode)
                report = ('👁‍🗨 Обновление статусов проведено <i>частично</i>. '
                          'Причины описаны в <b>/admin</b>.') if len(id_list) < len(number_list) \
                    else '🔷 Статусы всех указанных участников обновлены.'
            else:
                report = '🛑 Статусы <b>не обновлены</b>. Причины описаны в <b>/admin</b>.'

            await self._handler.answer(report, parse_mode='HTML')
            await show_event_with_manage_interface(self._handler, self._state, event_id=event['id'])
            asyncio.create_task(delete_bkg(self._handler))
        except Exception as e:
            text, except_text = '🚫 Произошла ошибка верификации оплаты', f'Ошибка в _write_participants: {e}'
            await self._exception_func(text, except_text)
            await logger.error(f'Ошибка в _write_participants: {e}')
            # stream_logger.error(e)

    # Функция, которая определяет из БД учатников по веденным порядковым номерам
    async def _participant_list_formation(self):
        try:
            data = await self._state.get_data()
            event, event_user  = data['event'], data['event_user']
            participants_count = event['participants_count']

            call_mess = self._handler.message if isinstance(self._handler, CallbackQuery) else self._handler
            available_count = participants_count if len(event_user) > participants_count else len(event_user)

            # Список порядковых номеров участников, которые введены админом для подтверждения оплаты
            number_list = call_mess.text.replace(' ', '').split(',')
            number_list = list(map(int, number_list))

            # Если админ ввел номера (в т.ч. 0), выходящие за пределы ОСНОВНОГО СПИСКА
            if any(num > available_count or num == 0 for num in number_list):
                raise IndexError
            index_list = list(map(lambda x: x - 1, number_list))
            asyncio.create_task(delete_bkg(self._handler))
            return {'index_list': index_list, 'number_list': number_list}
        except ValueError:
            error_msg = ('Нужно <i><u>через запятую</u></i> вводить только <b>целочисленные значения</b>. '
                         'Повторите ввод.')

        except IndexError:
            error_msg = (f'Допустимы только порядковые номера из '
                         f'<u>ОСНОВНОГО СПИСКА</u>.\n'
                         f'Повторите ввод.')

        keyboard = interrupt_or_return_button(callback_data=f"to_manage_of_event_is:{event['id']}")
        return {'error_msg': error_msg, 'keyboard': keyboard}


class GiveStars(ParentClassForTrainingOperations):
    async def dispatch(self):
        data = await self._state.get_data()
        if 'event_id' in data:
            event_id = data['event_id']
            self._cancel_kb = interrupt_or_return_button(callback_data=f'to_manage_of_event_is:{event_id}')
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('give_star_of_event_is'):
                await self._begin()
            elif (self._handler.data.startswith('give_stars_continue')
                  and await self._state.get_state() == st.GiveStarsFSM.continue_):
                await self._continue()
        elif await self._state.get_state() == st.GiveStarsFSM.finish:
            await self._finish_exec()

    async def _begin(self):
        _init_params = await self._init_params()
        event_id, event = _init_params['event_id'], _init_params['event']
        if event['stars'] is None:
            msg = ('<b>Сообщение боту зависит от контекста</b>:\n'
                   '🔸 🙅🏻 при <b>отсутствии</b> звезд отправьте прочерк <b><i>-</i></b>;\n'
                   '🔸 🤩 при <b>наличии</b> звезд наберите <u>через запятую</u> порядковые номера. '
                   '<b>Пример</b>: <i>1, 2, 3</i>')

            # Вынужден здесь определить клавиатуру из-за отсутствия event_id
            keyboard = interrupt_or_return_button(callback_data=f'to_manage_of_event_is:{event_id}')
            await self._state.set_state(st.GiveStarsFSM.finish)
        else:
            msg = '❗️ Предыдущая запись по этой операции сотрется.\n Продолжить?'
            keyboard = give_stars_continue_kb(event_id)
            await self._state.set_state(st.GiveStarsFSM.continue_)
        await self._handler.message.answer(msg, reply_markup=keyboard)

    async def _init_params(self):
        event_id = int(self._handler.data.split(':')[1])
        event = await db_rq.get_event(event_id)
        event_user = await db_event_user_rq.get_event_user(event_id=event_id)
        await self._state.update_data(event_id=event_id, event=event,event_user=event_user)
        return {'event_id': event_id, 'event': event}

    async def _continue(self):
        if 'Yes' in self._handler.data:
            text = 'Введите <u>через запятую</u> порядковые номера участников ОСНОВНОГО списка или поставьте прочерк.'
            await self._handler.message.answer(text, reply_markup=self._cancel_kb, parse_mode='HTML')
            await self._state.set_state(st.GiveStarsFSM.finish)
        else:
            await self._state.clear()

    async def _finish_exec(self):
        data = await self._state.get_data()
        event_id, event, event_user = data['event_id'], data['event'], data['event_user']
        stars = await self._stars(event, event_user)
        if stars:
            await db_rq.update_event(event_id=event_id, stars=stars, data=None)
            if stars != '-':
                msg = '⭐️ Тренировка отмечена звездами успешно'
            else:
                msg = '➖ Тренировка отмечена без звёзд'
            await self._handler.answer(msg)
            await self._state.clear()
            await show_event_with_manage_interface(self._handler, self._state, event_id)

    async def _stars(self, event, event_user):
        '''
        Определяется список и доступное количество:
        - доступное количество участников (квота или длина event_user)
        - формирует список id юзеров по введеным админом номерам
        '''
        try:
            prtcps_cnt = event['participants_count']
            available_count = prtcps_cnt if len(event_user) >= prtcps_cnt else len(event_user)
            _text_process = self._text_process(available_count, event_user)
            if isinstance(_text_process, str):
                await self._handler.answer(_text_process, parse_mode='HTML', reply_markup=self._cancel_kb)
                return

            stars = '-' if _text_process is False else ','.join(map(str, _text_process))
            return stars
        except Exception as e:
            await logger.error(f'GiveStars__list_form: {e}')

    def _text_process(self, available_count: int, event_user):
        try:
            if self._handler.text.strip() == '-':
                return False
            text_lst = self._handler.text.replace(' ', '').split(',')
            num_lst = list(map(lambda x: int(x), set(text_lst)))
            if any(x > available_count or x <= 0 for x in num_lst):
                raise IndexError
            idx_lst = [i - 1 for i in num_lst]
            id_list = [item['user__id'] for i, item in enumerate(event_user) if i in idx_lst]
            return id_list
        except IndexError:
            return '📛 Порядковые номера должны быть из ОСНОВНОГО СПИСКА'
        except ValueError:
            return '📛 Некорректный формат ввода'


class MoveToEndCls(ParentClassForTrainingOperations):
    async def dispatch(self):
        data = await self._state.get_data()
        if 'event_id' in data:
            event_id = data['event_id']
            self._cancel_kb = interrupt_or_return_button(callback_data=f'to_manage_of_event_is:{event_id}')
        if isinstance(self._handler.data, CallbackQuery):
            if self._handler.data.startswith('move_to_end_of_event_is'):
                await self._begin()
        elif await self._state.get_state() == st.MoveToEndFSM.process:
            await self._process()
        elif  await self._state.get_state() == st.MoveToEndFSM.finish:
            await self._finish()

    async def _begin(self):
        text = 'Введите порядковый номер участника списке'
        event_id = int(self._handler.data.split(':')[1])
        event_user = await db_event_user_rq.get_event_user(event_id=event_id)
        _cancel_kb = interrupt_or_return_button(callback_data=f'to_manage_of_event_is:{event_id}')
        await self._handler.message.answer(text, reply_markup=_cancel_kb)
        await self._state.update_data(event_id=event_id, event_user=event_user)
        await self._state.set_state(st.MoveToEndFSM.process)

    async def _process(self):
        try:
            idx = int(self._handler.text.strip())
            data = await self._state.get_data()
            event_user = data['event_user']
            user_id = event_user[idx-1]['user__id']
            await self._state.update_data(user_id=user_id)
            await self._state.set_state(st.MoveToEndFSM.finish)
            msg = 'Для подтверждения перемещения участника в конец очереди отправьте <b><i>да</i></b>'
        except IndexError:
            msg = 'Такого номера участника нет в списке'
        except ValueError:
            msg = 'Нужно вводить целочисленное значение'
        await self._handler.answer(msg, reply_markup=self._cancel_kb)
        return

    async def _finish(self):
        data = await self._state.get_data()
        user_id, event_id, = data['user_id'], data['event_id']
        if self._handler.text.strip().lower() == 'да':
            await db_event_user_rq.update_event_user(user_id=user_id, event_id=event_id, replace_to_end=True)
            msg = 'Участник перемещен в конец очереди ⬇️'
        else:
            msg = '🚫 Отправлено невалидное сообщение, операция отклонена'
        await self._handler.message.answer(msg)
        await self._state.clear()
        await show_event_with_manage_interface(self._handler, self._state, event_id)


class DropUser(ParentClassForTrainingOperations):
    async def dispatch(self):
        data = await self._state.get_data()
        if 'event_id' in data:
            event_id = data['event_id']
            self._cancel_kb = interrupt_or_return_button(callback_data=f'to_manage_of_event_is:{event_id}')
        if isinstance(self._handler.data, CallbackQuery):
            if self._handler.data.startswith('drop_user_from_event_is'):
                await self._begin()
        elif await self._state.get_state() == st.DropUserFSM.process:
            await self._process()
        elif await self._state.get_state() == st.DropUserFSM.finish:
            await self._finish()

    async def _begin(self):
        text = 'Введите порядковый номер участника списке'
        event_id = int(self._handler.data.split(':')[1])
        event_user = await db_event_user_rq.get_event_user(event_id=event_id)
        _cancel_kb = interrupt_or_return_button(callback_data=f'to_manage_of_event_is:{event_id}')
        await self._handler.message.answer(text, reply_markup=_cancel_kb)
        await self._state.update_data(event_id=event_id, event_user=event_user)
        await self._state.set_state(st.DropUserFSM.process)

    async def _process(self):
        try:
            idx = int(self._handler.text.strip())
            data = await self._state.get_data()
            event_user = data['event_user']
            user_id = event_user[idx - 1]['user__id']
            await self._state.update_data(user_id=user_id)
            await self._state.set_state(st.DropUserFSM.finish)
            msg = 'Для подтверждения удаления участника отправьте <b><i>да</i></b>'
        except IndexError:
            msg = 'Такого номера участника нет в списке'
        except ValueError:
            msg = 'Нужно вводить целочисленное значение'
        await self._handler.answer(msg, reply_markup=self._cancel_kb)
        return

    async def _finish(self):
        data = await self._state.get_data()
        user_id, event_id, = data['user_id'], data['event_id']
        if self._handler.text.strip().lower() == 'да':
            await db_event_user_rq.delete_event_user(user_id=user_id, event_id=event_id)
            msg = 'Участник удален 🚷'
        else:
            msg = '🚫 Отправлено невалидное сообщение, операция отклонена'
        await self._handler.message.answer(msg)
        await self._state.clear()
        await show_event_with_manage_interface(self._handler, self._state, event_id)


