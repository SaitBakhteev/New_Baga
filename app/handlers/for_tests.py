from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.loggers import event
from aiogram.types import Message

from ..database.models import *
from ..schedule import main_func, stat_execute_func
from config.log_config import setup_logger
from config.constants import user_cache

logger = setup_logger(__name__)

test_router = Router()

@test_router.message(Command('test'))
async def call_test(msg: Message):
    ev_user = await EventUser.all().delete()
    now = datetime.now()
    payment_dedline = now + timedelta(minutes=2)
    event_datetime, individual_dedline = now + timedelta(minutes=211), now + timedelta(hours=12)
    for i, k in enumerate(user_cache):
        if i > 6:
            break
        _date = now - timedelta(days=i)
        _ind_ddl = _date + timedelta(hours=12)
        user_id = user_cache[k].id
        event = await Event.all()
        event_id = event[-1].id
        await EventUser.create(user_id=user_id, event_id=event_id, created_at=_date, modified_at=_date, individual_dedline=_ind_ddl)

    #     await Event.filter(id=2).all().update(payment_dedline=payment_dedline, event_datetime=event_datetime)
    # await EventUser.all().update(individual_dedline=individual_dedline)
    await msg.answer('this test')


@test_router.message(Command('pay'))
async def call_schedule(msg: Message):
    evs = await EventUser.all()
    for ev in evs:
        _dt = ev.modified_at.replace(tzinfo=None) + timedelta(days=1, hours=12)
        ev.individual_dedline = _dt
        await ev.save()
    await msg.answer('норм pay')


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


@test_router.message(Command('usr'))
async def call_olg(msg: Message):
    users = await User.all()
    for user in users:
        if user.subscription:
            user.big_subscription = user.subscription
            await user.save()
    await msg.answer('подписки дублироаны другим полем')

