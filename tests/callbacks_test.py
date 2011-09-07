import tests
import unittest
from nose.plugins.skip import SkipTest

import pyperry
from pyperry import errors
from pyperry import callbacks
from pyperry.callbacks import Callback, CallbackManager

# Testing of CallbackManager
#
class CallbackManagerTestCase(unittest.TestCase):
    pass

class CallbackManagerInitTestCase(CallbackManagerTestCase):

    def test_sets_callbacks(self):
        """should set callbacks attribute to empty dict"""
        m = CallbackManager()
        self.assertTrue(hasattr(m, 'callbacks'))
        self.assertEqual(m.callbacks, {})

    def test_constructs_from_instance(self):
        """should construct copy when instance passed"""
        m = CallbackManager()
        m.callbacks['foo'] = 'bar'
        m2 = CallbackManager(m)

        self.assertEqual(m.callbacks, m2.callbacks)

        m.callbacks['foo'] = 'baz'

        self.assertEqual(m2.callbacks['foo'], 'bar')

    def test_requires_callback_manager_type(self):
        """should error on bad instance param"""
        self.assertRaises(errors.ConfigurationError, CallbackManager, 2)

class CallbackManagerRegisterMethod(CallbackManagerTestCase):

    def test_registers_callback_by_type(self):
        """should create key from type pointing to list containing callback"""
        m = CallbackManager()
        cb = callbacks.before_load(lambda: 1)

        m.register(cb)
        self.assertEqual(
                m.callbacks[callbacks.before_load],
                [cb] )

class CallbackManagerTriggerMethod(CallbackManagerTestCase):

    def test_trigger_callbacks_of_specified_type(self):
        """should trigger each registered callback"""
        m = CallbackManager()
        i = []
        def call(arg): arg.append(1)
        cb = callbacks.before_save(call)

        m.register(cb)
        m.register(cb)

        m.trigger(callbacks.before_save, i)

        self.assertEqual(len(i), 2)




# Testing of Callback and subclasses
#
class CallbacksTestCase(unittest.TestCase):
    pass

class CallbackInitMethodTestCase(CallbacksTestCase):

    def setUp(self):
        super(CallbackInitMethodTestCase, self).setUp()
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

class CallbackCallMethodTestCase(CallbacksTestCase):

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

