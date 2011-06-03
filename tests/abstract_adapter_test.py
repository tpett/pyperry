import tests
import unittest
from nose.plugins.skip import SkipTest
import socket
import pyperry
from pyperry.adapter.abstract_adapter import AbstractAdapter
from pyperry import errors
from pyperry.middlewares.model_bridge import ModelBridge

class MiddlewareTestBase(object):
    def __init__(self, next, options={}):
        self.next = next
        self.options = options
    def __call__(self, **kwargs):
        DummyAdapter.stack_tracer.append(self.trace_value)
        return self.next(**kwargs)

class MiddlewareA(MiddlewareTestBase): trace_value = 'a'
class MiddlewareB(MiddlewareTestBase): trace_value = 'b'
class ProcessorA(MiddlewareTestBase): trace_value = 'pa'
class ProcessorB(MiddlewareTestBase): trace_value = 'pb'

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

    def test_init_middleware(self):
        """middlewares should include ModelBridge by default"""
        adapter = AbstractAdapter({}, mode='read')
        self.assertEqual(adapter.middlewares, [(ModelBridge, {})])

    def test_init_middleware_with_kwargs(self):
        """middelwares should be initialized to the middlewares key word
        argument if provided"""
        adapter = AbstractAdapter({}, mode='read', middlewares=[1])
        self.assertEqual(adapter.middlewares, [1])

    def test_init_processors(self):
        """processors should be initialized as an empty list"""
        adapter = AbstractAdapter({}, mode='read')
        self.assertEqual(adapter.processors, [])


    def test_init_processors_with_kwargs(self):
        """
        processors should be initialized to the processors key word argument
        """
        adapter = AbstractAdapter({}, mode='read', processors='foo')
        self.assertEqual(adapter.processors, 'foo')

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
        self.assertEquals(adapter.middlewares,
                AbstractAdapter({}, mode='read').middlewares + middlewares)

    def test_appends_processors_option(self):
        """should append _processors option to the processors"""
        processors = ['foo']
        _processors = ['bar']
        adapter = AbstractAdapter({'_processors': _processors}, mode='read',
                                  processors=processors)
        self.assertEqual(adapter.processors, processors + _processors)


##
# Define NotImplemnted for read, write, and delete
#
class IsAbstractTestCase(AdapterBaseTestCase):

    def test_read_abstract(self):
        """read method should raise NotImplementedError"""
        self.assertRaises(NotImplementedError, self.adapter.read)

    def test_write_abstract(self):
        """write method should raise NotImplementedError"""
        self.assertRaises(NotImplementedError, self.adapter.write)

    def test_delete_abstract(self):
        """delete method should raise NotImplementedError"""
        self.assertRaises(NotImplementedError, self.adapter.delete)

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
                middlewares=[(MiddlewareA, {}), (MiddlewareB, {})],
                processors=[(ProcessorA, {}), (ProcessorB, {})])
        result = adapter()
        self.assertEqual(DummyAdapter.stack_tracer,
                ['pa', 'pb', 'a', 'b', 'read'])
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
            def __call__(self, **kwargs): pass
        self.adapter.middlewares = [(BrokenMiddleware, {})]

        self.assertEqual(self.adapter.stack.__class__.__name__,
                'BrokenMiddleware')

        self.assertRaises(errors.BrokenAdapterStack, self.adapter, mode='read')

    def test_broken_processor(self):
        """should raise exception if processor returns a non-iterable"""
        class BrokenProcessor(object):
            def __init__(self, next, options={}): self.next = next
            def __call__(self, **kwargs): pass
        self.adapter.processors = [(BrokenProcessor, {})]

        self.assertEqual(self.adapter.stack.__class__.__name__,
                'BrokenProcessor')

        self.assertRaises(errors.BrokenAdapterStack, self.adapter, mode='read')

class CallModeTestCase(AdapterBaseTestCase):

    def setUp(self):
        class CallModeAdapter(AbstractAdapter):
            def stack(self, **kwargs): return kwargs
        self.adapter = CallModeAdapter({}, mode='write')

    def test_mode_in_kwargs(self):
        """should include the adapter mode in the kwargs"""
        kwargs = self.adapter()
        self.assertEqual(kwargs['mode'], 'write')

    def test_allows_mode_override(self):
        """should allow adapter to be called with a different mode than the
        adapter itself"""
        kwargs = self.adapter(mode='delete')
        self.assertEqual(kwargs['mode'], 'delete')


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

##
# socket timeouts
#
class SocketTimeoutTestCase(AdapterBaseTestCase):

    def test_default(self):
        """default timeout should be 10 seconds"""
        socket.setdefaulttimeout(None)
        adapter = AbstractAdapter({}, mode='read')
        self.assertEqual(socket.getdefaulttimeout(), 10)

    def test_global_default(self):
        """
        should use global default instead of 10 second default if the global
        default is not None
        """
        socket.setdefaulttimeout(3)
        adapter = AbstractAdapter({}, mode='read')
        self.assertEqual(socket.getdefaulttimeout(), 3)

    def test_config(self):
        """socket timeout should be configurable"""
        adapter = AbstractAdapter({'timeout': 5}, mode='read')
        self.assertEqual(socket.getdefaulttimeout(), 5)

