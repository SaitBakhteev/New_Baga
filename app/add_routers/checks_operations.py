from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram import Router, F
from config import bot, setup_logger
from ..keyboards import return_to_start_markup
from ..database import requests as db_req
from app.states import SendCheckFSM

logger = setup_logger(__name__)

add_router = Router()  # дополнительный роутер, чтобы разгрузить бизнес-логику


# Класс отправки чека об оплате
class SendCheck():
    def __init__(self, call: Message | CallbackQuery, state: FSMContext):
        self._call, self._state = call, state
        if isinstance(call, CallbackQuery):
            self._call_data = 'upload_check'
        else:
            self._call_data = 'send_check'

    async def dispatch(self):
        match self._call_data:
            case 'upload_check':
                await self._upload_check()
            case 'send_check':
                await self._send_check()

    async def _upload_check(self):
        await self._call.message.answer('Загрузите чек об оплате', reply_markup=return_to_start_markup())
        await self._state.set_state(SendCheckFSM.send_check)

    async def _send_check(self):
        file_id = self._call.photo[-1].file_id
        await bot.send_photo(chat_id=1933865493, photo=file_id,  caption='Чек об оплате')
        await db_req.update_event_user(user_id, event_id, payment_notify)
        await choose_event(call, state, is_admin)
        if payment_notify is not True:
            await call.message.answer('❗️<b>ВНИМАНИЕ</b>❗️\n'
                                      'Вы отменили уведомление об оплате. Но это не '
                                      'означает автоматический возврат денежных средств, если '
                                      'Вы уже оплатили. Поэтому для возврата денежных средств обратитесь '
                                      'к админу тренировки.')

        # self._state.update_data(file_id = file_id)


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
