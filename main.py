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

