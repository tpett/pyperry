import pyperry
from pyperry.attribute import Attribute
from test_adapter import TestAdapter

class Test(pyperry.Base):
    id = Attribute()

class Source(pyperry.Base):
    id = Attribute()

class AssocTest(pyperry.Base):
    def _config(c):
        c.configure('read', adapter=TestAdapter)

class Site(AssocTest):
    id = Attribute()
    name = Attribute()
    maintainer_id = Attribute()
    def _config(c):
        c.belongs_to('maintainer', klass=lambda: Person)
        c.has_one('headline', klass=lambda: Article)
        c.has_one('master_comment', as_='parent', class_name='Comment')
        c.has_one('fun_articles', class_name='Article', conditions="1",
            sql=lambda s: """
                SELECT articles.*
                FROM articles
                WHERE articles.text LIKE %%monkeyonabobsled%%
                    AND articles.site_id = %s
            """ % s.id
        )
        c.has_many('articles', class_name='Article',
                   namespace='tests.fixtures.association_models')
        c.has_many('comments', as_='parent', class_name='Comment')
        c.has_many('awesome_comments', class_name='Comment', conditions="1",
            sql=lambda s: """
                SELECT comments.*
                FROM comments
                WHERE comments.text LIKE '%%awesome%%' AND
                    parent_type = "Site" AND parent_id = %s
            """ % s.id
        )
        c.has_many('article_comments', through='articles', source='comments')

class Article(AssocTest):
    id = Attribute()
    site_id = Attribute()
    author_id = Attribute()
    title = Attribute()
    text = Attribute()

    def _config(c):
        c.belongs_to('site', class_name='Site')
        c.belongs_to('author', class_name='Person')
        c.has_many('comments', as_='parent', class_name='Comment')
        c.has_many('awesome_comments', as_='parent', class_name='Comment',
            conditions="text LIKE '%awesome%'")
        c.has_many('comment_authors', through='comments', source='author')

class Comment(AssocTest):
    id = Attribute()
    person_id = Attribute()
    parent_id = Attribute()
    parent_type = Attribute()
    text = Attribute()

    def _config(c):
        c.belongs_to('parent', polymorphic=True)
        c.belongs_to('author', class_name='Person', foreign_key='person_id',
                     namespace='tests.fixtures.association_models')

class Person(AssocTest):
    id = Attribute()
    name = Attribute()
    manager_id = Attribute()
    company_id = Attribute()

    def _config(c):
        c.belongs_to('manager', class_name='Person', foreign_key='manager_id')
        c.has_many('authored_comments', class_name='Comment', foreign_key='person_id')
        c.has_many('articles', class_name='Article', foreign_key='author_id')
        c.has_many('comments', as_='parent', class_name='Comment')
        c.has_many('employees', class_name='Person', foreign_key='manager_id')
        c.has_many('sites', class_name='Site', foreign_key='maintainer_id')
        c.has_many('commented_articles', through='comments', source='parent',
                   source_type='Article')
        c.has_many('maintained_articles', through='sites', source='articles')

class Company(AssocTest):
    id = Attribute()
    name = Attribute()

    def _config(c):
        c.has_many('employees', class_name='Person',
            namespace='tests.fixtures.extended_association_models')
