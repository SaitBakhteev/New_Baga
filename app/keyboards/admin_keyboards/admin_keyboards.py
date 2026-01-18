from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import setup_logger, setup_sync_logger

from ..universal_keyboards import interrupt_or_return_button, RETURN_TO_START_BUTTON, training_types_list_kb

logger, sync_logger = setup_logger(__name__), setup_sync_logger(__name__)

# Константы модуля
_RETURN_TO_ADMIN_PANEL_BUTTON = interrupt_or_return_button(
    '↩️ Назад', callback_data='return_to_admin_panel',this_markup=False
)

_CANCEL_ADMIN_OPERATION_BUTTON = interrupt_or_return_button(
    callback_data='return_to_admin_panel', this_markup=False
)


def admin_panel(self):
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
    keyboard.add(InlineKeyboardButton(text='💠 Иструкция для админа 📕', callback_data='admin_tutorial'))
    keyboard.add(RETURN_TO_START_BUTTON)
    return keyboard.as_markup()


def edit_admins() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text='Добавить админа', callback_data='edit_admin:add')
    keyboard.button(text='Удалить админа', callback_data='edit_admin:delete')
    keyboard.add(_RETURN_TO_ADMIN_PANEL_BUTTON)
    keyboard.adjust(1)
    return keyboard.as_markup()


# КНОПКИ ПО СОЗДАНИЮ ТРЕНИРОВКИ
# =================================

# Выбор типа создаваемй тренировки
def choose_training_type_for_create():
    keyboard = training_types_list_kb('admin_create_event')
    keyboard.add(_RETURN_TO_ADMIN_PANEL_BUTTON)


# Отображает в поле ввода сообщения заготовку для создания тренировки
def input_template(current_template: str = None,
                   save: bool = False,
                   templates: list = None) -> InlineKeyboardMarkup:

    keyboard = InlineKeyboardBuilder()

    if not save:
        if current_template is None:
            template = ("Адрес зала: КЭК, Спартаковская 6\n"
                        "❗️Дата тренировки: 01.11.2025\n"
                        "❗️Время: 06:00\n"
                        "Длительность: 2 часа\n"
                        "❗️Квота участников: 12\n"
                        "Стоимость тренировки: 350\n"
                        "❗️Босс тренировки:\n"
                        "ИНФОРМАЦИЯ ОБ ОПЛАТЕ:  карта ТИНЬКОФФ 💳📍4377 7237 4025 3178📍💳. "
                        "После кидаем скрин чека @Rustambagautdinov")
            title = "Чистый шаблон"
        else:
            template, title = current_template, "Текущий шаблон"
        keyboard.add(InlineKeyboardButton(text=title,
                                          switch_inline_query_current_chat=template))

        # Формирование заголовка кнопок из загружаемых из БД шаблонов
        if templates:
            for dct in templates:
                title = ""
                for i, item in enumerate(dct["text"].split("\n")):
                    if i < 3:
                        title += f"{item.split(':')[1].strip()}; "
                    else:
                        break
                keyboard.add(InlineKeyboardButton(text=title,
                                                  switch_inline_query_current_chat=dct["text"]))

    else:
        keyboard.button(text="Сохранить шаблон", callback_data='save_template')

    keyboard.add(_CANCEL_ADMIN_OPERATION_BUTTON)
    keyboard.adjust(1)
    return keyboard.as_markup()


# Кнопка выбора типа дедлайна оплаты для тренировки
async def admin_dedline_type(*dedline_type) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    for dedline in dedline_type:
        keyboard.add(InlineKeyboardButton(text=dedline[0], callback_data=f"dedline_{dedline[1]}"))
    keyboard.adjust(2)
    keyboard.add(_CANCEL_ADMIN_OPERATION_BUTTON)
    keyboard.adjust(1)
    return keyboard.as_markup()


def payment_verify_kb(event_user_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Подтвердить оплату ✅', callback_data=f'confirm_payment:{event_user_id}'),],
        [InlineKeyboardButton(text='Опровергнуть оплату ❌', callback_data=f'refute_payment:{event_user_id}'),],
])
    return keyboard.as_markup()


# АДМИНИСТРИРОВАНИЕ ТРЕНИРОВКИ
# ==============================

def admin_train_manag_kb(event_id) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text='💠 Отмена верификации 🔘',
                                      callback_data=f'cancel_verify_payment:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Подтвердить оплату ✅',
                                      callback_data=f'confirm_payment:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Опровергнуть оплату ❌',
                                      callback_data=f'refute_payment:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Присвоить звезду ⭐️', callback_data=f'give_star:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Сдвинуть в конец очереди ⬇️',
                                      callback_data=f'replace_to_end:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Удалить участника 🚷',
                                      callback_data=f'drop_participant:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 Редактировать тренировку ✏️', callback_data=f'edit_event:{event_id}'))
    keyboard.add(InlineKeyboardButton(text='💠 🚫 ОТМЕНИТЬ ТРЕНИРОВКУ 💥',
                                      callback_data=f'cancel_training:{event_id}'))
    keyboard.add(interrupt_or_return_button('↩️ Назад', f'return_to_event:{event_id}',
                                            False))
    keyboard.adjust(1)
    return keyboard.as_markup()


# Клавиатура подтверждения удаления или перемещения в конец очереди участника
drop_participant_confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Да', callback_data='drop_paricipant:yes'),
     InlineKeyboardButton(text='Нет', callback_data='drop_paricipant:No')]
])


# Клавиатура для вставки текущего шаблона редактируемой тренировки
def insert_template_on_edit_admin(template: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Вставить текущий шаблон тренировки',
                              switch_inline_query_current_chat=template)]
    ])
    return keyboard
