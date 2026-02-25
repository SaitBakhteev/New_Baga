import asyncio
from datetime import date, time

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from functools import reduce

from app import states as st
from app.database import requests as db_rq

from config.constants import *

from ..often_ops_and_classes import delete_bkg, ParentClassForTrainingOperations, cmd_start, SendMessages
from ...keyboards.admin_keyboards.admin_keyboards import *
from .manage_operations import show_event_with_manage_interface


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
                await self._choose_dline()
            elif self._handler.data.startswith('payment_dedline'):
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

    async def _choose_dline(self):
        # Сохраняем сначал тип тренировки в памяти
        index = int(self._handler.data.split(':')[1])
        await self._state.update_data(training_type=TRAINING_TYPES[index])

        msg = 'Выберите первичный дедлайн для тренировки'
        keyboard = choose_pay_dline_kb
        await self._handler.message.answer(msg, reply_markup=keyboard)
        asyncio.create_task(delete_bkg(self._handler))

    async def _choose_template(self):
        #Созраняем сначала в память тип деделайна
        dline_hours = int(self._handler.data.split(':')[1])
        await self._state.update_data(dline_hours=dline_hours)

        templates = await db_rq.get_templates()
        _keyboard = input_template_kb(templates=templates)
        await self._handler.message.answer('Выберите шаблон', reply_markup=_keyboard)
        await self._state.set_state(st.CreateEventFSM.template)
        asyncio.create_task(delete_bkg(self._handler))

    async def _input_template(self, is_create_event=True):
        text = self._handler.text.replace(f"{BOT_NAME}", "").strip()
        try:
            now = datetime.now()
            event_info = self._parse_template_text(text, now)
            await self._state.update_data(event_text=event_info['event_text'],
                                          participants_count=event_info['participants_count'],
                                          boss_id=event_info['boss_id'],
                                          event_datetime=event_info['event_datetime'],
                                          current_template=text)
            data = await self._state.get_data()
            if is_create_event:
                dline_hours = data['dline_hours']
                payment_dedline = self._set_payment_dedline(now, event_info['event_datetime'], dline_hours)
                await self._state.update_data(payment_dedline=payment_dedline)
                text= "Если хотите сохранить текущий шаблон, нажмите на кнопку сохранения шаблона"
                _keyboard = finish_create_event_kb
            else:
                text = "Для завершения редактирования нажмите на кнопку сохранения изменений"
                _keyboard = finish_edit_event_kb(data['event_id'])
            await self._handler.answer(text, reply_markup=_keyboard)
        except ValueError as e:
            error_message = self._handle_template_error(str(e))
            user_message = f"{error_message}.\nПовторите действия, начиная со вставки шаблона."
            await self._handler.answer(user_message, reply_markup=curr_tmplt_kb(text), parse_mode='HTML')
            asyncio.create_task(delete_bkg(self._handler))

    def _parse_template_text(self, text, now):
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
                    delta_90 = timedelta(days=90)
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
        return {'event_text': event_text, 'participants_count': participants_count, 'boss_id': boss_id,
                'event_datetime': event_datetime, 'current_template': text,}

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

    def _set_payment_dedline(self, now, event_datetime, dline_hours: int):
        if now + timedelta(hours=dline_hours) < event_datetime - timedelta(hours=3):
            return now + timedelta(hours=dline_hours)
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
        msg = (f'<b>СОЗДАНА НОВАЯ ТРЕНИРОВКА</b>\n\n'
                        f'<b>{data["training_type"]}</b>\n{data["event_text"]}')
        await self._handler.message.answer(msg, parse_mode='HTML')
        await show_admin_panel(self._handler, self._state)

        async def _delayed_notification(msg: str, training_type: str):
            await asyncio.sleep(300)  # 5 минут
            await SendMessages.to_several_subscribers(msg, training_type)
        asyncio.create_task(_delayed_notification(msg, data["training_type"]))


class EditEvent(CreateEvent):
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('edit_event_is'):
                await self._show_current_template_kb()
            elif (self._handler.data.startswith('finish_edit_event') and
                  await self._state.get_state() == st.EditEventFSM.insert_template):
                await self._save_event()
        elif await self._state.get_state() == st.EditEventFSM.insert_template:
            await self._input_template(is_create_event=False)

    async def _show_current_template_kb(self):
        event_id = int(self._handler.data.split(':')[1])
        event = await db_rq.get_event(id=event_id)
        text = 'Вставьте текущий шаблон этой тренировки, после чего отредактируйте и отправьте в сообщении боту'
        _template = self._form_current_template(event['event_text'])
        await self._handler.message.answer(text, reply_markup=curr_tmplt_kb(_template, event_id))
        await self._state.update_data(event_id=event_id)
        await self._state.set_state(st.EditEventFSM.insert_template)

    # Переделка текущего шаблона редактируемой трени для последующей вставки
    def _form_current_template(self, event_text):
        template = event_text

        # Более приемлемый способ для множественной замены в большой строке
        replacements = {"<b>": "", "</b>": "", "<i>": "", "</i>": "",
                        "Дата тренировки": "❗️Дата тренировки",
                        "Время": "❗️Время",
                        "Квота участников": "❗️Квота участников",
                        'Босс тренировки': '❗️Босс тренировки',
                        # "ИНФОРМАЦИЯ ОБ ОПЛАТЕ:\n": "Как оплатить: ",
                        "\n\n": "\n"}

        # Переделка текущего текста тренировки под шаблон для создания
        template = reduce(lambda fragment, kv: fragment.replace(*kv), replacements.items(), template)

        return template

    async def _save_event(self):
        data = await self._state.get_data()
        event_id = data['event_id']
        await db_rq.update_event(event_id, data)
        await self._state.clear()
        await self._handler.answer('Тренировка успешно отредактирована')
        await show_event_with_manage_interface(self._handler, self._state, event_id)


class DeleteEvent(ParentClassForTrainingOperations):
    async def dispatch(self):
        if isinstance(self._handler, CallbackQuery):
            if self._handler.data.startswith('cancel_training'):
                await self._show_confirm_question()
        elif await self._state.get_state() == st.DeleteEventFSM.confirm:
            await self._confirm()

    async def _show_confirm_question(self):
        event_id = int(self._handler.data.split(':')[1])
        await self._state.update_data(event_id=event_id)
        await self._state.set_state(st.DeleteEventFSM.confirm)
        await self._handler.message.answer(
            '📛 Если Вы уверены в отмене тренировки,  отправьте <b><i>да</i></b> в сообщении боту',
            parse_mode='HTML',
            reply_markup=interrupt_or_return_button(callback_data=f'to_manage_of_event_is:{event_id}')
        )

    async def _confirm(self):
        try:
            data = await self._state.get_data()
            event_id = data['event_id']
            if self._handler.text.strip().lower() == 'да':
                await db_rq.delete_event(event_id)
                await self._handler.answer('Тренировка удалена 💥')
                await cmd_start(self._handler, self._state, self._is_admin, user_cache)
            else:
                await show_event_with_manage_interface(self._handler, self._state, event_id)
                await self._handler.answer('🚫 Удаление тренировки прервано.')
            await self._state.clear()
            asyncio.create_task(delete_bkg(self._handler))
        except Exception as e:
            await logger.error(f'Ошибка в DeleteEvent._confirm: {e}')


# Добавление или удаление админов
class AdminEdit(ParentClassForTrainingOperations):
    _return_kb = interrupt_or_return_button(callback_data='adm_list') #  возврат к точке выбора действия по админам


    async def _begin(self):
        msg = f'<b><i>Текущий список админов:</i></b>\n\n'
        for k in user_cache:
            if user_cache[k].admin_permissions:
                msg += f'{user_cache[k].tg_name} {user_cache[k].tg_username}\n'
        msg += '\nВыберите операцию'
        await self._handler.message.answer(msg, parse_mode='HTML',reply_markup=edit_admins())
        asyncio.create_task(delete_bkg(self._handler))

    async def _input_data(self):
        call_data = self._handler.data.split(':')[1]
        await self._state.update_data(call_data=call_data)
        text = 'добавить' if call_data == 'add' else 'удалить'
        msg = f'Отправьте в сообщении боту никнейм админа, которого хотите {text}'
        await self._handler.message.answer(msg, parse_mode='HTML',reply_markup=self._return_kb)
        await self._state.set_state(st.EditAdminFSM.input_data)

    async def _end(self):
        data = await self._state.get_data()
        tg_username = self._handler.text.replace('@', '').replace(' ', '')
        tg_id = next((k for k in user_cache if user_cache[k]._tg_username == tg_username), None)
        if tg_id:
            admin_permissions = True if data['call_data'] == 'add' else False
            await db_rq.update_admin(user_cache[tg_id].id, admin_permissions)
            user_cache[tg_id].admin_permissions = admin_permissions
            act_text = f'добавлен' if data['call_data'] == 'add' else 'удален'
            username = user_cache[tg_id].tg_username
            msg = f'Пользователь с никнеймом {username} {act_text} успешно 👌🏽'
        else:
            msg = f'Пользователь с таким никнеймом не зарегистрирован в боте 🤷🏼‍♂️'
        await self._handler.answer(msg)
        await self._state.clear()
        await self._begin()
