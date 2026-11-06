_INITIAL_BUCKETS = 16
_MAX_LOAD = 0.75

def _hash(key):
    """FNV-1a 32-bit hash of a string."""
    h = 2166136261
    for byte in key.encode("utf-8"):
        h ^= byte
        h = (h * 16777619) & 0xFFFFFFFF
    return h
    
class HashIndex:
    def __init__(self):
        self._buckets = [[] for _ in range(_INITIAL_BUCKETS)]
        self._size = 0

    def __len__(self):
        return self._size
    def _find(self, key):
        """Return (bucket, position) where position is -1 if absent."""
        bucket = self._buckets[_hash(key) % len(self._buckets)]
        for i, entry in enumerate(bucket):
            if entry[0] == key:
                return bucket, i
        return bucket, -1

    def get(self, key, default=None):
        bucket, i = self._find(key)
        return bucket[i][1] if i >= 0 else default
        
    def has(self, key):
        return self._find(key)[1] >= 0

    def set(self, key, value):
        """Insert or overwrite a key."""
        bucket, i = self._find(key)
        if i >= 0:
            bucket[i] = (key, value)
            return
        bucket.append((key, value))
        self._size += 1
        if self._size / len(self._buckets) > _MAX_LOAD:
            self._resize(len(self._buckets) * 2)

    def delete(self, key):
        """Remove a key. Returns True if it existed."""
        bucket, i = self._find(key)
        if i < 0:
            return False
        bucket.pop(i)
        self._size -= 1
        return True
