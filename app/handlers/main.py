from aiogram import Router, F
from aiogram.filters import Command

from ..operations.trainings_operations import *
from app.handlers.rare_handlers.rare import rare_router
from ..handlers.admin_handlers.admin import admin_router

from .. import states as st

logger = setup_logger(__name__)

# stream_logger = logging.getLogger(__name__)

BOT_NAME = os.getenv('BOT_NAME')

main_router = Router()

main_router.message.middleware(AdminMiddleware())
main_router.callback_query.middleware(AdminMiddleware())
main_router.include_routers(rare_router, admin_router)


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

@main_router.callback_query(F.data.startswith('delete_from_training_is'))
@main_router.message(st.DeleteFromTrainingFSM.delete_from_training)
async def call_delete_from_training(call: CallbackQuery | Message, state: FSMContext, is_admin: bool):
    dlt_from_trn = DeleteFromTraining(handler=call, state=state, is_admin=is_admin)
    await dlt_from_trn.dispatch()


# # Просмотр рейтинга
# @user_router.message(Command('rait'))
# async def choose_raiting(message: Message, state: FSMContext):
#     await message.answer('Выберите рейтинг по видам спорта', reply_markup=kb.training_types_kb(raiting=True))
#     await state.clear()
#     await state.set_state(st.ShowRaitingFSM.raiting)
#
#
# @user_router.callback_query(F.data.startswith('training_type'), st.ShowRaitingFSM.raiting)
# async def show_raiting(call: CallbackQuery, state: FSMContext, is_admin: bool):
#     if 'general' not in call.data:
#         training_index = int(call.data.split(':')[1])
#         training_type = TRAINING_TYPES[training_index]
#         stars_dict = stars_dict_getter()
#         if training_type in stars_dict:
#             text = ''
#             for i, item in enumerate(stars_dict[training_type]):
#                 if item.star_count > 0:
#                     stars = ''
#                     for _i, _num in enumerate(str(item.star_count)):
#                         # Здесь преобразуем цифру числа звезд в индекс
#                         idx = int(_num)
#                         stars += f'{NUMBERS[idx]}'
#                         stars = f'⭐️{stars}'
#                 else:
#                     stars = ''
#                 visit_count = f'🏃🏽‍♂️{item.visit_count}'
#                 name = item.user.tg_name
#                 username = '@' + item.user.tg_username if is_admin else ''
#                 if call.from_user.id == item.user.tg_id:
#                     text += f'<b>{i + 1}</b>. {stars} <b><i>{name} {username}</i></b> {visit_count}\n'
#                 else:
#                     text += f'<b>{i + 1}</b>. {stars} {name} {username} {visit_count}\n'
#             await call.message.answer(f'Текущий рейтинг по дисциплине <b>"{training_type}"</b>:\n\n'
#                                       f'{text}',
#                                       parse_mode='HTML', reply_markup=kb.back_kb_markup)
#         else:
#             await call.message.answer(
#                 f'По дисциплине <b>"{training_type}"</b> в этом сезоне тренировки пока не проводились',
#                 parse_mode='HTML', reply_markup=kb.back_kb_markup)
#     else:
#         general_raiting = general_raiting_getter()
#         if len(general_raiting) > 0:
#             gen_rait_txt = ''
#             for i, item in enumerate(general_raiting):
#                 tg_username = f'@{item[1]}' if is_admin else ''
#                 tg_name, star_count, marks = item[0], item[2], item[3]
#                 stars = ''
#                 for _i, _num in enumerate(str(star_count)):
#                     # Здесь преобразуем цифру числа звезд в индекс
#                     idx = int(_num)
#                     stars += f'{NUMBERS[idx]}'
#                     stars = f'⭐️{stars}'
#                 gen_rait_txt += f'<b>{i + 1}</b>. {stars} {tg_name} {tg_username} {marks}\n'
#             await call.message.answer(f'<b>ОБЩИЙ РЕЙТИНГ⚡️</b>\n\n'
#                                       f'{gen_rait_txt}',
#                                       parse_mode='HTML', reply_markup=kb.back_kb_markup)
#         else:
#             await call.message.answer(f'В этом сезоне тренировки пока не проводились',
#                                       parse_mode='HTML', reply_markup=kb.back_kb_markup)
#
#
# # Включение/выключение получения уведомлений
# @user_router.message(Command('ntf'))
# async def ntf(message: Message, state: FSMContext):
#     await state.clear()
#     user = await db_req.get_or_create_user(message.from_user, for_telegramm=True)
#     receive_notifications = user['receive_notifications']
#     text = ('При включенном уведомлении Вы:\n'
#             '🔹 сразу же будете получать сообщения о новых тренировках\n')
#     await message.answer(text, parse_mode='HTML', reply_markup=await app.keyboards.kb_registr_and_profile.notify(receive_notifications))
#     await state.update_data(receive_notifications=receive_notifications)
#
#
# @user_router.callback_query(F.data == 'on_off_notify')
# async def on_off_notify(call: CallbackQuery, state: FSMContext):
#     receive_notifications = await db_req.update_user_receive_notificcations(call.from_user.id)
#     await call.message.delete()
#     text = 'Уведомления по <b>ОБЩИМ</b> дедлайнам оплаты за тренировки включены 🔔' \
#         if receive_notifications else 'Уведомления отключены 🔕'
#     await call.message.answer(text, parse_mode='HTML')
#     user_cache[call.from_user.id].receive_notifications = receive_notifications
#
#
#
#
#
#
#
#
#
#
# ''' ДОСТУПНЫЕ АДМИНУ ФУНКЦИИ  '''
#
#
# # Функция, которая определяет из БД учатников по веденным порядковым номерам
# async def participant_list_formation(call_mess: Message | CallbackQuery, state: FSMContext, is_admin: bool):
#     try:
#         data = await state.get_data()
#         event = data.get('event')
#
#         call_mess = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
#         participants_count = event['participants_count']
#
#         # Список порядковых номеров участников, которые введены админом для подтверждения оплаты
#         number_list = call_mess.text.replace(' ', '').split(',')
#         number_list = list(map(int, number_list))
#
#         # Если админ ввел номера (в т.ч. 0), выходящие за пределы ОСНОВНОГО СПИСКА
#         if any(num > participants_count or num == 0 for num in number_list):
#             raise IndexError
#         index_list = list(map(lambda x: x - 1, number_list))
#         asyncio.create_task(delete_bkg(call_mess))
#         return {'index_list': index_list, 'number_list': number_list}
#     except ValueError:
#         await call_mess.answer('Нужно <i><u>через запятую</u></i> вводить только '
#                                '<b>целочисленные значения</b>. Повторите ввод.',
#                                parse_mode='HTML',
#                                reply_markup=kb.return_to_start_markup(process_interrupt=True))
#         raise
#     except IndexError:
#         await call_mess.answer(f'Допустимы только порядковые номера из '
#                                f'<u>ОСНОВНОГО СПИСКА</u>.\n'
#                                f'Повторите ввод.',
#                                parse_mode='HTML',
#                                reply_markup=kb.return_to_start_markup(process_interrupt=True))
#         raise
#
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
