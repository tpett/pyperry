import tests
import unittest
from nose.plugins.skip import SkipTest

import pyperry
from pyperry import errors
from pyperry.scope import Scope

import tests.fixtures.association_models

class ScopeTestCase(unittest.TestCase):
    pass

class InitMethodTestCase(ScopeTestCase):

    def test_takes_dict_or_callable(self):
        """should accept a dict or callable as first argument"""
        scope1 = Scope({ 'where': 'foo' })
        self.assertEqual(scope1.finder_options, { 'where': 'foo' })

        call = lambda(cls): cls.where('foo')
        scope2 = Scope(call)
        self.assertEqual(scope2.callable, call)

    def test_accepts_keywords(self):
        """should accept keywords and merge with dict"""
        scope = Scope(where='bar', limit=2)
        self.assertEqual(scope.finder_options, {'where': 'bar', 'limit': 2})

        scope = Scope({ 'where': 'foo' }, limit=1)
        self.assertEqual(scope.finder_options, {'where': 'foo', 'limit': 1})

    def test_sets_name(self):
        """should set `__name__` to None or __name__ of callable if present"""
        scope = Scope()
        self.assertEqual(scope.__name__, None)

        @Scope
        def scope2(cls): pass

        self.assertEqual(scope2.__name__, 'scope2')

    def test_sets_model(self):
        """should set `model` to None"""
        scope = Scope()
        self.assertEqual(scope.model, None)

    def test_errors_on_bad_argument(self):
        """should raise exception on bad arguments"""
        self.assertRaises(Exception, Scope, 'foo')
        self.assertRaises(Exception, Scope, 1)
        self.assertRaises(Exception, Scope, [])
        self.assertRaises(Exception, Scope, tuple())

class DescriptorTestCase(ScopeTestCase):

    def setUp(self):
        super(DescriptorTestCase, self).setUp()
        self.scope = Scope()
        class Test(object):
            foo = self.scope
        self.Test = Test

    def test_sets_model_to_owner(self):
        """should set `model` to owner when instance is None"""
        self.assertEqual(self.Test.foo.model, self.Test)

    def test_returns_self(self):
        """should return self"""
        self.assertEqual(self.Test.foo, self.scope)

    def test_raises_when_called_from_instance(self):
        """should raise exception when called from instance"""
        test = self.Test()
        self.assertRaises(Exception, getattr, test, 'foo')

class CallableTestCase(ScopeTestCase):

    def setUp(self):
        super(CallableTestCase, self).setUp()

        class Test(object):
            @Scope
            def foo(cls, *args, **kwargs):
                self.last_call = (args, kwargs)
                return 123

        self.Test = Test

    def test_delegates_callable(self):
        """should delegate to `callable` when present"""
        foo = self.Test.foo

        self.assertEqual(foo(), 123)

        foo(1, 2, 3, foo='bar')
        self.assertEqual(((1, 2, 3), dict(foo='bar')), self.last_call)

    def test_calls_finder_options(self):
        """should use apply_finder_options to apply dicts"""
        class Test(pyperry.base.Base):
            foo = Scope(where='foo')

        rel = Test.foo()

        self.assertEqual(type(rel), pyperry.relation.Relation)
        self.assertEqual(rel.query(), { 'where': ['foo'] })

