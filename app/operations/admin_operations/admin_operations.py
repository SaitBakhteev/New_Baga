import asyncio

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app import states as st
from app.handlers.main_handler import main_router
from app.keyboards import universal_keyboards as kb
from app.operations.often_ops_and_classes import delete_bkg


@main_router.callback_query(F.data == 'add_event')
async def add_event(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("Выберите тип создаваемой тренировки",
                              reply_markup=kb.training_types_kb())
    await state.set_state(st.CreateEventFSM.training_type)
    asyncio.create_task(delete_bkg(call))
