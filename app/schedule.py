import logging
import asyncio

from datetime import datetime, timedelta, time

from app.database.models import Event, EventUser, Statistic, Voting

from config.log_config import setup_logger
from config.constants import SEASON_INDEX

from app.operations.often_ops_and_classes import SendMessages, set_individual_dedline

logger, stream_logger = setup_logger(__name__), logging.getLogger(__name__)

stars_dict = dict()  # словарь рейтинга звезд, распределенный по типам тренировок
general_raiting = []  # список общего рейтинга
likes_rating = []  # рейтинг симпатий


# Класс для сканирования и перемещения в конец очереди
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
            await self._reserve_lst_ops(is_ex_move_to_end_ptcps)
            if len(self._update_list) > 0:
                await EventUser.bulk_update(self._update_list,
                                            ['modified_at', 'individual_dedline', 'paid_check'])

    # Метод, который извлекает в отдельный список участников основного с просроченным дедлайном
    def _extract_from_main_lst(self):
        seconds = 0
        for obj in self._event_user[:self._participants_count]:
            if len(self._update_list) == self._reserv_count:
                break
            if obj.individual_dedline.replace(tzinfo=None) <= self._now and obj.payment_confirmed is not True:
                # Обновляем время
                # --------------
                seconds += 1
                modified_at = self._now + timedelta(seconds=seconds)
                obj.modified_at = modified_at.replace(tzinfo=None)

                # Обновляем paid_check
                # --------------
                if obj.paid_check:
                    obj.paid_check = False

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
            transfer_lst_from_reserve = self._event_user[begin_idx:end_idx]
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
            f'<b>Дисциплина</b>: <i>{self._event_user[0].event.training_type}</i>\n'
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
            try:
                if obj.payment_confirmed is not True:
                    ind_dedline = obj.individual_dedline.replace(tzinfo=None)
                    last_payment_notify = obj.last_payment_notify
                    if last_payment_notify:
                        last_payment_notify = last_payment_notify.replace(tzinfo=None)

                        # Прошло ли 5 часов с последнего уведомления
                        is_5h_from_las = last_payment_notify + timedelta(hours=5) <= self._now
                    else:
                        is_5h_from_las = True

                    if ind_dedline <= self._before_1_hours and is_5h_from_las:
                        last_payment_notify = self._now
                        obj.last_payment_notify = last_payment_notify
                        self._update_list.append(obj)
            except Exception as e:
                await logger.error(f'Ошибка в SendReminders execute: {e}')

        if len(self._update_list) > 0:
            await self._send_msg()
            await EventUser.bulk_update(self._update_list, ['last_payment_notify'])

    async def _send_msg(self):
        text = (
            f'❗❗❗ ВАЖНАЯ ИНФОРМАЦИЯ ДЛЯ ВАС ❗❗❗\n'
            f'Посмотрите свой дедлайн оплаты ⏳ в записи на тренировку. По его истечении '
            f'Вы можете оказаться в конце очереди при наличии резерва.\n'
            f'Поэтому, настоятельно рекомендуется оплатить, <u><i>если Вы ещё не вылетели в резерв</i></u>\n'
            f'При этом ❗ВАЖНО❗ после оплаты <u><i>лично уведомить об этом АДМИНА</i></u>, '
            f'иначе он может не успеть подтвердить оплату\n'
            f'\n<b><i>Сведения о тренировке</i></b>:\n'
            f'<b>Дисциплина</b>: <i>{self._event_user[0].event.training_type}</i>\n'
            f'{self._event_user[0].event.event_text}'
        )
        _recepient_list = [item.user.tg_id for item in self._update_list]
        await SendMessages.to_several_receivers(tg_ids=_recepient_list, text=text)


# Главная исполняющая функция по классам MoveToEnd и SendReminders
async def main_func(is_move=True):
    now = datetime.now()

    # Устанавливаем двухминутные границы для 1 и 4 часов, внутри которых планировщик работать не должен
    time_begin_1, time_end_1 = time(hour=0, minute=58), time(hour=1, minute=2)
    time_begin_4, time_end_4 = time(hour=3, minute=58), time(hour=4, minute=2)
    _condition_1 = now.time() >= time_begin_1 and now.time() <= time_end_1
    _condition_4 = now.time() >= time_begin_4 and now.time() <= time_end_4

    if _condition_1 or _condition_4:
        return
    else:
        reper_h = now if is_move else now + timedelta(hours=1)
        event_user = await (
                EventUser.filter(event__payment_dedline__lte=reper_h, event__event_datetime__gt=now).
                select_related('event', 'user').order_by('event_id')
            )
        evs = set([item.event.id for item in event_user])
        print(f'evs = {evs}')
        if event_user:
            event_user_dct = _dct_form(event_user)
            if is_move:
                for k in event_user_dct:
                    move_to_end = MoveToEnd(event_user=event_user_dct[k], now=now)
                    await move_to_end.execute()
            else:
                for k in event_user_dct:
                    send_rmnd = SendReminders(event_user=event_user_dct[k], now=now)
                    await send_rmnd.execute()


# БЛОК РАБОТЫ СО СТАТИСТИКОЙ
# ==========================
class _LocalStatObj():
    '''Этот класс для того, чтобы создавать локальные экземпляры внутри списков общего рейтинга'''
    def __init__(self, tg_name, tg_username, star_count=None, text=None, likes=None):
        self.tg_name, self.tg_username = tg_name, tg_username
        self.star_count, self.text = star_count, text  # это для общего рейтинга звезд
        self.likes = likes  # это для общего рейтинга симпатий (лайков)


class StatisticOps():
    def __init__(self, event_user, now):
        _count = event_user[0].event.participants_count
        self._event_user = event_user[:_count]
        self._train_type = event_user[0].event.training_type
        self._update_list, self._create_list = [], []
        self._now = now

    async def execute(self):
        await self._load_stat()
        await self._extract_stars()
        self._lists_formation()
        if self._update_list:
            await Statistic.bulk_update(self._update_list, ['modifed_at', 'star_count', 'visit_count', 'likes'])
        if self._create_list:
            await Statistic.bulk_create(self._create_list)

    async def _load_stat(self):
        _user_ids = [item.user.id for item in self._event_user]
        stat = await Statistic.filter(
            user__id__in=_user_ids,
            training_type=self._train_type,
            season_index=SEASON_INDEX[0]
        ).prefetch_related('user').all()
        self._stat = stat

    async def _extract_stars(self):
        '''Функция извлекает звезд и лидера голосования. По голосованию обработка идет по следующему алгоритму:
            - находим по функции max объект с максимальным количеством лайков
            - формируем список лайков, соответствующих максимуму
            - смотрим количество записей этого списка
            - если максимум один, то тогда и присуждаем +1 звезду
         '''
        try:
            print(f'stars = {self._event_user[0].event.stars}')
            if self._event_user[0].event.stars != '-':
                _stars = self._event_user[0].event.stars.replace(' ', '').split(',')
                stars_of_event = list(map(lambda x: int(x), _stars))
                self._stars = stars_of_event
            else:
                self._stars = []
            if not all(item.likes==0 for item in self._event_user):  # если было голосование
                obj = max(self._event_user, key=lambda item: item.likes)
                max_count = len([item.likes for item in self._event_user if item.likes == obj.likes])
                training_type = obj.event.training_type
                _datetime = obj.event.event_datetime.strftime('%d.%m %H:%M')
                question = obj.event.question
                if max_count == 1:  # звезду добавляем, если лидер голосования один единственный
                    self._stars.append(obj.user.id)
                    fullname = f'{obj.user.tg_name} @{obj.user.tg_username}'
                    text=('<b>🩷 ИТОГИ ГОЛОСОВАНИЯ 🔥</b>\n\n'
                          f'Лидером голосования ❓"<b><i>{question}</i></b>"❓ прошедшей тренировки '
                          f'(<i>{_datetime}</i>) по дисциплине <b><i>{training_type}</i></b> становится участник '
                          f'<b><i>{fullname}</i></b> 🥳. Ему присуждается звезда 🤩\n\n'
                          f'💥🔥ПОЗДРАВЛЯЕМ!!😍')
                else:
                    text=('<b>🩷 ИТОГИ ГОЛОСОВАНИЯ 🔥</b>\n\n'
                          f'Голосование ❓"<b><i>{question}</i></b>"❓ прошедшей тренировки (<i>{_datetime}</i>) '
                          f'по дисциплине <b><i>{training_type}</i></b> не выявила лидера 🤷🏼‍♂️')
                await Voting.create(question=text, training_type=training_type)
        except Exception as e:
            await logger.error(f'Error on _extract_stars: {e}')

    def _lists_formation(self):
        for item in self._event_user:
            stat = next((_stat for _stat in self._stat if _stat.user.id==item.user.id),
                        None)
            stars_count = self._stars.count(item.user.id)  # сколько раз встречается id пользователя в звездах
            if stat:
                stat.visit_count += 1
                stat.modifed_at = self._now
                stat.likes = stat.likes + item.likes if item.likes is not None else 0
                stat.star_count += stars_count
                self._update_list.append(stat)

            else:
                likes = 0 if item.likes is None else item.likes
                new_stat = Statistic(
                    user=item.user, training_type=self._train_type,
                    visit_count=1, star_count=stars_count, likes=likes,
                    created_at=self._now, modifed_at=self._now
                )
                self._create_list.append(new_stat)

    @classmethod
    async def delete_events(cls, now):
        events_not_finished = await Event.filter(event_datetime__lt=now, is_finished__isnull=True).all()
        if events_not_finished:
            await SendMessages.to_admins_about_non_marked_events(events=events_not_finished)
        await Event.filter(event_datetime__lt=now, stars__isnull=False).delete()

    # Реформирование рейтинга звезд по типам тренировки
    @classmethod
    def _star_rating_by_type(cls, stats:list):
        global stars_dict
        stars_dict.clear()
        for item in stats:
            if item.training_type not in stars_dict:
                stars_dict[item.training_type] = []
            if item.star_count > 0:
                stars_dict[item.training_type].append(item)
        # Сортируем списки в словаре
        for k in stars_dict:
            stars_dict[k] = sorted(stars_dict[k], key=lambda item: item.star_count, reverse=True)

    # Формирование общего рейтинга звезд
    @classmethod
    def _stars_gen_rating_form(cls, stars_dict:dict):
        global general_raiting
        general_raiting.clear()

        users = set()
        for k in stars_dict:
            for item in stars_dict[k]:
                users.add(item.user)

        for _user in users:
            star_count = likes = 0
            text = ''
            for k in stars_dict:
                _user_raiting = next((item for item in stars_dict[k] if item.user.id == _user.id), None)
                if _user_raiting:
                    star_count += _user_raiting.star_count
                    text += str(k)[0]
            _obj = _LocalStatObj(tg_name=_user.tg_name,
                                 tg_username=_user.tg_username,
                                 star_count=star_count,
                                 text=text)
            general_raiting.append(_obj)

        general_raiting = sorted(general_raiting, key=lambda x: x.star_count, reverse=True)

    @classmethod
    def _like_rating_form(cls, stats: list):
        global likes_rating
        likes_rating.clear()

        _like_rating = []  # временный список
        for item in stats:
            if item.likes > 0:
                _like_rating.append(item)

        users = set()
        for item in _like_rating:
            users.add(item.user)

        for user in users:
            likes = 0
            for item in _like_rating:
                if user == item.user:
                    likes += item.likes
            _obj = _LocalStatObj(tg_name=user.tg_name,
                                 tg_username=user.tg_username,
                                 likes=likes)
            likes_rating.append(_obj)

        likes_rating = sorted(likes_rating, key=lambda x: x.likes, reverse=True)

    # Функция пересмотра статистики и формирования рейтинга
    @classmethod
    async def stat_raiting_form(cls):
        stats = await (Statistic.filter(season_index=SEASON_INDEX[0]).
                       prefetch_related('user').all().order_by('training_type'))
        cls._star_rating_by_type(stats)
        cls._stars_gen_rating_form(cls.stars_dict_getter())
        cls._like_rating_form(stats)

    # СПЕЦИАЛЬНЫЕ ГЕТТЕРЫ ДЛЯ ИЗБЕЖАНИЯ ПРОБЛЕМ ОБНУЛЕНИЯ В ДРУГИХ МОДУЛЯХ
    # -------------------------------------------------------------------
    @classmethod
    def stars_dict_getter(cls):
        return stars_dict

    @classmethod
    def general_raiting_getter(cls):
        return general_raiting

    @classmethod
    def likes_raiting_getter(cls):
        return likes_rating


# Формирование словаря из списка EventUser путем распределенных по ключам event_id
def _dct_form(event_user: list) -> dict:
    event_user_dct = dict()
    for item in event_user:
        if item.event.id not in event_user_dct:
            event_user_dct[item.event.id] = []
        event_user_dct[item.event.id].append(item)
    for k in event_user_dct:
        event_user_dct[k] = sorted(event_user_dct[k], key=lambda item: item.modified_at)
    return event_user_dct


# Главная исполняющая функция по работе со статистикой
async def stat_execute_func():
    now = datetime.now()
    event_user = await  EventUser.filter(
        event__event_datetime__lt=now, event__is_finished__isnull=False
    ).prefetch_related('event', 'user').all()
    if event_user:
        event_user_dct = _dct_form(event_user)

        # Исполняем класс StatisticOps
        for k in event_user_dct:
            stat_ops = StatisticOps(event_user=event_user_dct[k], now=now)
            await stat_ops.execute()
    await StatisticOps.delete_events(now)
    await StatisticOps.stat_raiting_form()


# Функция для рассылки уведомлений подписчикам
async def msg_send():
    msg = await Voting.all()
    if len(msg) > 0:
        for item in msg:
            await SendMessages.to_several_subscribers(item.question, item.training_type)
    await Voting.all().delete()

    events = await Event.filter(event_datetime__lt=datetime.now(), question__isnull=False).all()
    for event in events:
        begin_idx, end_idx = event.event_text.find('<b>Адрес зала</b>'), event.event_text.find('<b>Дата тренировки</b>')
        address = event.event_text[begin_idx:end_idx]
        event_dt_txt = event.event_datetime.strftime('%d.%m %H:%M')
        text = (f'<b>ПРОДОЛЖАЕТСЯ ГОЛОСОВАНИЕ 💚</b>\n\n'
                f'<b>Дисциплина</b>: {event.training_type}:\n'
                f'<b>Дата и время прошедшей тренировки</b>: {event_dt_txt}\n'
                f'{address}\n'
                f'<b>Вопрос голосования ❓</b>: <i>{event.question}</i>')
        await SendMessages.to_several_subscribers(text, event.training_type)
