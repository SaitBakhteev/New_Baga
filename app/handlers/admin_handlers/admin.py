import asyncio
from datetime import date, time, datetime, timedelta
from functools import reduce

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery

from app import states as st
from app.operations.admin_operations.admin_operations import *

from app.operations.admin_operations.manage_operations import *

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
@admin_router.message(st.EditEvent.insert_template)
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

#
# @admin_router.callback_query(F.data.startswith("dedline_"), st.CreateEventFSM.dedline_type)
# async def add_dedline_and_finish(call: CallbackQuery | Message, state: FSMContext, is_admin: bool):
#     show_mess = call.message if isinstance(call, CallbackQuery) else call
#     try:
#         data = await state.get_data()
#         event_text, event_datetime = data["event_text"], data["event_datetime"]
#         if 'is_update' not in data:  # если создается новая тренировка (там работает CallbackQuery)
#             # Здесь проверка скорее всего бесмысленна, так перестраховка
#             dedline_hour = int(call.data.split("_")[1]) if isinstance(call, CallbackQuery) else None
#             now = datetime.now()
#             # now = datetime.now() - timedelta(days=26)  # заглушка для теста
#
#             real_dedline = now + timedelta(hours=dedline_hour)
#             # real_dedline = now + timedelta(hours=400)  # заглушка для тестов
#             reper_dedline, _ = reper_dedline_definiton(real_dedline=real_dedline, is_string=False)
#             data["created_at"], data["payment_dedline"] = now, real_dedline
#
#             if event_datetime - timedelta(hours=2) < reper_dedline:
#                 raise ValueError
#
#             if real_dedline:
#                 data["event_text"] = (f"{event_text}\n"
#                                       f"<b><i>Начальный дедлайн оплаты</i></b>: до "
#                                       f"{reper_dedline.strftime('%H:%M %d.%m.%Y')}\n")
#
#             # Отложен в стороеку этот фрагмент
#             # else:  # иначе для тренировки устанавливается индивидуальный для каждого участника посуточный дедлайн
#             #     data["event_text"] = (f"{event_text}\n"
#             #                           f"<b><i>Срок оплаты</i></b>: в течение суток после записи на тренировку\n")
#             text = (
#                 f"<b>Создана следующая тренировка</b>:\n\n"
#                 f"<b>Тип тренировки</b>: {data['training_type']}\n"
#                 f"{data['event_text']}\n\n"
#             )
#
#             await show_mess.answer(text, parse_mode="HTML")
#
#             # Два запроса в БД: запись новой тренировки и получение её данных
#             await db_req.create_event(data)
#             await cmd_start(call, state, is_admin)
#             for k in user_cache:
#                 if user_cache[k].receive_notifications is True:
#                     tg_id = user_cache[k].tg_id
#                     # await bot.send_message(chat_id=tg_id, text=text, parse_mode='HTML')
#         else:
#             await show_mess.answer('Тренировка отредактирована')
#             event_text, end_fragment, event_id = str(data["event_text"]), str(data["end_fragment"]), int(
#                 data["event_id"])
#             end_key_idx = end_fragment.find(':')
#             end_key, end_val = end_fragment[:end_key_idx + 1], end_fragment[end_key_idx + 1:]
#             data["event_text"] = f'{event_text.strip()}\n<b>{end_key}</b> {end_val}'
#             await db_req.update_event(event_id, data)
#             event = await db_req.get_event(id=event_id)
#             await state.update_data(event=event[0])
#             # await choose_event(show_mess, state, is_admin)
#     except ValueError:
#         await state.set_state(st.CreateEventFSM.dedline_type)
#         await show_mess.answer('⛔️ Дедлайн оплаты должен быть минимум за два часа до начала '
#                                'тренировки. Выберите другой дедлайн',
#                                reply_markup=await kb.admin_dedline_type(*DEDLINE_TYPE))
#     except Exception as e:
#         await show_mess.answer("Возникла ошибка! Повторите создание тренировки")
#         await cmd_start(call, state, is_admin)
#         await logger.error(f"Ошибка при добавлении тренировки: {e}")
#     await show_formed_info_about_event(show_mess, state, is_admin)
#     asyncio.create_task(delete_bkg(show_mess))
#
#
# @admin_router.callback_query(F.data.startswith("training_manage"))
# async def training_manage(call: CallbackQuery, state: FSMContext):
#     try:
#         data = await state.get_data()
#         events, event_id, event, training_type = data['events'], data['event_id'], data['event'], data['training_type']
#         await state.set_state(st.ChooseEventFSM.admin_management)
#         trn_info = await training_info_formation(call, True, events=events,
#                                                  event_id=event_id,
#                                                  event=event,
#                                                  training_type=training_type)
#         await call.message.answer(trn_info['text'],
#                                   parse_mode="HTML",
#                                   reply_markup=kb.admin_train_manag_kb)
#         asyncio.create_task(delete_bkg(call))
#     except Exception:
#         pass
#
#
# @admin_router.callback_query(F.data == 'edit_event')
# async def edit_event(call: CallbackQuery, state: FSMContext):
#     data = await state.get_data()
#     template = data['event']['event_text']
#
#     # Более приемлемый способ для множественной замены в большой строке
#     replacements = {"<b>": "", "</b>": "", "<i>": "", "</i>": "",
#                     "Дата тренировки": "❗️Дата тренировки",
#                     "Время": "❗️Время",
#                     "Квота участников": "❗️Квота участников",
#                     'Босс тренировки': '❗️Босс тренировки',
#                     # "ИНФОРМАЦИЯ ОБ ОПЛАТЕ:\n": "Как оплатить: ",
#                     "\n\n": "\n"}
#
#     # Переделка текущего текста тренировки под шаблон для создания
#     template = reduce(lambda fragment, kv: fragment.replace(*kv), replacements.items(), template)
#     end_fragment = template[template.find('Начальный дедлайн оплаты'):]
#     end_idx = template.find(end_fragment)
#     template = template[:end_idx]  # урезаем до фразы срок оплаты
#
#     await state.update_data(is_update=True, end_fragment=end_fragment)
#     await state.set_state(st.CreateEventFSM.template)
#     await call.message.answer('Вставьте текущий шаблон этой тренировки, '
#                               'после чего отредактируйте и отправьте в сообщении боту',
#                               reply_markup=await kb.insert_template_on_edit_admin(template))
#
#
# @admin_router.callback_query(F.data.startswith('verify_payment:'))
# async def payment_verification(call: CallbackQuery, state: FSMContext):
#     try:
#         # Нажата кнопка '✅ Подтвердить оплату' или '❌ Опровергнуть оплату'
#         verify_type = call.data.split(':')[1]
#         await state.update_data(verify_type=verify_type)
#
#         if verify_type == 'change':
#             text = ("Вы выбрали тип верификации <i>'✖️ Отменить верификацию оплаты'</i>. "
#                     "Данное действие вы можете осуществить для участников с <u>любым</u> статусом.\n")
#
#         elif verify_type == 'confirm':
#             text = ("Вы выбрали тип верификации <i>'✅ Подтвердить оплату'</i>. "
#                     "Данное действие вы можете осуществить только для участников со статусами ✔️, ⚠️ и ❌.\n")
#
#         else:
#             text = ("Вы выбрали тип верификации <i>'❌ Опровергнуть оплату'</i>. "
#                     "Данное действие вы можете осуществить только для участников со статусом ✔️. "
#                     "Если ни один из выбранных вами участников не будет соответствовать данному критерию, "
#                     "то бот отменит операцию.\n")
#
#         text += ('\n Чтобы выполнить соответсвующую верификацию, наберите <i><u>через запятую</u></i> порядковые '
#                  'номера участников в вышеприведенном списке👆🏻 в виде <u>сообщения</u>, после чего отправьте его боту.\n'
#                  'Например, для верификации 3-го, 5-го и 8-го участников в списке наберите сообщение так:\n'
#                  '<i><b>3, 5, 8</b></i>\n\n'
#                  "<i>Примечание</i>: статусы могут быть обновлены <u>частично</u> или вовсе <u>не обновлены</u>.\n"
#                  'С более подробной иформацией можете ознакомиться в <b>/admin</b>')
#         await call.message.answer(text, parse_mode='HTML', reply_markup=kb.return_to_start_markup())
#         await state.set_state(st.UpdateEventUserFSM.payment_confirmed)
#     except Exception as e:
#         await logger.error(e)
#         # stream_logger.error(e)
#
#
# @admin_router.message(st.UpdateEventUserFSM.payment_confirmed)
# async def confirm_payment(message: Message, state: FSMContext, is_admin: bool):
#     try:
#         data = await state.get_data()
#         event, event_user, verify_type = (data.get('event'), data.get('event_user'),
#                                           data.get('verify_type'))
#         prtcp_lst_form = await participant_list_formation(message, state, is_admin)
#         index_list, number_list = prtcp_lst_form['index_list'], prtcp_lst_form['number_list']
#
#         # Формирование списка id объектов EventUser для обновления в БД значений поля 'payment_confirmed'
#         if verify_type == 'change':  # Отменить верификацию оплаты ✖️
#             id_list = [event_user[i]['id'] for i in index_list]
#         elif verify_type == 'confirm':  # Подтвердить платеж можно только, если поле 'payment_confirmed' не True
#             id_list = [event_user[i]['id'] for i in index_list if event_user[i]['payment_confirmed'] is not True]
#         else:  # Опровергнуть платеж можно, если 'payment_confirmed' пустое и 'paid_check' не пустое
#             id_list = [event_user[i]['id'] for i in index_list if event_user[i]['payment_confirmed'] is None
#                        and event_user[i]['paid_check'] is not None]
#
#         # Обновление в БД
#         if len(id_list) > 0:
#             if verify_type == 'change':
#                 await db_req.update_event_user_for_payment_verify(id_list, is_confirm=None)
#             elif verify_type == 'refute':
#                 await db_req.update_event_user_for_payment_verify(id_list, is_confirm=False)
#             else:
#                 await db_req.update_event_user_for_payment_verify(id_list)
#             report = ('👁‍🗨 Обновление статусов проведено <i>частично</i>. '
#                       'Причины описаны в <b>/admin</b>.') if len(id_list) < len(number_list) \
#                 else '🔷 Статусы всех указанных участников обновлены.'
#         else:
#             report = '🛑 Статусы <b>не обновлены</b>. Причины описаны в <b>/admin</b>.'
#
#         await message.answer(report, parse_mode='HTML')
#         await show_formed_info_about_event(message, state, is_admin)
#         asyncio.create_task(delete_bkg(message))
#
#     except Exception as e:
#         await logger.error(e)
#         # stream_logger.error(e)
#
#
# @admin_router.callback_query(F.data == 'give_star')
# async def give_star(call: CallbackQuery, state: FSMContext, is_admin: bool):
#     data = await state.get_data()
#     event = data['event']
#     if event['stars'] is None:
#         await state.set_state(st.ChooseEventFSM.give_star)
#         await call.message.answer(
#             '‼️ <b>ВНИМАНИЕ</b> ‼️\n'
#             'Зафиксировать звёзд можно только <b>ОДИН РАЗ (!!!)</b> \n'
#             'Введите через запятую порядковые номера игроков, которым хотите присвоить звезду',
#             reply_markup=kb.return_to_start_markup(), parse_mode='HTML'
#         )
#     else:
#         user_id_lst = [int(i) for i in event['stars'].replace(' ', '').split(',')]
#         stars_txt = ""
#         for k in user_cache:
#             if user_cache[k].id in user_id_lst:
#                 stars_txt += f"<b><i>{user_cache[k].tg_username}</i></b>\n"
#         await call.message.answer('СТОП🛑. Вы уже на данную тренировку зафиксировали звёзд со '
#                                   'следующими никнеймами:\n'
#                                   f'{stars_txt}', parse_mode='HTML')
#         await state.set_state(None)
#         await show_formed_info_about_event(call, state, is_admin)
#
#
# @admin_router.message(st.ChooseEventFSM.give_star)
# async def give_star_input(message: Message, state: FSMContext, is_admin: bool):
#     try:
#         data = await state.get_data()
#         event, event_user, verify_type = (data.get('event'), data.get('event_user'),
#                                           data.get('verify_type'))
#         prtcp_lst_form = await participant_list_formation(message, state, is_admin)
#         index_list, number_list = prtcp_lst_form['index_list'], prtcp_lst_form['number_list']
#         star_ids_list = [event_user[i]['user__id'] for i in index_list]
#         # Поеобразуем спискок id звезд в строку
#         stars = ",".join(str(x) for x in star_ids_list) if star_ids_list else None
#         await state.update_data(stars=stars)
#         await state.set_state(st.ChooseEventFSM.confirm_give_star)
#         await message.answer('⚠️ Если Вы убеждены, что это окончательный список звезд, '
#                              'отправьте в сообщении боту слово <i>да</i>',
#                              reply_markup=kb.return_to_start_markup(), parse_mode='HTML')
#     except Exception as e:
#         await logger.error(f'Ошибка в присвоении звезды: {e}')
#         # stream_logger.error(f'Ошибка в присвоении звезды: {e}')
#
#
# @admin_router.message(st.ChooseEventFSM.confirm_give_star)
# async def confirm_give_star(message: Message, state: FSMContext, is_admin: bool):
#     data = await state.get_data()
#     event_id, event, stars = data['event_id'], data['event'], data['stars']
#     text = message.text
#     if text == 'да':
#         if stars:
#             answer = 'Звезды тренировки добавлены успешно 🤩'
#             await db_req.update_event(event_id=event_id, stars=stars, data=None)
#             event['stars'] = stars
#             await state.update_data(event=event)
#         else:
#             answer = 'Вы никого не указали из звезд 🤷🏻‍♂️'
#     else:
#         answer = 'Отправлено невалидное сообщение. Операция отменена ⛔️'
#     await message.answer(answer)
#     # await state.set_state(None)
#     await show_formed_info_about_event(message, state, is_admin)
#
#
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
