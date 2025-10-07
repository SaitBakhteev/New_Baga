"""
В данном модуле выполняются задачи по расписанию.
1. Перемещение в конец очереди тех участников, которые не соблюли
условия дедлайна оплаты. При наступлении дедлайна оплаты в конец очереди
переместятся участники ОСНОВНОГО СПИСКА, у которых:
- paid_check == null и payment_confirmed != True;
- paid_check != null и payment_confirmed == False и current_position <= participants_count.

Алгоритм перемещения в конец очереди:
1) Получаем из БД объекты EventUser в отсортированном по 'event_id' виде;
2) Формируется словарь с ключами 'event_id', которым присваивается список объектов;
3) Каждый список, переданный ключам, сортируется по 'created_at';
4) Производится итерирование по каждому из этих списков, где обновляется время для участников,
соответвстующие условиям дедлайна

2. Удаляются неактуальные тренировки
"""

import logging

from aiogram import Bot
from tortoise.exceptions import DoesNotExist, DBConnectionError
from datetime import date, datetime, timedelta
from app.database.models import Event, EventUser, Statistic

from config import SEASON_INDEX

logger = logging.getLogger(__name__)


# Удаление записей прошедших тренировок из БД
async def delete_events():
    now = datetime.now()
    last_dt = datetime(2025, 6, 15)  # заглушка
    # await EventUser.filter(id=22).update(created_at=last_dt)
    # await Event.filter(id=45).update(event_datetime=last_dt)
    user_events = await  EventUser.filter(event__event_datetime__lt=now).prefetch_related('event','user').all()


    '''Формируем сеты текущих юзеров и типов тренировок'''
    users, training_types = {item.user.id for item in user_events}, {item.event.training_type for item in user_events}
    print(f'users = {users}\n'
          f'training_types = {training_types}\n')

    '''Подгружаем с БД статистики согласно вышеприведенным сетам'''
    statistics = await Statistic.filter(user__id__in=users, training_type__in=training_types).prefetch_related('user').all()

    print(statistics)
    # exist_stat
    general_list, list_type_user_idx = [], []
    for event_id in {item.event.id for item in user_events}:
        lst = sorted([_item for _item in user_events if _item.event.id == event_id], key=lambda x: x.created_at)
        ''' Находим крайний индекс основного списка участников тренировки по первому элементу'''
        last_index = lst[0].event.participants_count
        general_list.append(lst[:last_index])
        ''' Формируем список таплов (тип_трени, юзер, индекс_сезона) по прошедшему дню. '''
        for _item in lst[:last_index]:
            current_tpl = (_item.training_type, _item.user.id, SEASON_INDEX[0])
            list_type_user_idx.append(current_tpl)
        ''' Формируем список '''

        # for stat in statistics:
        #     stat.user.id



    ''' Формируем словарь звезд по видам спорта '''
    stars = dict()

    print(f'главный список = {general_list}')

    # for star in {item.event.id for item in user_events}:
    #     _stars = [_item.event.stars.replace(' ', '').split(',') for _item in user_events]
    #
    ''' Определяем, все комбинации юзер-тип тренировки,-индекс сезона уже есть в БД '''
    update_list = []
    for item in user_events:
        if (tpl := (item.event.training_type, item.user.id)) not in update_list:
            update_list.append(tpl)

    # update_stat_objs = await Statistic.filter(training_type='Футбол', user_id__in=lstr)

    # statistics =  await Statistic.filter(event__datetime__lt=now).prefetch_related('event').all()


    #

    # user_events[0].text = "Chnget"
    #
    # # Сначала смотрим какие тренировки неактуальны уже
    # user_events = await (EventUser.filter().prefetch_related('event','user').all().
    #           values('event__id',
    #                  'event__training_type',
    #                  'event__participants_count',
    #                  'event__stars', 'user_id',
    #                  'created_at'))

    print(update_list)

    dt = [{'id': 21, 'user__tg_name': 'Eldar', 'training_type': '🏀 Баскетбол'},
     {'id': 21, 'user__tg_name': 'Рустем', 'training_type': '🏀 Баскетбол'},
     {'id': 21, 'user__tg_name': 'Vlad', 'training_type': '🏀 Баскетбол'},
     {'id': 21, 'user__tg_name': 'Булат', 'training_type': '🏀 Баскетбол'},
     {'id': 21, 'user__tg_name': 'Саит', 'training_type': '🏀 Баскетбол'}]
    # for item in user_events:


    # await Event.filter(event_datetime__lt=now).delete()


async def message(event_id=None, notify=False, bot: Bot = None):
    try:
        # Получение из БД всех объектов EventUser
        event_user = await (EventUser.filter(event__payment_dedline__isnull=True).
                            select_related('event', 'user').order_by('event_id')) \
            if event_id is None else await ((EventUser.all().select_related('event', 'user').
                                             filter(event_id=event_id).order_by('created_at')))
        if event_user:
            print(f'schedule = {event_user[0].event.event_text}')

            # Установка порогового значения даты, определяющая дедлайн оплаты
            now = datetime.now()
            dedline_date = now - timedelta(days=1) if event_id is None \
                else event_user[0].event.payment_dedline.replace(tzinfo=None)

            # Распределение объектов event_user по ключам 'event_id' в новом словаре
            _dict = dict()
            for i, item in enumerate(event_user):
                if item.event.id not in _dict.keys():
                    _dict[item.event.id] = []
                _dict[item.event.id].append(item)

            # Сортировка сформированных списков в словаре по 'created_at'
            sorted_dict = {k: sorted(v, key=lambda obj: obj.created_at) for k, v in _dict.items()}
            objects_to_update = []
            for item in sorted_dict:
                participants_count = sorted_dict[item][0].event.participants_count
                seconds = 0
                for i, obj in enumerate(sorted_dict[item]):
                    if obj.created_at.replace(tzinfo=None) <= dedline_date or notify:
                        if (obj.paid_check is None and obj.payment_confirmed is None) \
                                or (obj.paid_check is not None and obj.payment_confirmed is False):
                            seconds += 1
                            update_datetime = now + timedelta(seconds=seconds)
                            obj.paid_check, obj.payment_confirmed, obj.created_at = (
                                None, None, update_datetime)
                            objects_to_update.append(obj)

                    if i == participants_count - 1:
                        break
            if objects_to_update and notify is False:
                await EventUser.bulk_update(objects_to_update, ['paid_check', 'payment_confirmed', 'created_at'])

            # Если сюда в том числе передается конкретное id тренировки, то срабатывает рассылка уведомлений
            elif objects_to_update and notify is True and event_id:
                text = (f'Напоминаем, что необходимо внести оплату за тренировку, через час наступит дедлайн.\n'
                        f'<b><i>Сведения о тренировке</i></b>:\n'
                        f'{event_user[0].event.event_text}')
                for obj in objects_to_update:
                    if obj.user.receive_notifications is True:
                        try:                
                            await bot.send_message(chat_id=obj.user.tg_id,
                                                   text=text, parse_mode='HTML')
                        except Exception:
                            continue

    except DoesNotExist as e:
        logger.info(f'DoesNotExist: {e}')
    except DBConnectionError as e:
        logger.info(f'DBConnectionError: {e}')
    except Exception as e:
        logger.error(f'on_schedule_update: {e}')

