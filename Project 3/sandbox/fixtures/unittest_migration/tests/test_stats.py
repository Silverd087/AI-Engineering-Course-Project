import unittest

from calc.stats import mean, median, spread


class StatsTests(unittest.TestCase):
    def setUp(self):
        self.data = [1, 2, 3, 4]

    def test_mean(self):
        self.assertEquals(mean(self.data), 2.5)

    def test_median_even_count(self):
        self.assertEquals(median(self.data), 2.5)

    def test_median_odd_count(self):
        self.assertEquals(median([3, 1, 2]), 2)

    def test_spread(self):
        self.assertEquals(spread(self.data), 3)

    def test_mean_of_empty_raises(self):
        with self.assertRaises(ValueError):
            mean([])