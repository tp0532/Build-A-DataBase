import sys

from store import Store, StoreError


def _int(text):
    try:
        return int(text)
    except ValueError as exc:
        raise StoreError("value is not an integer") from exc


def _need(args, n, usage):
    if len(args) != n:
        raise StoreError("usage: " + usage)


def _rest(line, parts, skip):
    """Return the remainder of `line` after `skip` whitespace-separated tokens."""
    if len(parts) <= skip:
        return ""
    return line.strip().split(None, skip)[skip]

def execute(store, line):
    """Run one command line; return a list of output lines, or None to exit."""
    parts = line.split()
    if not parts:
        return []
    cmd, args = parts[0].upper(), parts[1:]

    if cmd == "EXIT":
        return None
    if cmd == "SET":
        if len(args) < 2:
            raise StoreError("usage: SET key value")
        # Value is everything after the key, so it may contain spaces.
        return [store.set(args[0], _rest(line, parts, 2))]
    if cmd == "GET":
        _need(args, 1, "GET key")
        return [store.get(args[0])]
    if cmd == "DEL":
        _need(args, 1, "DEL key")
        return [store.delete(args[0])]
    if cmd == "EXISTS":
        _need(args, 1, "EXISTS key")
        return [store.exists(args[0])]
    if cmd == "MSET":
        if len(args) < 2 or len(args) % 2:
            raise StoreError("usage: MSET k1 v1 [k2 v2 ...]")
        return [store.mset(list(zip(args[0::2], args[1::2])))]
    if cmd == "MGET":
        if not args:
            raise StoreError("usage: MGET k1 [k2 ...]")
        return store.mget(args)
    if cmd == "EXPIRE":
        _need(args, 2, "EXPIRE key seconds")
        return [store.expire(args[0], _int(args[1]))]
    if cmd == "TTL":
        _need(args, 1, "TTL key")
        return [store.ttl(args[0])]
    if cmd == "RANGE":
        _need(args, 2, "RANGE start end")
        return store.range(args[0], args[1])
    if cmd == "BEGIN":
        return [store.begin()]
    if cmd == "COMMIT":
        return [store.commit()]
    if cmd == "ABORT":
        return [store.abort()]
    if cmd == "HSET":
        if len(args) < 3:
            raise StoreError("usage: HSET hash key value")
        return [store.hset(args[0], args[1], _rest(line, parts, 3))]
    if cmd == "HGET":
        _need(args, 2, "HGET hash key")
        return [store.hget(args[0], args[1])]
    if cmd == "HGETALL":
        _need(args, 1, "HGETALL hash")
        return store.hgetall(args[0])
    if cmd in ("LPUSH", "RPUSH"):
        if len(args) < 2:
            raise StoreError("usage: %s key value" % cmd)
        value = _rest(line, parts, 2)
        fn = store.lpush if cmd == "LPUSH" else store.rpush
        return [fn(args[0], value)]
    if cmd == "LRANGE":
        _need(args, 3, "LRANGE key start stop")
        return store.lrange(args[0], _int(args[1]), _int(args[2]))
    if cmd == "INCR":
        _need(args, 1, "INCR key")
        return [store.incr(args[0])]
    if cmd == "DECR":
        _need(args, 1, "DECR key")
        return [store.decr(args[0])]
    if cmd == "FLUSHDB":
        return [store.flushdb()]
    raise StoreError("unknown command '%s'" % cmd)
