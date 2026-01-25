from aiogram import F, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.router import Router

from app.operations.often_ops_and_classes import cmd_start, AdminMiddleware
from app.operations.regisration_ops import registration_and_welcome

from config.constants import user_cache

rare_router = Router()


@rare_router.callback_query(F.data=='start')
@rare_router.message(CommandStart())
async def call_cmd_start(call: Message | CallbackQuery, state: FSMContext, is_admin: bool):
    await cmd_start(call, state, is_admin, user_cache)


@rare_router.callback_query(F.data == 'registration')
async def call_registration(call: CallbackQuery):
    await registration_and_welcome(call)


# @rare_router.message(Command('dev'))
# async def dev(mesage: Message, state: FSMContext, is_admin: bool):
#     await mesage.answer('Разработчик бота <a href="https://t.me/SaitBakhteev">Саит Бахтеев</a>\n'
#                         '<a href="https://github.com/SaitBakhteev">GitHub</a> разработчика',
#                         parse_mode='HTML')
#
# @rare_router.message(Command('sign'))
# async def general_tut(message: Message, bot: Bot):
#     await load_video(message, bot, 'sign_rend')
#
#
# @rare_router.message(Command('met'))
# async def general_tut(message: Message, bot: Bot):
#     await load_video(message, bot, 'tags_rend')
#
#
#
# @rare_router.message(Command('help'))
# @rare_router.callback_query(F.data == 'tutorial')
# async def tutorial(call_mess: Message | CallbackQuery, state: FSMContext):
#     await state.clear()
#     message = call_mess.message if isinstance(call_mess, CallbackQuery) else call_mess
#     await message.answer(GENERAL_TUTORIAL, parse_mode='HTML')
#
#
# @rare_router.callback_query(F.data == 'tutorial_list')
# async def tutorial_list(call: CallbackQuery, state: FSMContext):
#     await tutorial(call, state)
#
#
# async def load_video(message: Message, bot: Bot, file_name: str):
#     await message.answer('Подождите, загружается видеоинструкция ...')
#     file_path = f'media/{file_name}.mp4'
#     with open(file_path, 'rb') as video_file:
#         await bot.send_video(
#             chat_id=message.from_user.id,
#             video=BufferedInputFile(video_file.read(),
#                                     filename=file_path)
#         )
#
#
# @rare_router.message(Command('gen'))
# async def general_tut(message: Message, bot: Bot):
#     await load_video(message, bot, 'general_new_render')
#
#
# @rare_router.message(Command('train'))
# async def show_sign_up_for_training_tutorial(message: Message, state: FSMContext):
#     await state.clear()
#     await message.answer(SIGN_UP_FOR_TRAINING_TUTORIAL, parse_mode='HTML',
#                          reply_markup=app.keyboards.kb_tutorials.tutorial_list_kb)
#
#
# @rare_router.message(Command('marks'))
# async def marks_description(message: Message):
#     await message.answer(MARKS_DESCRIPTION, parse_mode='HTML', reply_markup=app.keyboards.kb_tutorials.tutorial_list_kb)
#
#
# @rare_router.message(Command('rec'))
# async def queue(message: Message):
#     text = ('🔹\n'
#             'Если вы оплатили за тренировку, настоятельно рекомендуется оповестить об этом бот. '
#             'Для этого нажмите <i>"✔️ Тренировка оплачена"</i>.\n'
#             '\n🔹\n'
#             'Кнопка <i>"✔️ Тренировка оплачена"</i> доступна <u>ТОЛЬКО</u> участникам со статусом ⚠️;\n'
#             '\n🔹\n'
#             'Участники со статусами ⚠️ и ❌ при наступлении <i>ДЕДЛАЙНА</i> перемещаются ботом '
#             'в конец очереди.\n\n'
#             'Более подробную информацию читайте в <b>/train</b> и <b>/marks</b>.\n\n')
#     await message.answer(text, parse_mode='HTML', reply_markup=app.keyboards.kb_tutorials.tutorial_list_kb)
#
#
# @rare_router.message(Command('bug'))
# async def bug(message: Message, state: FSMContext):
#     await message.answer('Напишите о проблеме работы бота и отправьте сообщение.',
#                          reply_markup=kb.return_to_start_markup())
#     await state.set_state(st.WrightBugsFSM.wright_bug)
#
#
# @rare_router.message(st.WrightBugsFSM.wright_bug)
# async def send_bugs_message(message: Message, state: FSMContext, is_admin: bool):
#     try:
#         text = message.text
#         if '0' not in text:
#             await logger.critical(text, extra={'username': message.from_user.username})
#             await message.answer('Благодарим Вас за обратную связь.')
#         else:
#             raise Exception
#     except Exception as e:
#         await message.answer('Извините возникла ошибка.\n'
#                              'Возможно причина в отстуствии имени аккаунта телеграмм.')
#         await logger.error('Error on /bugs')
#         # stream_logger.error('Error on /bugs')
#         pass
#     await state.clear()
