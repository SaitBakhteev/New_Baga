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
    now = datetime.now()
    payment_dedline = now + timedelta(minutes=2)
    event_datetime, individual_dedline = now + timedelta(minutes=211), now + timedelta(hours=12)
    await Event.filter(id=2).all().update(payment_dedline=payment_dedline, event_datetime=event_datetime)
    await EventUser.all().update(individual_dedline=individual_dedline)
    await msg.answer('this test')

@test_router.message(Command('sch'))
async def call_schedule(msg: Message):
    await main_func()

@test_router.message(Command('log'))
async def call_schedule(msg: Message):
    await logger.critical('logs_tet')

