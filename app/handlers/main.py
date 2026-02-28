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
