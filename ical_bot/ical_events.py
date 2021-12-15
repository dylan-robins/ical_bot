import datetime
from dataclasses import dataclass

from dateutil import tz
from icalevents.icalevents import events

UTC_TZ = tz.gettz("UTC")
CET_TZ = tz.gettz("CET")


@dataclass
class Event:
    summary: str
    location: str
    start: datetime.datetime
    end: datetime.datetime


def day_with_offset(day=datetime.date.today(), offset: int = 0):
    return day + datetime.timedelta(days=offset)


def get_day_events(url: str, day: datetime.date):
    es = events(url=url, start=day_with_offset(day, 0), end=day_with_offset(day, 1))
    for e in sorted(es, key=lambda e: e.start):
        start_time_utc = e.start.replace(tzinfo=UTC_TZ)
        end_time_utc = e.end.replace(tzinfo=UTC_TZ)
        yield Event(
            summary=e.summary,
            location=e.location,
            start=start_time_utc.astimezone(CET_TZ),
            end=end_time_utc.astimezone(CET_TZ),
        )
