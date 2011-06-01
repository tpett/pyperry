import tests
import unittest
from nose.plugins.skip import SkipTest
import pyperry
import fixtures.association_models
import fixtures.extended_association_models
from fixtures.test_adapter import TestAdapter
from pyperry import errors
from pyperry import Relation, Association
from pyperry.association import BelongsTo, Has, HasMany, HasOne, HasManyThrough
from pyperry.middlewares.local_cache import LocalCache

finder_options = (Relation.singular_query_methods + Relation.plural_query_methods +
    Relation.aliases.keys())

class BaseAssociationTestCase(unittest.TestCase):
    pass

class GenericAssociationTestCase(BaseAssociationTestCase):

    def setUp(self):
        self.klass = fixtures.association_models.Test
        self.id = 'associations'
        self.args = { 'foo': 'bar' }
        self.primary_key = 'primary_key'
        self.foreign_key = 'foreign_key'
        self.source_class = fixtures.association_models.Source
        self.association = Association(self.klass, self.id, **self.args)

    def test_initialize(self):
        """should take klass, id, and kwarg arguments on initialize"""
        self.assertEqual(self.klass, self.association.target_klass)
        self.assertEqual(self.id, self.association.id)
        self.assertEqual(self.args, self.association.options)

    def test_type_raises(self):
        """should raise a NotImplementedError on type"""
        self.assertRaises(NotImplementedError, self.association.type)

    def test_polymorphic_raises(self):
        """should raise a NotImplementedError on polymorphic"""
        self.assertRaises(NotImplementedError, self.association.polymorphic)

    def test_colletion_raises(self):
        """should raise a NotImplementedError on collection"""
        self.assertRaises(NotImplementedError, self.association.collection)

    def test_scope_raises(self):
        """should raise a NotImplementedError on scope"""
        self.assertRaises(NotImplementedError, self.association.scope)

    def test_foreign_key_returns_None(self):
        """should return None when no foreign_key was passed"""
        self.assertEqual(None, self.association.foreign_key)

    def test_foreign_key_returns_foreign_key(self):
        """should return the foreign_key that was passed in options"""
        self.association.foreign_key = self.foreign_key
        self.assertEqual(self.foreign_key, self.association.foreign_key)

    def test_eager_loadable(self):
        """should be eager_loadable when the moethods do not rely
        on instance data"""
        association = BelongsTo(self.klass, self.id)
        self.assertEqual(True, association.eager_loadable())

    def test_eager_loadable_lambda(self):
        """should return false if a block is used for the param of
        any finder option"""
        for option in finder_options:
            self.assertEqual(False, Association(self.klass, self.id, **{
                option: lambda x: {}
            }).eager_loadable())

    def test_eager_loadable_poly(self):
        """should return false for polymorphic belongs to associations"""
        association = BelongsTo(self.klass, self.id, polymorphic=True)
        self.assertEqual(association.eager_loadable(), False)

    def test_source_klass(self):
        """should return the class that is passed in the options"""
        self.association.options['klass'] = self.source_class
        self.assertEqual(self.source_class, self.association.source_klass())

class SourceClassTestCase(BaseAssociationTestCase):

    def setUp(self):
        self.site = fixtures.association_models.Site
        self.article = fixtures.association_models.Article
        self.comment = fixtures.association_models.Comment
        self.company = fixtures.association_models.Company
        self.person = fixtures.extended_association_models.Person

    def test_klass(self):
        """should return the class specified by :class_name option"""
        self.assertEqual(self.site, self.article.defined_associations['site'].source_klass())

    def test_namespace(self):
        """should return the class in the proper namespace"""
        self.assertEqual(self.person, self.company.defined_associations['employees'].source_klass())

    # need to test polymorphic
    def test_polymorphic(self):
        """should use the optional object parameter's polymorphic _type
        attribute to determine the class if polymorphic is true"""
        comment = self.comment({'parent_type': "Site"})
        self.assertEqual(self.site, comment.__class__.defined_associations['parent'].source_klass(comment))

    def test_malicious_values(self):
        """should sanitize malicious values in _type column"""
        comment = self.comment({'parent_type': 'Site.UHOH = True'})
        comment.__class__.defined_associations['parent'].source_klass(comment)
        try:
            UHOH
        except NameError:
            pass
        except:
            self.assertTrue(False)

    def test_missing_types(self):
        """should raise ModelNotDefined for missing types"""
        comment = self.comment({'parent_type': 'OhSnap'})
        self.assertRaises(errors.ModelNotDefined,
            comment.__class__.defined_associations['parent'].source_klass, comment)

class BelongsToTestCase(BaseAssociationTestCase):

    def setUp(self):
        self.klass = fixtures.association_models.Test
        self.id = 'belongs'
        self.foreign_key = 'some_id'
        self.belongs_to = BelongsTo(self.klass, self.id)
        self.article = fixtures.association_models.Article

    def test_type(self):
        """should return 'belongs_to' as the type"""
        self.assertEqual('belongs_to', self.belongs_to.type())

    def test_collection(self):
        """should return False on a collection"""
        self.assertEqual(False, self.belongs_to.collection())

    def test_foreign_key_not_set(self):
        """should return the association's foreign_key if one is set"""
        self.belongs_to.foreign_key = self.foreign_key
        self.assertEqual(self.foreign_key, self.belongs_to.foreign_key)

    def test_foreign_key_not_set_in_super(self):
        """sould return #{id}_id if the association doesn't have a foreign_key"""
        self.assertEqual('%s_id' % self.id, self.belongs_to.foreign_key)

    # need to test polymorphic and polymorphic_type
    def test_polymorphic(self):
        """should return true for polymorphic if polymorphic options specified
        and false otherwise"""
        self.assertFalse(self.belongs_to.polymorphic())
        belongs = BelongsTo(self.klass, 'bar', polymorphic=True)
        self.assertTrue(belongs.polymorphic())

    def test_polymorphic_type(self):
        """should return #{id}_type if it is polymorphic"""
        belongs = BelongsTo(self.klass, 'bar', polymorphic=True)
        self.assertEqual('bar_type', belongs.polymorphic_type())

    # scope tests
    def test_scope_foreign_key(self):
        """should return None if no foreign_key present"""
        record = self.article({})
        self.assertEqual(None, self.article.defined_associations['site'].scope(record))

    def test_scope_for_source_class(self):
        """should return a scope for the source class if association present"""
        record = self.article({'site_id': 1})
        self.assertTrue(self.article.defined_associations['site'].scope(record).__class__ is Relation)

    def test_scope_options(self):
        """should the scope should have the options for the association query"""
        record = self.article({'site_id': 1})
        self.assertEqual({'id': 1}, self.article.defined_associations['site'].scope(record).params['where'][0])


class HasTestCase(BaseAssociationTestCase):

    def setUp(self):
        self.site = fixtures.association_models.Site
        self.klass = fixtures.association_models.Test
        self.id = 'has'
        self.foreign_key = 'some_id'
        self.has = Has(self.klass, self.id)
        self.article = fixtures.association_models.Article

    def test_primary_key(self):
        """should use 'id' as default primary key"""
        self.assertEqual('id', self.has.primary_key())

    # Need to test polymorphic stuff
    def test_polymorphic(self):
        """should return set polymorphic true if 'as' option passed and false otherwise"""
        self.assertEqual(False, self.has.polymorphic())
        self.assertTrue(Has(self.klass, 'bar', _as='parent').polymorphic())

    def test_foreign_key(self):
        """should return the lowercase target class name followed by _id if association is not polymorphic"""
        articles = self.site.defined_associations['articles']
        self.assertEqual('site_id', articles.foreign_key)

    def test_foreign_key_option(self):
        """should use 'foreign_key' option if specified"""
        a = Has(self.klass, 'bar', foreign_key='purple_monkey')
        self.assertEqual('purple_monkey', a.foreign_key)

    # scope tests
    def test_scope_foreign_key(self):
        """should return None if no foreign_key present"""
        record = self.article({})
        self.assertEqual(None, self.article.defined_associations['comments'].scope(record))

    def test_scope_for_source_class(self):
        """should return a scope for the source class if association present"""
        record = self.article({'id': 1})
        self.assertTrue(self.article.defined_associations['comments'].scope(record).__class__ is Relation)

    def test_scope_options(self):
        """should the scope should have the options for the association method"""
        record = self.article({'id': 1})
        self.assertEqual([{ 'parent_id': 1 }, { 'parent_type': 'Article' }],
            self.article.defined_associations['comments'].scope(record).params['where'])

    def test_scope_base_assoc_options(self):
        """should include base association options in the scope"""
        record = self.article({'id': 1})
        self.assertEqual("text LIKE '%awesome%'",
            self.article.defined_associations['awesome_comments'].scope(record).params['where'][0])

class HasManyTestCase(BaseAssociationTestCase):

    def setUp(self):
        self.klass = fixtures.association_models.Test
        self.id = 'has_many'
        self.foreign_key = 'some_id'
        self.has_many = HasMany(self.klass, self.id)

    def test_type(self):
        """should set type to has_many"""
        self.assertEqual('has_many', self.has_many.type())

    def test_collection(self):
        """should set collection to true"""
        self.assertTrue(self.has_many.collection())

class HasOneTestCase(BaseAssociationTestCase):

    def setUp(self):
        self.klass = fixtures.association_models.Test
        self.id = 'has_one'
        self.foreign_key = 'some_id'
        self.has_one = HasOne(self.klass, self.id)

    def test_type(self):
        """should set type to has_one"""
        self.assertEqual('has_one', self.has_one.type())

    def test_collection(self):
        """should set collection to false"""
        self.assertFalse(self.has_one.collection())


class HasManyThroughTestCase(BaseAssociationTestCase):

    MODELS = ['Site', 'Comment', 'Article', 'Person']

    def setUp(self):
        self.klass = fixtures.association_models.Test
        self.id = 'has_many_through'
        self.association = HasManyThrough(self.klass, self.id)
        self.adapter = TestAdapter

        # assign fixtures.association_models.ModelClass to self.ModelClass
        for m in self.MODELS:
            setattr(self, m, getattr(fixtures.association_models, m))

    def tearDown(self):
        """reset read adapter instances for each model"""
        for m in self.MODELS:
            model = getattr(self, m)
            model._adapters = {}
            if '_middlewares' in model.adapter_config['read']:
                del model.adapter_config['read']['_middlewares']
            model.set_primary_key('id')


    def test_type(self):
        """should set association type to has_many_through"""
        self.assertEqual(self.association.type(), 'has_many_through')

    def test_collection(self):
        """should set collection to true"""
        self.assertEqual(self.association.collection(), True)

    def test_not_polymorphic(self):
        """should not allow polymorphic associations"""
        association = HasManyThrough(self.Site, 'comments', through='articles',
                                     _as='whatever')
        self.assertEqual(association.polymorphic(), False)

    def test_through_exists(self):
        """should raise when through is not an existing association"""
        association = HasManyThrough(self.Site, self.id, through='a_tunnel')
        self.assertRaises(errors.AssociationNotFound,
                          association.proxy_association)

    def test_source_association_exists_on_proxy(self):
        """
        should raise when the source association is not defined on the proxy
        association's class
        """
        association = HasManyThrough(self.Site, self.id, through='articles')
        self.assertRaises(errors.AssociationNotFound,
                          association.source_association)

    def test_association_name(self):
        """should use the source association that matches the association id"""
        association = HasManyThrough(self.Site, 'comments', through='articles')
        self.assertEqual(association.source_association().id, 'comments')

    def test_source_option(self):
        """
        should use the source option as the target association name if provided
        """
        association = HasManyThrough(self.Site, 'dumb_comments',
                                     through='articles', source='comments')
        self.assertEqual(association.source_association().id, 'comments')

    def test_relation_mapped_to_source(self):
        """should return a relation mapped to the source association's class"""
        self.adapter.data = {'id': 1}
        site = self.Site.first()
        comments = site.article_comments()

        self.assertEqual(type(comments), pyperry.Relation)
        self.assertEqual(comments.klass, self.Comment)

    def test_executes_2_queries(self):
        """should execute two queries when calling the association method"""
        self.adapter.data = {'id': 1}
        site = self.Site.first()

        self.adapter.calls = []
        comments = site.article_comments().all()
        self.assertEqual(len(self.adapter.calls), 2)

    def test_when_source_is_has(self):
        """
        should use the primary key values from the proxy association and the
        foreign key attribute from the source association when the source
        association is a has association
        """
        self.adapter.data = {'id': 1}
        site = self.Site.first()
        self.adapter.calls = []

        self.adapter.data = [{'id': 1}, {'id': 2}, {'id': 3}]
        relation = site.article_comments()
        where_values = relation.query()['where']
        self.assertEqual(len(self.adapter.calls), 1)

        where_values.sort()
        self.assertEqual(self.Comment, relation.klass)
        self.assertEqual(where_values[0], {'parent_id': [1,2,3]})
        self.assertEqual(where_values[1], {'parent_type': 'Article'})

    def test_custom_proxy_pk_when_source_is_has(self):
        """
        should use the source association's primary_key attribute to
        collect the proxy_ids when the source association is a has
        """
        self.adapter.data = {'id': 1}
        person = self.Person.first()
        self.adapter.calls = []

        self.Site.set_primary_key('name')

        self.adapter.data = [{'id': 1, 'name': 'a'}, {'id': 2, 'name': 'b'},
                {'id': 3, 'name': 'c'}]
        relation = person.maintained_articles()
        where_values = relation.query()['where']
        self.assertEqual(len(self.adapter.calls), 1)

        self.assertEqual(self.Article, relation.klass)
        # For this test we are assuming that Article.site_id references
        # Site.name instead of assuming Article.site_id references Site.id
        self.assertEqual(where_values, [{'site_id': ['a','b','c']}])


    def test_when_source_is_belongs_to(self):
        """
        should use the foreign key values from the proxy association and the
        primary key attribute from the source association when the source
        association is a belongs_to association
        """
        self.adapter.data = {'id': 1}
        article = self.Article.first()

        self.adapter.calls = []
        self.adapter.data = [{'id': 1, 'person_id': 11},
                {'id': 2, 'person_id': 12}, {'id': 3, 'person_id': 13}]

        relation = article.comment_authors()
        where_values = relation.query()['where']

        self.assertEqual(len(self.adapter.calls), 1)
        self.assertEqual(relation.klass, self.Person)
        self.assertEqual([{'id': [11, 12, 13]}], where_values)

    def test_when_source_is_polymorphic_belongs_to(self):
        """
        should use the source_type attribute to determine the source's class
        when the source association is a polymorphic belongs_to asssociation
        """
        self.adapter.data = {'id': 1}
        person = self.Person.first()

        self.adapter.calls = []
        self.adapter.data = [
            {'id': 1, 'parent_id': 11, 'parent_type': 'FooBar'},
            {'id': 2, 'parent_id': 12, 'parent_type': 'FooBar'},
            {'id': 3, 'parent_id': 13, 'parent_type': 'FooBar'}
        ] # parent_type should be ignored by has many through

        relation = person.commented_articles()
        where_values = relation.query()['where']

        self.assertEqual(len(self.adapter.calls), 1)
        self.assertEqual(relation.klass, self.Article)
        self.assertEqual([{'id': [11, 12, 13]}], where_values)

    def test_fresh(self):
        """
        should apply the fresh scope to both the proxy association and the
        source association
        """
        raise SkipTest
        # TODO: currently it is not possible to share the fresh scope between
        # the proxy and source associations

        self.adapter.data = {'id': 1}
        self.Article.add_middleware('read', LocalCache)
        self.Comment.add_middleware('read', LocalCache)
        self.Article._adapters = {}
        self.Comment._adapters = {}

        site = self.Site.first()
        self.adapter.calls = []

        relation = site.article_comments()
        relation.all()
        self.assertEqual(len(self.adapter.calls), 2)

        relation.all()
        self.assertEqual(len(self.adapter.calls), 2) # should hit cache

        relation = relation.fresh().all()
        self.assertEqual(len(self.adapter.calls), 4) # should skip cache


class TargetModel(pyperry.Base):
    def _config(c):
        c.attributes('id', 'foo', 'whatever_type')
        c.set_primary_key('foo')

class SourceModel(pyperry.Base):
    def _config(c):
        c.attributes('id', 'bar')
        c.set_primary_key('bar')

class PrimaryKeyTestCase(BaseAssociationTestCase):

    def test_default(self):
        """
        should return target class's primary key if no primary_key was passed
        as a kwarg
        """
        association = Association(TargetModel, 'whatever')
        self.assertEqual(TargetModel.primary_key(), association.primary_key())

    def test_kwarg(self):
        """should use the primary key given in the kwargs"""
        association = BelongsTo(TargetModel, 'whatever', primary_key='asdf')
        self.assertEqual(association.primary_key(), 'asdf')
        association = Has(TargetModel, 'whatever', primary_key='asdf')
        self.assertEqual(association.primary_key(), 'asdf')

    def test_belongs_to(self):
        """
        should use the source class's primary key in a belongs to association
        """
        association = BelongsTo(TargetModel, 'whatever',
                                class_name='SourceModel')
        self.assertEqual(association.primary_key(), SourceModel.primary_key())

    def test_polymorphic_belongs_to(self):
        """
        should use the source class's primary key in a polymorphic belongs to
        association
        """
        association = BelongsTo(TargetModel, 'whatever', polymorphic=True)
        target_instance = TargetModel({'whatever_type': 'SourceModel'})
        self.assertEqual(association.primary_key(target_instance),
                         SourceModel.primary_key())

    def test_has_one(self):
        """
        should use the target class's primary key in a has one association
        """
        association = HasOne(TargetModel, 'whatever', class_name='SourceModel')
        self.assertEqual(association.primary_key(), TargetModel.primary_key())

    def test_has_many(self):
        """
        should use the target class's primary key in a has many association
        """
        association = HasMany(TargetModel, 'whatever', class_name='SourceModel')
        self.assertEqual(association.primary_key(), TargetModel.primary_key())
