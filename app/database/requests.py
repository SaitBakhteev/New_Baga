import uuid
from uuid import uuid1
import logging
from tortoise.exceptions import DoesNotExist

from app.database.models import User, Event, EventUser, Template
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


# ----- ПОЛЬЗОВАТЕЛЬ -----------
# Создание или получение пользователя
async def get_or_create_user(from_user, for_telegramm=False, create_user=False):
    try:
        if for_telegramm:
            return await User.get(tg_id=from_user.id).values('id', 'admin_permissions', 'receive_notifications')

        user = await User.get_or_none(tg_id=from_user.id)
        if create_user:
            await User.create(
                tg_id=from_user.id, tg_username=from_user.username,
                tg_name=from_user.first_name, created_at=datetime.now()
            )
            return
        return user
    except Exception as e:
        logger.error(f"User is not created; {e}")
        return


async def get_all_users():
    return await User.all()


async def get_user_by_username(tg_username: str):
    try:
        boss = await User.filter(tg_username=tg_username).get()
        return boss.id
    except DoesNotExist as e:
        logger.error(f"get_user_by_username: {e}")
        return None


''' ДЕЙСТВИЯ С БД, ДОСТУПНЫЕ ТОЛЬКО АДМИНУ '''
# добавление объектов моделей

async def create_event(data):  # добавить событие
    try:
        await Event.create(
            created_at = data['created_at'],
            payment_dedline = data['payment_dedline'],
            event_datetime = data['event_datetime'],
            participants_count = data['participants_count'],
            event_text = data['event_text'],
            boss_id = data['boss_id']
        )
    except Exception:
        return


# Создание записи пользователя на тренировку
async def create_event_user(data, **kwargs):
    user_id = kwargs['friend_id'] if 'friend_id' in kwargs else data['user_id']
    await EventUser.create(user_id=user_id,
                           event_id=data['event_id'],
                           created_at=datetime.now())


async def create_template(text: str):
    await Template.create(modified_at=datetime.now(), text=text)


# Получение объектов моделей

async def get_event(id=None, for_telegramm=False,
                    for_schedule=False, last_record=False) -> Event():
    try:
        if for_telegramm:
            return await (
                Event.get(id=id).values('payment_dedline',
                                        'event_datetime', 'event_text',
                                        'participants_count')
            )
        elif for_schedule:
            # Добавлять времена планировщику имеет смысл не менее, чем за час до наступдения дедлайна
            reper_datetime = datetime.now() + timedelta(hours=1)
            return await (Event.filter(payment_dedline__gt=reper_datetime).order_by('-id').
                          first().values('id', 'payment_dedline')) if last_record \
                else await (Event.filter(payment_dedline__gt=reper_datetime).order_by('payment_dedline').
                            values('id', 'payment_dedline'))
        else:
            return await Event.get(id=id) if id else \
                await (
                    Event.all().order_by('id').
                    values('id', 'payment_dedline', 'event_datetime',
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
                                 ))
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
                                 'paid_check',
                                 'friend',))
    except DoesNotExist:
        logger.error('get_event_user: User DoesNotExist')
    except Exception as e:
        logger.error(f'get_event_user: {e}')


async def get_templates() -> Template():
    return await Template.all().values('id', 'text')


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


async def delete_template(template_id: int):
    try:
        template = await Template.filter(id=template_id).get()
        await template.delete()
        return 'OK'
    except DoesNotExist as e:
        logger.error(f'delete_template: {e}')
        return 'Error'

""" Обновление времени записи на тренировку для участников,
которые не выполнинли условия по оплате. Данное обновление
выполняется за один запрос к БД """

# Обновление поля включения или отключения уведомлений
async def update_user_receive_notificcations(tg_id: int):
    try:
        user = await User.filter(tg_id=tg_id).get()
        receive_notifications = not user.receive_notifications
        user.receive_notifications = receive_notifications
        await user.save()
        return receive_notifications
    except DoesNotExist as e:
        logger.error(f'ошибка при обновлении поля получения уведомлений: {e}')
        return None


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


async def update_event(event_id: int, data):
    await Event.filter(id=event_id).update(
        event_datetime=data['event_datetime'],
        participants_count=data['participants_count'],
        event_text=data['event_text'],
        boss_id=data['boss_id']
    )


# Запрос к БД для обновления записей EventUser при нажатии пользователем кнопки '✔️ Я оплатил'
async def update_event_user(user_id: int, event_id: int,
                            payment_notify: bool = False,
                            replace_to_end: bool=None):
    try:
        if payment_notify:
            await (EventUser.filter(user_id=user_id,
                                   event_id=event_id).
                   update(paid_check='paid'))
        elif replace_to_end:
            await (EventUser.filter(user_id=user_id,
                                   event_id=event_id).
                   update(created_at=datetime.now()))

        else:
            await (EventUser.filter(user_id=user_id,
                                   event_id=event_id).
                   update(paid_check=None, payment_confirmed=None))
    except DoesNotExist:
        logger.error(f'update_event_user: Does Not exist')
    except Exception as e:
        logger.error(f'update_event_user: {e}')


# Запрос к БД для обновления записей EventUser при проверке админом оплаты
async def update_event_user_for_payment_verify(id_list: list, is_confirm=True):
    if is_confirm: # если админ подтверждает оплату
        await EventUser.filter(id__in=id_list).update(payment_confirmed=True)
    elif is_confirm == False: # если админ опровергает оплату
        await EventUser.filter(id__in=id_list).update(payment_confirmed=False)
    else:  # если админ отменяет верификацию оплаты
        print(f'is_conf = {is_confirm}')
        await EventUser.filter(id__in=id_list).update(payment_confirmed=None)


# Обновление поля friend после записи друга на тренировку
async def update_event_user_after_add_friend(user):
    await EventUser.filter(user=user).update(friend='+')


async def test():
    print('test')
    # for i in  range(52, 59):
    #     await EventUser.create(event_id=14, user_id=i)
    # for i in range(50):
    #     posfix = str(uuid1())
    #     posfix = posfix[:posfix.find('-')]
    #     await User.create(
    #         tg_id=-100-i, tg_username=f'username_{posfix}',
    #         tg_name=f'test_name_{posfix[::-1]}'
    #     )
    # #
    # #
