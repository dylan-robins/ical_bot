from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from typing import Optional

from dateutil import tz
from icalevents.icalevents import events

logger = logging.getLogger("ical_bot")

UTC_TZ = tz.gettz("UTC")
CET_TZ = tz.gettz("CET")


@dataclass
class Event:
    summary: str
    location: str
    start: datetime.datetime
    end: datetime.datetime

    def intersects_event(self, other: Event) -> bool:
        """Returns True if the current event intersects with 'other'"""
        return self.start <= other.end and self.end >= other.start

    def contains_day(self, day: datetime.date) -> bool:
        """Returns True if the day is contained in the event"""
        return self.start.date() <= day and self.end.date() >= day


def day_with_offset(day: Optional[datetime.date] = None, offset: int = 0):
    if day is None:
        day = datetime.date.today()

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
