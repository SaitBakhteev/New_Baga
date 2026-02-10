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

from app.database import requests as rqs
from aiogram import Bot
from tortoise.exceptions import DoesNotExist, DBConnectionError
from tortoise import transactions

from datetime import date, datetime, timedelta

from app.database.models import Event, EventUser, Statistic, User

from config.log_config import setup_logger
from config.constants import SEASON_INDEX

from app.operations.often_ops_and_classes import SendMessages, set_individual_dedline

logger, stream_logger = setup_logger(__name__), logging.getLogger(__name__)

stars_dict = dict()  # словарь рейтинга звезд, распределенный по типам тренировок
general_raiting = []  # список общего рейтинга


# Класс для сканирования и пермещения в конец очереди
class MoveToEnd():
    def __init__(self, event_user, now):
        self._event_user, self._now = event_user, now
        self._participants_count = self._event_user[0].event.participants_count
        if len(self._event_user) > self._participants_count:
            self._reserv_list = self._event_user[self._participants_count:]
            self._reserv_count = len(self._event_user) - self._participants_count
            self._update_list = []  # список участников на обновление в БД

    # Главный исполняющий метод класса
    async def execute(self):
        if len(self._event_user) > self._participants_count:
            is_ex_move_to_end_ptcps = self._extract_from_main_lst()
            self._reserv_list(is_ex_move_to_end_ptcps)
            if len(self._update_list) > 0:
                await EventUser.bulk_update(self._update_list, ['modified_at', 'individual_dedline'])

    # Метод, который извлекает в отдельный список участников основного с просроченным дедлайном
    def _extract_from_main_lst(self):
        seconds = 0
        for obj in self._event_user[:self._participants_count]:
            if len(self._update_list) > self._reserv_count:
                break
            if obj.individual_dedline.replace(tzinfo=None) <= self._now and obj.payment_confirmed is not True:
                seconds += 1
                modified_at = self._now + timedelta(seconds=seconds)
                obj.modified_at = modified_at.replace(tzinfo=None)
                self._update_list.append(obj)
        return True if len(self._update_list) > 0 else None

    async def _reserve_lst_ops(self, is_ex_move_to_end_ptcps):
        '''
        Метод выполняет следующие операции над резервным списком:
        - выявляет тех, кто перешел из резерва в основной список
        - обновляет modified_at всем резервникам со знаком "-"
        - вызывает класс по рассылке тем, кто перешел из резерва
        :return: список тех, кто перешел из резерва
        '''
        if is_ex_move_to_end_ptcps:  # если есть из основного списка те, кто перемещен в конец
            # Устанавливаем индвидуальный дедлайн
            payment_dedline = self._event_user[0].event.payment_dedline
            event_datetime  = self._event_user[0].event.event_datetime
            individual_dedline = set_individual_dedline(payment_dedline, event_datetime, self._now)
            begin_idx, end_idx = self._participants_count, self._participants_count + len(self._update_list)

            # Обновляем individual_dedline для перешедших из резерва
            transfer_lst_from_reserve = self._reserv_list[begin_idx:end_idx]
            for obj in transfer_lst_from_reserve:
                obj.individual_dedline = individual_dedline['individual_dedline'].replace(tzinfo=None)
            for i, obj in enumerate(self._reserv_list):
                seconds = len(self._event_user) - i
                modified_at = self._now - timedelta(seconds=seconds)
                obj.modified_at = modified_at.replace(tzinfo=None)
                self._update_list.append(obj)
            tg_ids = [item.user.tg_id for item in transfer_lst_from_reserve]
            tg_usernames = [item.user.tg_username for item in transfer_lst_from_reserve]
            dedline_txt = individual_dedline['text']
            await self._send_msg(tg_ids, tg_usernames, dedline_txt)

    async def _send_msg(self, tg_ids: list, tg_usernames: list, dedline_txt):
        '''
        Функция выполняет слудеюущие действия:
        - рассылает уведомления участникам, перешедшим из резерва;
        - формирует список никнеймов, согласно пункту выше
        - включает список по п. выше в текст рассылки админам
        :param tg_ids:
        :param tg_usernames:
        :param dedline_txt:
        :return:
        '''

        # БЛОК ДЛЯ РАССЫЛКИ УЧАСТНИКАМБ ПЕРЕШЕДШИМ ИЗ РЕЗЕРВА
        # --------------------------------------------------
        text = (
            f'️⚡️ ️⚡️ <b>ВАЖНАЯ ИНФОРМАЦИЯ</b>\n'
            f'Уважаемый участник, вы перемещены из резерва в основной список.\n'
            f'<b><i>Сведения о тренировке</i></b>:\n'
            f'<b>Дисциплина</b>: <i>{self._event_user.event.training_type}</i>\n'
            f'{self._event_user[0].event.event_text}'
        )
        text += f'\n{dedline_txt}'
        await SendMessages.to_several_receivers(text=text, tg_ids=tg_ids)

        # БЛОК ДЛЯ РАССЫЛКИ АДМИНАМ
        # --------------------------
        usernames = ''
        for username in tg_usernames:
            usernames += f'- @{username}\n'

        adm_txt = (
            f'🔊⚡️ ВНИМАНИЕ админам❗️\n'
            f'По тренировке, до которой остается <b>МЕНЕЕ 12 ЧАСОВ</b> планировщик переместил в ОСНОВНОЙ список '
            f'участников со следующими никнеймами\n{usernames}'
            f'\n<b>Данные тренировки</b>\n\n'
            f'<b>Дисциплина</b>: <i>{self._event_user[0].event.training_type}</i>\n'
            f'{self._event_user[0].event.event_text}'
        )
        event_datetime = self._event_user[0].event.event_datetime.replace(tzinfo=None)
        await SendMessages.to_admins(adm_txt, self._now, event_datetime)


class SendReminders():
    def __init__(self, event_user, now):
        self._event_user = event_user
        self._participants_count = self._event_user[0].event.participants_count
        self._now, self._before_1_hours = now, now + timedelta(hours=1)
        self._update_list = []

    async def execute(self):
        for obj in self._event_user[:self._participants_count]:
            if obj.individual_dedline <= self._before_1_hours:
                last_payment_notify = self._now
                obj.last_payment_notify = last_payment_notify.replace(tzinfo=None)
                self._update_list.append(obj)
        if len(self._update_list) > 0:
            await self._send_msg()
            await EventUser.bulk_update(self._update_list, ['last_payment_notify'])

    async def _send_msg(self):
        text = (
            f'❗❗❗ ВАЖНАЯ ИНФОРМАЦИЯ ДЛЯ ВАС ❗❗❗\n'
            f'Напоминаем, что необходимо внести оплату за тренировку, иначе через час(❗) есть риск '
            f'оказаться в конце очереди при соответствующем превышении квоты.\n'
            f'<b><i>Сведения о тренировке</i></b>:\n'
            f'<b>Дисциплина</b>: <i>{self._event_user[0].event.training_type}</i>\n'
            f'{self._event_user[0].event.event_text}'
        )
        _recepient_list = [item.user.tg_id for item in self._update_list]
        await SendMessages.to_several_receivers(tg_ids=_recepient_list, text=text)


class StatisticOps():
    def __init__(self, event_user, now):
        _count = event_user[0].event.participants_count
        self._event_user = event_user[:_count]
        self._train_type = event_user[0].event.training_type
        self._update_list, self._create_list = [], []
        self._now = now

    async def execute(self):
        await self._load_stat()
        self._extract_stars()
        self._lists_formation()
        if self._update_list:
            await Statistic.bulk_update(self._update_list, ['modifed_at', 'star_count', 'visit_count', 'likes'])
        if self._create_list:
            await Statistic.bulk_create(self._create_list)

    async def _load_stat(self):
        _user_ids = [item.user.id for item in self._event_user]
        stat = await Statistic.filter(
            user__id__in=_user_ids,
            training_type__in=self._train_type,
            season_index=SEASON_INDEX[0]
        ).prefetch_related('user').all()
        self._stat = stat

    def _extract_stars(self):
        if self._event_user[0].event.stars != 'No':
            _stars = self._event_user[0].event.stars.replace(' ', '').split(',')
            stars_of_event = tuple(map(lambda x: int(x), _stars))
            self._stars = stars_of_event
        else:
            self._stars = []

    def _lists_formation(self):
        for item in self._event_user:
            stat = next((_stat for _stat in self._stat if _stat.user.id==item.user.id),
                        None)
            if stat:
                stat.visit_count += 1
                stat.modifed_at = self._now
                stat.likes += item.likes
                if item.user.id in self._stars:
                    stat.star_count += 1
                self._update_list.append(stat)

            else:
                new_stat = Statistic(
                    user=item.user, training_type=self._train_type,
                    visit_count=1, star_count=0, likes=item.likes,
                    created_at=self._now, modifed_at=self._now
                )
                if item.user.id in self._stars:
                    new_stat.star_count += 1
                self._create_list.append(new_stat)


# специальный геттер во избедание проблемы обнуления stars_dict при импорте
def stars_dict_getter():
    return stars_dict


def general_raiting_getter():
    return general_raiting


async def test_stat():
    try:
        await delete_events(test=True)
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
        lst = sorted([_item for _item in event_user if _item.event.id == event_id],
                     key=lambda x: x.modified_at.replace(tzinfo=None))
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
    global general_raiting
    stars_dict.clear()
    stats = await Statistic.filter(season_index=SEASON_INDEX[0]).prefetch_related('user').all().order_by(
        'training_type')
    for item in stats:
        if item.training_type not in stars_dict:
            stars_dict[item.training_type] = []
        if item.star_count > 0:
            stars_dict[item.training_type].append(item)
    # Сортируем списки в словаре
    for k in stars_dict:
        stars_dict[k] = sorted(stars_dict[k], key=lambda item: item.star_count, reverse=True)

    # Формирование общего рейтинга
    users = set()

    for k in stars_dict:
        for item in stars_dict[k]:
            users.add(item.user)
    general_raiting.clear()
    for _user in users:
        star_count = 0
        text = ''
        for k in stars_dict:
            _user_raiting = next((item for item in stars_dict[k] if item.user.id == _user.id), None)
            if _user_raiting:
                star_count += _user_raiting.star_count
                text += str(k)[0]
        general_raiting.append((_user.tg_name, _user.tg_username, star_count, text))
        general_raiting = sorted(general_raiting, key=lambda x: x[2], reverse=True)

    # for item in general_raiting:
    #     await logger.critical(f'общий рейтинг{item}')


# Удаление записей прошедших тренировок из БД
async def delete_events(bot: Bot, test=None, model_event_users=None):
    try:
        now = datetime.now() if test is None else datetime.now() + timedelta(days=45)
        event_user = await  EventUser.filter(
            event__event_datetime__lt=now, event__stars__isnull=False).prefetch_related('event', 'user'
                                                                                        ).all()
        '''Загружаем из БД все содержимое прошедших треней'''

        # if model_event_users:
        #     event_user = model_event_users

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
            async with transactions.in_transaction():
                if stat_upd_lst:
                    await Statistic.bulk_update(stat_upd_lst, ['modifed_at', 'star_count', 'visit_count'])
                if stat_cre_lst:
                    await Statistic.bulk_create(stat_cre_lst)
            await stat_raiting()
        await Event.filter(event_datetime__lt=now, stars__isnull=False).delete()
        events_without_stars = await Event.filter(event_datetime__lt=now, stars__isnull=True).all()
        if events_without_stars:
            admins = await User.filter(admin_permissions=True).all()
            for adm in admins:
                text = ('❗️<b>УВАЖАЕМЫЕ АДМИНЫ</b>❗️\n'
                        'Остались прошедшие тренировки с ⚡️<i>неотмеченными звёздами⭐️</i> ⚡️\n'
                        'Отметьте звезд и тогда бот в свои ночные часы обработает эти тренировки')
                await bot.send_message(chat_id=adm.tg_id, text=text, parse_mode='HTML')
    except Exception as e:
        await logger.error(f'Ошибка в delete_events: {e}')
        # stream_logger.info(f'Ошибка в delete_events: {e}')


async def check_payment_dedline(user_cache: dict, notify=False, bot: Bot = None):
    try:
        now = datetime.now().replace(tzinfo=None)
        if notify is False:
            # await logger.critical(f'Текущее время работы планировщика scan: {now}')
            # Получение из БД всех объектов EventUser, по которым наступил дедлайн оплаты
            event_user = await (EventUser.filter(event__payment_dedline__lte=now, event__event_datetime__gte=now).
                                select_related('event', 'user').order_by('event_id'))
        else:
            # Получение из БД всех объектов EventUser, по которым через час наступит дедлайн оплаты
            event_user = await (
                EventUser.filter(event__payment_dedline__lte=now + timedelta(hours=1, minutes=2),
                                 event__event_datetime__gte=now).
                select_related('event', 'user').order_by('event_id'))
        if event_user:
            # Распределение объектов event_user по ключам 'event_id' в новом словаре
            _dict = dict()
            for i, item in enumerate(event_user):
                if item.event.id not in _dict.keys():
                    _dict[item.event.id] = []
                _dict[item.event.id].append(item)

            # Сортировка сформированных списков в словаре по 'modified_at'
            sorted_dict = {k: sorted(v, key=lambda obj: obj.modified_at.replace(tzinfo=None)) for k, v in _dict.items()}
            objects_to_update = []
            rep_dedl_for_individ = now - timedelta(hours=12) if notify is False else now - timedelta(hours=11)

            # rep_dedl_for_individ = now - timedelta(minutes=2)  # заглушка для тестирования
            ''' Реперная точка для проверки индивидуального дедлайна '''

            for item in sorted_dict:
                participants_count = sorted_dict[item][0].event.participants_count
                event_id = sorted_dict[item][0].event.id
                if len(sorted_dict[item]) > participants_count:  # если список превышает квоту
                    reserv_list = sorted_dict[item][participants_count:]  # смотрим кто находился в резерве
                    res_users = [_item.user.tg_username for _item in reserv_list]
                    # await logger.critical(f'Пользователи резервного списка до обновления для тренировки с id={event_id}: {res_users}')
                seconds = 0

                delta = len(sorted_dict[item]) - participants_count  # разница между текущим списком и квотой участников
                count = 0  # счетчик числа задвинутых в конец очереди участников
                for i, obj in enumerate(sorted_dict[item]):
                    if i < participants_count:  # работаем сначала с основным списком
                        # Теперь смотрим, прошли ли 12 часов у пользователя с момента записи им на тренировку
                        if obj.modified_at.replace(tzinfo=None) <= rep_dedl_for_individ:
                            if (obj.paid_check is None and obj.payment_confirmed is None) \
                                    or (obj.paid_check is not None and obj.payment_confirmed is False):
                                # Если это не рассылка уведомлений, то обновляем очередь
                                if notify is False and len(sorted_dict[item]) > participants_count:
                                    if count < delta:  # обновляем времена только у тех, кто на самом верху списка
                                        seconds += 1
                                        update_datetime = now + timedelta(seconds=seconds)
                                        update_datetime = update_datetime.replace(tzinfo=None)
                                        obj.paid_check, obj.payment_confirmed, obj.modified_at = (
                                            None, None, update_datetime
                                        )
                                        count += 1
                                        # await logger.critical(f'обновлен created_at пользователя {obj.user.tg_username} по тренировке с id={event_id}, для него установлено значение created_at={obj.created_at}')
                                objects_to_update.append(obj)
                    else:
                        if notify is False:
                            obj.modified_at = now - timedelta(seconds=len(sorted_dict[item]) - i)
                            objects_to_update.append(obj)
                            # await logger.critical(f'обновлен created_at РЕЗЕРВНОГО пользователя {obj.user.tg_username} по тренировке с id={event_id}, для него установлено значение created_at={obj.created_at}')
                if len(sorted_dict[item]) > participants_count and notify is False:  # если список превышает квоту
                    new_sorted_dct = sorted(sorted_dict[item], key=lambda x: x.modified_at.replace(tzinfo=None))[
                                     :participants_count]
                    log_sorted_dct_ = [(_item.user.tg_username, _item.modified_at) for _item in new_sorted_dct]
                    # await logger.critical(f'Новый отсортированный усеченный список после обновления по тренировке с id = {event_id}: {log_sorted_dct_}')
                    for _obj in new_sorted_dct:
                        if _obj in reserv_list:  # and _obj.user.receive_notifications is True:
                            text = (
                                f'️⚡️ ️⚡️ <b>ВАЖНАЯ ИНФОРМАЦИЯ</b>\n'
                                f'Уважаемый участник, вы перемещены из резерва в основной список.\n'
                                f'<b><i>Сведения о тренировке</i></b>:\n'
                                f'<b>Дисциплина</b>: <i>{_obj.event.training_type}</i>\n'
                                f'{_obj.event.event_text}'
                            )
                            reper_dedline = reper_dedline_definiton(real_dedline=_obj.event.payment_dedline,
                                                                    now=now,
                                                                    event_datetime=_obj.event.event_datetime)
                            text += (f'\n\n<b><i>🔆ВАЖНО!</i></b>\n'
                                     f'Теперь Вам необходимо оплатить до <b><i>{reper_dedline[0]}</i></b>, '
                                     f'иначе Вы переместитесь в конец очереди')
                            await bot.send_message(chat_id=_obj.user.tg_id, text=text, parse_mode='HTML')
                            # await logger.critical(f'Пользователь {_obj.user.tg_username} получил уведомление о переходе из резерва по тренировке с id={event_id} следующего содержания: {text}')
                            # Если у пользователя отключены уведомления, то рассылаем информацию админам
                            # elif _obj in reserv_list: # and _obj.user.receive_notifications is False:
                            text = (
                                f'ВНИМАНИЕ админам❗️\nПользователь с никнеймом '
                                f'@{_obj.user.tg_username} перешел из резерва в основной список. '
                                f'Ему было выслано уведомление, что ему необходимо внести оплату в течение 12 часов.'
                                f'\n<b>Данные тренировки</b>\n\n'
                                f'<b>Дисциплина</b>: <i>{_obj.event.training_type}</i>\n'
                                f'{_obj.event.event_text}'
                            )
                            for tg_id in user_cache:
                                if user_cache[tg_id].admin_permissions is True:
                                    admin_tg_id = user_cache[tg_id].tg_id
                                    await bot.send_message(chat_id=admin_tg_id, text=text, parse_mode='HTML')

            if objects_to_update and notify is False:
                await EventUser.bulk_update(objects_to_update, ['paid_check', 'payment_confirmed', 'created_at'])
                await logger.info('Очередь участников изменена успешно')
                return
            # Если сюда в том числе передается конкретное id тренировки, то срабатывает рассылка уведомлений
            elif objects_to_update and notify is True:
                errors = 0
                for obj in objects_to_update:
                    # if obj.user.receive_notifications is True:  # Если пользователь включил уведомления
                    # Если пользователю ещё не высылалось уведомление и у него через час наступит дедлайн
                    # if (obj.notify_is_sended is False and
                    #         obj.created_at.replace(tzinfo=None) <= rep_dedl_for_individ):
                    try:
                        text = (
                            f'❗❗❗ ВАЖНАЯ ИНФОРМАЦИЯ ДЛЯ ВАС ❗❗❗\n'
                            f'Напоминаем, что необходимо внести оплату за тренировку, иначе через час(❗) есть риск оказаться в конце очереди при соответствующем превышении квоты.\n'
                            f'<b><i>Сведения о тренировке</i></b>:\n'
                            f'<b>Дисциплина</b>: <i>{obj.event.training_type}</i>\n'
                            f'{obj.event.event_text}')
                        await bot.send_message(chat_id=obj.user.tg_id, text=text, parse_mode='HTML')
                        # obj.notify_is_sended = True
                        text = (
                            f'🔉ИНФОРМАЦИЯ админам❗️\nДо пользователя с никнеймом '
                            f'@{obj.user.tg_username} дошло автоматическое уведомление о необходимости внести оплату за следующую тренировку:\n'
                            f'\n<b>Данные тренировки</b>\n\n'
                            f'<b>Дисциплина</b>: <i>{obj.event.training_type}</i>\n'
                            f'{obj.event.event_text}\n\n'
                            f'<b>Рекомендуется его об этом лично уведомить, если он игнорирует сообщения бота.</b>'
                        )
                    except Exception as e:
                        errors += 1
                        text = (
                            f'⚡️⚡️ЭКСТРЕННО для админов❗️\nПользователь с никнеймом '
                            f'@{obj.user.tg_username} не получил автоматического уведомления о необходимости внести оплату за следущую тренировку:\n'
                            f'\n<b>Данные тренировки</b>\n\n'
                            f'<b>Дисциплина</b>: <i>{obj.event.training_type}</i>\n'
                            f'{obj.event.event_text}\n\n'
                            f'<b>Оповестите его об этом лично!</b>'
                        )
                        await logger.error(f'Ошибка в рассылке уведомлений пользователю {obj.user.tg_username}: {e}')

                    for tg_id in user_cache:
                        if user_cache[tg_id].admin_permissions is True:
                            admin_tg_id = user_cache[tg_id].tg_id
                            await bot.send_message(chat_id=admin_tg_id, text=text, parse_mode='HTML')
                            # stream_logger.info(f'Ошибка в рассылке уведомений: {e}')
                # await EventUser.bulk_update(objects_to_update, ['notify_is_sended'])
                if errors == 0:
                    await logger.info('Рассылка уведомлений прошла успешно')
                else:
                    await logger.info('Были ошибки в рассылке уведомлений')
            elif len(objects_to_update) < 1 and notify is True:
                await logger.info(
                    'Рассылки уведомлений не состоялось по причине отстуствия соответствующих пользователей')
                text = (f'🔎 Уважаемые админы❗️\n'
                        f'Рассылки уведомлений не состоялось по причине отстуствия соответствующих пользователей')
                for tg_id in user_cache:
                    if user_cache[tg_id].admin_permissions is True:
                        admin_tg_id = user_cache[tg_id].tg_id
                        await bot.send_message(chat_id=admin_tg_id, text=text, parse_mode='HTML')

    except DoesNotExist as e:
        await logger.error(f'DoesNotExist in check_pyment_dedline: {e}')
        # stream_logger.info(f'DoesNotExist: {e}')
    except DBConnectionError as e:
        await logger.error(f'DBConnectionError in check_pyment_dedline: {e}')
        # stream_logger.info(f'DBConnectionError: {e}')
    except Exception as e:
        await logger.error(f'Иная Ошибка в check_pyment_dedline : {e}')
        # stream_logger.error(f'on_schedule_update: {e}')





async def test_for_sch(tst=None, bot=None, user_cache=None):
    try:
        if tst:
            Statistic.filter(user_id=210, training_type='🏐 Волейбол').update(visit_count=2, star_count=1)
            data = {
                # '🏐 Волейбол': ['@gh0street', '@ttuisee', '@motirevskiy', '@alfiya_mf',
                #                   '@FDR162', '@RinoStyle63', '@KhakimovaGuzelya', '@ILMIR131169',
                #                   '@azalka011', '@ruben_mta', '@Rustambagautdinov'],
                #     '🏀 Баскетбол': ['@DFogell', '@dima_nikolaev', '@ya_elen', '@lipatnorm', '@lvnnnrtch'],
                '🏸 Бадминтон': ['@yoai2024', '@Anton_271084']}
            # now = datetime.now() - timedelta(days=55)
            # not_found_usernames = dict()
            # event_user_lst = []
            # for k in data:
            #     event = await Event.create(training_type=k, participants_count=100, created_at=now,
            #                               payment_dedline=now, event_datetime=now)

            #     users_id = []
            #     not_found_usernames[k] = []
            #     for tg_name in data[k]:
            #         tg_name = tg_name.replace('@', '').strip()
            #         user = await User.filter(tg_username=tg_name).all()
            #         if user:
            #             users_id.append(user[0].id)
            #             event_user = await EventUser.create(user=user[0], event=event)
            #             event_user_lst.append(event_user)
            #         else:
            #             not_found_usernames[k].append(tg_name)
            #     stars = ','.join(map(lambda x: str(x), users_id))
            #     event.stars = stars
            #     await event.save()
            # await delete_events(model_event_users=event_user_lst, bot=bot)
            # logger.critical(f'не найденные юзеры: {not_found_usernames}')
            # logger.critical(f'ручное обновление статичстки прошло успешно')

            # for item in stat:
            #     await logger.critical(f'({item.training_type}, {item.user_id}, {item.user.tg_username}, {item.star_count}, {item.visit_count})')

            # event_users = await EventUser.filter(event__training_type='⚽️ Футбол', user__tg_username='joraso').prefetch_related('user').all()
            # event_users[0].created_at = datetime.now() - timedelta(days=55)
            # await event_users[0].save()
            # await Event.filter(training_type='⚽️ Футбол').update(payment_dedline=datetime.now() - timedelta(days=55))
            # event_user = await EventUser.filter(event__training_type='⚽️ Футбол').prefetch_related('user', 'event').all()
            # await logger.critical(f'дата деделайга футбола: {event_user[0].event.payment_dedline}')
            # await logger.critical(f'тип тренировки: {event_user[0].event.training_type}')
            # for item in event_user:
            #     await logger.critical(f'участгник {item.user.tg_name}, {item.created_at}')

            # Симуляция создания тренровки и записи на нее
            # await Event.filter(training_type='⚽️ Футбол').update(

            #     created_at = datetime.now()-timedelta(days=56),
            #     payment_dedline = datetime.now()-timedelta(days=56),
            #     event_datetime  = datetime.now()+timedelta(days=6),
            #     participants_count = 3,

            # )
            # event = await Event.all().order_by('-id')

            # for i in [3,10,32,35,36,38]:
            #     if i>32:
            #         await EventUser.create(event=event[0], user_id=i, created_at=datetime.now()-timedelta(days=14)+timedelta(hours=i))
            #     else:
            #         await EventUser.create(event=event[0], user_id=i, created_at=datetime.now()-timedelta(days=14)+timedelta(hours=i+40))
            # _date = ('211|Liliya_Bakhteeva', '33|KhBA716', '32|SaitBakhteev', '26|Rustambagautdinov')
            # ids = (33, 26, 211,  32 )
            # now = datetime.now() - timedelta(days=15)
            # for i, item in enumerate(ids):
            #     await EventUser.create(user_id=item, created_at = now+timedelta(seconds=i), event_id=118)
        else:
            # await Event.filter(id==116).update(created_at=now, )
            # now = datetime.now().replace(tzinfo=None)

            # evt = await Event.get(id=117)
            # await logger.critical(f'Меньше ли деделайн чем сейчас: {evt.payment_dedline < now}')
            # await logger.critical(f'Больше ли дата проведения чем сейчас: {evt.event_datetime > now}')

            # await check_payment_dedline(user_cache=user_cache, notify=False, bot = bot)
            pass
            # await check_payment_dedline(bot=bot)
    except Exception as e:
        logger.error(f'Ошибка в test_for_sch: {e}')

# stars_dict_getter()
