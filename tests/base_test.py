import tests
import unittest
from nose.plugins.skip import SkipTest
import copy

import pyperry
from pyperry import errors
from pyperry.field import Field
from pyperry.scope import Scope, DefaultScope
import pyperry.association as associations

from tests.fixtures.test_adapter import TestAdapter
import tests.fixtures.association_models

class BaseTestCase(unittest.TestCase):

    def tearDown(self):
        TestAdapter.reset()

class ClassSetupTestCase(BaseTestCase):

    def test_sets_name_on_attributes(self):
        """should set the `name` attribute on all Field attributes"""
        class Test(pyperry.Base):
            id = Field()
            name = Field()
            poop = Field()

        self.assertEqual(Test.id.name, 'id')
        self.assertEqual(Test.name.name, 'name')
        self.assertEqual(Test.poop.name, 'poop')

        self.assertEqual(Test.defined_attributes, set(['id', 'name', 'poop']))

    def test_sets_target_and_id_on_associations(self):
        """should set target_klass and id on instances of Association"""
        class Test(pyperry.Base):
            foo_id = Field()
            foo = associations.HasMany()

        self.assertEqual(Test.foo.id, 'foo')
        self.assertEqual(Test.foo.target_klass, Test)

    def test_adds_to_defined_associations(self):
        """should add association to the list of defined associations"""
        class Test(pyperry.Base):
            foo123 = associations.HasMany()

        self.assertTrue('foo123' in Test.defined_associations.keys())

    def test_sets_name_on_scope(self):
        """should set the `__name__` attribute on Scope instance"""
        class Test(pyperry.Base):
            foo = Scope(where='foo')

        self.assertEqual(Test.foo.__name__, 'foo')

    def test_adds_scope_to_list(self):
        """should add scope to `scopes` dict"""
        class Test(pyperry.Base):
            bar = Scope(where='bar')

        self.assertTrue(hasattr(Test, 'scopes'))
        self.assertTrue('bar' in Test.scopes.keys())

    def test_inheritence_stomping(self):
        """should not stomp parent classes scopes dict"""
        class Parent(pyperry.Base):
            base = Scope()
        class Child(pyperry.Base):
            child = Scope()

        self.assertFalse('child' in Parent.scopes.keys())

    def test_default_scope(self):
        class Test(pyperry.Base):
            @DefaultScope
            def default_ordering(cls):
                return cls.order('foo')

        self.assertEqual(len(Test._scoped_methods), 1)
        relation = Test._scoped_methods[0]

        self.assertEqual(relation.query(), { 'order': ['foo'] })

    def test_config_attr(self):
        """should parse __config attr and apply to adapter_config"""
        class Test(pyperry.Base):
            __config = {
                    'read': dict(adapter=TestAdapter, foo='read'),
                    'write': dict(adapter=TestAdapter, foo='write') }

        # Should get name mangled
        self.assertTrue(hasattr(Test, '_Test__config'))
        self.assertEqual(Test.adapter_config['read']['foo'], 'read')
        self.assertEqual(Test.adapter_config['write']['foo'], 'write')

    def test_inheritence_stomping_for_config(self):
        class Parent(pyperry.Base):
            __config = { 'read': dict(foo=1) }
        class Child(Parent):
            __config = { 'read': dict(bar=2) }

        self.assertEqual(Parent.adapter_config['read'], { 'foo': 1 })
        self.assertEqual(Child.adapter_config['read'], { 'foo': 1, 'bar': 2 })

##
# Test the initializer
#
class InitializeTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base):
            id = Field()
            name = Field()
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

    def test_init_with_no_args(self):
        t = self.Test()
        self.assertEqual(t.id, None)

    def test_init_with_kwargs(self):
        t = self.Test(name='test')
        self.assertEqual(t.name, 'test')

    def test_init_with_attributes_and_kwargs(self):
        t = self.Test({'id': 3}, False, name='test')
        self.assertEqual(t.id, 3)
        self.assertEqual(t.name, 'test')


##
# Configurable primary keys
#
class PrimaryKeyTestCase(BaseTestCase):

    def setUp(self):
        class Model(pyperry.Base):
            id = Field()
            foo = Field()
        self.Model = Model

    def test_primary_key_class_methods(self):
        """primary_key and set_primary_key methods should be defined on Base"""
        self.assertTrue(hasattr(self.Model, 'primary_key'))
        self.assertTrue(callable(self.Model.primary_key))
        self.assertTrue(hasattr(self.Model, 'set_primary_key'))
        self.assertTrue(callable(self.Model.set_primary_key))

    def test_defaults_to_id(self):
        """the primary_key method should return 'id' by default"""
        self.assertEqual(self.Model.primary_key(), 'id')

    def test_set_primary_key_class_method(self):
        """should change the primary_key with the set_primary_key method"""
        self.Model.set_primary_key('foo')
        self.assertEqual(self.Model.primary_key(), 'foo')

    def test_raise_if_no_attr(self):
        """should raise if setting primary key to an undefined attribute"""
        self.assertRaises(AttributeError, self.Model.set_primary_key, 'asdf')

    def test_pk_attr_shortcut_method(self):
        """should access the primary key attribute name from an instance"""
        m = self.Model({})
        self.assertEqual(m.pk_attr(), 'id')
        self.Model.set_primary_key('foo')
        self.assertEqual(m.pk_attr(), 'foo')

    def test_pk_value_shortcut_method(self):
        """should access the primary key attribute value from the instance"""
        m = self.Model({'id': 6, 'foo': 'bar'})
        self.assertEqual(m.pk_value(), 6)
        self.Model.set_primary_key('foo')
        self.assertEqual(m.pk_value(), 'bar')
        m.foo = 'asdf'
        self.assertEqual(m.pk_value(), 'asdf')


##
# Test the accessors for defined attributes
#
class AttributeAccessTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base):
            id = Field()
            name = Field()
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

        self.assertRaises(AttributeError, getattr, test, 'poop')
        # test.poop = 'foo' should set a new object attr 'poop'
        self.assertRaises(KeyError, test.__getitem__, 'poop')
        self.assertRaises(KeyError, test.__setitem__, 'poop', 'foo')

##
# Test setting of configure('read') and it merging with superclass configuration
#
class AdapterConfigurationTestCase(BaseTestCase):

    def setUp(self):
        pass

    def test_confiure_read_merge(self):
        """setting read config should merge all dicts up the inheritance tree"""
        class TestBase(pyperry.Base):
            __config = { 'read': dict(poop="smells") }

        class Test(TestBase):
            __config = { 'read': dict(foo='bar') }

        self.assertEqual(Test.adapter_config['read']['foo'], 'bar')
        self.assertEqual(Test.adapter_config['read']['poop'], 'smells')

        class Test2(Test):
            __config = { 'read': dict(poop='stanks') }

        self.assertEqual(Test2.adapter_config['read']['poop'], 'stanks')
        self.assertEqual(Test.adapter_config['read']['poop'], 'smells')

    def test_adapter_required(self):
        """should complain if 'adapter' option not set"""
        from fixtures.test_adapter import TestAdapter
        from pyperry import errors
        class Test(pyperry.Base):
            __config = { 'read': dict(poop='smells') }

        self.assertRaises(errors.ConfigurationError, Test.adapter, 'read')

    def test_delayed_exec_configs(self):
        """should delay calling any lambda config values until they are needed"""
        from fixtures.test_adapter import TestAdapter
        class Test(pyperry.Base):
            __config = {
                    'read': dict(adapter=TestAdapter, foo=lambda: 'barbarbar')}

        adapter = Test.adapter('read', )
        self.assertEquals(adapter.config['foo'], 'barbarbar')

    def test_unique_adapters(self):
        """adapters changes to child objects should not affect super objects"""
        class Super(pyperry.Base): pass
        Super.configure('read', adapter=TestAdapter, conf='super')

        class Child(Super): pass
        Child.configure('read', adapter=TestAdapter, conf='child')

        super_adapter = Super.adapter('read')
        child_adapter = Child.adapter('read')

        self.assertTrue(super_adapter is not child_adapter)
        self.assertEqual(super_adapter.config['conf'], 'super')
        self.assertEqual(child_adapter.config['conf'], 'child')

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
# add_processor method
#
class BaseAddProcessorMethodTestCase(BaseTestCase):

    def setUp(self):
        class Processor(object):
            def __init__(self, adapter, options=None):
                self.adapter = adapter

            def __call__(self, **kwargs):
                return self.adapter(**kwargs)
        self.Processor = Processor

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(pyperry.Base.add_processor.im_self.__name__, 'Base')

    def test_parameters(self):
        """should require 2 params taking an optional 3rd dict / kwargs"""
        class Test(pyperry.Base): pass
        Test.add_processor('read', self.Processor)
        Test.add_processor('read', self.Processor, { 'foo': 'bar' })
        Test.add_processor('read', self.Processor, foo='bar')

    def test_saves_config(self):
        """should append value to adapter_config[type] middlewares option"""
        class Test(pyperry.Base): pass
        Test.add_processor('read', self.Processor, { 'foo': 'bar' })
        self.assertEqual(Test.adapter_config['read']['_processors'],
                [(self.Processor, { 'foo': 'bar' })])
        Test.add_processor('read', self.Processor, { 'baz': 'boo' })
        self.assertEqual(Test.adapter_config['read']['_processors'],
                [
                    (self.Processor, { 'foo': 'bar' }),
                    (self.Processor, { 'baz': 'boo' }) ])

    def test_add_processor_after_adapter(self):
        """
        should add processor without raising exception if adapter already
        configured
        """
        class Test(pyperry.Base): pass
        Test.configure('read', adapter='Foo')
        Test.add_processor('read', self.Processor, { 'foo': 'bar' })
        self.assertEqual(len(Test.adapter_config['read']['_processors']), 1)


##
# Adapter method
#
class BaseAdapterMethodTestCase(BaseTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(pyperry.Base.adapter.im_self.__name__, 'Base')

    def test_read(self):
        """if exists return adapter described by type"""
        raise SkipTest
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

    def test_no_double_configuration(self):
        """
        the _config method should be called at most once and should not be
        inherited by subclasses
        """
        class A(pyperry.Base):
            def _config(cls):
                cls.add_processor('read', 'some processor')
        self.assertEqual(len(A.adapter_config['read']['_processors']), 1)

        class B(A): pass
        self.assertEqual(len(B.adapter_config['read']['_processors']), 1)


class BaseFetchRecordsMethodTestCase(BaseTestCase):

    def test_nil_results(self):
        """should ignore None results"""
        class Test(pyperry.Base):
            id = Field()
            def _config(cls):
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

class BaseComparisonTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base):
            id = Field()
            name = Field()

        class Test2(pyperry.Base):
            id = Field()
            name = Field()

        self.Test = Test
        self.Test2 = Test2

    def test_object_equal(self):
        """should compare the same object as equal to itself"""
        test = self.Test({ 'id': 1, 'name': 'foo' })
        self.assertEqual(test, test)

    def test_attributes_equal(self):
        """should compare two differnt objects with the same attributes as equal"""
        test1 = self.Test({ 'id': 2, 'name': 'Poop Head' })
        test2 = self.Test({ 'id': 2, 'name': 'Poop Head' })
        self.assertEqual(test1, test2)

    def test_not_equal(self):
        """should not be equal when attributes are different"""
        test1 = self.Test({ 'id': 1, 'name': 'Poop Head' })
        test2 = self.Test({ 'id': 1, 'name': 'Poop Head!' })
        self.assertNotEqual(test1, test2)

    def test_not_equal_different_class(self):
        """should not be equal when different classes"""
        test1 = self.Test({ 'id': 1, 'name': 'Poop Head' })
        test2 = self.Test2({ 'id': 1, 'name': 'Poop Head' })
        self.assertNotEqual(test1, test2)


class BaseInheritanceTestCase(BaseTestCase):

    def setUp(self):
        self.base_article = tests.fixtures.association_models.Article
        class MyArticle(self.base_article):
            pass
        self.sub_article = MyArticle
        TestAdapter.data = { 'id': 1 }

    def test_article_subclass_behavior(self):
        """subclass should behave like base class"""
        print self.base_article.defined_attributes
        print self.sub_article.defined_attributes
        self.assertEqual(self.sub_article.first().attributes,
                self.base_article.first().attributes)


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
                pyperry.Relation.plural_query_methods + ['modifiers'])

        for method in methods:
            result = getattr(self.Test, method)
            self.assertEqual(type(result).__name__, 'instancemethod')

    def test_all_finder_methods(self):
        """test finder methods on Relation accessible from Base"""
        methods = ['all', 'first', 'find']

        for method in methods:
            result = getattr(self.Test, method)
            self.assertEqual(type(result).__name__, 'instancemethod')
            self.assertEqual(result.im_class.__name__, 'Relation')


##
# DefaultScope behavior
#
# This method's purpose is to setup default query options accross a model.
# It can be called multiple times and each call will merge into previous calls
#
class BaseDefaultScopeTestCase(BaseScopingTestCase):

    def test_applies_scopes_to_query_methods(self):
        """default scopes should apply to base query methods"""
        self.Test._default = DefaultScope(where='foo')
        rel = self.Test.where('bar')
        self.assertEqual(rel.params['where'], ['foo', 'bar'])

    def test_no_query_run(self):
        """should not execute a query when setting a DefaultScope"""
        self.Test._default = DefaultScope(where='foo')
        self.assertEqual(len(TestAdapter.calls), 0)

class BaseUnscopedMethodTestCase(BaseScopingTestCase):

    def test_class_method(self):
        """should be a class method"""
        self.assertEqual(self.Test.unscoped.im_self.__name__, 'Test')

    def test_function_argument(self):
        """
        should accept a function or lambda with no args
        should clear any scoped_methods and execute the given function
        """
        self.Test._default = DefaultScope(where='bar')
        self.assertEqual(self.Test.scoped().params['where'], ['bar'])
        self.Test.unscoped(lambda:
                self.assertEqual(self.Test.scoped().params['where'], []))

    def test_finally(self):
        """should always reset scoped_methods to previous value"""
        self.Test._default = DefaultScope(where='bar')

        def foo():
            self.assertEqual(self.Test.scoped().params['where'], [])
            raise RuntimeError("POOP!")

        try:
            self.Test.unscoped(foo)
        except(RuntimeError):
            pass

        self.assertEqual(self.Test.scoped().params['where'], ['bar'])

##
# Saving and Deleting
#
class BasePersistenceTestCase(BaseTestCase):
    def setUp(self):
        TestAdapter.reset()
        class Test(pyperry.Base):
            id = Field()
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

    def test_raise_when_no_id(self):
        """
        should raise when attempting to save an existing record without an id
        """
        model = self.Test({}, False)
        self.assertRaises(errors.PersistenceError, model.save)


##
# update_attributes method
#
class BaseUpdateAttributesMethodTestCase(BasePersistenceTestCase):

    def test_instance_method(self):
        """should be an instance method"""
        self.assertEqual(self.Test.update_attributes.im_class, self.Test)


##
# delete method
#
class BaseDeleteMethodTestCase(BasePersistenceTestCase):

    def test_instance_method(self):
        """should be an instance method"""
        self.assertEqual(self.Test.delete.im_class, self.Test)

    def test_raise_when_new_record(self):
        """should raise when attempting to delete a new record"""
        self.test.new_record = True
        self.assertRaises(errors.PersistenceError, self.test.delete)

    def test_raise_when_no_id(self):
        """should raise when attempting to delete a record without an id"""
        model = self.Test({}, False)
        self.assertRaises(errors.PersistenceError, model.delete)



##
# reload method
#

class ReloadTestModel(pyperry.Base):
    id = Field()
    a = Field()
    b = Field()

    @classmethod
    def fetch_records(cls, relation):
        cls.last_relation = relation
        return [cls({ 'id': 2, 'a': 3, 'b': 4 })]

class BaseReloadMethodTestCase(BasePersistenceTestCase):

    def setUp(self):
        super(self.__class__, self).setUp()

    def test_reload(self):
        before = { 'id': '1' }
        test = ReloadTestModel(copy.copy(before))
        test.reload()
        self.assertNotEqual(test.attributes, before)
        self.assertEqual(test.attributes, { 'id': 2, 'a': 3, 'b': 4 })
        self.assertEqual(test.a, 3)

    def test_fresh(self):
        """should set the fresh value to True in the reload relation"""
        test = ReloadTestModel({'id': 1})
        test.reload()
        self.assertEqual(test.last_relation.query()['fresh'], True)


##
# Freezing objects
#
class BaseFreezeMethodsTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base):
            id = Field()

        Test.configure('write', adapter=TestAdapter)
        self.test_model = Test({'id':1}, False)
        self.model = pyperry.Base({})

    def test_default(self):
        """model should not be frozen by default"""
        self.assertEqual(self.model.frozen(), False)

    def test_freeze(self):
        """calling freeze should set frozen to false"""
        self.model.freeze()
        self.assertEqual(self.model.frozen(), True)

    def test_raise_on_write_when_frozen(self):
        """should raise on save if model is frozen"""
        self.test_model.freeze()
        self.assertRaises(errors.PersistenceError, self.test_model.save)

    def test_raise_on_delete_when_frozen(self):
        """should raise on delete if model is frozen"""
        self.test_model.freeze()
        self.assertRaises(errors.PersistenceError, self.test_model.delete)


##
# Association methods
#
# Methods for managing the associations on a model
#
class BaseAssociationTestCase(BaseTestCase):
    pass

class AssociationCachingTest(BaseAssociationTestCase):

    def setUp(self):
        self.Site = tests.fixtures.association_models.Site
        self.site = self.Site({})

    def test_cache_association(self):
        """should cache the result of the association after the first call"""
        self.assertFalse('_articles_cache' in self.site.__dict__)
        self.site.articles
        self.assertTrue('_articles_cache' in self.site.__dict__)

    def test_add_maually(self):
        """should allow the result of the association to be set manually"""
        self.site.articles = 'foo'
        self.assertEqual(self.site._articles_cache, 'foo')
        self.assertEqual(self.site.articles, 'foo')

