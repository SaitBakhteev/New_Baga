from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.log_config import setup_logger, setup_sync_logger
from ..universal_keyboards import interrupt_or_return_button, RETURN_TO_START_BUTTON, training_types_list_kb

logger, sync_logger = setup_logger(__name__), setup_sync_logger(__name__)

# Константы модуля
_RETURN_TO_ADMIN_PANEL_BUTTON = interrupt_or_return_button(
    text='↩️ Назад', callback_data='/admpan', this_markup=False
)

_CANCEL_ADMIN_OPERATION_BUTTON = interrupt_or_return_button(
    callback_data='/admpan', this_markup=False
)


def admin_panel_kb():
    """
    Создаёт клавиатуру стартового меню администратора.

    Returns:
        InlineKeyboardMarkup с кнопками:
        - Создать тренировку
        - Удалить шаблон
        - Управление админами
        - Инструкция
    """

    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='💠 Создать тренировку 🗓', callback_data='add_event'))
    keyboard.add(InlineKeyboardButton(text='💠 Удалить шаблон 🗑', callback_data='delete_template'))
    keyboard.add(InlineKeyboardButton(text='💠 Управление списком админов 😎', callback_data='admin_list'))
    keyboard.add(InlineKeyboardButton(text='💠 Коррекция статистики 📊', callback_data='stat_edit_begin'))
    keyboard.add(RETURN_TO_START_BUTTON)
    keyboard.adjust(1)
    return keyboard.as_markup()


# КНОПКИ ПО СОЗДАНИЮ ТРЕНИРОВКИ
# =================================

# Выбор типа создаваемй тренировки
def show_creating_event_types_kb():
    keyboard = training_types_list_kb('create_event_type_is')
    keyboard.add(_RETURN_TO_ADMIN_PANEL_BUTTON)
    keyboard.adjust(1)
    return keyboard.as_markup()


def _default_template_kb():
    template = ("Адрес зала: КЭК, Спартаковская 6\n"
                "❗️Дата тренировки: 01.11.2025\n"
                "❗️Время: 06:00\n"
                "Длительность: 2 часа\n"
                "❗️Квота участников: 12\n"
                "Стоимость тренировки: 350\n"
                "❗️Босс тренировки:-\n"
                "ИНФОРМАЦИЯ ОБ ОПЛАТЕ:  карта ТИНЬКОФФ 💳📍4377 7237 4025 3178📍💳. "
                "После кидаем скрин чека @Rustambagautdinov")
    title = "Шаблон по умолчанию"
    keyboard = InlineKeyboardButton(text=title, switch_inline_query_current_chat=template)
    return keyboard


def input_template_kb(templates: list) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.add(_default_template_kb())
    if templates:
        for dct in templates:
            title = ""
            for i, item in enumerate(dct["text"].split("\n")):
                if i < 3:
                    title += f"{item.split(':')[1].strip()}; "
                else:
                    break
            keyboard.add(
                InlineKeyboardButton(text=title, switch_inline_query_current_chat=dct["text"])
            )
    keyboard.add(_CANCEL_ADMIN_OPERATION_BUTTON)
    keyboard.adjust(1)
    return keyboard.as_markup()


choose_pay_dline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='12 часов', callback_data='payment_dedline:12')],
    [InlineKeyboardButton(text='24 часа', callback_data='payment_dedline:24')],
    [_CANCEL_ADMIN_OPERATION_BUTTON]
])


# Клавиатура вставки текущего шаблона при редактировании или создании тренировки
def curr_tmplt_kb(template_text: str, event_id: int=None) -> InlineKeyboardMarkup:
    text, switch = 'Текущий шаблон', template_text
    if event_id:
        _cancel_btn = interrupt_or_return_button(callback_data=f'to_manage_of_event_is:{event_id}',
                                             this_markup=False)
    else:
        _cancel_btn = _RETURN_TO_ADMIN_PANEL_BUTTON
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, switch_inline_query_current_chat=switch)],
        [_cancel_btn],
    ])
    return keyboard


finish_create_event_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Сохранить шаблон', callback_data='save_template')],
    [InlineKeyboardButton(text='Утвердить новую тренировку 🆗', callback_data='add_new_event')],
    [_CANCEL_ADMIN_OPERATION_BUTTON]
])


# АДМИНИСТРИРОВАНИЕ ТРЕНИРОВКИ
# ==============================

def admin_train_manag_kb(event_id) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='💠 Отмена верификации 🔘',
                                      callback_data=f'cancel_verify_payment_of_event_is:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Подтвердить оплату ✅',
                                      callback_data=f'confirm_payment_of_event_is:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Опровергнуть оплату ❌',
                                      callback_data=f'refute_payment_of_event_is:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Присвоить звезду ⭐️', callback_data=f'give_star_of_event_is:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Добавить вопрос для голосования ❓',
                                      callback_data=f'add_question_to_event_is:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Сдвинуть в конец очереди ⬇️',
                                      callback_data=f'move_to_end_of_event_is:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Удалить участника 🚷',
                                      callback_data=f'drop_user_from_event_is:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Редактировать тренировку ✏️', callback_data=f'edit_event_is:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 🚫 ОТМЕНИТЬ ТРЕНИРОВКУ 💥',
                                      callback_data=f'cancel_training:{event_id}'))
    keyboard.add(interrupt_or_return_button(text='↩️ Назад',
                                            callback_data= f'to_event_is:{event_id}',
                                            this_markup=False))
    keyboard.adjust(1)
    return keyboard.as_markup()


def payment_verify_kb(event_user_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Подтвердить оплату ✅', callback_data=f'confirm_payment:{event_user_id}')],
        [InlineKeyboardButton(text='Опровергнуть оплату ❌', callback_data=f'refute_payment:{event_user_id}')]
    ])
    return keyboard.as_markup()


# Клавиатура подтверждения удаления или перемещения в конец очереди участника
drop_participant_confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Да', callback_data='drop_paricipant:yes'),
     InlineKeyboardButton(text='Нет', callback_data='drop_paricipant:No')]
])


# Кнопка для сохранения изменений редактируемой тренировки
def finish_edit_event_kb(event_id) -> InlineKeyboardMarkup:
    _return_to_manage_btn = interrupt_or_return_button(
        callback_data=f'to_manage_of_event_is:{event_id}',
        this_markup=False
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Сохранить изменения 🖊', callback_data=f'finish_edit_event:{event_id}')],
        [_return_to_manage_btn]
    ])
    return keyboard


# БЛОК РЕДКИХ АДМИНСКИХ ОПЕРАЦИЙ
# ==============================

def edit_admins() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text='Добавить админа 😎', callback_data='edit_admin:add')
    keyboard.button(text='Удалить админа 🚯', callback_data='edit_admin:delete')
    keyboard.add(_RETURN_TO_ADMIN_PANEL_BUTTON)
    keyboard.adjust(1)
    return keyboard.as_markup()


# Панель кнопок редактирования статистики
def stat_edit_kb() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Редактирование посещений 🏃‍♂️', callback_data='stat_edit:visit')],
        [InlineKeyboardButton(text='Редактирование звезд ⭐️', callback_data='stat_edit:star')],
        [InlineKeyboardButton(text='Редактирование симпатий 💚', callback_data='stat_edit:like')],
        [_RETURN_TO_ADMIN_PANEL_BUTTON]
    ])
    return keyboard
