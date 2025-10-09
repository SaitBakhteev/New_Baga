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
from tortoise import transactions
from datetime import date, datetime, timedelta
from app.database.models import Event, EventUser, Statistic

from config import SEASON_INDEX

logger = logging.getLogger(__name__)

stars_dict = dict()  # словарь рейтинга звезд, распределенный по типам тренировок

# специальный геттер во избедание проблемы обнуления stars_dict при импорте
def stars_dict_getter():
    return stars_dict


async def test_stat():
    try:
        # await Statistic.all().delete()
        # await Event.all().delete()
        await EventUser.create(user_id=23, event_id=69)
        await EventUser.create(user_id=24, event_id=69)
        await EventUser.create(user_id=25, event_id=69)
        await EventUser.create(user_id=26, event_id=69)
        await EventUser.create(user_id=27, event_id=69)
        #
        # await EventUser.create(user_id=10, event_id=64)
        # await EventUser.create(user_id=15, event_id=64)
        # await EventUser.create(user_id=19, event_id=64)
        # await EventUser.create(user_id=22, event_id=64)
        # await EventUser.create(user_id=29, event_id=64)

        # await delete_events()
    except Exception as e:
        print(f'Ошибка теста: {e}')


# Формирование списков на обновление и сощдание новых записе в Statistic
async def statistic_list_formation(now, event_user, statistics) -> dict:
    # Инициируем список на обновление и создание статистики
    stat_upd_lst, stat_cre_lst = [], []

    # Инициируем список списков на добавление звезд в формате [[<event_id>, (<юзер_1>, <юзер_2>...)]]
    for event_id in {item.event.id for item in event_user}:
        # Определяем текущий user_id и считываем его звезд
        current_event = next(filter(lambda x: x.event.id == event_id, event_user), None)

        # если есть звезды этой тренировки, то начинаем обработку
        stars_of_event = ()  # но сначала ставим заглушку
        if current_event.event.stars:
            # Для читаемости кода сначала формируем текстовый список user_id
            stars_text_lst = current_event.event.stars.replace(' ', '').split(',')
            # Затем уже преобразуем в int и формируем кортеж звезд
            stars_of_event = tuple(map(lambda x: int(x), stars_text_lst))
        lst = sorted([_item for _item in event_user if _item.event.id == event_id], key=lambda x: x.created_at)
        '''Фомируем список QuerySet по данной трени, отсортированный по временам записи участников  '''

        last_index = lst[0].event.participants_count
        ''' Находим крайний индекс основного списка участников тренировки по первому элементу'''

        '''Теперь идем по сформированному списку'''
        for _event_user in lst[:last_index]:
            user_id, _train_type = _event_user.user.id, _event_user.event.training_type
            stat = next(filter(lambda x: x.user.id == user_id and x.training_type == _train_type and
                                         x.season_index == SEASON_INDEX[0], statistics), None)

            # Если комбинация "юзер-тип_трени-индекс_сезона" встретилась в статистике, то пускаем на обновление
            if stat:
                stat.visit_count += 1
                stat.modifed_at = now
                if user_id in stars_of_event:
                    stat.star_count += 1
                # Если обновляемый объект не присутствует в списке на обновление, то добавляем его
                if stat not in stat_upd_lst:
                    stat_upd_lst.append(stat)

            # Если ранее такая комбинация "юзер - тип_трени - индекс_сезона не встречалась"
            else:
                # Проверяем, не иниицировали ли мы ранее создаваемый объект
                current_create_obj = next(
                    filter(lambda x: x.user.id == user_id and x.training_type == _train_type,
                           stat_cre_lst),
                    None
                )
                if current_create_obj is None:
                    '''Если ранее этот объект статистики отсутствовал, то добавляем его'''
                    new_stat_object = Statistic(user=_event_user.user, training_type=_train_type, visit_count=1,
                                                created_at=now, star_count=0, modifed_at=now)
                    stat_cre_lst.append(new_stat_object)
                    current_create_obj = new_stat_object
                else:
                    current_create_obj.visit_count += 1
                if user_id in stars_of_event:  # если новый у нового объекта есть звезды
                    current_create_obj.star_count += 1

    return {'stat_upd_lst': stat_upd_lst, 'stat_cre_lst': stat_cre_lst}


# Функция пересмотра статистики и формирования рейтинга
async def stat_raiting():
    global stars_dict
    stars_dict.clear()
    stats = await Statistic.filter(season_index=SEASON_INDEX[0]).prefetch_related('user').all()
    for item in stats:
        if item.training_type not in stars_dict:
            stars_dict[item.training_type] = []
        stars_dict[item.training_type].append(item)
    # Сортируем списки в словаре
    for k in stars_dict:
        stars_dict[k] = sorted(stars_dict[k], key=lambda item: item.star_count, reverse=True)
    print(f'stars_dict внутри stat_raiting {stars_dict}')

# Удаление записей прошедших тренировок из БД
async def delete_events():
    try:
        now = datetime.now()
        last_dt = datetime(2025, 6, 15)  # заглушка
        event_user = await  EventUser.filter(
            event__event_datetime__gt=last_dt).prefetch_related('event','user'
                                                                ).all()
        '''Загружаем из БД все содержимое прошедших треней'''

        # Если есть прошедшие тренировки, то двигаемся дальше
        if event_user:
            users, training_types = ({item.user.id for item in event_user if item.user.id},
                                     {item.event.training_type for item in event_user})
            '''Формируем сеты текущих юзеров и типов тренировок'''
            statistics = await (Statistic.filter(user__id__in=users,
                                                 training_type__in=training_types,
                                                 season_index=SEASON_INDEX[0])
                                .prefetch_related('user').all())
            '''Подгружаем с БД статистики согласно вышеприведенным сетам'''
            data = await statistic_list_formation(now, event_user, statistics)
            stat_upd_lst, stat_cre_lst = data['stat_upd_lst'], data['stat_cre_lst']

            # Обертываем в единую транзакцию
            with transactions.in_transaction():
                if stat_upd_lst:
                    await Statistic.bulk_update(stat_upd_lst, ['modifed_at', 'star_count', 'visit_count'])
                if stat_cre_lst:
                    await Statistic.bulk_create(stat_cre_lst)
            await stat_raiting()

    except Exception as e:
        logger.info(f'Ошибка в delete_events: {e}')


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

# stars_dict_getter()