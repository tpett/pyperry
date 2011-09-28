import tests
import unittest
from nose.plugins.skip import SkipTest

import pyperry
from pyperry import errors
from pyperry import caching

# Testing of caching module
#
class CachingTestCase(unittest.TestCase):
    pass

class CachingDefaults(CachingTestCase):

    def test_enabled(self):
        self.assertEqual(caching.enabled, True)

    def test_registry(self):
        self.assertEqual(type(caching.registry), list)

class CachingReset(CachingTestCase):

    def test_calls_each_registry_item(self):
        self.called = False
        def foo():
            self.called = True

        caching.register(foo)
        self.assertEqual(self.called, False)
        caching.reset()
        self.assertEqual(self.called, True)



