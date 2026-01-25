"""
Модель EventUsers. Данная модель предназначена для того, чтобы заносить в БД заявившихся участников на
определенные тренировки. Поле paid_check может принимать следующие значения:
- пустое NULL означает, что пользователь не обозначил оплату за тренировку;
- текст 'I payed' означает, что пользователь оплатил, но чек об оплате не загрузил;
- адрес чека об оплате, загруженный пользователем
"""
from tortoise.models import Model
from tortoise import fields
from pytz import timezone

from config.constants import SEASON_INDEX

class User(Model):
    id = fields.IntField(primary_key=True)
    tg_id = fields.BigIntField(unique=True)
    tg_username = fields.CharField(max_length=64, null=True)
    tg_name = fields.CharField(max_length=150, null=True)
    created_at = fields.DatetimeField(auto_now_add=True, timezone=timezone('Europe/Moscow'))
    admin_permissions = fields.BooleanField(default=False)
    receive_notifications = fields.BooleanField(default=False)  # получать или не получать уведомления

    # На какие типы тренировок должны приходить уведомления
    subscription = fields.CharField(null=True, max_length=64)

    def __str__(self):
        return self.tg_username


class Event(Model):  # модель создаваемых тренирвок
    id = fields.IntField(primary_key=True)
    training_type = fields.CharField(max_length=30, null=True)
    created_at = fields.DatetimeField()
    payment_dedline = fields.DatetimeField(null=True)
    event_datetime = fields.DatetimeField()  # запланированная дата и время тренировки
    participants_count = fields.IntField(default=18)  # число участников тренировки
    event_text = fields.TextField(null=True)
    boss = fields.ForeignKeyField('models.User', related_name='boss', null=True, on_delete=fields.NO_ACTION)
    user = fields.ManyToManyField('models.User', related_name="participants", through='EventUser')
    stars = fields.TextField(null=True)

    def __str__(self):
        return f'event_id = {self.id}'


class EventUser(Model):
    id = fields.IntField(primary_key=True)
    event = fields.ForeignKeyField('models.Event', on_delete=fields.CASCADE)
    user = fields.ForeignKeyField('models.User', on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True, timezone=timezone('Europe/Moscow'))
    modified_at = fields.DatetimeField(auto_now_add=True, timezone=timezone('Europe/Moscow'))
    individual_dedline = fields.DatetimeField(auto_now_add=True, timezone=timezone('Europe/Moscow'))

    # Два поля по уведомлению об оплате: состояния уведомления, время жизни ✔️
    paid_check = fields.BooleanField(null=True)
    paid_check_dedline = fields.DatetimeField(null=True, timezone=timezone('Europe/Moscow'))

    payment_confirmed = fields.BooleanField(default=None, null=True)  # подтверждение оплаты, доступное только админу

    # Последняя дата и время отправки напоминания об оплате
    last_payment_notify = fields.DatetimeField(null=True, timezone=timezone('Europe/Moscow'))

    # По идее это поле должно быть bool и по умолчанию быть False, но из-за ограничений SQLite оставляем как есть
    friend = fields.CharField(max_length=50, null=True, on_delete=fields.NO_ACTION)

    class Meta:
        table = 'EventUser'
        unique_together = ('event', 'user')

    async def upload_check(self):
        self.paid_check = 'paid'
        await self.save()

    async def verify_payment(self, confirm=True):
        if confirm:
            self.payment_confirmed = True
        elif confirm is None:  # если верификация отменена (например нечаянно нажал на подтверждение)
            self.payment_confirmed = None
        else:
            self.payment_confirmed = False
        await self.save()


# Класс для сохранения шаблонов по созданию тренировок
class Template(Model):
    id = fields.IntField(primary_key=True)
    modified_at = fields.DatetimeField()
    text = fields.TextField()


class Statistic(Model):
    season_index = fields.IntField(default=SEASON_INDEX[0])  # индекс начала летоисчисления каждого сезона
    created_at = fields.DatetimeField(auto_now_add=True, timezone=timezone('Europe/Moscow'))
    modifed_at = fields.DatetimeField(auto_now_add=True, timezone=timezone('Europe/Moscow'))
    user = fields.ForeignKeyField('models.User', on_delete=fields.NO_ACTION)
    training_type = fields.CharField(max_length=30)
    visit_count = fields.IntField()
    star_count = fields.IntField()
    likes = fields.IntField()


# Голосование
class Voting(Model):
    question = fields.TextField()
    