from aiogram import F, Router
from aiogram.filters import Command

from app.operations.admin_operations.admin_operations import *

from app.operations.admin_operations.manage_operations import *
from app.schedule import MoveToEnd

admin_router = Router()


@admin_router.callback_query(F.data=='/admpan')
@admin_router.message(Command('admpan'))
async def call_show_admin_panel(call: CallbackQuery | Message, state: FSMContext):
    await show_admin_panel(call, state)


@admin_router.callback_query(F.data=='add_event')
@admin_router.callback_query(F.data.startswith('create_event_type_is'))
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


@admin_router.callback_query(F.data.startswith('move_to_end_of_event_is'))
@admin_router.message(st.MoveToEndFSM.process)
@admin_router.message(st.MoveToEndFSM.finish)
async def call_move_to_end(call: Message | CallbackQuery, state: FSMContext, is_admin:bool):
    move_to_end = MoveToEndCls(call, state, is_admin)
    await move_to_end.dispatch()




# @admin_router.callback_query(F.data.startswith('drop_or_chancel'))
# async def drop_or_chancel(call: CallbackQuery, state: FSMContext):
#     call_data = call.data.split(':')[1]
#     if call_data != 'chancel_training':
#         await state.update_data(call_data=call_data)
#         fragment = 'исключить из тренировки' if call_data == 'participant' else 'переместить в конец очереди'
#         text = (f'Укажите в сообщении боту порядковый номер участника, которого '
#                 f'хотите <b><i><u>{fragment}</u></i></b> и отправьте это сообщение.')
#         await state.set_state(st.DropParticipantFromTrainFSM.waiting)
#     else:
#         text = ('Если точно хотите отменить эту тренировку, введите "да" '
#                 'в сообщении боту, иначе операция будет отменена.')
#         await state.set_state(st.ChancelTraininigFSM.chancel_training)
#     keyboard = kb.return_to_start_markup()
#     await call.message.answer(text, reply_markup=keyboard, parse_mode='HTML')
#
#
# @admin_router.message(st.DropParticipantFromTrainFSM.waiting)
# async def drop_participant_middlware_state(message: Message, state: FSMContext, is_admin: bool):
#     try:
#         data = await state.get_data()
#         event_user, event_id = data.get('event_user'), data.get('event_id')
#         index = int(message.text)  # порядковый номер участника
#
#         if index > len(event_user) or index == 0:
#             raise IndexError
#
#         user_id = next(item['user__id'] for i, item in enumerate(event_user) if i == index - 1)
#         await state.update_data(user_id=user_id)
#         await message.answer('Вы подтверждаете выполнение данного действия?',
#                              reply_markup=kb.drop_participant_kb)
#         return
#
#     except ValueError:
#         text = 'Допустим ввод только одного целого числа.'
#         pass
#     except IndexError:
#         text = 'Таких порядковых номеров нет в списке.'
#
#         pass
#     except Exception as e:
#         await logger.error(e)
#         # stream_logger.error(e)
#         text = 'Возникла неизвестная ошибка.'
#         pass
#
#     await state.set_state(None)
#     await show_formed_info_about_event(message, state, is_admin)
#     await message.answer(f'{text}\nОперация отклонена')
#     asyncio.create_task(delete_bkg(message))
#
#
# @admin_router.callback_query(F.data.startswith('drop_paricipant'))
# async def drop_participant(call: CallbackQuery, state: FSMContext, is_admin: bool):
#     if call.data.split(':')[1] == 'yes':
#         data = await state.get_data()
#         call_data = data['call_data']  # удаляем или перемещаем в конец очереди
#         user_id, event_id = data['user_id'], data['event_id']
#         if call_data == 'participant':  # удаление участника из тренировки
#             await db_req.delete_event_user(user_id, event_id=event_id)
#             text = 'Участник удален.'
#         else:  # перемещение участника в конец очереди
#             await db_req.update_event_user(user_id, event_id, replace_to_end=True)
#             text = 'Участник перемещен в конец очереди.'
#     else:
#         text = 'Операция отменена.'
#     await show_formed_info_about_event(call, state, is_admin)
#     await call.message.answer(text)
#     asyncio.create_task(delete_bkg(call))
#
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
