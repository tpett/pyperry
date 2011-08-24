import tests
import unittest
from nose.plugins.skip import SkipTest

import pyperry
from pyperry.errors import AssociationNotFound, AssociationPreloadNotSupported
from pyperry.processors.preload_associations import PreloadAssociations
from pyperry.field import Field

from tests.fixtures.test_adapter import PreloadTestAdapter
from tests.fixtures.association_models import Site, Article, Comment, Person

class PreloadAssociationsProcessorTestCase(unittest.TestCase):

    MODELS = [Site, Article, Comment, Person]

    def setUp(self):
        class Model(pyperry.Base):
            id = Field()

            def _config(c):
                c.configure('read', adapter=PreloadTestAdapter)
                c.add_processor('read', PreloadAssociations)

        for klass in self.MODELS:
            klass._adapters = {}
            klass.configure('read', adapter=PreloadTestAdapter)
            klass.add_processor('read', PreloadAssociations)

        self.adapter = Model.adapter('read')
        self.relation = Model.scoped()
        self.Model = Model

        self.data = lambda count: [{
            'Site': {'id': x, 'maintainer_id': 100},
            'Article': {'id': 1, 'site_id': 1},
            'Comment': {'id': 1, 'parent_id': 2, 'parent_type': 'Site'},
            'Person': {'id': 100},
            'Model': {'id': 1}
        } for x in range(1, count + 1)]
        PreloadTestAdapter.data = self.data(5)

    def tearDown(self):
        self.adapter.reset()

        # Put models back the way they were
        for klass in self.MODELS:
            klass._adapters = {}
            read_config = klass.adapter_config['read']
            if '_processors' in read_config:
                del read_config['_processors']


    def test_no_effect(self):
        """should not effect a normal request"""
        self.adapter.data = self.data(1)
        results = self.adapter(relation=self.relation, mode='read')
        self.assertEqual([{'id': 1}], [r.attributes for r in results])
        self.assertEqual(len(self.adapter.calls), 1)

    def test_run_additional_queries(self):
        """
        should run n additional queries, where n is the number of associations
        in the query 'includes' value
        """
        Site.includes('articles', 'comments', 'maintainer').all()
        self.assertEqual(len(self.adapter.calls), 4)

    def test_include_results(self):
        """should include the preload results on the relation"""
        rel = Site.includes('articles', 'comments', 'maintainer', 'headline')
        results = rel.all()
        site = results[0]
        call_count = len(self.adapter.calls)

        # has_many
        self.assertEqual(type(site.articles), pyperry.Relation)
        for article in site.articles:
            self.assertEqual(type(article), Article)

        # has_many polymorphic
        self.assertEqual(type(site.comments), pyperry.Relation)
        for comment in site.comments:
            self.assertEqual(type(comment), Comment)

        # belongs_to
        self.assertEqual(type(site.maintainer), Person)

        # has_one
        self.assertEqual(type(site.headline), Article)

        # Ensure no more calls were made during our assertions
        self.assertEqual(len(self.adapter.calls), call_count)


    def test_only_include_matching_records(self):
        """should only include records that match for a given model"""
        rel = Site.includes('articles', 'comments', 'maintainer', 'headline')
        sites = rel.all()
        call_count = len(self.adapter.calls)

        for site in sites:
            # has_many
            for article in site.articles:
                self.assertEqual(article.site_id, site.id)
            # has_many polymorphic
            for comment in site.comments:
                self.assertEqual(comment.parent_id, site.id)
                self.assertEqual(comment.parent_type, 'Site')
            # belongs_to
            self.assertEqual(site.maintainer.id, site.maintainer_id)
            # has_one
            if site.id == 1:
                self.assertEqual(site.headline.site_id, site.id)

        call_count = len(self.adapter.calls)

    def test_include_modifiers(self):
        """
        should include the modifiers value from the original query in
        subsequent queries
        """
        test = {'agentp': 'platypus', 'agentm': 'monkey'}
        sites = Site.modifiers(test).includes('articles', 'comments',
                            'maintainer', 'headline').all()

        for call in self.adapter.calls:
            self.assertEqual(call.modifiers_value(), test)

    def test_cache_results(self):
        """
        should cache results for collection associations in a relation with the
        correct scope
        """
        site = Site.includes('articles', 'comments')[0]

        article_relation = site.defined_associations['articles'].scope(site)
        comment_relation = site.defined_associations['comments'].scope(site)

        self.assertEqual(site.articles.query(), article_relation.query())
        self.assertEqual(site.comments.query(), comment_relation.query())

    def test_nested_includes(self):
        """should nest includes queries using a tree like syntax"""
        data = self.data(5)
        for d in data:
            d.update({
                'Comment': {'parent_id': 1, 'parent_type': 'Article',
                            'person_id': 1},
                'Person': {'id': 1}
            })
        PreloadTestAdapter.data = data

        rel = Site.includes({'articles': 'comments', 'comments': 'author'})
        sites = rel.all()
        self.assertEqual(len(self.adapter.calls), 5)

    def test_association_not_found(self):
        """
        should raise AssociationNotFound for associations given in 'includes'
        that do not exist on the model
        """
        self.assertRaises(AssociationNotFound, Site.includes('batteries').all)

    def test_preload_not_supported(self):
        """
        should raise AssociationPreloadNotSupported if the association requires
        an instance of a model (e.g. polymorphic belongs_to)
        """
        self.assertRaises(AssociationPreloadNotSupported,
                          Site.includes('fun_articles').all)
