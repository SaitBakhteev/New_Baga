import asyncio
import traceback

from aiogram.types import CallbackQuery, Message

from typing import Optional

from math import ceil
from html import escape

from ..database.requests import get_stat_archive
from ..operations.often_ops_and_classes import ParentClassForTrainingOperations

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
                fullname = f'{escape(item.user.tg_name)} @{escape(item.user.tg_username)}'
                fullname = f'<b>{fullname}</b>' if call.from_user.id == item.user.tg_id else fullname
                text += f'<b>{i + 1}</b>. {stars} {fullname}\n  {visit_count}\n'
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
                sum_info = f'{_tag_txt} {escape(fullname)}'
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
        try:
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
        except Exception as e:
            logger.error(f'ERROR on _show_type_raiting {e}:\n{traceback.format_exc()}')

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


class ShowStatArchive(ParentClassForTrainingOperations):
    _back_kb = interrupt_or_return_button(text=BACK_TEXT_KB, callback_data='/rait')
    
    async def run(self):
        await self._init_dict()
        await self._msg_formation()

    async def _init_dict(self):
        ''' Формируем исходный словарь по игрокам '''
        self._stat_archive = await get_stat_archive()
        self._players_dict = dict()
        for item in self._stat_archive:
            if item.user.id not in self._players_dict:
                tg_name = escape(item.user.tg_name)
                tg_username = escape(item.user.tg_username) if item.user.tg_username else ""
                self._players_dict[item.user.id] = {'userdata': f"{tg_name} @{tg_username}"}

            # По каждому игроку добавляем внутренние словари по каждой дисциплине
            icon, visits, stars, likes = item.training_type[0], item.visit_count, item.star_count, item.likes
            _inner_dict = {"visits": visits, "stars": stars, "likes": likes}
            self._players_dict[item.user.id][f"{icon}"] = _inner_dict

        # сортируем по сумме stars по всем дисциплинам (по убыванию)
        self._players_dict = dict(sorted(
            self._players_dict.items(),
            key=lambda item: sum(sport['stars'] for sport in item[1].values() if isinstance(sport, dict)),
            reverse=True,
        ))

    async def _msg_formation(self):
        msg = "<b>Статистика сезона 2025-2026</b>\n\n"
        for i, user_id in enumerate(self._players_dict):
            userdata = self._players_dict[user_id]["userdata"]
            msg += (f'<b>{i + 1}</b>. {userdata}\n')
            # Идем по внутреннему словарю игрока по каждой дисциплине
            for _k in self._players_dict[user_id]:
                if _k != "userdata":
                    visits = self._players_dict[user_id][_k]["visits"]
                    stars = self._players_dict[user_id][_k]["stars"]
                    likes = self._players_dict[user_id][_k]["likes"]
                    msg += (f'{_k}: 🏃🏼‍♂️{visits} ⭐️{stars} 💚{likes}\n')

            msg += '\n'

        # Условия определения для разбивки текста
        if len(self._players_dict) > 40:
            self._msg = msg
            await self._big_text()
        else:
            await self._handler.message.answer(msg, parse_mode='HTML')

    async def _big_text(self):
        n = ceil(len(self._players_dict) / 30)  # поярдковое число, округленное всегда вверх
        for i in range(0, n):
            if i == 0:
                idx_end = self._msg.find('<b>31</b>')
                msg = self._msg[:idx_end]
                await self._handler.message.answer(msg, parse_mode='HTML')
            else:
                idx_begin = self._msg.find(f'<b>{i * 30 + 1}</b>')
                idx_end = self._msg.find(f'<b>{(i + 1) * 30 + 1}</b>')
                msg = f'{self._msg[idx_begin:idx_end]}'
                keyboard = self._back_kb if i == n - 1 else None
                await self._handler.message.answer(msg, parse_mode='HTML', reply_markup=keyboard)