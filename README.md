# Build-A-DataBase
For CSCE 4350 Assignment

# Simple Key-Value Store

An append-only key-value store with a STDIN/STDOUT command interface created for the database assignment.

## Run

    python3 main.py
## Test

    python3 -m unittest discover -s tests -v

## Design

- `hashindex.py` – custom hash table (FNV-1a, separate chaining, auto-resize). No built-in dict/map is used for the index.
- `store.py` – command engine. Every mutation is appended to `data.db` as one JSON line and fsync'd immediately. On startup the log is replayed to rebuild state (last write wins). TTLs are logged as absolute timestamps so they survive restarts.
- `main.py` – CLI parser.
- Transactions buffer log records until `COMMIT`, `ABORT` restores an in-memory snapshot.

## Commands

SET, GET, DEL, EXISTS, MSET, MGET, EXPIRE, TTL, RANGE, BEGIN, COMMIT, ABORT,
HSET, HGET, LPUSH, RPUSH, LRANGE, INCR, DECR, FLUSHDB, EXIT
