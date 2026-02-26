import asyncio

from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, Message

from typing import Optional

from math import ceil

from config.constants import TRAINING_TYPES, NUMBERS
from ..schedule import StatisticOps
from .often_ops_and_classes import delete_bkg
from ..keyboards.kb_look_statistic import choose_raiting_kb
from ..keyboards.universal_keyboards import interrupt_or_return_button, BACK_TEXT_KB

from config.log_config import setup_logger

logger = setup_logger(__name__)


class ShowStat():
    _back_kb = interrupt_or_return_button(text=BACK_TEXT_KB, callback_data='/rait')

    @classmethod
    def _rating_txt_form(self, call: CallbackQuery, rating_list: list, tag: str) -> Optional[str]:
        ''' Здесь tag это тег, который символизирует конкретный рейтинг'''
        if len(rating_list) > 0:
            text = ''
            for i, item in enumerate(rating_list):
                if item.star_count > 0:
                    stars = ''
                    for _i, _num in enumerate(str(item.star_count)):
                        # Здесь преобразуем цифру числа звезд в индекс
                        idx = int(_num)
                        stars += f'{NUMBERS[idx]}'
                        stars = f'{tag}{stars}'
                else:
                    stars = ''
                visit_count = f'🏃🏽‍♂️{item.visit_count}'
                fullname = f'{item.user.tg_name} @{item.user.tg_username}'
                fullname = f'<b>{fullname}</b>' if call.from_user.id == item.user.tg_id else fullname
                text += f'<b>{i + 1}</b>. {stars} {fullname} {visit_count}\n'
            return text
        else:
            return None

    # Формируем вновь текст тегов, как и вдругом модуле (нарушаем DRY)
    @classmethod
    def _general_rating_formation(cls, rating_lst:list, tag: str, call:CallbackQuery) -> Optional[str]:
        call_username = call.from_user.username
        if len(rating_lst) > 0:
            txt = ''
            for i, item in enumerate(rating_lst):
                count = item.star_count if tag == '⭐️' else item.likes
                if count == 1:
                    _tag_txt = f'{tag}'
                elif count > 1:
                    _tag_txt = ''
                    for _i in str(count):
                        _tag_txt += f'{NUMBERS[int(_i)]}'
                    _tag_txt += f'{tag}'

                fullname = f'{item.tg_name} @{item.tg_username}'
                sum_info = f'{_tag_txt} {fullname}'
                if tag == '⭐️':
                    sum_info += f' {item.text}'

                txt += f'<b>{i+1}.</b> <b>{sum_info}</b>\n' if call_username == item.tg_username \
                    else f'<b>{i+1}.</b> {sum_info}\n'
            return txt
        else:
            return None

    @classmethod
    async def dispatch(cls, call: CallbackQuery):
        if isinstance(call, CallbackQuery):
            if call.data == '/rait':
                await cls._show_raiting_types_buttons(call)
            elif call.data.startswith('to_raiting_type_is'):
                await cls._show_type_raiting(call)
            elif call.data == 'general_statistics':
                await cls._show_general_raiting(call)
            elif call.data == 'likes_statistics':
                await cls._show_likes_rating(call)
        elif isinstance(call, Message):
            if call.text == '/rait':
                await cls._show_raiting_types_buttons(call)
        asyncio.create_task(delete_bkg(call))

    @classmethod
    async def _show_raiting_types_buttons(cls, call: CallbackQuery | Message):
        msg = 'Выберите тип рейтинга'
        _handler = call.message if isinstance(call, CallbackQuery) else call
        await _handler.answer(msg, reply_markup=choose_raiting_kb())

    @classmethod
    async def _show_type_raiting(cls, call: CallbackQuery):
        training_index = int(call.data.split(':')[1])
        training_type = TRAINING_TYPES[training_index]
        stars_dict = StatisticOps.stars_dict_getter()
        rating_txt = cls._rating_txt_form(call, stars_dict[training_type], '⭐️') if training_type in stars_dict else None
        if rating_txt:
            msg = (f'Текущий рейтинг по дисциплине <b>"{training_type}"</b>:\n\n'
                   f'{rating_txt}')
        else:
            msg = f'По дисциплине <b>"{training_type}"</b> в этом сезоне тренировки пока не проводились'
        await call.message.answer(msg, parse_mode='HTML', reply_markup=cls._back_kb)

    @classmethod
    async def _process_big_txt(cls, _count:int, rating_txt:str, call: CallbackQuery):
        n = ceil(_count / 100)  # поярдковое число, округленное всегда вверх
        for i in range(0, n):
            if i == 0:
                idx_end = rating_txt.find('<b>101.</b>')
                msg = f'<b>ОБЩИЙ РЕЙТИНГ⚡️</b>\n\n{rating_txt[:idx_end]}'
                await call.message.answer(msg, parse_mode='HTML')
            else:
                idx_begin = rating_txt.find(f'<b>{i * 100 + 1}.</b>')
                idx_end = rating_txt.find(f'<b>{(i + 1) * 100 + 1}.</b>')
                msg = f'{rating_txt[idx_begin:idx_end]}'
                keyboard = cls._back_kb if i == n - 1 else None
                await call.message.answer(msg, parse_mode='HTML', reply_markup=keyboard)

    @classmethod
    async def _show_general_raiting(cls, call: CallbackQuery):
        general_raiting = StatisticOps.general_raiting_getter()
        rating_txt = cls._general_rating_formation(general_raiting, '⭐️', call)
        _count = rating_txt.count('\n') if rating_txt else 0
        if _count > 100:
            await cls._process_big_txt(_count, rating_txt, call)
        else:
            msg = f'<b>ОБЩИЙ РЕЙТИНГ⚡️</b>\n\n{rating_txt}' if rating_txt \
                else 'В этом сезоне тренировки пока не проводились'
            await call.message.answer(msg, parse_mode='HTML', reply_markup=cls._back_kb)

    @classmethod
    async def _show_likes_rating(cls, call: CallbackQuery):
        try:
            likes_statistics = StatisticOps.likes_raiting_getter()
            rating_txt = cls._general_rating_formation(likes_statistics, '💚', call)
            _count = rating_txt.count('\n') if rating_txt else 0
            if _count > 100:
                await cls._process_big_txt(_count, rating_txt, call)
            else:
                msg = f'🔥 <b>ОБЩИЙ РЕЙТИНГ СИМПАТИЙ</b> 💚\n\n{rating_txt}' if rating_txt \
                    else 'В этом сезоне голосования пока не проводились'
                await call.message.answer(msg, parse_mode='HTML', reply_markup=cls._back_kb)
        except Exception as e:
            await logger.error(f'Ошибка _show_likes_rating: {e}')