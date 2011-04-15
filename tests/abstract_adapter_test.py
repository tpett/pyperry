import tests
import unittest
import pyperry
from pyperry.adapter.abstract_adapter import AbstractAdapter
from pyperry import errors

class MiddlewareA(object):
    def __init__(self, next, options={}):
        self.next = next
        self.options = options

    def __call__(self, **kwargs):
        DummyAdapter.stack_tracer.append('a')
        return self.next(**kwargs)

class MiddlewareB(object):
    def __init__(self, next, options={}):
        self.next = next
        self.options = options

    def __call__(self, **kwargs):
        DummyAdapter.stack_tracer.append('b')
        return self.next(**kwargs)

class DummyAdapter(AbstractAdapter):

    # Just used for a few tests testing the adapter stack
    stack_tracer = []

    def read(self, **kwargs):
        DummyAdapter.stack_tracer.append('read')

        if kwargs.has_key('foo'):
            return [ "FOO" ]
        else:
            return []


class AdapterBaseTestCase(unittest.TestCase):

    def setUp(self):
        self.adapter = AbstractAdapter({}, mode='read')

    def tearDown(self):
        DummyAdapter.stack_tracer = []

##
# Initialize
#
class InitTestCase(AdapterBaseTestCase):

    def test_accepts_dict(self):
        """accepts a dictionary to initialize"""
        adapter = AbstractAdapter({ 'foo': 'bar' }, mode='read')
        self.assertEqual(adapter.config.foo, 'bar')

    def test_requires_mode_keyword(self):
        """requires a valid mode keyword"""
        self.assertRaises(errors.ConfigurationError, AbstractAdapter, {})
        self.assertRaises(errors.ConfigurationError,
                AbstractAdapter, {}, mode='poop')

    def test_delayed_exec(self):
        """should delay execution of lambdas"""
        foo_val = 'BAD'
        adapter = AbstractAdapter({'foo': lambda: foo_val }, mode='read')
        foo_val = 'GOOD'
        self.assertEqual(adapter.config.foo, 'GOOD')

    def test_sets_inits_middleware(self):
        """middleware should be set to empty list or the keyword if passed"""
        adapter = AbstractAdapter({}, mode='read', middlewares=[1])
        self.assertEqual(adapter.middlewares, [1])

        adapter = AbstractAdapter({}, mode='read')
        self.assertEqual(adapter.middlewares, [])

    def test_declares_stack(self):
        """should declate a _stack attr"""
        adapter = AbstractAdapter({}, mode='read')
        self.assertTrue(hasattr(adapter, '_stack'))
        self.assertEquals(adapter._stack, None)

    def test_appends_middlewares_option(self):
        """should append _middlewares option to middlewares"""
        middlewares = [(MiddlewareA, {})]
        adapter = AbstractAdapter({ '_middlewares': middlewares },
            mode='read')
        self.assertEquals(adapter.middlewares, middlewares)


##
# Define NotImplemnted for read, write, and delete
#
class IsAbstractTestCase(AdapterBaseTestCase):

    def test_read_abstract(self):
        """read method should raise NotImplementedError"""
        self.assertRaises(NotImplementedError, self.adapter.read)

    def test_write_abstract(self):
        """read method should raise NotImplementedError"""
        self.assertRaises(NotImplementedError, self.adapter.write)

##
# Define stack method that returns a callable stack of middlewares / adapter
#
class StackMethodTestCase(AdapterBaseTestCase):

    def test_stack_returns_callable(self):
        """should return a callable"""
        self.assertTrue(hasattr(self.adapter.stack, '__call__'))

    def test_stack_called_in_order(self):
        """use the DummyAdapter to test middleware call order"""
        adapter = DummyAdapter({}, mode='read',
                middlewares=[(MiddlewareA, {}), (MiddlewareB, {})])
        result = adapter()
        self.assertEqual(DummyAdapter.stack_tracer, ['a', 'b', 'read'])
        self.assertEqual(result, [])

##
# __call__ method
#
class CallMethodTestCase(AdapterBaseTestCase):

    def setUp(self):
        self.adapter = DummyAdapter({}, mode='read')

    def test_kwargs(self):
        """should pass keywords on"""
        val = self.adapter(foo=True)
        self.assertEqual(val, ['FOO'])

    def test_iterable(self):
        """should return an iterable"""
        val = self.adapter()
        self.assertTrue( hasattr(val, '__iter__') )

    def test_broken_middleware(self):
        """should raise excp if middleware returns a non iterable"""
        class BrokenMiddleware(object):
            def __init__(self, next, options={}): self.next = next
            def __call__(self): pass
        self.adapter.middlewares = [(BrokenMiddleware, {})]

        self.assertEqual(self.adapter.stack.__class__.__name__,
                'BrokenMiddleware')

        self.assertRaises(errors.BrokenAdapterStack, self.adapter)

##
# reset method
#
# should clear the _stack
class ResetMethodTestCase(AdapterBaseTestCase):

    def test_should_remove_value_from_stack(self):
        """should clear out _stack var"""
        self.adapter.stack
        self.assertTrue(self.adapter._stack)
        self.adapter.reset()
        self.assertFalse(self.adapter._stack)

