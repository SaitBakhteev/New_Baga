from aiogram import F, Router
from aiogram.filters import Command

from app.operations.admin_operations.admin_operations import *

from app.operations.admin_operations.manage_operations import *

admin_router = Router()


@admin_router.callback_query(F.data=='/admpan')
@admin_router.message(Command('admpan'))
async def call_show_admin_panel(call: CallbackQuery | Message, state: FSMContext):
    await show_admin_panel(call, state)


@admin_router.callback_query(F.data=='add_event')
@admin_router.callback_query(F.data.startswith('create_event_type_is'))
@admin_router.callback_query(F.data.startswith('payment_dedline'))
@admin_router.message(st.CreateEventFSM.template)
@admin_router.callback_query(F.data=='save_template')
@admin_router.callback_query(F.data=='add_new_event')
async def call_input_template(call: CallbackQuery | Message, state: FSMContext, is_admin: bool):
    create_event = CreateEvent(handler=call, state=state, is_admin=is_admin)
    await create_event.dispatch()


@admin_router.callback_query(F.data.startswith('edit_event_is'))
@admin_router.callback_query(F.data.startswith('finish_edit_event'))
@admin_router.message(st.EditEventFSM.insert_template)
async def call_edit_event(call: CallbackQuery | Message, state: FSMContext, is_admin: bool):
    edit_event = EditEvent(call, state, is_admin)
    await edit_event.dispatch()


@admin_router.callback_query(F.data.startswith('to_manage_of_event_is'))
async def call_show_event_with_manage_interface(call: CallbackQuery, state: FSMContext):
    await show_event_with_manage_interface(call, state)


@admin_router.callback_query(F.data.startswith('confirm_payment_of_event_is'))
@admin_router.callback_query(F.data.startswith('refute_payment_of_event_is'))
@admin_router.callback_query(F.data.startswith('cancel_verify_payment_of_event_is'))
@admin_router.message(st.PayConfirmationFSM.write_participants)
async def call_payment_verify(call: CallbackQuery | Message, state: FSMContext, is_admin: bool):
    pay_vrfy = PaymentVerification(call, state, is_admin)
    await pay_vrfy.dispatch()


@admin_router.callback_query(F.data.startswith('cancel_training'))
@admin_router.message(st.DeleteEventFSM.confirm)
async def call_cancel_training(call: CallbackQuery | Message, state: FSMContext, is_admin: bool):
    del_event = DeleteEvent(call, state, is_admin)
    await del_event.dispatch()


@admin_router.callback_query(F.data.startswith('give_star_of_event_is'))
@admin_router.callback_query(F.data.startswith('give_stars_continue'))
@admin_router.message(st.GiveStarsFSM.continue_)
@admin_router.message(st.GiveStarsFSM.finish)
async def call_give_stars(call: Message | CallbackQuery, state: FSMContext, is_admin:bool):
    give_stars = GiveStars(call, state, is_admin)
    await give_stars.dispatch()


@admin_router.callback_query(F.data.startswith('add_question_to_event_is'))
@admin_router.message(st.AddQuestion.finish)
async def call_add_question(call: CallbackQuery, state: FSMContext, is_admin: bool):
    add_question = AddQuestion(call, state, is_admin)
    await add_question.dispatch()


@admin_router.callback_query(F.data.startswith('move_to_end_of_event_is'))
@admin_router.message(st.MoveToEndFSM.process)
@admin_router.message(st.MoveToEndFSM.finish)
async def call_move_to_end(call: Message | CallbackQuery, state: FSMContext, is_admin:bool):
    move_to_end = MoveToEndCls(call, state, is_admin)
    await move_to_end.dispatch()


@admin_router.callback_query(F.data.startswith('drop_user_from_event_is'))
@admin_router.message(st.DropUserFSM.process)
@admin_router.message(st.DropUserFSM.finish)
async def call_move_to_end(call: Message | CallbackQuery, state: FSMContext, is_admin:bool):
    drop_user = DropUser(call, state, is_admin)
    await drop_user.dispatch()


#
# @admin_router.message(st.ChancelTraininigFSM.chancel_training)
# async def chancel_training_state(message: Message, state: FSMContext, is_admin: bool):
#     await state.set_state(None)
#     if message.text.lower() == 'да':
#         data = await state.get_data()
#         event_id = data.get('event_id')
#         await db_req.delete_event(event_id)
#         await message.answer('Тренировка удалена.')
#         await cmd_start(message, state, is_admin)
#     else:
#         await message.answer('Удаление тренировки отменено.')
#         await state.set_state(None)
#     asyncio.create_task(delete_bkg(message))
