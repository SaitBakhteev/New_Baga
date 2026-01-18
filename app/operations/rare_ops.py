import asyncio

from aiogram.types import Message, CallbackQuery

import app.keyboards.kb_registr_and_profile
from config import user_cache
from app.keyboards import universal_keyboards as kb
from app import states as st
from app.database import requests as db_req
from ..operations.often_ops_and_classes import ParentClassForTrainingOperations, delete_bkg


class ProfileManagment(ParentClassForTrainingOperations):
    # Кнопка возврата для управления профилем
    __return_to_profile_show = kb.interrupt_or_return_button(callback_data='return_to_profile_show')

    async def dispatch(self):
        if isinstance(self._handler, Message):
            if self._handler.text == '/prof':
                await self._show_profile()
        elif isinstance(self._handler, CallbackQuery):
            if self._handler.data == 'profile_edit':
                await self._edit_profile()
        elif self._state.get_state() == st.EditProfileFSM.edit_tg_name:
            await self._profile_edit_tg_name()

    async def _show_profile(self):
        tg_name = user_cache[self._handler.from_user.id].tg_name
        text = f'На данный момент Вы зарегистрированы в боте как <b><i>{tg_name}</i></b>'
        _handler = self._handler.message if isinstance(self._handler, CallbackQuery) else self._handler
        await _handler.answer(text, reply_markup=app.keyboards.kb_registr_and_profile.profile_edit_kb, parse_mode='HTML')

    async def _edit_profile(self):
        text = 'Введите свое имя. Например, <i>Иван Иванов</i>'
        await self._handler.answer(text, parse_mode='HTML', reply_markup=self.__return_to_profile_show)
        await self._state.set_state(st.EditProfileFSM.edit_tg_name)

    async def _profile_edit_tg_name(self):
        try:
            tg_name = self._handler.text.strip()
            if len(tg_name.replace(" ", "")) == 0:
                text = "Вы не ввели свое имя"
                await self._handler.answer(text, reply_markup=self.__return_to_profile_show)
                return
            user_cache[self._handler.from_user.id].tg_name = tg_name
            user_id = user_cache[self._handler.from_user.id].id
            await db_req.update_user(tg_name=tg_name, user_id=user_id)
            await self._handler.answer('Редактирование профиля прошло успешно ✅')
            await self._handler.state.clear()
            await self._show_profile()
            asyncio.create_task(delete_bkg(self._handler))
        except Exception as e:
            text, exept_text = 'Произошла неизвестная ошибка', f'Ошибка из profile_edit_tg_name: {e}'
            await self._exception_func(text, exept_text)
            return
