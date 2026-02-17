from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from ..database.models import *

test_router = Router()

@test_router.message(Command('test'))
async def call_test(msg: Message):
    dt = datetime.now() + timedelta(minutes=13)
    await Event.all().update(event_datetime=dt)
    await msg.answer('this test')