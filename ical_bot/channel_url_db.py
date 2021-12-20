from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Iterable, Optional

logger = logging.getLogger("ical_bot")


class ICalRole(Enum):
    event_source = auto()
    exclusion_list = auto()

    @staticmethod
    def from_string(val: Optional[str]) -> Optional[ICalRole]:
        # default value:
        if val is "" or val is None:
            return ICalRole.event_source
        # else parse known values
        elif val == "event_source":
            return ICalRole.event_source
        elif val == "exclusion_list":
            return ICalRole.exclusion_list
        else:
            return None


@dataclass
class ICalRecord:
    channel_id: int
    url: str
    role: ICalRole


class ChannelUrlDb:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

        self.records: list[ICalRecord] = []
        if db_path.is_file():
            self.records = self.load()
            logger.info(f"Loaded {len(self.records)} records from file")

    def load(self) -> list[ICalRecord]:
        """Load existing records from a pickle file"""
        data: bytes = self.db_path.read_bytes()
        return pickle.loads(data)

    def dump(self) -> None:
        """Write records to a pickle file"""
        data: bytes = pickle.dumps(self.records)
        self.db_path.write_bytes(data)

    def add_record(self, record: ICalRecord) -> bool:
        """Sets a record in the database"""
        records_iter = self.get_records_by_channel(record.channel_id, record.role)

        if len(list(records_iter)) > 0:
            logger.warn(f"Record {record} was already present in database")
            return False

        self.records.append(record)
        self.dump()
        return True

    def get_records_by_channel(
        self, channel_id: int, role: Optional[ICalRole] = None
    ) -> Iterable[ICalRecord]:
        """Gets the calendars of a given role for a channel"""

        if role:
            f: Callable[[ICalRecord], bool] = (
                lambda r: r.channel_id == channel_id and r.role == role
            )
        else:
            f: Callable[[ICalRecord], bool] = lambda r: r.channel_id == channel_id

        yield from (record for record in self.records if f(record))

    def remove_record(self, rec: ICalRecord):
        """Gets the calendars of a given role for a channel"""
        self.records.remove(rec)
        self.dump()

    @property
    def channels(self) -> list[int]:
        return [rec.channel_id for rec in self.records]

    @property
    def sources(self) -> list[str]:
        return [rec.url for rec in self.records if rec.role == ICalRole.event_source]
