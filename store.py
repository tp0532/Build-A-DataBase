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

    def _write_records(self, records):
        for record in records:
            self._log_file.write(json.dumps(record) + "\n")
        self._log_file.flush()
        os.fsync(self._log_file.fileno())

    def close(self):
        if self._tx_log is not None:
            self.abort()
        self._log_file.close()

    def _apply(self, rec):
        op = rec[0]
        if op == "SET":
            self.data.set(rec[1], rec[2])
            self.expiry.delete(rec[1])
        elif op == "DEL":
            self.data.delete(rec[1])
            self.expiry.delete(rec[1])
        elif op == "EXPIREAT":
            self.expiry.set(rec[1], rec[2])
        elif op == "HSET":
            h = self.data.get(rec[1])
            if not isinstance(h, HashIndex):
                h = HashIndex()
                self.data.set(rec[1], h)
            h.set(rec[2], rec[3])
        elif op in ("LPUSH", "RPUSH"):
            lst = self.data.get(rec[1])
            if not isinstance(lst, list):
                lst = []
                self.data.set(rec[1], lst)
            if op == "LPUSH":
                lst.insert(0, rec[2])
            else:
                lst.append(rec[2])
        elif op == "FLUSHDB":
            self.data.clear()
            self.expiry.clear()

    def _do(self, record):
        """Apply a record to memory and log it."""
        self._apply(record)
        self._persist(record)
