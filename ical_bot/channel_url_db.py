import pickle
from pathlib import Path
from typing import Optional
import logging


logger = logging.getLogger("ical_bot")

class ChannelUrlDb:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

        self.records: dict[int, str] = {}
        if db_path.is_file():
            self.records = self.load()
            logger.info(f"Loaded {len(self.records)} records from file")

    def load(self):
        """Load existing records from a pickle file"""
        data: bytes = self.db_path.read_bytes()
        return pickle.loads(data)

    def dump(self):
        """Write records to a pickle file"""
        data: bytes = pickle.dumps(self.records)
        self.db_path.write_bytes(data)

    def set_record(self, channel: int, url: str):
        """Sets a record in the database"""
        self.records[channel] = url
        self.dump()

    def get_record(self, channel: int) -> Optional[str]:
        """Gets a record from the database, or returns None is it's not there"""
        if channel in self.records:
            return self.records[channel]
        else:
            return None

    @property
    def channels(self):
        return list(self.records.keys())

    @property
    def urls(self):
        return list(self.records.values())

    @property
    def items(self):
        return [(chan, url) for (chan, url) in self.records.items()]
