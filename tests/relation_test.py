import tests
import unittest
import pyperry

from fixtures.test_adapter import TestAdapter

Relation = pyperry.Relation
#
#
# Relation
#
# Relation is used for building queries for a collection of records.

# Default query options
singular_query_methods = ['limit', 'offset', 'from', 'sql']
plural_query_methods = ['select', 'group', 'order', 'joins', 'includes',
        'where', 'having']
# finder_methods = singular_query_methods + plural_query_methods + [
#         'conditions', 'search']



class BaseRelationTestCase(unittest.TestCase):

    def setUp(self):
        # Used for testing
        class Test(pyperry.Base):
            def _config(c):
                c.attributes('id')
                c.configure('read', adapter=TestAdapter)
                c.scope('foo', where='bar')
        self.Test = Test
        self.relation = Relation(Test)
        TestAdapter.data = { 'id': 1 }
        TestAdapter.count = 3

    def tearDown(self):
        TestAdapter.reset()

##
# Test the init of a relation
#
class InitTestCase(BaseRelationTestCase):

    def test_init_takes_klass(self):
        """Relation should init with a pyperry.Base klass)"""

        assert(isinstance(self.relation, Relation))
        self.assertEqual(self.relation.klass, self.Test)


##
# Test the building of the request dictionary
#
class RequestDictTestCase(BaseRelationTestCase):

    def test_dictionary_format(self):
        """Return a dictionary matching the adapter format"""
        rel = self.relation.where('foo', 'bar').from_('foo').limit(1)
        query = rel.query()

        self.assertEqual(query,
                { 'where': ['foo', 'bar'], 'from': 'foo', 'limit': 1 })


    def test_delayed_exec_expressions(self):
        """Should eval any lambda expressions"""
        rel = self.relation.where(lambda: 'foo').limit(lambda: 1)
        query = rel.query()

        self.assertEqual(query, { 'where': ['foo'], 'limit': 1 })


##
# Test fetching records through the base class and returning the results
#
class FetchRecordsTestCase(BaseRelationTestCase):

    def test_return_list(self):
        """should return a list of records"""
        rel = self.relation.where('foo')
        records = rel.fetch_records()

        assert isinstance(records, list)
        self.assertEqual(len(records), 3)
        self.assertEqual(TestAdapter.calls[0], rel.query())

    def test_list_is_pyperry_base(self):
        """the list should contain klass objects"""
        records = self.relation.fetch_records()

        for record in records:
            assert isinstance(record, self.relation.klass)

    def test_caches_results(self):
        """should only fetch through the adapter once"""
        self.relation.fetch_records()
        self.assertEqual(len(TestAdapter.calls), 1)

        self.relation.fetch_records()
        self.assertEqual(len(TestAdapter.calls), 1)

    def test_caches_empty_list(self):
        TestAdapter.count = 0
        self.relation.fetch_records()
        self.assertEqual(len(TestAdapter.calls), 1)

        self.relation.fetch_records()
        self.assertEqual(len(TestAdapter.calls), 1)

    def test_list_is_alias(self):
        """list method should be an alias for fetch_records"""
        self.assertEqual(self.relation.list(), self.relation.fetch_records())



##
# Test the query methods (where, select, limit, from, etc.)
#
# Each of these methods should make a copy of the relation and return the
# newly created copy with the updates made by the specific method.  The original
# relation object should not be modified
#
class QueryMethodsTestCase(BaseRelationTestCase):

    def test_from_underscore(self):
        """Because `from` is a keyword -- allow `from_` to be called"""
        rel = self.relation.from_('foo')
        self.assertEqual(rel.params['from'], 'foo')

    def test_singular_query_methods(self):
        """singular query methods should return new relation with new value"""
        for method_name in singular_query_methods:
            method = getattr(self.relation, method_name)

            relation = method('foo')
            self.assertEqual(relation.params[method_name], 'foo')
            self.assertEqual(self.relation.params[method_name], None)

            relation = method('poop')
            self.assertEqual(relation.params[method_name], 'poop')
            self.assertEqual(self.relation.params[method_name], None)

    def test_plural_query_methods(self):
        """
        plural query methods should return new relation with appended values
        """
        for method_name in plural_query_methods:
            method = getattr(self.relation, method_name)

            relation = method('foo', 'baz')
            self.assertEqual(relation.params[method_name], ['foo', 'baz'])
            self.assertEqual(self.relation.params[method_name], [])

            next_relation = getattr(relation, method_name)('bar')
            self.assertEqual(next_relation.params[method_name],
                    ['foo', 'baz', 'bar'])
            self.assertEqual(relation.params[method_name], ['foo', 'baz'])
            self.assertEqual(self.relation.params[method_name], [])

##
# Test merging two relations
#
class MergeRelationTestCase(BaseRelationTestCase):

    def test_singular_methods(self):
        """should overwrite singular values with new relation's value"""
        new_relation = Relation(self.Test).limit(5).offset(3)
        relation = self.relation.limit(1).from_('foo')

        merged = relation.merge(new_relation)

        self.assertEqual(relation.params['limit'], 1)

        self.assertEqual(merged.params['limit'], 5)
        self.assertEqual(merged.params['offset'], 3)
        self.assertEqual(merged.params['from'], 'foo')


    def test_plural_methods(self):
        """should append plural values with new relation's values"""
        new_relation = Relation(self.Test).where('foo', 'bar').select('poop')
        relation = self.relation.group('baz').where('baz')

        merged = relation.merge(new_relation)

        self.assertEqual(relation.params['group'], ['baz'])
        self.assertEqual(relation.params['where'], ['baz'])

        self.assertEqual(merged.params['where'], ['baz', 'foo', 'bar'])
        self.assertEqual(merged.params['group'], ['baz'])
        self.assertEqual(merged.params['select'], ['poop'])

##
# Test that modifiers behaves almost like a query method
#
class ModifiersTestCase(BaseRelationTestCase):

    def test_methods_defined(self):
        """should define a modifiers and modifiers_value method"""
        self.assertTrue(hasattr(self.relation, 'modifiers'))
        self.assertTrue(callable(self.relation.modifiers))
        self.assertTrue(hasattr(self.relation, 'modifiers_value'))
        self.assertTrue(callable(self.relation.modifiers_value))

    def test_init(self):
        """
        should set a modifiers key in the relation params and initialize it to
        an empty list
        """
        self.assertTrue('modifiers' in self.relation.params)
        self.assertEqual(self.relation.params['modifiers'], [])

    def test_new_relation(self):
        """should return a new relation when calling modifiers()"""
        relation = self.relation.modifiers({})
        self.assertEqual(type(relation), type(self.relation))
        self.assertNotEqual(hash(relation), hash(self.relation))

    def test_write_to_params(self):
        """should store modifiers in the params dict"""
        relation = self.relation.modifiers({'foo': 'bar'})
        self.assertEqual(relation.params['modifiers'][0]['foo'], 'bar')

    def test_delegate_to_scoped(self):
        """should delgate Base.modifiers to Base.scoped.modifiers"""
        self.assertTrue(hasattr(self.Test, 'modifiers'))
        self.assertTrue(callable(self.Test.modifiers))

    def test_value_always_dict(self):
        """modifiers value should always return a dict"""
        self.assertEqual(self.relation.modifiers_value(), {})

    def test_combine_dicts(self):
        """should combine all of the dict values into one dict"""
        relation = (self.relation.modifiers({'foo': 'bar'})
                                 .modifiers({'biz': 'baz'}))
        self.assertEqual(relation.modifiers_value(), {
            'foo': 'bar', 'biz': 'baz'
        })

    def test_eval_lambdas(self):
        """should evaluate lambdas when building modifiers_value dict"""
        relation = self.relation.modifiers(lambda: {'foo': 'bar'})
        self.assertEqual(relation.modifiers_value(), {'foo': 'bar'})

    def test_raise_when_value_not_dict(self):
        """should raise if a non-dict value is added to the modifiers"""
        relation = self.relation.modifiers('eek!')
        self.assertRaises(TypeError, relation.modifiers_value)

    def test_raise_when_lambda_not_dict(self):
        """should raise if a lambda value does not return a dict"""
        relation = self.relation.modifiers(lambda: 'gah!')
        self.assertRaises(TypeError, relation.modifiers_value)

    def test_reset_when_none(self):
        """should remove old modifiers if modifiers called with None"""
        relation = self.relation.modifiers({'foo': 'bar'}).modifiers(None)
        self.assertEqual(relation.modifiers_value(), {})

    def test_combine_in_order(self):
        """should combine dict values in the order they were given"""
        relation = (self.relation.modifiers({'foo': 'bar', 'biz': 'baz'})
                                 .modifiers({'biz': 'bur', 'dum': 'dum'})
                                 .modifiers(lambda: {'dum': 'der'}))
        self.assertEqual(relation.modifiers_value(), {
            'foo': 'bar', 'biz': 'bur', 'dum': 'der'
        })

    def test_merge(self):
        """should include modifiers when merging relation"""
        r1 = self.relation.modifiers({'foo': 'bar'})
        r2 = self.relation.merge(r1)
        self.assertEqual(self.relation.modifiers_value(), {})
        self.assertEqual(r1.modifiers_value(), {'foo': 'bar'})
        self.assertEqual(r2.modifiers_value(), {'foo': 'bar'})

    def test_apply_finder_options(self):
        """should recognize modifiers when applying finder options"""
        relation = self.relation.apply_finder_options({
            'modifiers': {'foo': 'bar'}
        })
        self.assertEqual(relation.modifiers_value(), {'foo': 'bar'})

    def test_exclude_from_query(self):
        """should not include modifiers in the query() dict"""
        relation = self.relation.modifiers({'foo': 'bar'})
        self.assertFalse('modifiers' in relation.query())

    def test_include_in_scopes(self):
        """modifiers should be usable in scopes"""
        self.Test.scope('mod', modifiers={'foo': 'bar'})
        scoped = self.Test.scoped()
        relation = scoped.mod()
        self.assertEqual(relation.modifiers_value(), {'foo': 'bar'})

    def test_cache_modifiers_value(self):
        """should cache combined modifiers dict on the first call"""
        relation = self.relation.modifiers({'foo': 'bar'})
        self.assertFalse(hasattr(relation, '_modifiers'))
        relation.modifiers_value()
        self.assertTrue(hasattr(relation, '_modifiers'))
        self.assertEqual(relation._modifiers, relation.modifiers_value())


##
# Test Relation instance delegates defined scopes to its klass
#
class RelationDelegatesScopesTestCase(BaseRelationTestCase):

    def test_delegates_to_klass(self):
        """should delegate to klass if declared scope"""
        self.assertEqual(self.relation.foo().params['where'], ['bar'])

    def test_doesnt_delegate_when_not_scope(self):
        """should raise AttributeError if not a scope on klass"""
        self.assertRaises(AttributeError, getattr, self.relation, 'baz')

    def test_merges_scope(self):
        """should keep any previous relation data"""
        rel = self.relation.where('foo').foo().where('baz')
        self.assertEqual(rel.params['where'], ['foo', 'bar', 'baz'])


##
# Scoping method
#
# Takes a function as an argument and makes any calls within that function
# scoped within the current relation
#
#
# TODO: Need a scoped aware Base before this is possible
#


##
# apply_finder_options method
#
# Takes a dictionary of finder options and applies them to the relation
#
class ApplyFinderOptionsTestCase(BaseRelationTestCase):

    def test_singular_query_methods(self):
        """Should take any singular query methods as options"""
        rel = self.relation.apply_finder_options({ 'from': 'foo', 'limit': 1 })

        self.assertEqual(rel.params['from'], 'foo')
        self.assertEqual(rel.params['limit'], 1)

    def test_plural_query_methods(self):
        """Should take any plural query methods as options"""
        rel = self.relation.apply_finder_options({
            'where': { 'id': 1 }, 'group': ['bar', 'baz'] })

        self.assertEqual(rel.params['where'], [{ 'id': 1 }])
        self.assertEqual(rel.params['group'], ['bar', 'baz'])

    def test_conditions_key(self):
        """Should allow conditions key as alias for where"""
        rel = self.relation.apply_finder_options({
            'conditions': { 'id': 1 }})

        self.assertEqual(rel.params['where'], [{ 'id': 1 }])

##
# All method
#
# Takes a dictionary of finder options and applies them to the existing query
# and executes it returning the resulting list
#

class RelationAllMethodTestCase(BaseRelationTestCase):
    """Relation class all method"""

    def test_arguments_optional(self):
        """should just return array if no arguments passed"""
        result = self.relation.all()

        self.assertEqual(len(result), 3)
        assert( isinstance(result, list) )

    def test_applies_finder_options(self):
        """Should take finder options and apply them"""
        result = self.relation.where('bar').all({ 'where': 'foo' })

        self.assertEqual(len(result), 3)
        self.assertEqual(TestAdapter.calls[-1], { 'where': ['bar', 'foo']})


##
# First method
#
# Takes a dictionary of finder options and applies them to the existing query
# together with a limit(1) and executes it returning the first record
#

class RelationFirstMethodTestCase(BaseRelationTestCase):
    """Relation class first method"""
    pass

    def test_arguments_optional(self):
        """Should optionally take parameters and return record"""
        result = self.relation.first()

        self.assertEqual(result.id, 1)
        assert isinstance(result, self.relation.klass)

    def test_applies_finder_options(self):
        """Should apply finder options and return record"""
        result = self.relation.where('bar').first({ 'where': 'foo' })

        assert isinstance(result, self.relation.klass)
        self.assertEqual(TestAdapter.calls[-1]['where'], ['bar', 'foo'])

    def test_limit_1_added(self):
        """Should add limit(1) scope"""
        result = self.relation.limit(5).first({ 'limit': 10 })

        assert isinstance(result, self.relation.klass)
        self.assertEqual(TestAdapter.calls[-1]['limit'], 1)

##
# Find method
#
# If first argument is an integer or list it will assume they are primary keys
# and scope the query with that requirement.  If any of the records were not
# returned a RecordNotFound exception will be raised.
#
# TODO: Add this method

##
# Fresh scope
#
# Ensures that next call will bypass any cached values and refetch data from
# the data store.
#
# TODO: Add this method


##
# When the Relation object is treated like a list the query should be executed
# and the operation should be performed on the resulting list
#
class RelationActsLikeListTestCase(BaseRelationTestCase):

    def test_array_comprehension(self):
        """When used in an array comprehension it should behave like a list"""
        ary = [ i.id for i in self.relation ]
        self.assertEqual(ary, [1,1,1])

    def test_for_loop(self):
        """When used in a for loop it should behave like a list"""
        for i in self.relation:
            self.assertEqual(i.id, 1)

    def test_functional_structures(self):
        """When used in a functional structure it should behave like a list"""
        self.assertEqual(map(lambda(i): i.id, self.relation), [1,1,1])

    def test_array_indexing(self):
        """getitem should return the correct item in the list"""
        self.assertEqual(self.relation[0].id, 1)

    def test_splicing(self):
        """Splices should work on the list of records"""
        result = [ i.id for i in self.relation[0:2] ]
        self.assertEqual(result, [1, 1])

    def test_len(self):
        """len should return record count"""
        self.assertEqual(len(self.relation), 3)


