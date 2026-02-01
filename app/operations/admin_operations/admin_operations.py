import asyncio
from datetime import date, time

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import states as st
from app.database import requests as db_rq

from config.constants import *

from ..often_ops_and_classes import delete_bkg, ParentClassForTrainingOperations, show_formed_info_about_event
from ...keyboards.admin_keyboards.admin_keyboards import *


async def show_admin_panel(call: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    _call = call.message if isinstance(call, CallbackQuery) else call
    admin_permissions = user_cache[call.from_user.id].admin_permissions
    if admin_permissions:
        await _call.answer('Панель администратора', reply_markup=admin_panel_kb())
    else:
        await _call.answer('У Вас нет прав администратора')
    asyncio.create_task(delete_bkg(call))


class CreateEvent(ParentClassForTrainingOperations):
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data == 'add_event':
                await self._show_creating_event_types()
            elif self._handler.data.startswith('create_event_type_is'):
                await self._choose_template()
            elif (self._handler.data == 'save_template' and
                  await self._state.get_state() == st.CreateEventFSM.template):
                await self._save_template()
            elif (self._handler.data=='add_new_event' and
                  await self._state.get_state() == st.CreateEventFSM.template):
                await self._add_new_event()
        elif await self._state.get_state() == st.CreateEventFSM.template:
                await self._input_template()

    # Вывод списка для выбора типа создаваемой тренировки
    async def _show_creating_event_types(self):
        text, keyboard = 'Выберите тип создаваемой тренировки', show_creating_event_types_kb()
        await self._handler.message.answer(text, reply_markup=keyboard)
        asyncio.create_task(delete_bkg(self._handler))

    async def _choose_template(self):
        '''Здесь сначала сохраняем тип создаваемой тренировки,
        а потом уже выводим кнопки выбора шаблона'''
        index = int(self._handler.data.split(':')[1])
        await self._state.update_data(training_type=TRAINING_TYPES[index])

        templates = await db_rq.get_templates()
        _keyboard = input_template_kb(templates=templates)
        await self._handler.message.answer('Выберите шаблон', reply_markup=_keyboard)
        await self._state.set_state(st.CreateEventFSM.template)

    async def _input_template(self):
        text = self._handler.text.replace(f"{BOT_NAME}", "").strip()
        try:
            event_info = self._parse_template_text(text)
            await self._state.update_data(event_text=event_info['event_text'],
                                          participants_count=event_info['participants_count'],
                                          boss_id=event_info['boss_id'],
                                          event_datetime=event_info['event_datetime'],
                                          payment_dedline=event_info['payment_dedline'],
                                          current_template=text)
            text= "Если хотите сохранить текущий шаблон, нажмите на кнопку сохранения шаблона"
            await self._handler.answer(text, reply_markup=finish_create_event_kb)
        except ValueError as e:
            error_message = self._handle_template_error(str(e))
            user_message = f"{error_message}.\nПовторите действия, начиная со вставки шаблона."
            await self._handler.answer(user_message, reply_markup=current_template_kb(text), parse_mode='HTML')
            asyncio.create_task(delete_bkg(self._handler))

    def _parse_template_text(self, text):
        event_text = ""
        for index, fragment in enumerate(text.split("\n")):
            reper_index = fragment.find(":")  # реперный индекс двоеточия
            key, value = fragment[:reper_index], fragment[reper_index + 1:].strip()

            # Некоторые строки шаблона, значения которых должны соответствовать строгим форматам
            match index:
                case 1:  # дата тренировки
                    day, month, year = value.replace(" ", "").replace(",", ".").split(".")
                    event_date = date(year=int(year), month=int(month), day=int(day))
                case 2:  # время тренировки и дальнейшее формирование datetime тренировки
                    hour, minute = value.replace(" ", "").split(":")
                    event_time = time(hour=int(hour), minute=int(minute))
                    event_datetime = datetime.combine(date=event_date, time=event_time)
                    now, delta_90 = datetime.now(), timedelta(days=90)
                    if (event_datetime < now or event_datetime > now + delta_90):
                        raise ValueError("unreal date")
                case 4:
                    participants_count = int(value)
                case 6:
                    if value.strip() != "" and value.strip() != "-":
                        boss_val = value.strip().replace('@', '')
                        boss = next((user for user in user_cache.values() if user.tg_username == boss_val), None)
                        if boss:
                            boss_id = boss.id
                        else:
                            raise ValueError(f"User does not exist")
                    else:  # если никнейм босса не вводить, то None
                        boss_id = None
            if 'Босс тренировки' not in key:
                event_text += f"<b>{key}</b>: {value}\n"
            else:
                value = f'@{value}' if boss_id is not None else '-'
                value.replace('@@', '@')  # ещё одна перестраховка
                event_text += f"<b>{key}</b>: {value}\n"
        event_text = event_text.replace("❗️", "")
        payment_dedline = self._set_payment_dedline(now, event_datetime)
        return {'event_text': event_text, 'participants_count': participants_count, 'boss_id': boss_id,
                'event_datetime': event_datetime, 'payment_dedline': payment_dedline,
                'current_template': text,}

    def _handle_template_error(self, error_text: str):
        match error_text:
            case "month must be in 1..12":
                return "Некорректно введен месяц"
            case "unreal date":
                return "Тренировка не может быть запланирована прошедним днем и более, чем за <u>90 дней вперед</u>."
            case "minute must be in 0..59":
                return "Некорректное значение минут"
            case "hour must be in 0..23":
                return "Некорректное значение часов"
            case "day is out of range for month":
                return "Введен несуществующий день месяца"
            case "User does not exist":
                return "Для босса тренировки такой никнейм пользователя в боте не зарегистрирован."
            case "too_fast_event":
                return "Тренировка должна быть запланирована за 6 и более часов"
        if error_text.startswith("invalid literal for int() with base 10"):
            return "Строка со знаком ❗️ содержит некорректное значение"

        # Если ни одному из условий не соответствует, возвращается такая ошибка
        return "Ошибка в формате иного плана, проверьте внимательно"

    def _set_payment_dedline(self, now, event_datetime):
        if now + timedelta(days=1) < event_datetime - timedelta(hours=3):
            return now + timedelta(days=1)
        else:
            if now >= event_datetime - timedelta(hours=6):
                raise ValueError('too_fast_event')
            else:
                return event_datetime - timedelta(hours=3)

    async def _save_template(self):
        data = await self._state.get_data()
        await db_rq.create_template(text=data['current_template'])
        await self._handler.answer(f"Шаблон сохранен!")

    async def _add_new_event(self):
        data = await self._state.get_data()
        await db_rq.create_event(data)
        message_text = (f'<b>СОЗДАНА НОВАЯ ТРЕНИРОВКА</b>\n\n'
                        f'<b>{data["training_type"]}</b>\n{data["event_text"]}')
        await self._handler.message.answer(message_text, parse_mode='HTML')
        await show_admin_panel(self._handler, self._state)


class EditEvent(CreateEvent):
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('edit_event_is'):
                await self._show_current_template_kb()
        elif await self._state.get_state() == st.EditEvent.insert_template:
                await self._save_event()

    async def _show_current_template_kb(self):
        event_id = int(self._handler.data.split(':')[1])
        event = db_rq.get_event(id=event_id)
        text = 'Вставьте текущий шаблон этой тренировки, после чего отредактируйте и отправьте в сообщении боту'
        await self._handler.message.answer(text, reply_markup=current_template_kb(event['event_text']))
        await self._state.update_data(event_id=event_id)
        await self._state.set_state(st.EditEvent.insert_template)

    async def _save_event(self):
        data = await self._state.get_data()
        text = self._handler.text.replace(f"{BOT_NAME}", "").strip()
        event_id, event_info = data['event_id'], self._parse_template_text(text)
        data['event_datetime'], data['event_text'] = event_info['event_datetime'], event_info['event_text']
        data['participants_count'], data['boss_id'] = event_info['participants_count'], event_info['boss_id']
        await db_rq.update_event(event_id, data)
        await self._state.clear()
        await self._handler.answer('Тренировка успешно отредактирована')
        await show_formed_info_about_event(self._handler, self._is_admin, event_id, self._user_id)


class DeleteEvent():
    pass