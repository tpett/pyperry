import tests
import unittest
from nose.plugins.skip import SkipTest

import pyperry
from pyperry import errors
from pyperry.callbacks import _Callback as Callback

class CallbacksTestCase(unittest.TestCase):
    pass

class InitMethodTestCase(CallbacksTestCase):

    def setUp(self):
        super(InitMethodTestCase, self).setUp()
        self.method = lambda(self): 'foo'
        self.callback = Callback(self.method)

    def test_takes_callable(self):
        """should require callable and set it to callback attr"""
        self.assertEqual(self.callback.callback, self.method)

    def test_sets_action(self):
        """should set action attr to None"""
        self.assertTrue(hasattr(self.callback, 'action'))
        self.assertEqual(self.callback.action, None)

    def test_sets_when(self):
        """should set when attr to None"""
        self.assertTrue(hasattr(self.callback, 'when'))
        self.assertEqual(self.callback.when, None)

    def test_ensures_callable(self):
        """should ensure callback is callable"""
        self.assertRaises(errors.ConfigurationError, Callback, 3)

class CallMethodTestCase(CallbacksTestCase):

    def test_calls_callable(self):
        """should call the callable and return result"""
        call = Callback(lambda(self): 'foo')
        self.assertTrue(callable(call))
        self.assertEqual(call('bar'), 'foo')

    def test_passes_arg_through(self):
        """should pass arg on through"""
        call = Callback(lambda(self): self)
        self.assertEqual(call('foo'), 'foo')

class CallbackChildTest(CallbacksTestCase):
    """
    Tests are added dynamically below
    """
    pass

def set_callback_dynamic_tests():
    for when in ['before', 'after']:
        for action in ['load', 'create', 'update', 'save', 'destroy']:
            name = '%s_%s' % (when, action)

            def method(self):
                """
                Dynamically generated test
                """

                self.assertTrue(hasattr(pyperry.callbacks, name))

                cls = getattr(pyperry.callbacks, name)
                instance = cls(lambda(self): 'bar')

                self.assertEqual(instance.when, when)
                self.assertEqual(instance.action, action)

            method.__name__ = 'test_%s' % name

            if not hasattr(CallbackChildTest, method.__name__):
                setattr(CallbackChildTest, method.__name__, method)

set_callback_dynamic_tests()

