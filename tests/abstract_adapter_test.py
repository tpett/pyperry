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

    def execute(self, **kwargs):
        DummyAdapter.stack_tracer.append('execute')
        return super(DummyAdapter, self).execute(**kwargs)


class AdapterBaseTestCase(unittest.TestCase):

    def setUp(self):
        self.adapter = AbstractAdapter({})

    def tearDown(self):
        DummyAdapter.stack_tracer = []

##
# Initialize
#
class InitTestCase(AdapterBaseTestCase):

    def test_copy_construcotr(self):
        adapter = AbstractAdapter({ 'foo': 1 }, middlewares=[1], processors=[2])
        copy = AbstractAdapter(adapter)
        self.assertEqual(copy.config['foo'], 1)
        self.assertEqual(copy.middlewares, [1])
        self.assertEqual(copy.processors, [2])

    def test_accepts_dict(self):
        """accepts a dictionary to initialize"""
        adapter = AbstractAdapter({ 'foo': 'bar' })
        self.assertEqual(adapter.config['foo'], 'bar')

    def test_delayed_exec(self):
        """should delay execution of callables"""
        foo_val = 'BAD'
        adapter = AbstractAdapter({'foo': lambda: foo_val })
        foo_val = 'GOOD'
        self.assertEqual(adapter.config['foo'], 'GOOD')

        foo_val = 'BAD'
        def foo():
            return foo_val
        adapter = AbstractAdapter({'foo': foo })
        foo_val = 'GOOD'
        self.assertEqual(adapter.config['foo'], 'GOOD')

    def test_delayed_exec_arity(self):
        """should not execute callables if ther arity is greater than 1"""
        adapter = AbstractAdapter({'foo': lambda x: 'bar' * x})
        self.assertEqual(adapter.config['foo'](3), 'barbarbar')

        def foo(x):
            return 'bar' * x
        adapter = AbstractAdapter({'foo': foo})
        self.assertEqual(adapter.config['foo'](3), 'barbarbar')

    def test_allows_kwarg_config(self):
        """should allow config values through kwargs"""
        adapter = AbstractAdapter(foo='bar', middlewares=[1])

        self.assertEqual(adapter.config['foo'], 'bar')
        self.assertEqual(adapter.middlewares, [1])

    def test_init_middleware(self):
        """middlewares should include ModelBridge by default"""
        adapter = AbstractAdapter({})
        self.assertEqual(adapter.middlewares, [(ModelBridge, {})])

    def test_init_middleware_with_kwargs(self):
        """middelwares should be initialized to the middlewares key word
        argument if provided"""
        adapter = AbstractAdapter({}, middlewares=[1])
        self.assertEqual(adapter.middlewares, [1])

    def test_init_processors(self):
        """processors should be initialized as an empty list"""
        adapter = AbstractAdapter({})
        self.assertEqual(adapter.processors, [])


    def test_init_processors_with_kwargs(self):
        """
        processors should be initialized to the processors key word argument
        """
        adapter = AbstractAdapter({}, processors='foo')
        self.assertEqual(adapter.processors, 'foo')

    def test_declares_stack(self):
        """should declate a _stack attr"""
        adapter = AbstractAdapter({})
        self.assertTrue(hasattr(adapter, '_stack'))
        self.assertEquals(adapter._stack, None)

    def test_appends_middlewares_option(self):
        """should append _middlewares option to middlewares"""
        middlewares = [(MiddlewareA, {})]
        adapter = AbstractAdapter({ '_middlewares': middlewares })
        self.assertEquals(adapter.middlewares,
                AbstractAdapter({}).middlewares + middlewares)

    def test_appends_processors_option(self):
        """should append _processors option to the processors"""
        processors = ['foo']
        _processors = ['bar']
        adapter = AbstractAdapter({'_processors': _processors},
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
        adapter = DummyAdapter({},
                middlewares=[(MiddlewareA, {}), (MiddlewareB, {})],
                processors=[(ProcessorA, {}), (ProcessorB, {})])
        result = adapter(mode='read')
        self.assertEqual(DummyAdapter.stack_tracer,
                ['pa', 'pb', 'a', 'b', 'execute', 'read'])
        self.assertEqual(result, [])

##
# __call__ method
#
class CallMethodTestCase(AdapterBaseTestCase):

    def setUp(self):
        self.adapter = DummyAdapter({})

    def test_kwargs(self):
        """should pass keywords on"""
        val = self.adapter(foo=True, mode='read')
        self.assertEqual(val, ['FOO'])

    def test_iterable(self):
        """should return an iterable"""
        val = self.adapter(mode='read')
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
        self.adapter = CallModeAdapter({})

    def test_mode_in_kwargs(self):
        """should include the adapter mode in the kwargs"""
        kwargs = self.adapter(mode='write')
        self.assertEqual(kwargs['mode'], 'write')

    def test_allows_mode_override(self):
        """should allow adapter to be called with a different mode than the
        adapter itself"""
        kwargs = self.adapter(mode='delete')
        self.assertEqual(kwargs['mode'], 'delete')

class MergeMethodTestCase(AdapterBaseTestCase):

    def test_exists(self):
        """should be a callable attribute"""
        self.assertTrue(hasattr(AbstractAdapter, 'merge'))
        self.assertTrue(callable(AbstractAdapter.merge))

    def test_takes_instance_of_adapter(self):
        a1 = AbstractAdapter({ 'foo': 1 })
        a2 = AbstractAdapter({ 'bar': 2 })
        a3 = a1.merge(a2)

        self.assertEqual(a1.config['foo'], 1)
        self.assertEqual(a2.config['bar'], 2)
        self.assertEqual(a3.config['foo'], 1)
        self.assertEqual(a3.config['bar'], 2)

    def test_takes_dict(self):
        a1 = AbstractAdapter({ 'foo': 1 }, middlewares=[1], processors=[2])
        a3 = a1.merge({'bar': 2})

        self.assertEqual(a3.config['foo'], 1)
        self.assertEqual(a3.config['bar'], 2)
        self.assertEqual(a3.middlewares, [1])
        self.assertEqual(a3.processors, [2])

    def test_takes_keywords(self):
        a1 = AbstractAdapter({ 'foo': 1 })
        a3 = a1.merge(bar=2)

        self.assertEqual(a3.config['foo'], 1)
        self.assertEqual(a3.config['bar'], 2)

    def test_allow_middlewares_and_processors_through_kwargs(self):
        a1 = AbstractAdapter({ 'foo': 1 }, middlewares=[1], processors=[2])
        a3 = a1.merge(bar='2', middlewares=[1], processors=[2])

        self.assertEqual(a3.config['foo'], 1)
        self.assertEqual(a3.config['bar'], '2')
        self.assertEqual(a3.middlewares, [1])
        self.assertEqual(a3.processors, [2])


class ExecuteMethodTestCase(AdapterBaseTestCase):

    def setUp(self):
        class Test(AbstractAdapter):
            last_called = None
            def read(self, **kwargs):
                self.last_called = 'read'
                return 'foo'
            def write(self, **kwargs):
                self.last_called = 'write'
            def delete(self, **kwargs):
                self.last_called = 'delete'
        self.adapter = Test({})

    def test_mode_option(self):
        """should call the method matching the mode given in the kwargs"""
        for mode in ['read', 'write', 'delete']:
            self.adapter.execute(mode=mode)
            self.assertEqual(self.adapter.last_called, mode)

    def test_return_value(self):
        """should return the same value as the method it calls"""
        result = self.adapter.execute(mode='read')
        self.assertEqual(result, 'foo')


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
        adapter = AbstractAdapter({})
        self.assertEqual(socket.getdefaulttimeout(), None)

    def test_global_default(self):
        """
        should use global default instead of 10 second default if the global
        default is not None
        """
        socket.setdefaulttimeout(3)
        adapter = AbstractAdapter({})
        self.assertEqual(socket.getdefaulttimeout(), 3)

    def test_config(self):
        """socket timeout should be configurable"""
        adapter = AbstractAdapter({'timeout': 5})
        self.assertEqual(socket.getdefaulttimeout(), 5)

