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
