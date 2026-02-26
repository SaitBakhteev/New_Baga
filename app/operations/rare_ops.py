import asyncio

from aiogram.types import Message, CallbackQuery

from app.keyboards.kb_registr_and_profile import *
from config.constants import user_cache, TRAINING_TYPES
from app.keyboards import universal_keyboards as kb
from app import states as st
from app.database import requests as db_req
from ..operations.often_ops_and_classes import ParentClassForTrainingOperations, delete_bkg


class ProfileManagment(ParentClassForTrainingOperations):
    # Кнопка возврата для управления профилем
    _return_to_profile_kb = kb.interrupt_or_return_button(callback_data='/prof')

    async def dispatch(self):
        if isinstance(self._handler, Message):
            if self._handler.text == '/prof':
                await self._show_profile()
            elif await self._state.get_state() == st.EditProfileFSM.edit_tg_name:
                await self._profile_edit_tg_name()
        elif isinstance(self._handler, CallbackQuery):
            if self._handler.data == 'profile_edit':
                await self._edit_profile()
            elif self._handler.data == '/prof':
                await self._show_profile()
        asyncio.create_task(delete_bkg(self._handler))

    async def _show_profile(self):
        await self._state.clear()
        tg_name = user_cache[self._handler.from_user.id].tg_name
        text = f'На данный момент Вы зарегистрированы в боте как <b><i>{tg_name}</i></b>'
        _handler = self._handler.message if isinstance(self._handler, CallbackQuery) else self._handler
        await _handler.answer(text, reply_markup=profile_edit_kb, parse_mode='HTML')

    async def _edit_profile(self):
        text = 'Введите свое имя. Например, <i>Иван Иванов</i>'
        await self._handler.message.answer(text, parse_mode='HTML', reply_markup=self._return_to_profile_kb)
        await self._state.set_state(st.EditProfileFSM.edit_tg_name)

    async def _profile_edit_tg_name(self):
        try:
            tg_name = self._handler.text.strip()
            if len(tg_name.replace(" ", "")) == 0:
                text = "Вы не ввели свое имя"
                await self._handler.answer(text, reply_markup=self._return_to_profile_kb)
                return
            user_cache[self._handler.from_user.id].tg_name = tg_name
            user_id = user_cache[self._handler.from_user.id].id
            await db_req.update_user(tg_name=tg_name, user_id=user_id)
            await self._handler.answer('Редактирование профиля прошло успешно ✅')
            await self._state.clear()
            await self._show_profile()
            asyncio.create_task(delete_bkg(self._handler))
        except Exception as e:
            text, exept_text = 'Произошла неизвестная ошибка', f'Ошибка из profile_edit_tg_name: {e}'
            await self._exception_func(text, exept_text)
            return


class SubscriptionManage(ParentClassForTrainingOperations):
    _return_to_subscrb_mng_kb = kb.interrupt_or_return_button(callback_data='/ntf')
    async def _dispatch(self):
        if isinstance(self._handler, Message):
            if self._handler.text == '/ntf':
                await self._begin()
            elif await self._state.get_state() == st.SubscriptionEditFSM.confirm:
                await self._confirm()
        elif isinstance(self._handler, CallbackQuery):
            if self._handler.data == 'subscription_edit':
                await self._input_data()
            elif self._handler.data == '/ntf':
                await self._begin()
        asyncio.create_task(delete_bkg(self._handler))

    async def _begin(self):
        await self._state.clear()
        tg_id = self._handler.from_user.id
        subscription = user_cache[tg_id].big_subscription
        if subscription is None:
            msg = 'В настоящий момент у Вас нет подписок на уведомления'
        else:
            txt = ';\n'.join(map(str, subscription.split(',')))
            msg = f'У Вас на данный момент подписки на следующие уведомления:\n\n<b><i>{txt}</i></b>'
        _handler = self._handler.message if isinstance(self._handler, CallbackQuery) else self._handler
        await _handler.answer(msg, reply_markup=subscription_manage_kb)

    async def _input_data(self):
        txt = ('Отправьте боту сообщение в зависимости от задачи:\n'
               '🔸 если хотите одну подписку, то отправьте порядковый номер подписки;\n'
               '🔸 если хотите нексолько подписок, то наберите через запятую список порядковых номеров;\n'
               '🔸 если хотите отказаться от всех подписок, то отправьте 0.\n\n'
               '<b>Доступны следующие подписки:</b>\n')
        for i, item in enumerate(TRAINING_TYPES):
            txt += f'<b>{i+1}.</b> {item}\n'
        await self._handler.message.answer(txt, parse_mode='HTML', reply_markup=self._return_to_subscrb_mng_kb)
        await self._state.set_state(st.SubscriptionEditFSM.confirm)

    async def _check_data(self):
        try:
            if ',' in self._handler.text:  # если несколько подписок
                text = self._handler.text.replace(' ', '').split(',')
                _lst = list(map(lambda x:TRAINING_TYPES[int(x)-1], text))  # формируем список подписок
                subscription = ','.join(map(str, _lst))
            elif self._handler.text.replace(' ', '') == '0':  # если отказываемся от подписки
                subscription = None
            else:  # если выбрал только одну подписку
                idx = int(self._handler.text.replace(' ', '')) - 1
                subscription = TRAINING_TYPES[idx]
            await self._state.update_data(subscription=subscription)
        except IndexError:
            return 'Введен несуществующий порядковый номер. Операция отклонена 📛'
        except ValueError:
            return 'Нарушен формат ввода. Операция отклонена 📛'

    async def _confirm(self):
        _check = await self._check_data()
        if not isinstance(_check, str):
            msg = 'Вы обновили подписку 🔔'
            data = await self._state.get_data()
            await db_req.update_subscription(self._user_id, data['subscription'])
            user_cache[self._handler.from_user.id].big_subscription = data['subscription']
        else:
            msg = _check
        await self._state.clear()
        await self._begin()
        await self._handler.answer(msg)
