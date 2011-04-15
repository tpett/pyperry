import pyperry
from test_adapter import TestAdapter

class Test(pyperry.Base):
    def _config(c):
        c.attributes('id')

class Target(pyperry.Base):
    def _config(c):
        c.attributes('id')

class AssocTest(pyperry.Base):
    def _config(c):
        c.configure_read(adapter=TestAdapter)

class Site(AssocTest):
    def _config(c):
        c.attributes('id', 'name', 'maintainer_id')
        c.belongs_to('maintainer', klass=lambda: Person)
        c.has_one('headline', klass=lambda: Article)
        c.has_one('master_comment', _as='parent', class_name='Comment')
        c.has_one('fun_articles', class_name='Article', conditions="1",
            sql=lambda s: """
                SELECT articles.*
                FROM articles
                WHERE articles.text LIKE %%monkeyonabobsled%%
                    AND articles.site_id = %s
            """ % s.id
        )
        c.has_many('articles', class_name='Article')
        c.has_many('comments', _as='parent', class_name='Comment')
        c.has_many('awesome_comments', class_name='Comment', conditions="1",
            sql=lambda s: """
                SELECT comments.*
                FROM comments
                WHERE comments.text LIKE '%%awesome%%' AND
                    parent_type = "Site" AND parent_id = %s
            """ % s.id
        )

class Article(AssocTest):
    def _config(c):
        c.attributes('id', 'site_id', 'author_id', 'title', 'text')
        c.belongs_to('site', class_name='Site')
        c.belongs_to('author', class_name='Person')
        c.has_many('comments', _as='parent', class_name='Comment')
        c.has_many('awesome_comments', _as='parent', class_name='Comment',
            conditions="text LIKE '%awesome%'")

class Comment(AssocTest):
    def _config(c):
        c.attributes('id', 'person_id', 'parent_id', 'parent_type', 'text')
        c.belongs_to('parent', polymorphic=True)
        c.belongs_to('author', class_name='Person', foreign_key='person_id')

class Person(AssocTest):
    def _config(c):
        c.attributes('id', 'name', 'manager_id', 'company_id')
        c.belongs_to('manager', class_name='Person', foreign_key='manager_id')
        c.has_many('authored_comments', class_name='Comment', foreign_key='person_id')
        c.has_many('articles', class_name='Article', foreign_key='author_id')
        c.has_many('comments', _as='parent', class_name='Comment')
        c.has_many('employees', class_name='Person', foreign_key='manager_id')
        c.has_many('sites', class_name='Site', foreign_key='maintainer_id')

class Company(AssocTest):
    def _config(c):
        c.attributes('id', 'name')
        c.has_many('employees', class_name='Person',
            namespace='tests.fixtures.extended_association_models')
