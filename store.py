import copy
import json
import os
import time

from hashindex import HashIndex

OK = "OK"
NIL = "(nil)"
EMPTY = "(empty)"

class StoreError(Exception):
    """Raised for user-visible command errors."""


class Store:
    """Persistent store. Every mutation is appended to the log immediately."""

    def __init__(self, path="data.db", clock=time.time):
        self.path = path
        self._clock = clock
        self.data = HashIndex()  # key -> str | HashIndex | list
        self.expiry = HashIndex()  # key -> absolute expiry (epoch seconds)
        self._tx_log = None  # buffered log records during a transaction
        self._tx_snapshot = None
        # Create the file up front so it exists even before the first write.
        open(self.path, "a", encoding="utf-8").close()
        self._replay()
        self._log_file = open(self.path, "a", encoding="utf-8")
    def _replay(self):
        """Rebuild in-memory state by re-applying every logged record."""
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue  # ignore a torn final line after a crash
                self._apply(record)

    def _persist(self, record):
        """Append a record and force it to disk (or buffer it in a tx)."""
        if self._tx_log is not None:
            self._tx_log.append(record)
            return
        self._write_records([record])
