from datetime import datetime, timedelta
from logging import exception

from tortoise.exceptions import DoesNotExist

from config.log_config import setup_logger
from app.database.models import EventUser, User


logger = setup_logger(__name__)


''' ---------------------------------- CREATE ---------------------------------------------- '''

# Создание записи пользователя на тренировку
async def create_event_user(data, **kwargs):
    if 'friend_id' not in kwargs:
        await EventUser.create(
            user_id=data['user_id'],
            event_id=data['event_id'],
            created_at=data['created_at'],
            modified_at=data['modified_at'],
            individual_dedline=data['individual_dedline']
        )
    else:
        await EventUser.create(
            user_id=kwargs['friend_id'],
            event_id=data['event_id'],
            friend=kwargs['i_am_friend'],
            created_at=data['created_at'],
            modified_at=data['modified_at'],
            individual_dedline=data['individual_dedline']
        )


''' ----------------------------------------- GET ---------------------------------------------- '''

async def get_event_user(event_id=None, user_tg_id=None,
                         payment_verification=False,
                         event_ids: list = None) -> EventUser():
    try:

        # Запрос к БД для верификации оплаты
        if payment_verification:
            return await (EventUser.filter(paid_check__not=None, payment_confirmed=None).
                          prefetch_related('user', 'event').
                          values('user__tg_username',
                                 'user__tg_name',
                                 'payment_confirmed',
                                 'paid_check',
                                 ))
        else:

            # Запрос к БД для выделения знаком 🟢 тех тренировок, на которые уже записан пользователь
            if user_tg_id:
                user = await User.get(tg_id=user_tg_id)
                return await (EventUser.filter(
                    user=user, event__id__in=event_ids).
                              prefetch_related('user', 'event').
                              values('user__tg_id', 'event__id'))

            # Запрос к БД для отображения списка участников согласно хронологии их записи
            result = await (EventUser.filter(event_id=event_id).prefetch_related(
                'event', 'user'
            ).order_by('created_at').
                            values('id',
                                   'user__id',
                                   'user__tg_id',
                                   'user__tg_name',
                                   'user__tg_username',
                                   'payment_confirmed',
                                   'paid_check',
                                   'friend',
                                   'created_at',
                                   'event__participants_count'))
            result = sorted(result, key=lambda x: x['created_at'].replace(tzinfo=None))
            return result

    except DoesNotExist:
        await logger.error('get_event_user: User DoesNotExist')
    except Exception as e:
        await logger.error(f'get_event_user: {e}')


# Проверка не состоит ли уже в записи участник, во избежание багов
async def get_event_user_for_check_existing(event_id, user_id):
    return await EventUser.filter(event_id=event_id, user_id=user_id).exists()


async def get_event_user_for_check_pay_notify(event_id, user_id):
    return await EventUser.filter(event_id=event_id, user_id=user_id, paid_check='paid').exists()


async def get_event_user_before_delete(event_id):
    result = await EventUser.filter(event_id=event_id).prefetch_related('event', 'user').all()
    result = sorted(result, key=lambda x: x.modified_at.replace(tzinfo=None))
    return result


# Запрос для проверки можно ли добавить друга
async def get_event_user_for_check_friend(event_id, friend_id=None, i_am_friend=None):
    ''' Проверяем, не записался ли до нас друг сам или нет ли у нас уже добавленного друга'''
    if friend_id:
        return await EventUser.filter(event_id=event_id, user_id=friend_id).exists()
    elif i_am_friend:
        event_user = await EventUser.filter(event_id=event_id, friend=i_am_friend).values('user__tg_username')
        return event_user[0]['user__tg_username'] if len(event_user) > 0 else None


''' --------------------------------------- UPDATE --------------------------------------- '''

# Запрос к БД для обновления записей EventUser при проверке админом оплаты
async def update_event_user_for_payment_verify(id_list: list, verification_mode: str):
    match verification_mode:
        case 'confirm': await EventUser.filter(id__in=id_list).update(payment_confirmed=True)
        case 'refute': await EventUser.filter(id__in=id_list).update(payment_confirmed=False)
        case 'cancel': await EventUser.filter(id__in=id_list).update(payment_confirmed=None)


async def update_event_user_for_payment_notify(even_id: id, user_id: int):
    try:
        await EventUser.filter(event_id=even_id, user_id=user_id).update(
            paid_check='paid', paid_check_datetime=datetime.now()
        )
    except exception as e:
        await logger.error(f'Ошибка в update_event_user_for_payment_notify: {e}')


async def update_event_user(user_id: int, event_id: int,
                            payment_notify: bool = False,
                            replace_to_end: bool = None):
    try:
        if payment_notify:
            await (EventUser.filter(user_id=user_id, event_id=event_id).update(
                paid_check='paid', paid_check_datetime=datetime.now()
            ))
        elif replace_to_end:
            await (EventUser.filter(user_id=user_id, event_id=event_id).update(modified_at=datetime.now()))
        else:
            await (EventUser.filter(user_id=user_id, event_id=event_id).update(paid_check=None, payment_confirmed=None))
    except DoesNotExist:
        await logger.error(f'update_event_user: Does Not exist')
    except Exception as e:
        await logger.error(f'update_event_user: {e}')


# Обновление поля friend после записи друга на тренировку
async def update_event_user_after_add_friend(user):
    await EventUser.filter(user=user).update(friend='+')

async def update_event_user_after_delete(update_list):
    await EventUser.bulk_update(update_list, ['created_at'])


''' -------------------------------------- DELETE ---------------------------------------- '''

async def delete_event_user(user_id: int, event_id: int):
    try:
        await EventUser.filter(user_id=user_id, event_id=event_id).delete()
    except DoesNotExist as e:
        await logger.error(f'delete_event_user: {e}')
    except Exception as e:
        await logger.error(f'delete_event_user_other error: {e}')