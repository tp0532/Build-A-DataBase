import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hashindex import HashIndex  # noqa: E402
from main import execute  # noqa: E402
from store import Store  # noqa: E402

class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "data.db")
        self.clock = FakeClock()
        self.open()

    def tearDown(self):
        self.s.close()
        self.dir.cleanup()

    def open(self):
        self.s = Store(self.path, clock=self.clock)

    def reopen(self):
        self.s.close()
        self.open()

    def run_cmd(self, line):
        return execute(self.s, line)

class TestHashIndex(unittest.TestCase):
    def test_set_get_overwrite_delete(self):
        h = HashIndex()
        h.set("a", 1)
        h.set("a", 2)
        self.assertEqual(h.get("a"), 2)
        self.assertEqual(len(h), 1)
        self.assertTrue(h.delete("a"))
        self.assertFalse(h.delete("a"))

    def test_resize_keeps_all_keys(self):
        h = HashIndex()
        for i in range(1000):
            h.set("k%d" % i, i)
        self.assertEqual(len(h), 1000)
        self.assertEqual(h.get("k777"), 777)

class TestBasics(StoreTestCase):
    def test_data_file_created(self):
        self.assertTrue(os.path.exists(self.path))

    def test_set_get_overwrite(self):
        self.assertEqual(self.run_cmd("SET a 1"), ["OK"])
        self.run_cmd("SET a 2")
        self.assertEqual(self.run_cmd("GET a"), ["2"])

    def test_value_with_spaces(self):
        self.run_cmd("SET a hello big world")
        self.assertEqual(self.run_cmd("GET a"), ["hello big world"])

    def test_nonexistent_get(self):
        self.assertEqual(self.run_cmd("GET nope"), ["(nil)"])

    def test_del_exists(self):
        self.run_cmd("SET a 1")
        self.assertEqual(self.run_cmd("EXISTS a"), ["1"])
        self.assertEqual(self.run_cmd("DEL a"), ["1"])
        self.assertEqual(self.run_cmd("EXISTS a"), ["0"])
        self.assertEqual(self.run_cmd("DEL a"), ["0"])

    def test_mset_mget(self):
        self.run_cmd("MSET a 1 b 2")
        self.assertEqual(self.run_cmd("MGET a b c"), ["1", "2", "(nil)"])

    def test_range(self):
        self.run_cmd("MSET a 1 b 2 c 3 d 4")
        self.assertEqual(self.run_cmd("RANGE b c"), ["b", "c"])

    def test_incr_decr(self):
        self.assertEqual(self.run_cmd("INCR n"), ["1"])
        self.assertEqual(self.run_cmd("INCR n"), ["2"])
        self.assertEqual(self.run_cmd("DECR n"), ["1"])
        self.run_cmd("SET s abc")
        with self.assertRaises(Exception):
            self.run_cmd("INCR s")

    def test_flushdb(self):
        self.run_cmd("MSET a 1 b 2")
        self.run_cmd("FLUSHDB")
        self.assertEqual(self.run_cmd("GET a"), ["(nil)"])
        self.assertEqual(self.run_cmd("RANGE a z"), [])

    def test_unknown_command(self):
        with self.assertRaises(Exception):
            self.run_cmd("BOGUS")

class TestTTL(StoreTestCase):
    def test_ttl_and_expiry(self):
        self.run_cmd("SET a 1")
        self.assertEqual(self.run_cmd("TTL a"), ["-1"])
        self.assertEqual(self.run_cmd("EXPIRE a 10"), ["1"])
        self.assertEqual(self.run_cmd("TTL a"), ["10"])
        self.clock.now += 4
        self.assertEqual(self.run_cmd("TTL a"), ["6"])
        self.clock.now += 7
        self.assertEqual(self.run_cmd("GET a"), ["(nil)"])
        self.assertEqual(self.run_cmd("TTL a"), ["-2"])

    def test_expire_missing_key(self):
        self.assertEqual(self.run_cmd("EXPIRE nope 5"), ["0"])

    def test_ttl_survives_restart(self):
        self.run_cmd("SET a 1")
        self.run_cmd("EXPIRE a 10")
        self.reopen()
        self.assertEqual(self.run_cmd("TTL a"), ["10"])

    def test_set_clears_ttl(self):
        self.run_cmd("SET a 1")
        self.run_cmd("EXPIRE a 10")
        self.run_cmd("SET a 2")
        self.assertEqual(self.run_cmd("TTL a"), ["-1"])

class TestStructures(StoreTestCase):
    def test_hashes(self):
        self.assertEqual(self.run_cmd("HSET h f v"), ["1"])
        self.assertEqual(self.run_cmd("HSET h f v2"), ["0"])
        self.run_cmd("HSET h g w")
        self.assertEqual(self.run_cmd("HGET h f"), ["v2"])
        self.assertEqual(self.run_cmd("HGET h zz"), ["(nil)"])
        self.assertEqual(self.run_cmd("HGETALL h"), ["f", "v2", "g", "w"])

    def test_lists(self):
        self.assertEqual(self.run_cmd("RPUSH l a"), ["1"])
        self.run_cmd("RPUSH l b")
        self.assertEqual(self.run_cmd("LPUSH l z"), ["3"])
        self.assertEqual(self.run_cmd("LRANGE l 0 -1"), ["z", "a", "b"])
        self.assertEqual(self.run_cmd("LRANGE l 1 1"), ["a"])
        self.assertEqual(self.run_cmd("LRANGE l 5 9"), [])
