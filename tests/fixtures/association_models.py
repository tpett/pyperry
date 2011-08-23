import pyperry
from pyperry.attribute import Attribute
from pyperry.association import BelongsTo, HasMany, HasManyThrough, HasOne
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

    maintainer = BelongsTo(klass=lambda: Person)
    headline = HasOne(klass=lambda: Article)
    master_comment = HasOne(as_='parent', class_name='Comment')
    fun_articles = HasOne(class_name='Article', conditions='1',
            sql=lambda s: """
                SELECT articles.*
                FROM articles
                WHERE articles.text LIKE %%monkeyonabobsled%%
                    AND articles.site_id = %s
            """ % s.id )
    articles = HasMany(class_name='Article',
            namespace='tests.fixtures.association_models')
    comments = HasMany(as_='parent', class_name='Comment')
    awesome_comments = HasMany(class_name='Comment', conditions='1',
            sql=lambda s: """
                SELECT comments.*
                FROM comments
                WHERE comments.text LIKE '%%awesome%%' AND
                    parent_type = "Site" AND parent_id = %s
            """ % s.id )
    article_comments = HasManyThrough(through='articles', source='comments')


class Article(AssocTest):
    id = Attribute()
    site_id = Attribute()
    author_id = Attribute()
    title = Attribute()
    text = Attribute()

    site = BelongsTo(class_name='Site')
    author = BelongsTo(class_name='Person')
    comments = HasMany(as_='parent', class_name='Comment')
    awesome_comments = HasMany(as_='parent', class_name='Comment',
            conditions="text LIKE '%awesome%'")
    comment_authors = HasManyThrough(through='comments', source='author')

class Comment(AssocTest):
    id = Attribute()
    person_id = Attribute()
    parent_id = Attribute()
    parent_type = Attribute()
    text = Attribute()

    parent = BelongsTo(polymorphic=True)
    author = BelongsTo(class_name='Person', foreign_key='person_id',
            namespace='tests.fixtures.association_models')

class Person(AssocTest):
    id = Attribute()
    name = Attribute()
    manager_id = Attribute()
    company_id = Attribute()

    manager = BelongsTo(class_name='Person', foreign_key='manager_id')
    authored_comments = HasMany(class_name='Comment', foreign_key='person_id')
    articles = HasMany(class_name='Article', foreign_key='author_id')
    comments = HasMany(as_='parent', class_name='Comment')
    employees = HasMany(class_name='Person', foreign_key='manager_id')
    sites = HasMany(class_name='Site', foreign_key='maintainer_id')
    commented_articles = HasManyThrough(through='comments', source='parent',
            source_type='Article')
    maintained_articles = HasManyThrough(through='sites', source='articles')

class Company(AssocTest):
    id = Attribute()
    name = Attribute()

    employees = HasMany(class_name='Person',
            namespace='tests.fixtures.extended_association_models' )

