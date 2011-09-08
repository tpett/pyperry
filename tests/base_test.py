import sys
import tests
import unittest
from nose.plugins.skip import SkipTest
import copy

import pyperry
from pyperry import errors
from pyperry import callbacks
from pyperry.field import Field
from pyperry.scope import Scope, DefaultScope
from pyperry.response import Response
import pyperry.association as associations

from tests.fixtures.test_adapter import TestAdapter
import tests.fixtures.association_models

class BaseTestCase(unittest.TestCase):

    def tearDown(self):
        TestAdapter.reset_calls()

class ClassSetupTestCase(BaseTestCase):

    def test_sets_name_on_fields(self):
        """should set the `name` attribute on all Field instances"""
        class Test(pyperry.Base):
            id = Field()
            name = Field()
            poop = Field()
            foo = Field(name='bar')

        self.assertEqual(Test.id.name, 'id')
        self.assertEqual(Test.name.name, 'name')
        self.assertEqual(Test.poop.name, 'poop')
        self.assertEqual(Test.foo.name, 'bar')

        self.assertEqual(Test.defined_fields, set(['id', 'name', 'poop',
                'foo']))

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

    def test_reader_copied(self):
        class Parent(pyperry.Base):
            reader = TestAdapter()

        class Child(Parent):
            pass

        self.assertNotEqual(Child.reader, Parent.reader)

    def test_writer_copied(self):
        class Parent(pyperry.Base):
            writer = TestAdapter()

        class Child(Parent):
            pass

        self.assertNotEqual(Child.writer, Parent.writer)

    def test_callbacks_registered(self):
        class Test(pyperry.Base):
            @callbacks.before_save
            def foo(self): pass
            @callbacks.before_update
            def bar(self): pass

        self.assertTrue(hasattr(Test, 'callback_manager'))
        self.assertTrue(isinstance(Test.callback_manager,
            callbacks.CallbackManager ))

        self.assertEqual(
                Test.callback_manager.callbacks[callbacks.before_save],
                [Test.foo] )
        self.assertEqual(
                Test.callback_manager.callbacks[callbacks.before_update],
                [Test.bar] )

    def test_callback_manager_copied(self):
        class Parent(pyperry.Base): pass
        class Child(pyperry.Base): pass

        self.assertTrue(Parent.callback_manager is not
                Child.callback_manager)

##
# Test the initializer
#
class InitializeTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base):
            id = Field()
            name = Field()
            foo = Field(type=int)
            bar = Field(default=3)
        self.Test = Test

    def test_init_fields(self):
        """init should set any defined fields in the provided dict"""
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

    def test_when_existing_record_set_raw_fields(self):
        t = self.Test(new_record=False, foo='1')
        self.assertEqual(t['foo'], '1')

    def test_when_new_record_set_attr_fields(self):
        t = self.Test(new_record=True, foo='1')
        self.assertEqual(t['foo'], 1)

    def test_sets_field_defaults(self):
        """should set the default values of fields to the fields dict"""
        t = self.Test()
        self.assertEqual(t.bar, 3)


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
# Test the accessors for defined fields
#
class AttributeAccessTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base):
            id = Field()
            name = Field()
        self.Test = Test
        self.test = Test(dict(id=1, name='Foo'))

    def test_attribute_getters(self):
        """[] and attribute based getter for defined fields"""
        test = self.test
        self.assertEqual(test.name, 'Foo')
        self.assertEqual(test['id'], 1)

    def test_attribute_setters(self):
        """[]= and attribute based setter for defined_fields"""
        test = self.test
        test.id = 2
        test['name'] = 'bar'

        self.assertEqual(test.id, 2)
        self.assertEqual(test['name'], 'bar')

    def test_bad_attribute_access(self):
        """Undefined fields should raise AttributeError and KeyError"""
        test = self.test

        self.assertRaises(AttributeError, getattr, test, 'poop')
        # test.poop = 'foo' should set a new object attr 'poop'
        self.assertRaises(KeyError, test.__getitem__, 'poop')
        self.assertRaises(KeyError, test.__setitem__, 'poop', 'foo')

class KeysMethodTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base):
            id = Field()
            name = Field()
        self.Test = Test
        self.test = Test()

    def test_is_a_method(self):
        """should be an instance method"""
        assert hasattr(self.test, 'keys')

    def test_returns_defined_fields(self):
        """should return a list of all fields"""
        self.assertEqual(self.test.keys(), set(["id", "name"]))

class HasKeyMethodTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base):
            id = Field()
            name = Field()
        self.Test = Test
        self.test = Test()

    def test_is_a_method(self):
        """should be an instance method"""
        assert hasattr(self.test, 'has_key')

    def test_returns_true_when_field_exists(self):
        self.assertEqual(self.test.has_key('name'), True)

    def test_returns_false_when_field_doesnt_exist(self):
        self.assertEqual(self.test.has_key('foo'), False)


class BaseFetchRecordsMethodTestCase(BaseTestCase):

    def test_nil_results(self):
        """should ignore None results"""
        class Test(pyperry.Base):
            id = Field()
            reader = TestAdapter()

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


class BaseMethodAutoImportTestCase(BaseTestCase):

    def setUp(self):
        super(BaseMethodAutoImportTestCase, self).setUp()
        sys.path.insert(0, tests.test_sys_path_dir)

    def tearDown(self):
        super(BaseMethodAutoImportTestCase, self).tearDown()
        sys.path.remove(tests.test_sys_path_dir)

    def test_auto_imports(self):
        """should import modules if needed and possible"""
        self.assertFalse(sys.modules.has_key('pyperry_foobar'))
        pyperry.Base._auto_import('pyperry_foobar.foo.bar')
        self.assertTrue(sys.modules.has_key('pyperry_foobar'))
        try:
            import pyperry_foobar.foo.bar
        except ImportError:
            assert False, "Failed to import submodules of pyperry_foobar"

    # This is really an integration test
    def test_called_by_resolve_name(self):
        """should allow models not yet imported to be referenced"""
        class Test(pyperry.Base):
            id = Field()
            baz_id = Field()
            baz = associations.BelongsTo(
                    class_name='pyperry_foobar.foo.baz.Bazaroo5234')

        self.assertFalse(Test.defined_models.has_key('Bazaroo5234'))
        cls = Test.baz.source_klass()
        self.assertTrue(Test.defined_models.has_key('Bazaroo5234'))

        import pyperry_foobar.foo.baz
        self.assertEqual(cls, pyperry_foobar.foo.baz.Bazaroo5234)



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

    def test_fields_equal(self):
        """should compare two different objects with the same fields as equal"""
        test1 = self.Test({ 'id': 2, 'name': 'Poop Head' })
        test2 = self.Test({ 'id': 2, 'name': 'Poop Head' })
        self.assertEqual(test1, test2)

    def test_not_equal(self):
        """should not be equal when fields are different"""
        test1 = self.Test({ 'id': 1, 'name': 'Poop Head' })
        test2 = self.Test({ 'id': 1, 'name': 'Poop Head!' })
        self.assertNotEqual(test1, test2)

    def test_not_equal_different_class(self):
        """should not be equal when different classes"""
        test1 = self.Test({ 'id': 1, 'name': 'Poop Head' })
        test2 = self.Test2({ 'id': 1, 'name': 'Poop Head' })
        self.assertNotEqual(test1, test2)

    def test_none_case(self):
        """should compare to None as False"""
        test = self.Test()
        assert not test == None


class BaseInheritanceTestCase(BaseTestCase):

    def setUp(self):
        self.base_article = tests.fixtures.association_models.Article
        class MyArticle(self.base_article):
            pass
        self.sub_article = MyArticle
        TestAdapter.data = { 'id': 1 }

    def test_article_subclass_behavior(self):
        """subclass should behave like base class"""
        print self.base_article.defined_fields
        print self.sub_article.defined_fields
        self.assertEqual(self.sub_article.first().fields,
                self.base_article.first().fields)


##
# Scoping methods
#
# Methods for managing the query scope of a model
#
class BaseScopingTestCase(BaseTestCase):

    def setUp(self):
        class Test(pyperry.Base):
            fields = ['id']
            reader = TestAdapter()

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
        TestAdapter.reset_calls()
        class Test(pyperry.Base):
            id = Field(type=int)
            name = Field()
            bar_id = Field()
            bar = associations.BelongsTo()
            reader = TestAdapter()
            writer = TestAdapter(foo='bar')
        self.Test = Test
        self.test = Test({ 'id': 1 })

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
# update method
#
class BaseUpdateMethodTestCase(BasePersistenceTestCase):

    def test_instance_method(self):
        """should be an instance method"""
        self.assertEqual(self.Test.update.im_class, self.Test)

    def test_raises_on_new_record(self):
        """should raise PersistenceError when called on new_record"""
        self.assertRaises(errors.PersistenceError, self.test.update)

    def test_calls_save(self):
        """should call save() when all is well and return"""
        TestAdapter.data = { 'id': 1 }
        TestAdapter.return_val = Response(success=True)
        self.test.new_record = False
        val = self.test.update()
        # One for the save, one for the reload
        self.assertEqual(len(TestAdapter.calls), 2)
        self.assertEqual(val, True)

##
# create method
#
class BaseCreateMethodTestCase(BasePersistenceTestCase):

    def test_instance_method(self):
        """should be an instance method"""
        self.assertEqual(self.Test.create.im_class, self.Test)

    def test_raises_on_not_new_record(self):
        """should raise PersistenceError when called on new_record"""
        self.test.new_record = False
        self.assertRaises(errors.PersistenceError, self.test.create)

    def test_calls_save(self):
        """should call save() when all is well and return"""
        TestAdapter.data = { 'id': 1 }
        TestAdapter.return_val = Response(success=True)
        TestAdapter.return_val._parsed = TestAdapter.data
        self.test.new_record = True
        val = self.test.create()
        # One for the save, one for the reload
        self.assertEqual(len(TestAdapter.calls), 2)
        self.assertEqual(val, True)

##
# update_fields method
#
class BaseUpdateAttributesMethodTestCase(BasePersistenceTestCase):

    def test_instance_method(self):
        """should be an instance method"""
        self.assertEqual(self.Test.update_fields.im_class, self.Test)

class SetFieldsMethodTestCase(BasePersistenceTestCase):

    def test_instance_method(self):
        """should be an instance method"""
        self.assertEqual(self.Test.set_fields.im_class, self.Test)

    def test_accepts_dict_and_kwargs(self):
        """should accept dict and kwargs"""
        self.test.set_fields({ 'id': 1 }, name='bar')
        self.assertEqual(self.test.fields, { 'id': 1, 'name': 'bar' })

    def test_sets_field_from_dict(self):
        """should set the python attribute for each item in the dict"""
        self.test.set_fields(id='1')
        self.assertEqual(self.test['id'], 1)

    def test_doesnt_set_non_fields(self):
        self.test.set_fields(foo='bar')
        self.assertEqual(self.test.fields.get('foo'), None)

    def test_allow_setting_association_values(self):
        self.test.set_fields(bar=self.Test(id=5))
        self.assertEqual(self.test['bar_id'], 5)

class SetRawFieldsMethodTestCase(BasePersistenceTestCase):

    def test_instance_method(self):
        """should be an instance method"""
        self.assertEqual(self.Test.set_raw_fields.im_class, self.Test)

    def test_accepts_dict_and_kwargs(self):
        """should accept dict and kwargs"""
        self.test.set_raw_fields({ 'id': 1 }, name='bar')
        self.assertEqual(self.test.fields, { 'id': 1, 'name': 'bar' })

    def test_sets_field_from_dict(self):
        """should set the python attribute for each item in the dict"""
        self.test.set_raw_fields(id='1')
        self.assertEqual(self.test['id'], '1')

    def test_doesnt_set_non_fields(self):
        self.test.set_raw_fields(foo='bar')
        self.assertEqual(self.test.fields.get('foo'), None)

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
# Callback triggering
#
class BaseCallbackTriggeringTestCase(BaseTestCase):

    def setUp(self):
        super(BaseCallbackTriggeringTestCase, self).setUp()
        TestAdapter.data = { 'id': 1 }
        TestAdapter.return_val = Response(success=True)
        TestAdapter.return_val._parsed = { 'id': 1 }
        c_bld = callbacks.before_load
        c_ald = callbacks.after_load
        c_bsv = callbacks.before_save
        c_asv = callbacks.after_save
        c_bct = callbacks.before_create
        c_act = callbacks.after_create
        c_bup = callbacks.before_update
        c_aup = callbacks.after_update
        c_bde = callbacks.before_destroy
        c_ade = callbacks.after_destroy
        class CallbackTest(pyperry.Base):
            id = Field()
            reader = TestAdapter()
            writer = TestAdapter()
            log = []
            bld = c_bld(lambda(self): self.log.append('before_load'))
            ald = c_ald(lambda(self): self.log.append('after_load'))
            bsv = c_bsv(lambda(self): self.log.append('before_save'))
            asv = c_asv(lambda(self): self.log.append('after_save'))
            bct = c_bct(lambda(self): self.log.append('before_create'))
            act = c_act(lambda(self): self.log.append('after_create'))
            bup = c_bup(lambda(self): self.log.append('before_update'))
            aup = c_aup(lambda(self): self.log.append('after_update'))
            bde = c_bde(lambda(self): self.log.append('before_destroy'))
            ade = c_ade(lambda(self): self.log.append('after_destroy'))

        self.CallbackTest = CallbackTest

    def test_load(self):
        self.CallbackTest()
        self.assertEqual(self.CallbackTest.log, ['before_load', 'after_load'])

    def test_create(self):
        cb = self.CallbackTest()
        self.CallbackTest.log = []
        cb.save()
        self.assertEqual(self.CallbackTest.log, [
                'before_save', 'before_create', 'before_load', 'after_load',
                'after_create', 'after_save'])

    def test_create_without_callbacks(self):
        cb = self.CallbackTest()
        self.CallbackTest.log = []
        cb.save(run_callbacks=False)
        self.assertEqual(self.CallbackTest.log, ['before_load', 'after_load'])

    def test_update(self):
        cb = self.CallbackTest(new_record=False, id=1)
        self.CallbackTest.log = []
        cb.save()
        self.assertEqual(self.CallbackTest.log, [
                'before_save', 'before_update', 'before_load', 'after_load',
                'after_update', 'after_save'])

    def test_update_without_callbacks(self):
        cb = self.CallbackTest(new_record=False, id=1)
        self.CallbackTest.log = []
        cb.save(run_callbacks=False)
        self.assertEqual(self.CallbackTest.log, ['before_load', 'after_load'])

    def test_destroy(self):
        cb = self.CallbackTest(new_record=False, id=1)
        self.CallbackTest.log = []
        cb.delete()
        self.assertEqual(self.CallbackTest.log,
                ['before_destroy', 'after_destroy'])

    def test_update_without_callbacks(self):
        cb = self.CallbackTest(new_record=False, id=1)
        self.CallbackTest.log = []
        cb.delete(run_callbacks=False)
        self.assertEqual(self.CallbackTest.log, [])


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
        self.assertNotEqual(test.fields, before)
        self.assertEqual(test.fields, { 'id': 2, 'a': 3, 'b': 4 })
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
            writer = TestAdapter()

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

