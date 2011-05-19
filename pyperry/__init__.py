"""
pyperry
=======

pyperry is an ORM designed to interface with a datastore through an abstract
interface.  Rather than building SQL queries itself, queries are built in a
generic way that can be interpreted by an adapter and converted to any desired
query interface (like SQL, or any domain specific language).  Adapter results
are mapped to instances of L{pyperry.base.Base}.

Documentation Overview
----------------------

    - Defining models, Querying, and Persistence:  L{pyperry.base.Base}
    - Adapter Configuration:  L{pyperry.adapter}

Basic Usage
-----------

This is an example of a Person model::

    class Person(pyperry.base.Base):
        def config(cls):
            # Define attributes
            cls.attributes('id', 'name', 'favorite_color')

            # Basic adapter configuration
            cls.configure('read', type='bertrpc', procedure='person')
            cls.add_middleware('read', MyMiddleware, config='val')

            # Associations
            cls.has_one('address', class_name='Address')

            # Example of defining scopes
            cls.scope('ordered', cls.order('order_by'))
            @cls.scope
            def name_like(word):
                return cls.where('asset.`name` LIKE '"%%s%"' % word))

        # ...

Some example usage:

    >>> bob = Person({ 'name': 'Bob' })
    >>> bob.name
    'Bob'
    >>> bob.save()
    True
    >>> perry = Person.where({ 'name': 'Perry' }).first()
    >>> perry.name
    'Perry'
    >>> perry.address()
    #<Address ...>

For detailed documentation on these methods see:

    - L{pyperry.base.Base.attributes}
    - Adapter Configuration
        - L{Base.configure}
        - L{Base.add_middleware}
    - Associations
        - L{pyperry.base.Base.has_many}
        - L{pyperry.base.Base.has_one}
        - L{pyperry.base.Base.belongs_to}
    - L{pyperry.base.Base.scope}

"""

from pyperry.base import Base
from pyperry.relation import Relation
from pyperry.association import Association
import logging

# Override this with a custom logger
logger = logging

