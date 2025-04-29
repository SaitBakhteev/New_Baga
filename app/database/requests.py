import logging
from tortoise.exceptions import DoesNotExist

from app.database.models import User, Event, EventUser, Template
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


# ----- ПОЛЬЗОВАТЕЛЬ -----------
# Создание или получение пользователя
async def get_or_create_user(from_user, for_telegramm=False):
    try:
        if for_telegramm:
            return await User.get(tg_id=from_user.id).values('id', 'admin_permissions')

        user = await User.get_or_none(tg_id=from_user.id)
        if not user:
            await User.create(
                tg_id=from_user.id, tg_username=from_user.username,
                tg_name=from_user.first_name, created_at=datetime.now()
            )
        return user
    except Exception as e:
        logger.error(f"User is not created; {e}")
        return




async def get_all_users():
    return await User.all()


''' ДЕЙСТВИЯ С БД, ДОСТУПНЫЕ ТОЛЬКО АДМИНУ '''
# добавление объектов моделей

async def create_event(data):  # добавить событие
    try:
        await Event.create(
            created_at = data['created_at'],
            payment_dedline = data['payment_dedline'],
            event_datetime = data['event_datetime'],
            participants_count = data['participants_count'],
            event_text = data['event_text']
        )
    except Exception:
        return


# Создание записи пользователя на тренировку
async def create_event_user(data):
    await EventUser.create(user_id=data['user_id'],
                           event_id=data['event_id'],
                           created_at=datetime.now())


async def create_template(text: str):
    await Template.create(modified_at=datetime.now(), text=text)


# Получение объектов моделей

async def get_event(id=None, for_telegramm=False) -> Event():
    try:
        if for_telegramm:
            return await (
                Event.get(id=id).values('payment_dedline',
                                        'event_datetime', 'event_text',
                                        'participants_count')
            )
        return await Event.get(id=id) if id else \
            await (
                Event.all().order_by('id').
                values('payment_dedline', 'event_datetime',
                       'event_text','participants_count')
            )
    except DoesNotExist:
        return


async def get_event_user(event_id=None, user_tg_id=None,
                         payment_verification=False) -> EventUser():
    try:

        # Запрос к БД для верификации оплаты
        if payment_verification:
            return await (EventUser.filter(paid_check__not=None, payment_confirmed=None).
                          prefetch_related('user', 'event').
                          values('user__tg_username',
                                 'user__tg_name',
                                 'payment_confirmed',
                                 'paid_check',
                                 'event__training_type',
                                 'event__date',
                                 'event__gym__info',))
        else:

            # Запрос к БД для выделения знаком 🟢 тех тренировок, на которые уже записан пользователь
            if user_tg_id:
                user = await User.get(tg_id=user_tg_id).values('tg_id')
                return await (EventUser.filter(user__tg_id=user['tg_id']).
                              prefetch_related('user', 'event').
                              values('user__tg_id', 'event__id'))

            # Запрос к БД для отображения списка участников согласно хронологии их записи
            return await (EventUser.filter(event_id=event_id).prefetch_related(
                'event','user'
            ).order_by('created_at').
                          values('id',
                                 'user__id',
                                 'user__tg_id',
                                 'user__tg_name',
                                 'user__tg_username',
                                 'payment_confirmed',
                                 'paid_check'))
    except DoesNotExist:
        logger.error('get_event_user: User DoesNotExist')
    except Exception as e:
        logger.error(f'get_event_user: {e}')


async def get_templates() -> Template():
    return await Template.all().values('text')


# Удаление объектов моделей

async def delete_event(id: int):
    await Event.filter(id=id).delete()


async def delete_event_user(user_id: int, event_id: int):
    try:
        await EventUser.filter(user_id=user_id, event_id=event_id).delete()
    except DoesNotExist as e:
        logger.error(f'delete_event_user: {e}')
    except Exception as e:
        logger.error(f'delete_event_user_other error: {e}')


""" Обновление времени записи на тренировку для участников,
которые не выполнинли условия по оплате. Данное обновление
выполняется за один запрос к БД """

async def update_admin_and_get(tg_username: str, admin_permissions: bool):
    try:
        user = await User.get_or_none(tg_username=tg_username)
        logger.info(f'USER: {user.tg_name}')
        user_id = user.id
        user.admin_permissions = admin_permissions
        await User.filter(id=user_id).update(admin_permissions=admin_permissions)
        return (user, user.tg_id)
    except DoesNotExist as e:
        logger.error(f'update_admin_and_get: User does not exist')
    except Exception as e:
        logger.error(f'update_admin_and_get: {e}')


# Запрос к БД для обновления записей EventUser при нажатии пользователем кнопки '✔️ Я оплатил'
async def update_event_user(user_id: int, event_id: int,
                            paid_check: bool, payment_confirmed: bool):
    logger.error(f'even - {event_id}; user: {user_id}')
    if paid_check and not payment_confirmed:
        await (EventUser.filter(user_id=user_id,
                               event_id=event_id).
               update(paid_check='paid'))


# Запрос к БД для обновления записей EventUser при проверке админом оплаты
async def update_event_user_for_payment_verify(id_list: list, is_confirm=True):
    if is_confirm: # если админ подтверждает оплату
        await EventUser.filter(id__in=id_list).update(payment_confirmed=True)
    else: # если админ опровергает оплату
        await EventUser.filter(id__in=id_list).update(payment_confirmed=False)



# async def test():
#     try:
#         now = datetime.now()
#         await EventUser.filter(id__gt=0).update(created_at=now)
#     except Exception as e:
#         logger.error(f'{e}')
#
#
