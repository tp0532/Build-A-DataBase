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
