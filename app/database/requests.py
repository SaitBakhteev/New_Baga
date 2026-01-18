import uuid
from uuid import uuid1
from config import setup_logger

from tortoise.exceptions import DoesNotExist

from app.database.models import User, Event, EventUser, Template
from datetime import datetime, timedelta

logger = setup_logger(__name__)


''' ---------------------------- USER -------------------------------------- '''
# Создание или получение пользователя
async def get_or_create_user(from_user, for_telegramm=False, create_user=False):
    try:
        if for_telegramm:
            return await User.get(tg_id=from_user.id).values('id', 'admin_permissions', 'receive_notifications')

        user = await User.get_or_none(tg_id=from_user.id)
        if create_user:
            last_name = f' {from_user.last_name}' if from_user.last_name else ''
            full_name = f'{from_user.first_name}{last_name}'
            await User.create(
                tg_id=from_user.id, tg_username=from_user.username,
                tg_name=full_name, created_at=datetime.now()
            )
            return
        return user
    except Exception as e:
        await logger.error(f"User is not created; {e}")
        return


async def get_all_users():
    return await User.all()


async def get_user_by_username(tg_username: str):
    try:
        boss = await User.filter(tg_username=tg_username).get()
        return boss.id
    except DoesNotExist as e:
        await logger.error(f"get_user_by_username: {e}")
        return None


# Запрос на редактирование профиля
async def update_user(**kwargs):
    try:
        if 'new_username' in kwargs:
            await User.filter(id=kwargs['user_id']).update(tg_username=kwargs['new_username'])
        elif 'tg_name' in kwargs:
            tg_name, id = kwargs['tg_name'], kwargs['user_id']
            await User.filter(id=id).update(tg_name=tg_name)
    except Exception as e:
        await logger.error(f'Ошибка в update_user: {e}')
        # stream_await logger.error(f'update_user: {e}')


# Обновление поля включения или отключения уведомлений
async def update_user_receive_notificcations(tg_id: int):
    try:
        user = await User.filter(tg_id=tg_id).get()
        receive_notifications = not user.receive_notifications
        user.receive_notifications = receive_notifications
        await user.save()
        return receive_notifications
    except DoesNotExist as e:
        await logger.error(f'ошибка при обновлении поля получения уведомлений: {e}')
        return None


# Специфицеский запрос из админ-панели
async def update_admin_and_get(tg_username: str, admin_permissions: bool):
    try:
        user = await User.get_or_none(tg_username=tg_username)
        await logger.info(f'USER: {user.tg_name}')
        user_id = user.id
        user.admin_permissions = admin_permissions
        await User.filter(id=user_id).update(admin_permissions=admin_permissions)
        return (user, user.tg_id)
    except DoesNotExist as e:
        await logger.error(f'update_admin_and_get: User does not exist')
    except Exception as e:
        await logger.error(f'update_admin_and_get: {e}')


''' ---------------------------- EVENT ------------------------------------------------ '''
async def create_event(data):  # добавить событие
    try:
        await Event.create(
            training_type=data['training_type'],
            created_at=data['created_at'],
            payment_dedline=data['payment_dedline'],
            event_datetime=data['event_datetime'],
            participants_count=data['participants_count'],
            event_text=data['event_text'],
            boss_id=data['boss_id']
        )
    except Exception:
        return


async def get_event(id=None, for_telegramm=False,
                    for_schedule=False, last_record=False,
                    training_type=None, **kwargs) -> Event():
    try:
        if for_telegramm:
            return await (
                Event.get(id=id).values('id', 'payment_dedline', 'stars',
                                        'event_datetime', 'event_text',
                                        'participants_count')
            )
        elif for_schedule:
            # Добавлять времена планировщику имеет смысл не менее, чем за час до наступдения дедлайна
            reper_datetime = datetime.now() + timedelta(hours=1)
            return await (Event.filter(payment_dedline__gt=reper_datetime).order_by('-id').
                          first().values('id', 'payment_dedline', 'stars')) if last_record \
                else await (Event.filter(payment_dedline__gt=reper_datetime).order_by('payment_dedline').
                            values('id', 'payment_dedline', 'stars'))
        elif id:
            return await (Event.filter(id=id).values(
                'id', 'payment_dedline', 'event_datetime', 'event_text', 'participants_count', 'stars',
                'training_type'
            )
            )
        else:
            return await Event.get(id=id) if id else \
                await (
                    Event.all().order_by('id').
                    values('id', 'payment_dedline', 'event_datetime', 'training_type',
                           'event_text', 'participants_count', 'stars')
                )
    except DoesNotExist:
        return


# Запрос для отображения списка тренировок по выбранному типу
async def get_events_by_training_type(training_type, is_admin):
    if is_admin is False:  # админы видят и прошедшие необработанные по звезлам тренировки
        return await (
            Event.filter(training_type=training_type,
                         event_datetime__gt=datetime.now() - timedelta(hours=12)).order_by('id').
            values('id', 'payment_dedline', 'event_datetime', 'event_text', 'participants_count', 'stars')
        )
    else:
        return await (
            Event.filter(training_type=training_type).order_by('id').
            values('id', 'payment_dedline', 'event_datetime', 'event_text', 'participants_count', 'stars')
        )


async def update_event(event_id: int, data, **kwargs):
    if 'stars' not in kwargs:
        await Event.filter(id=event_id).update(
            event_datetime=data['event_datetime'],
            participants_count=data['participants_count'],
            event_text=data['event_text'],
            boss_id=data['boss_id']
        )
    else:  # вносим звёзд в event
        await Event.filter(id=event_id).update(stars=kwargs['stars'])


async def delete_event(id: int):
    await Event.filter(id=id).delete()


''' ------------------------------------- TEMPLATE ----------------------------------- '''
async def create_template(text: str):
    await Template.create(modified_at=datetime.now(), text=text)


async def get_templates() -> Template():
    return await Template.all().values('id', 'text')


async def delete_template(template_id: int):
    try:
        template = await Template.filter(id=template_id).get()
        await template.delete()
        return 'OK'
    except DoesNotExist as e:
        await logger.error(f'delete_template: {e}')
        return 'Error'


''' ДЛЯ ТЕСТИРОВАНИЯ '''

# # Обновление поля created_at после перехода из резерва
# async def update_event_user_after_transfer(event_id, user_id, now):
#     await EventUser.filter(user_id=user_id, event_id=event_id).update(created_at=now)
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
