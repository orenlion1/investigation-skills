import unittest

from src.cache_loader import load


class LoadTest(unittest.TestCase):
    def test_returns_each_key(self):
        self.assertEqual(load(["a"]), {"a": None})


if __name__ == "__main__":
    unittest.main()
