import tests
import unittest
import copy

import pyperry
from pyperry import errors

from tests.fixtures.test_adapter import TestAdapter
import tests.fixtures.association_models

class BaseTestCase(unittest.TestCase):
    pass

##
# Test the interfaces for defining attributes on pyperry.Base
#
class DefineAttributesTestCase(BaseTestCase):

    def test_define_attributes(self):
        """define_attributes should append to the set defined_attributes"""

        class Test(pyperry.Base): pass

        self.assertEqual(len(Test.defined_attributes), 0)

        Test.define_attributes(['id', 'name', 'name'])
        self.assertEqual(len(Test.defined_attributes), 2)

        Test.define_attributes(['foo_id', 'foo_id', 'id'])
        self.assertEqual(len(Test.defined_attributes), 3)

    def test_ignore_dups(self):
        """should ignore duplicate attributes"""
        class Test(pyperry.Base): pass
        Test.attributes('id', 'poop', 'poop')

        self.assertEqual(Test.defined_attributes, set(['id', 'poop']))

    def test_takes_param_list_attributes(self):
        """Should interpret parameter list of attributes and alias method"""
        class Test(pyperry.Base):
            def _config(cls):
                cls.attributes('id', 'name', 'poop')

        self.assertEqual(Test.defined_attributes, set(['id', 'name', 'poop']))

##
# Test the initializer
#
class InitializeTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base): pass
        Test.attributes('id', 'name')
        self.Test = Test

    def test_init_attributes(self):
        """init should set any defined attributes in the provided dict"""
        t = self.Test({'id': 1, 'poop': 'abc'})

        self.assertEqual(t.id, 1)
        self.assertEqual(t.name, None)
        self.assertRaises(AttributeError, t.__getattribute__, 'poop')

    def test_init_sets_new_record_true(self):
        """init should set new_record true by default"""
        t = self.Test({'id': 1})
        self.assertEqual(t.new_record, True)

    def test_should_allow_override_new_record(self):
        """init should take 2nd paramter to set new_record field"""
        t = self.Test({'id': 1}, False)
        self.assertEqual(t.new_record, False)

    def test_init_sets_saved_none(self):
        """init should set saved to None by default"""
        t = self.Test({})
        self.assertEqual(t.saved, None)

    def test_init_errors(self):
        """init should set the errors attribute to any empty dict"""
        t = self.Test({})
        self.assertEqual(t.errors, {})


##
# Test the accessors for defined attributes
#
class AttributeAccessTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base): pass
        Test.attributes('id', 'name')
        self.Test = Test
        self.test = Test(dict(id=1, name='Foo'))

    def test_attribute_getters(self):
        """[] and attribute based getter for defined attributes"""
        test = self.test
        self.assertEqual(test.name, 'Foo')
        self.assertEqual(test['id'], 1)

    def test_attribute_setters(self):
        """[]= and attribute based setter for defined_attributes"""
        test = self.test
        test.id = 2
        test['name'] = 'bar'

        self.assertEqual(test.id, 2)
        self.assertEqual(test['name'], 'bar')

    def test_bad_attribute_access(self):
        """Undefined attributes should raise AttributeError and KeyError"""
        test = self.test

        self.assertRaises(AttributeError, test.__getattr__, 'poop')
        # test.poop = 'foo' should set a new object attr 'poop'
        self.assertRaises(KeyError, test.__getitem__, 'poop')
        self.assertRaises(KeyError, test.__setitem__, 'poop', 'foo')

    def test_getter_shadowing(self):
        """Property method getters should shadow attribute accessors"""
        class Test(pyperry.Base):

            @property
            def foo(self):
                return "purple"

        Test.attributes('foo')
        test = Test({'foo': 1})

        self.assertEqual(test.foo, 'purple')
        self.assertEqual(test['foo'], 1)

    def test_setter_shadowing(self):
        """Property method setters should shadow attribute setters"""
        class Test(pyperry.Base):

            def get_foo(self):
                return self['foo']

            def set_foo(self, val):
                self['foo'] = "Mine"

            foo = property(get_foo, set_foo)
        Test.attributes('foo')

        test = Test({'foo': 1})

        self.assertEqual(test.foo, 1)
        test.foo = 'Test'
        self.assertEqual(test.foo, 'Mine')

##
# Test setting of configure('read') and it merging with superclass configuration
#
class AdapterConfigurationTestCase(BaseTestCase):

    def setUp(self):
        pass

    def test_confiure_read_merge(self):
        """setting read config should merge all dicts up the inheritance tree"""
        class TestBase(pyperry.Base):
            def _config(cls):
                cls.configure('read', poop='smells')

        class Test(TestBase):
            def _config(cls):
                cls.configure('read', foo='bar')

        self.assertEqual(Test.adapter_config['read']['foo'], 'bar')
        self.assertEqual(Test.adapter_config['read']['poop'], 'smells')

        class Test2(Test):
            def _config(cls):
                cls.configure('read', { 'poop': 'stanks' })

        self.assertEqual(Test2.adapter_config['read']['poop'], 'stanks')
        self.assertEqual(Test.adapter_config['read']['poop'], 'smells')

    def test_adapter_required(self):
        """should complain if 'adapter' option not set"""
        from fixtures.test_adapter import TestAdapter
        from pyperry import errors
        class Test(pyperry.Base):
            def _config(cls):
                cls.configure('read', poop='smells')

        self.assertRaises(errors.ConfigurationError, Test.adapter, 'read')

    def test_delayed_exec_configs(self):
        """should delay calling any lambda config values until they are needed"""
        from fixtures.test_adapter import TestAdapter
        class Test(pyperry.Base):
            def _config(cls):
                cls.configure('read', adapter=TestAdapter, foo=lambda: 'barbarbar')

        adapter = Test.adapter('read', )
        self.assertEquals(adapter.config.foo, 'barbarbar')

    def test_unique_adapters(self):
        """adapters changes to child objects should not affect super objects"""
        class Super(pyperry.Base): pass
        Super.configure('read', adapter=TestAdapter, conf='super')

        class Child(Super): pass
        Child.configure('read', adapter=TestAdapter, conf='child')

        super_adapter = Super.adapter('read')
        child_adapter = Child.adapter('read')

        self.assertTrue(super_adapter is not child_adapter)
        self.assertEqual(super_adapter.config.conf, 'super')
        self.assertEqual(child_adapter.config.conf, 'child')

##
# add_middleware method
#
class BaseAddMiddlewareMethodTestCase(BaseTestCase):

    def setUp(self):
        class Middle(object):
            def __init__(self, adapter, options=None):
                self.adapter = adapter

            def __call__(self, **kwargs):
                return self.adapter(**kwargs)
        self.Middle = Middle

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(pyperry.Base.add_middleware.im_self.__name__, 'Base')

    def test_parameters(self):
        """should require 2 params taking an optional 3rd dict / kwargs"""
        class Test(pyperry.Base): pass
        Test.add_middleware('read', self.Middle)
        Test.add_middleware('read', self.Middle, { 'foo': 'bar' })
        Test.add_middleware('read', self.Middle, foo='bar')

    def test_saves_config(self):
        """should append value to adapter_config[type] middlewares option"""
        class Test(pyperry.Base): pass
        Test.add_middleware('read', self.Middle, { 'foo': 'bar' })
        self.assertEqual(Test.adapter_config['read']['_middlewares'],
                [(self.Middle, { 'foo': 'bar' })])
        Test.add_middleware('read', self.Middle, { 'baz': 'boo' })
        self.assertEqual(Test.adapter_config['read']['_middlewares'],
                [
                    (self.Middle, { 'foo': 'bar' }),
                    (self.Middle, { 'baz': 'boo' }) ])

##
# Adapter method
#
class BaseAdapterMethodTestCase(BaseTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(pyperry.Base.adapter.im_self.__name__, 'Base')

    def test_read(self):
        """if exists return adapter described by type"""
        class Test(pyperry.Base): pass
        Test.configure('read', adapter=TestAdapter)
        self.assertEqual(Test.adapter('read').mode, 'read')

        Test.configure('write', adapter=TestAdapter)
        self.assertEqual(Test.adapter('write').mode, 'write')

##
# `setup_model` method should be called after class definition if it is defined
#
class BaseConfigTestCase(BaseTestCase):
    def setUp(self):
        class Foo(pyperry.Base):
            _passed = False

            def _config(cls):
                cls._passed = True
        self.Foo = Foo

    def test_call_config(self):
        """
        should be called if it exists
        should be called with the class as parameter
        """
        self.assertTrue(self.Foo._passed)

    def test_cant_call_after_creation(self):
        """should be obfiscated after class creation"""
        self.assertTrue(not hasattr(self.Foo, '_config'))


class BaseFetchRecordsMethodTestCase(BaseTestCase):

    def test_nil_results(self):
        """should ignore None results"""
        class Test(pyperry.Base):
            def _config(cls):
                cls.attributes('id')
                cls.configure('read', adapter=TestAdapter)
        TestAdapter.data = None
        TestAdapter.count = 3
        result = Test.fetch_records(Test.scoped())
        self.assertEqual(len(result), 0)


class BaseResolveNameMethodTestCase(BaseTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(pyperry.Base.resolve_name.im_self.__name__, 'Base')

    def test_resolves_name(self):
        """should resolve to a list of classes by the same name"""
        class Foo(pyperry.Base):
            pass

        self.assertEqual(pyperry.Base.resolve_name('Foo')[-1], Foo)

    def test_empty_list(self):
        """should return None if class doesn't exist"""
        self.assertEqual(pyperry.Base.resolve_name('ChittyChittyBangBang'), [])

    def test_namespace(self):
        """should parse out namespace to resolve ambiguity"""
        """should return all matches if class name ambiguous"""
        class Article(pyperry.Base):
            pass

        result = pyperry.Base.resolve_name('Article')
        self.assertEqual(result,
                [tests.fixtures.association_models.Article, Article])

        result = pyperry.Base.resolve_name('base_test.Article')
        self.assertEqual(result, [Article])


##
# Scoping methods
#
# Methods for managing the query scope of a model
#
class BaseScopingTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base):
            attributes = ['id']
        Test.configure('read', adapter=TestAdapter)

        self.Test = Test
        TestAdapter.data = { 'id': 1 }
        TestAdapter.count = 3


class BaseRelationMethodTestCase(BaseScopingTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(self.Test.relation.im_self.__name__, 'Test')

    def test_returns_correct_relation(self):
        """should return a new relation for the given model"""
        self.assertEqual(type(self.Test.relation()).__name__, 'Relation')
        self.assertEqual(self.Test.relation().klass, self.Test)

    def test_relation_caching(self):
        """should cache the relation"""
        rel = self.Test.relation()
        self.assertEqual(hash(self.Test.relation()), hash(rel))

    def test_no_relation_subclass_caching(self):
        """should not copy cached relation to subclasses"""
        base_rel = self.Test.relation()
        class Subclass(self.Test): pass
        subclass_rel = Subclass.relation()
        self.assertNotEqual(hash(base_rel), hash(subclass_rel))
        self.assertEqual(subclass_rel.klass, Subclass)


class BaseCurrentScopeMethodTestCase(BaseScopingTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(self.Test.current_scope.im_self.__name__, 'Test')

    def test_returns_correct_relation(self):
        """should return the currently scoped relation if present or None"""
        rel = self.Test.current_scope()
        assert not rel
        scoped = self.Test.relation().clone()
        self.Test._scoped_methods = [scoped]
        self.assertEqual(self.Test.current_scope(), scoped)

class BaseScopedMethodTestCase(BaseScopingTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(self.Test.scoped.im_self.__name__, 'Test')

    def test_return_value(self):
        """
        should return the base relation merged with current_scope if present
        should return a cloned relation if no current_scope
        """
        rel = self.Test.scoped()
        self.assertEqual(type(rel).__name__, 'Relation')
        self.assertNotEqual(hash(self.Test.relation()), hash(rel))

        self.Test._scoped_methods = [ rel.where('foo') ]
        self.assertEqual(self.Test.scoped().params['where'], ['foo'])

class BaseRelationQueryMethodTestCase(BaseScopingTestCase):

    def test_all_query_methods(self):
        """defined query methods on Relation should be accessible from Base"""
        methods = (pyperry.Relation.singular_query_methods +
                pyperry.Relation.plural_query_methods)

        for method in methods:
            result = getattr(self.Test, method)
            self.assertEqual(type(result).__name__, 'instancemethod')

    def test_all_finder_methods(self):
        """test finder methods on Relation accessible from Base"""
        methods = ['all', 'first']

        for method in methods:
            result = getattr(self.Test, method)
            self.assertEqual(type(result).__name__, 'instancemethod')
            self.assertEqual(result.im_class.__name__, 'Relation')


##
# default_scope
#
# This method's purpose is to setup default query options accross a model.
# It can be called multiple times and each call will merge into previous calls
#
class BaseDefaultScopeMethodTestCase(BaseScopingTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(self.Test.default_scope.im_self.__name__, 'Test')

    def test_accepts_dictionary(self):
        """should accept a dictionary of finder options"""
        self.Test.default_scope({ 'where': 'foo' })
        self.assertEqual(self.Test.scoped().params['where'], ['foo'])

    def test_accepts_relation(self):
        """should accept a Relation instance for this class"""
        rel = self.Test.relation().where('bar')
        self.Test.default_scope(rel)
        self.assertEqual(self.Test.scoped().params['where'], ['bar'])

    def test_aggregates(self):
        """each call should aggregate on the previous ones"""
        rel = self.Test.relation()
        self.Test.default_scope(rel.where('foo'))
        self.Test.default_scope(rel.where('bar'))
        self.assertEqual(self.Test.scoped().params['where'], ['foo', 'bar'])

    def test_kwargs(self):
        """should accept kwargs in lou of a dictionary"""
        self.Test.default_scope(where='foo')
        self.assertEqual(self.Test.scoped().params['where'], ['foo'])

    def test_argument_errors(self):
        """should raise exception on bad arguments"""
        method = self.Test.default_scope
        self.assertRaises(errors.ArgumentError,
                method,
                { 'where': 'foo' },
                where='bar')

        self.assertRaises(errors.ArgumentError, method, "POOP")

    def test_applies_scopes_to_query_methods(self):
        """default scopes should apply to base query methods"""
        self.Test.default_scope(where='foo')
        rel = self.Test.where('bar')
        self.assertEqual(rel.params['where'], ['foo', 'bar'])

    # IDEA: """should accept a lambda returning a dict or Relation"""

class BaseUnscopedMethodTestCase(BaseScopingTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(self.Test.unscoped.im_self.__name__, 'Test')

    def test_function_argument(self):
        """
        should accept a function or lambda with no args
        should clear any scoped_methods and execute the given function
        """
        self.Test.default_scope(where='bar')
        self.assertEqual(self.Test.scoped().params['where'], ['bar'])
        self.Test.unscoped(lambda:
                self.assertEqual(self.Test.scoped().params['where'], []))

    def test_finally(self):
        """should always reset scoped_methods to previous value"""
        self.Test.default_scope(where='bar')

        def foo():
            self.assertEqual(self.Test.scoped().params['where'], [])
            raise RuntimeError("POOP!")

        try:
            self.Test.unscoped(foo)
        except(RuntimeError):
            pass

        self.assertEqual(self.Test.scoped().params['where'], ['bar'])

class BaseDefineScopeMethodTestCase(BaseScopingTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(self.Test.define_scope.im_self.__name__, 'Test')

    def test_accepts_dictionary(self):
        """should accept a name then a dictionary of finder options"""
        self.Test.define_scope('foo', {'where': 'foo'})
        self.assertEqual(self.Test.foo().params['where'], ['foo'])

    def test_accepts_relation(self):
        """should accept a name then a Relation instance for this class"""
        self.Test.define_scope('foo', self.Test.relation().where('foo'))
        self.assertEqual(self.Test.foo().params['where'], ['foo'])

    def test_accepts_function(self):
        """should allow function returning a relation or dictionary"""
        def scope(cls):
            return cls.where('foo')

        def scope2(cls):
            return { 'where': 'bar' }

        self.Test.define_scope(scope)
        self.assertEqual(self.Test.scope().params['where'], ['foo'])

        result = self.Test.define_scope(scope2)
        self.assertEqual(self.Test.scope2().params['where'], ['bar'])

    def test_function_accepting_arguments(self):
        """should allow a function with params passed at runtime"""
        def scope(cls, name, **blah):
            return cls.where("name like '%s'" % name).where(blah['foo'])

        self.Test.define_scope(scope)
        self.assertEqual(self.Test.scope('FOO', foo='bar').params['where'],
                ["name like 'FOO'", 'bar'])

    def test_accepts_named_lambda(self):
        """should accept lambda as second parameter"""
        self.Test.define_scope('foo', lambda(cls): {'where': 'baz'})
        self.assertEqual(self.Test.foo().params['where'], ['baz'])

    def test_accepts_kwargs(self):
        """should accept a name then a list of kwargs finder_options"""
        self.Test.define_scope('foo', where='foo')
        self.assertEqual(self.Test.foo().params['where'], ['foo'])

    def test_name_of_func_should_be_passed_name(self):
        """should set __name__ on return value"""
        scope = self.Test.define_scope('foo', where='foo')
        self.assertEqual(scope.__name__, 'foo')

    def test_scopes_list(self):
        """should append scope to the scopes list"""
        scope = self.Test.define_scope('foo', where='bar')
        self.assertEqual(self.Test.scopes.get('foo'), scope)

    def test_scopes_method_access(self):
        """should allow access to a method for this scope on the class"""
        self.Test.define_scope('foo', where='baz')
        self.assertTrue(hasattr(self.Test, 'foo'))
        rel = self.Test.foo()
        self.assertEqual(rel.params['where'], ['baz'])


    def test_alias_scope(self):
        """should be aliased as `scope`"""
        self.assertEqual(self.Test.define_scope, self.Test.scope)

##
# Saving and Deleting
#
class BasePersistenceTestCase(BaseTestCase):
    def setUp(self):
        TestAdapter.reset()
        class Test(pyperry.Base): pass
        Test.attributes('id')
        Test.configure('read', adapter=TestAdapter)
        Test.configure('write', adapter=TestAdapter, foo='bar')
        self.Test = Test
        self.test = Test({ 'id': 1 })

# Configuration
class WriteAdapterConfigTestCase(BasePersistenceTestCase):

    def test_configuration(self):
        """should allow 'write' configuration"""
        self.assertEqual(self.Test.adapter_config['write'],
                { 'adapter': TestAdapter, 'foo': 'bar' })

##
# save method
#
class BaseSaveMethodTestCase(BasePersistenceTestCase):

    def test_instance_method(self):
        """should be an instance method"""
        self.assertEqual(self.Test.save.im_class, self.Test)

    def test_calls_write_adapter(self):
        """should call write adapter passing current model"""
        self.test.save()
        self.assertEqual(len(TestAdapter.calls), 1)
        self.assertEqual(TestAdapter.calls[0][0], 'write')
        self.assertEqual(TestAdapter.calls[0][1]['model'].attributes,
                self.test.attributes)


    def test_true_on_success(self):
        """should return true for success"""
        TestAdapter.return_val = True
        self.assertTrue(self.test.save())

    def test_false_on_failure(self):
        """should return false for failure"""
        TestAdapter.return_val = False
        self.assertFalse(self.test.save())

##
# update_attributes method
#
class BaseUpdateAttributesMethodTestCase(BasePersistenceTestCase):

    def test_instance_method(self):
        """should be an instance method"""
        self.assertEqual(self.Test.update_attributes.im_class, self.Test)

    def test_sets_attributes(self):
        """should set any provided attributes"""
        self.test.update_attributes({'id': 2})
        self.assertEqual(self.test.id, 2)
        self.test.update_attributes(id=3)
        self.assertEqual(self.test.id, 3)

    def test_saves_after_set(self):
        """should run save after setting attributes"""
        self.test.update_attributes({ 'id': 2 })
        self.assertEqual(TestAdapter.calls[0][0], 'write')
        self.assertEqual(TestAdapter.calls[0][1]['model'].attributes,
                { 'id': 2 })

    def test_true_on_success(self):
        """should return true for success"""
        TestAdapter.return_val = True
        self.assertTrue(self.test.update_attributes())

    def test_false_on_failure(self):
        """should return false for failure"""
        TestAdapter.return_val = False
        self.assertFalse(self.test.update_attributes())

##
# destroy method
#
class BaseDestroyMethodTestCase(BasePersistenceTestCase):

    def test_instance_method(self):
        """should be an instance method"""
        self.assertEqual(self.Test.destroy.im_class, self.Test)


    def test_calls_write(self):
        """should call write adapter for current model with delete=True"""
        self.test.destroy()
        (mode, dic) = TestAdapter.calls[0]
        self.assertEqual(mode, 'write')
        self.assertEqual(dic['model'].attributes, self.test.attributes)
        self.assertTrue(dic['delete'])

    def test_true_on_success(self):
        """should return true for success"""
        TestAdapter.return_val = True
        self.assertTrue(self.test.destroy())

    def test_false_on_failure(self):
        """should return false for failure"""
        TestAdapter.return_val = False
        self.assertFalse(self.test.delete())

    def test_alias(self):
        """should be aliased as delete"""
        self.assertEqual(self.test.delete, self.test.destroy)


##
# reload method
#

class ReloadTest(pyperry.Base):
    def _config(cls):
        cls.attributes('id', 'a', 'b')


class BaseDestroyMethodTestCase(BasePersistenceTestCase):

    def _fake_fetch_records(cls, relation):
        return [ReloadTest({ 'id': 2, 'a': 3, 'b': 4 })]

    def setUp(self):
        super(self.__class__, self).setUp()
        ReloadTest.fetch_records = self._fake_fetch_records

    def test_reload(self):
        before = { 'id': '1' }
        test = ReloadTest(copy.copy(before))
        test.reload()
        self.assertNotEqual(test.attributes, before)
        self.assertEqual(test.attributes, { 'id': 2, 'a': 3, 'b': 4 })
        self.assertEqual(test.a, 3)


##
# Freezing objects
#
class BaseFreezeMethodsTestCase(BaseTestCase):

    def setUp(self):
        self.model = pyperry.Base({})

    def test_default(self):
        """model should not be frozen by default"""
        self.assertEqual(self.model.frozen(), False)

    def test_freeze(self):
        """calling freeze should set frozen to false"""
        self.model.freeze()
        self.assertEqual(self.model.frozen(), True)
##
# Association methods
#
# Methods for managing the associations on a model
#
class BaseAssociationTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base):
            attributes = ['id']

        self.Test = Test
        self.Test.belongs_to('something')
        self.Test.has_many('things')
        self.Test.has_one('thing')

class BaseBelongsToMethodTestCase(BaseAssociationTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(self.Test.belongs_to.im_self.__name__, 'Test')

    def test_defined_associations(self):
        """should add to the defined_associations dict"""
        self.assertEqual(True, len(self.Test.defined_associations) > 0)

    def test_instance(self):
        """should be an instance of BelongsTo"""
        self.assertEqual(True, type(self.Test.defined_associations['something']) is pyperry.association.BelongsTo)

class BaseHasManyMethodTestCase(BaseAssociationTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(self.Test.has_many.im_self.__name__, 'Test')

    def test_defined_associations(self):
        """should add to the defined_associations dict"""
        self.assertEqual(True, len(self.Test.defined_associations) > 0)

    def test_instance(self):
        """should be an instance of HasMany"""
        self.assertEqual(True, type(self.Test.defined_associations['things']) is pyperry.association.HasMany)

class BaseHasOneMethodTestCase(BaseAssociationTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(self.Test.has_one.im_self.__name__, 'Test')

    def test_defined_associations(self):
        """should add to the defined_associations dict"""
        self.assertEqual(True, len(self.Test.defined_associations) > 0)

    def test_instance(self):
        """should be an instance of HasOne"""
        self.assertEqual(True, type(self.Test.defined_associations['thing']) is pyperry.association.HasOne)
