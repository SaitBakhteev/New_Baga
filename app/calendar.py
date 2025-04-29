from pydantic.types import conlist
from pydantic.fields import Field
from datetime import datetime
from aiogram_calendar import SimpleCalendar, CalendarLabels


class NewCalendarLabels(CalendarLabels):
    days_of_week: conlist(str, max_length=7, min_length=7) = [
        "Пн",
        "Вт",
        "Ср",
        "Чт",
        "Пт",
        "Сб",
        "Вс",
    ]
    months: conlist(str, max_length=12, min_length=12) = [
        "Янв",
        "Фев",
        "Мар",
        "Апр",
        "Maй",
        "Июн",
        "Июл",
        "Ауг",
        "Сен",
        "Окт",
        "Ноя",
        "Дек",
    ]
    cancel_caption: str = Field(
        default="Отмена", description="Caption for Cancel button"
    )
    today_caption: str = Field(
        default="Сегодня", description="Caption for Cancel button"
    )


class NewCalendar(SimpleCalendar):
    def __init__(self):
        super().__init__()
        self._labels = NewCalendarLabels()

    async def process_day_select(self, data, query):
        date = datetime(int(data.year), int(data.month), int(data.day))
        if self.min_date and self.min_date > date:
            await query.answer(
                f'Дата должна быть позже {self.min_date.strftime("%d.%m.%Y")}',
                show_alert=self.show_alerts,
            )
            return False, None
        elif self.max_date and self.max_date < date:
            await query.answer(
                f'Дата должна быть раньше {self.max_date.strftime("%d.%m.%Y")}',
                show_alert=self.show_alerts,

            )
            return False, None
        await query.message.delete_reply_markup()  # removing inline keyboard
        return True, date


class NewServiceCalendar(NewCalendar):
    pass
