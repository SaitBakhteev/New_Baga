import asyncio
from datetime import datetime, date, time, timedelta

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import states as st
from app.database import requests as db_rq
from app.database import event_user_requests as db_event_user_rq
from ..often_ops_and_classes import show_text_about_event

from config.constants import *

from ..often_ops_and_classes import delete_bkg, ParentClassForTrainingOperations, show_formed_info_about_event
from ...keyboards.admin_keyboards.admin_keyboards import *


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

    # Собрать список участников на проведение операции
    async def _write_participants(self):

        try:
            data = await self._state.get_data()
            event, event_user, verification_mode = data['event'], data['event_user'], data['verification_mode']
            prtcp_lst_form = await self._participant_list_formation()
            index_list, number_list = prtcp_lst_form['index_list'], prtcp_lst_form['number_list']

            # Формирование списка id объектов EventUser для обновления в БД значений поля 'payment_confirmed'
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
            # asyncio.create_task(delete_bkg(self._handler))
        except Exception as e:
            text, except_text = 'Произошла ошибка верификации оплаты', f'Ошибка в _write_participants: {e}'
            await self._exception_func(text, except_text)
            await logger.error(e)
            # stream_logger.error(e)

    # Функция, которая определяет из БД учатников по веденным порядковым номерам
    async def _participant_list_formation(self):
        try:
            data = await self._state.get_data()
            event = data.get('event')

            call_mess = self._handler.message if isinstance(self._handler, CallbackQuery) else self._handler
            participants_count = event['participants_count']

            # Список порядковых номеров участников, которые введены админом для подтверждения оплаты
            number_list = call_mess.text.replace(' ', '').split(',')
            number_list = list(map(int, number_list))

            # Если админ ввел номера (в т.ч. 0), выходящие за пределы ОСНОВНОГО СПИСКА
            if any(num > participants_count or num == 0 for num in number_list):
                raise IndexError
            index_list = list(map(lambda x: x - 1, number_list))
            asyncio.create_task(delete_bkg(self._handler))
            return {'index_list': index_list, 'number_list': number_list}
        except ValueError:
            error_msg = ('Нужно <i><u>через запятую</u></i> вводить только <b>целочисленные значения</b>. '
                         'Повторите ввод.'),
            pass
        except IndexError:
            error_msg = (f'Допустимы только порядковые номера из '
                         f'<u>ОСНОВНОГО СПИСКА</u>.\n'
                         f'Повторите ввод.')
            pass
        await call_mess.answer(
            error_msg, parse_mode='HTML',
            reply_markup=interrupt_or_return_button(callback_data=f"to_manage_of_event_is:{event['id']}")
        )
        raise


class GiveStars(ParentClassForTrainingOperations):
    pass
