
"""test_utils.py -- Unit tests for Generic classes"""

import unittest

from pin import utils

class TestDList(unittest.TestCase):
    """Test the dictionary list."""

    def setUp(self):
        self.data = utils.DList({'asdf': 15, 'mid': 'dill', 'arst': 1})

    def test_first(self):
        self.assertEqual(self.data[0], 15)

    def test_last(self):
        self.assertEqual(self.data[-1], 1)

    def test_middle(self):
        self.assertEqual(self.data['mid'], 'dill')

    def test_set(self):
        cop = utils.DList(self.data)
        cop[1] = 7
        self.assertEqual(cop['mid'], 7)

    def test_before(self):
        self.assertEqual(self.data.before('mid'), 15)

    def test_after(self):
        self.assertEqual(self.data.after('mid'), 1)

