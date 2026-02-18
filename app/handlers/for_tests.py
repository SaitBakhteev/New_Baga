from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from ..database.models import *
from ..schedule import main_func, stat_execute_func
from config.log_config import setup_logger

logger = setup_logger(__name__)

test_router = Router()

@test_router.message(Command('test'))
async def call_test(msg: Message):
    await EventUser.all().delete()
    now = datetime.now()
    payment_dedline = now + timedelta(minutes=2)
    event_datetime, individual_dedline = now + timedelta(minutes=211), now + timedelta(hours=12)
    for i in range(4,15):
        _date = now - timedelta(days=i)
        _ind_ddl = _date + timedelta(hours=12)
        await EventUser.create(user_id=i, event_id=3, created_at=_date, modified_at=_date, individual_dedline=_ind_ddl)

    #     await Event.filter(id=2).all().update(payment_dedline=payment_dedline, event_datetime=event_datetime)
    # await EventUser.all().update(individual_dedline=individual_dedline)
    await msg.answer('this test')

@test_router.message(Command('upd'))
async def call_test(msg: Message):
    yesterday = datetime.now() - timedelta(days=1)
    await Event.all().update(event_datetime=yesterday)


@test_router.message(Command('sch'))
async def call_schedule(msg: Message):
    await main_func()


@test_router.message(Command('stat'))
async def call_schedule(msg: Message):
    await stat_execute_func()


@test_router.message(Command('log'))
async def call_schedule(msg: Message):
    await logger.critical('logs_tet')

