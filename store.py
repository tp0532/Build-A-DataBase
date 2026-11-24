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
    def _purge_if_expired(self, key):
        """Lazily delete a key whose TTL has passed. Logs the deletion."""
        deadline = self.expiry.get(key)
        if deadline is not None and self._clock() >= deadline:
            self._do(["DEL", key])

    def _live(self, key):
        self._purge_if_expired(key)
        return self.data.has(key)
    def set(self, key, value):
        self._do(["SET", key, value])
        return OK

    def get(self, key):
        if not self._live(key):
            return NIL
        value = self.data.get(key)
        if not isinstance(value, str):
            raise StoreError("WRONGTYPE")
        return value

    def delete(self, key):
        existed = self._live(key)
        if existed:
            self._do(["DEL", key])
        return "1" if existed else "0"

    def exists(self, key):
        return "1" if self._live(key) else "0"

    def mset(self, pairs):
        for key, value in pairs:
            self._do(["SET", key, value])
        return OK

    def mget(self, keys):
        out = []
        for k in keys:
            if self._live(k) and isinstance(self.data.get(k), str):
                out.append(self.data.get(k))
            else:
                out.append(NIL)
        return out

    def expire(self, key, seconds):
        if not self._live(key):
            return "0"
        self._do(["EXPIREAT", key, self._clock() + seconds])
        return "1"

    def ttl(self, key):
        if not self._live(key):
            return "-2"
        deadline = self.expiry.get(key)
        if deadline is None:
            return "-1"
        return str(max(0, int(round(deadline - self._clock()))))

    def range(self, start, end):
        keys = [k for k in self.data.keys() if self._live(k)]
        keys = sorted(k for k in keys if start <= k <= end)
        return keys
    def hset(self, name, field, value):
        self._purge_if_expired(name)
        existing = self.data.get(name)
        if existing is not None and not isinstance(existing, HashIndex):
            raise StoreError("WRONGTYPE")
        is_new = not (isinstance(existing, HashIndex) and existing.has(field))
        self._do(["HSET", name, field, value])
        return "1" if is_new else "0"

    def hget(self, name, field):
        if not self._live(name):
            return NIL
        h = self.data.get(name)
        if not isinstance(h, HashIndex):
            raise StoreError("WRONGTYPE")
        return h.get(field, NIL)

    def hgetall(self, name):
        if not self._live(name):
            return []
        h = self.data.get(name)
        if not isinstance(h, HashIndex):
            raise StoreError("WRONGTYPE")
        out = []
        for field, value in sorted(h.items()):
            out.extend([field, value])
        return out
