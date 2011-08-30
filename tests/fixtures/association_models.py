import pyperry
from pyperry.field import Field
from pyperry.association import BelongsTo, HasMany, HasOne
from test_adapter import TestAdapter

class Test(pyperry.Base):
    id = Field()

class Source(pyperry.Base):
    id = Field()

class AssocTest(pyperry.Base):
    reader = TestAdapter()

class Site(AssocTest):
    id = Field()
    name = Field()
    maintainer_id = Field()

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
    article_comments = HasMany(through='articles', source='comments')


class Article(AssocTest):
    id = Field()
    site_id = Field()
    author_id = Field()
    title = Field()
    text = Field()

    site = BelongsTo(class_name='Site')
    author = BelongsTo(class_name='Person')
    comments = HasMany(as_='parent', class_name='Comment')
    awesome_comments = HasMany(as_='parent', class_name='Comment',
            conditions="text LIKE '%awesome%'")
    comment_authors = HasMany(through='comments', source='author')

class Comment(AssocTest):
    id = Field()
    person_id = Field()
    parent_id = Field()
    parent_type = Field()
    text = Field()

    parent = BelongsTo(polymorphic=True)
    author = BelongsTo(class_name='Person', foreign_key='person_id',
            namespace='tests.fixtures.association_models')

class Person(AssocTest):
    id = Field()
    name = Field()
    manager_id = Field()
    company_id = Field()

    manager = BelongsTo(class_name='Person', foreign_key='manager_id')
    authored_comments = HasMany(class_name='Comment', foreign_key='person_id')
    articles = HasMany(class_name='Article', foreign_key='author_id')
    comments = HasMany(as_='parent', class_name='Comment')
    employees = HasMany(class_name='Person', foreign_key='manager_id')
    sites = HasMany(class_name='Site', foreign_key='maintainer_id')
    commented_articles = HasMany(through='comments', source='parent',
            source_type='Article')
    maintained_articles = HasMany(through='sites', source='articles')

class Company(AssocTest):
    id = Field()
    name = Field()

    employees = HasMany(class_name='Person',
            namespace='tests.fixtures.extended_association_models' )

