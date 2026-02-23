from aiogram import Router, F
from aiogram.filters import Command

from ..operations.trainings_operations import *
from app.handlers.rare_handlers.rare import rare_router
from ..handlers.admin_handlers.admin import admin_router
from ..handlers.for_tests import test_router
from ..operations.stat_ops import ShowStat

from .. import states as st

logger = setup_logger(__name__)

# stream_logger = logging.getLogger(__name__)

BOT_NAME = os.getenv('BOT_NAME')

main_router = Router()

main_router.message.middleware(AdminMiddleware())
main_router.callback_query.middleware(AdminMiddleware())
main_router.include_routers(rare_router, admin_router, test_router)


# БЛОК ВЫБОРА ТРЕНИРОВОК
# ======================
@main_router.callback_query(F.data=='/event')
@main_router.message(Command('event'))
async def call_show_traininig_types(call: Message | CallbackQuery, state: FSMContext):
    _handler = call.message if isinstance(call, CallbackQuery) else call
    await show_training_types(_handler, state)


@main_router.callback_query(F.data.startswith('to_training_type_is'))
async def call_show_events(call: CallbackQuery, state: FSMContext, is_admin: bool):
    await show_events(call, state, is_admin)


@main_router.callback_query(F.data.startswith('to_event_is'))
async def call_show_training(call: CallbackQuery, is_admin: bool):
    event_id = int(call.data.split(':')[1])
    user_id = user_cache[call.from_user.id].id
    await show_formed_info_about_event(call, is_admin, event_id, user_id)


@main_router.callback_query(F.data.startswith('sign_up_to_training_is'))
async def call_sign_up_to_training(call: CallbackQuery, state: FSMContext, is_admin: bool):
    await sign_up_to_training(call, state, is_admin)


# БЛОК ВЫЗОВА МНОГОШАГОВЫХ ОПЕРАЦИЙ
# ==================================

@main_router.callback_query(F.data.startswith('payment_notify_by_event_is'))
@main_router.message(st.PaymenNotify.confirm)
async def call_payment_notify(call: CallbackQuery | Message, state: FSMContext, is_admin: bool):
    payment_notify = PaymentNotify(call, state, is_admin)
    await payment_notify.dispatch()


@main_router.callback_query(F.data.startswith('add_friend_to_event'))
@main_router.callback_query(F.data.startswith('add_friend_confirm_to_event_is'))
@main_router.message(st.AddFriendFSM.add_friend)
async def call_add_friend(call: CallbackQuery | Message, state: FSMContext, is_admin: bool):
    add_friend = AddFriend(call, state, is_admin)
    await add_friend.dispatch()


@main_router.callback_query(F.data.startswith('delete_from_training_is'))
@main_router.message(st.DeleteFromTrainingFSM.delete_from_training)
async def call_delete_from_training(call: CallbackQuery | Message, state: FSMContext, is_admin: bool):
    dlt_from_trn = DeleteFromTraining(handler=call, state=state, is_admin=is_admin)
    await dlt_from_trn.dispatch()


@main_router.callback_query(F.data.startswith('add_like_of_event_is'))
@main_router.message(st.AddLike.input_prtcp)
@main_router.message(st.AddLike.confirm)
async def call_add_like(call: CallbackQuery | Message, state: FSMContext, is_admin: bool):
    add_like = AddLike(handler=call, state=state, is_admin=is_admin)
    await add_like.dispatch()


# БЛОК ПРОСМОТРА СТАТИСТИКИ
# ========================

@main_router.message(Command('rait'))
@main_router.callback_query(F.data == '/rait')
@main_router.callback_query(F.data.startswith('to_raiting_type_is'))
@main_router.callback_query(F.data == 'general_statistics')
@main_router.callback_query(F.data == 'likes_statistics')
async def call_rait(call: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    await ShowStat.dispatch(call)


#
# # -------------- Список админов ----------------
# @user_router.callback_query(F.data == 'admin_list')
# async def admin_list(call_mess: CallbackQuery | Message, state: FSMContext):
#     call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
#     try:
#         text = ''
#         for k in user_cache:
#             if user_cache[k].admin_permissions == True:
#                 text += f'{user_cache[k].tg_username}\n'
#         if len(text) > 0:
#             await call_mess.answer(f'<b><i>Текущий список админов</i></b>:\n{text}',
#                                    reply_markup=kb.edit_admins(),
#                                    parse_mode='HTML')
#             await state.set_state(st.EditAdminFSM.show_list)
#         else:
#             await call_mess.answer('Кроме Вас больше нет админов', reply_markup=kb.edit_admins())
#     except Exception as e:
#         await logger.error(f'Error_on admin_list: {e}\n'
#                            f'user_cache = {user_cache}')
#         # stream_logger.error(f'Error_on admin_list: {e}\n'
#         #              f'user_cache = {user_cache}')
#         await call_mess.answer('Возникла неизвестная ошибка.')
#         await state.clear()
#         await admin_panel(call_mess, state, True)
#         asyncio.create_task(delete_bkg(call_mess))
#
#
# @user_router.callback_query(F.data.startswith('edit_admin:'))
# async def edit_admin(call: CallbackQuery, state: FSMContext):
#     try:
#         call_data = call.data.split(':')[1]
#         admin_permissions = True if call_data == 'add' else False
#         await state.update_data(admin_permissions=admin_permissions)
#         await state.set_state(st.EditAdminFSM.edit_admin)
#         await call.message.answer('Введите никнейм телеграмм-аккаунта ❗️<i>без "@"</i>❗️, '
#                                   'для которого хотите установить или отменить админский статус.\n '
#                                   '<i>Например, если у пользователя аккаунт <u>"@Ivanov_79"</u>, то '
#                                   'нужно ввести <u>"Ivanov_79"</u></i>.',
#                                   reply_markup=kb.return_to_start_markup(), parse_mode='HTML')
#         await state.set_state(st.EditAdminFSM.edit_admin)
#     except Exception as e:
#         await logger.error(f'Ошибка при редактировании списка админов: {e}')
#         # stream_logger.error(f'Ошибка при редактировании списка админов: {e}')
#         await call.message.answer('Неизвестная ошибка.')
#         await state.clear()
#         await admin_panel(call, state, True)
#         asyncio.create_task(delete_bkg(call))
#
#
# @user_router.message(st.EditAdminFSM.edit_admin)
# async def finish_edit_admin(message: Message, state: FSMContext):
#     try:
#         tg_username = message.text.replace('@', '').strip()
#         data = await state.get_data()
#         admin_permissions = data['admin_permissions']
#         user, tg_id = await db_req.update_admin_and_get(tg_username, admin_permissions)
#         user_cache[tg_id] = user
#         await message.answer('Статус изменен.')
#     except Exception as e:
#         await logger.error(e)
#         # stream_logger.error(e)
#         await message.answer('Данный пользователь не зарегистрирован в боте.')
#         pass
#     await state.clear()
#     await admin_list(message, state)
#     asyncio.create_task(delete_bkg(message))
#
#
# # ---------- Конец редактирования списка админов ---------------
#
# # ----------- Удаление шаблонов ---------------
# @user_router.callback_query(F.data == 'delete_template')
# async def delete_template(call: CallbackQuery, state: FSMContext):
#     try:
#         templates = await db_req.get_templates()
#         tempale_list_text = ''
#         if templates:
#             for template in templates:
#                 id, text = template['id'], template['text']
#                 tempale_list_text += f'<b>{id}</b>. {text}\n\n'
#             await call.message.answer(f'{tempale_list_text}\n\n'
#                                       f'Введите id шаблона (выделен жирным шрифтом), который хотите удалить '
#                                       f'и отправьте в сообщении боту.',
#                                       reply_markup=kb.return_to_start_markup())
#             await state.set_state(st.DeleteTemplateFSM.delete_template)
#         else:
#             await call.message.answer(f'У Вас нет сохраненных шаблонов.')
#     except Exception as e:
#         await logger.error(f'ошибка в delete_template: {e}')
#         # stream_logger.error(f'ошибка в delete_template: {e}')
#         await admin_panel(call, state, True)
#         asyncio.create_task(delete_bkg(call))
#
#
# @user_router.message(st.DeleteTemplateFSM.delete_template)
# async def delete_template_finish(message: Message, state: FSMContext):
#     try:
#         template_id = int(message.text.strip())
#         var_delete_template = await db_req.delete_template(template_id)
#         if var_delete_template == 'OK':
#             text = 'Шаблон удален'
#         else:
#             text = 'Возможно Вы ввели несуществующий id шаблона. Операция отменена'
#     except ValueError:
#         text = 'Значение id шаблона должно быть в формате целого числа. Операция отменена'
#         pass
#     except Exception as e:
#         await logger.error(f'unknown error on delete_template_finish: {e}')
#         # stream_logger.error(f'unknown error on delete_template_finish: {e}')
#         text = 'Возникла неизвестная ошибка. Операция отклонена'
#         pass
#     await message.answer(text)
#     await state.clear()
#     await admin_panel(message, state, True)
#
#
# # Админ-панель
# @user_router.message(Command('admpan'))
# async def admin_panel(call_mess: Message | CallbackQuery, state: FSMContext, is_admin: bool):
#     call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
#     if is_admin == True:
#         await call_mess.answer('Панель администратора', reply_markup=await kb.admin_panel())
#     else:
#         await call_mess.answer('У Вас нет прав администратора')
#
#
# # Видео-Инструкция для админа
# @user_router.message(Command('admin'))
# @user_router.callback_query(F.data == 'admin_tutorial')
# async def admin_tutorial(call_mess: Message | CallbackQuery, state: FSMContext):
#     await state.clear()
#     message = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
#     await message.answer(VIDEO_ADMIN_TUTORIAL, parse_mode='HTML')
#
#
# @user_router.message(Command('adm_cre'))
# async def general_tut(message: Message, bot: Bot):
#     await load_video(message, bot, 'create_event')
#
#
# @user_router.message(Command('adm_nts'))
# async def general_tut(message: Message, bot: Bot):
#     await load_video(message, bot, 'main_notes')
#
#
# @user_router.message(Command('adm_vrf'))
# async def general_tuut(message: Message, bot: Bot):
#     await load_video(message, bot, 'verify')
#
#
# @user_router.message(Command('adm_trs'))  # сдвинуть участников, удалить тренровку
# async def general_tut_1(message: Message, bot: Bot):
#     await load_video(message, bot, 'transfer')
#
#
# @user_router.message(Command('adm_edt'))  # редактировать тренровку
# async def general_tut_1(message: Message, bot: Bot):
#     await load_video(message, bot, 'edit_event')
#
#
# # СОЗДАНИЕ ТРЕНИРОВКИ
#
#
# @user_router.message(Command('test'))
# async def test(message: Message):
#     try:
#         # await test_for_sch(user_cache=user_cache, bot = bot)
#         await message.answer('Это тест')
#     except Exception as e:
#         await logger.error(e)
#         # stream_logger.error(e)
#
#
# @user_router.message(Command('tst'))
# async def test(message: Message):
#     try:
#         # test_for_sch
#         # await test_for_sch(tst=True)
#         await message.answer('Это тест ТСТ')
#     except Exception as e:
#         await logger.error(e)
#         # stream_logger.error(e)
#
