import datetime
import types
from copy import deepcopy, copy
import traceback

from pyperry import errors
from pyperry import callbacks
from pyperry.relation import Relation
from pyperry.adapter.abstract_adapter import AbstractAdapter
from pyperry.association import BelongsTo, HasMany, HasOne, Association
from pyperry.field import Field
from pyperry.scope import Scope, DefaultScope

class BaseMeta(type):
    """
    The Metaclass for Base

    This allows for tracking all models defined using perry.Base as well as
    dynamic class level methods.  Class methods are delegated to an instance of
    L{pyperry.relation.Relation} if it knows how to handle them.

    """

    defined_models = {}

    def __new__(mcs, name, bases, class_dict):
        """
        Called any time a new Base class is created using this metaclass

        Models names are tracked in order to allow quick lookup of the model's
        class by its name.

        """

        # Create the new class
        cls = type.__new__(mcs, name, bases, class_dict)

        # Track model definitions by name
        if not mcs.defined_models.has_key(name):
            mcs.defined_models[name] = []
        mcs.defined_models[name].append(cls)

        return cls

    _relation_delegates = (Relation.singular_query_methods +
                Relation.plural_query_methods +
                ['modifiers', 'all', 'first', 'find', 'update_all',
                'delete_all'])

    def __init__(cls, name, bases, class_dict):
        """Class has been created now setup additional needs"""
        # Create a default primary_key value
        if not hasattr(cls, '_primary_key'):
            cls._primary_key = 'id'

        # Define any fields set during class definition
        if not hasattr(cls, 'defined_fields'):
            cls.defined_fields = set()
        else:
            cls.defined_fields = copy(cls.defined_fields)
            for base in bases:
                if hasattr(base, 'defined_fields'):
                    cls.defined_fields |= base.defined_fields

        # Define a mapping of raw field names to actual defined fields
        if not hasattr(cls, 'defined_field_mappings'):
            cls.defined_field_mappings = {}
        else:
            cls.defined_field_mappings = copy(cls.defined_field_mappings)
            for base in bases:
                if hasattr(base, 'defined_field_mappings'):
                    cls.defined_field_mappings.update(
                            base.defined_field_mappings)

        # Define any associations set during class definition
        if not hasattr(cls, 'defined_associations'):
            cls.defined_associations = {}
        else:
            cls.defined_associations = deepcopy(cls.defined_associations)
            for base in bases:
                if hasattr(base, 'defined_associations'):
                    cls.defined_associations.update(base.defined_associations)

        if not hasattr(cls, 'callback_manager'):
            cls.callback_manager = callbacks.CallbackManager()
        else:
            cls.callback_manager = callbacks.CallbackManager(
                    [ base.callback_manager for base in bases
                        if hasattr(base, 'callback_manager') ] )

        # Force calling of __setattr__ for each defined attribute for special
        # attribute handling
        for key in class_dict.keys():
            setattr(cls, key, class_dict[key])

        if hasattr(cls, 'reader'):
            cls.reader = deepcopy(cls.reader)
        if hasattr(cls, 'writer'):
            cls.writer = deepcopy(cls.writer)

        cls._docstring = cls.__doc__
        cls.__doc__ = cls.get_docstring()

    def __getattr__(cls, key):
        """Allow delegation to Relation or raise AttributeError"""
        if key in cls._relation_delegates:
            return getattr(cls.scoped(), key)
        else:
            raise AttributeError("Undefined attribute '%s'" % key)

    def __setattr__(cls, key, value):
        """
        Allows special behavior when setting class attributes.

        Each of the pieces of functionality is triggered by a type of class.
        This allows extending functionality through subclasses on any of the
        different types.  The super class is always called regardless of type.
        Special classes include::

            - %L{Field}
            - %L{Association}
            - %L{DefaultScope} (special case of Scope)
            - %L{Scope}
            - %L{Callback}

        This method is also called for each attribute set during class creation
        allowing for common behavior to be applied whether set during class
        creation or directly on the class after creation.

        """
        if isinstance(value, Field):
            if value.name is None:
                value.name = key
            else:
                cls.defined_field_mappings[value.name] = key
            cls._define_fields(key)
        elif isinstance(value, Association):
            value.id = key
            value.target_klass = cls
            cls.defined_associations[key] = value
        elif isinstance(value, DefaultScope):
            value.model = cls
            base_scope = cls.current_scope() or cls.relation()
            cls._scoped_methods.append(base_scope.merge(value()))
        elif isinstance(value, Scope):
            value.model = cls
            value.__name__ = key
            if not hasattr(cls, 'scopes'): cls.scopes = {}
            cls.scopes[key] = value
        elif isinstance(value, callbacks.Callback):
            cls.callback_manager.register(value)

        type.__setattr__(cls, key, value)

    def __dir__(cls):
        """add the methods delegated to relation to dir() results"""
        attrs = cls.__dict__.keys()
        for b in cls.__bases__:
            attrs += dir(b)
        attrs += cls._relation_delegates
        all_attrs = list(set(attrs)) # remove duplicates from list

        # If the call to __dir__ is triggered by a call to help(), we need to
        # remove the attributes delegated to relation from the list we return
        # or the help page will be blank.
        frame = traceback.extract_stack(None, 2)[0]
        if 'inspect.py' in frame[0] and 'classify_class_attrs' in frame[2]:
            all_attrs = [x for x in all_attrs
                         if not x in cls._relation_delegates]
        return all_attrs

    def resolve_name(cls, name):
        """
        Lookup class by the given name

        Returns all models that match the given name.  To avoid ambiguous
        matches you can pass any section of the preceding namespace or a full
        absolute path name to the class. For example, to find the class
        foo.bar.Baz you could specify::

            # Matches all models named 'Baz'
            Base.resolve_name('Baz')
            # Matches all models named 'Baz' in a 'bar' namespace
            Base.resolve_name('bar.Baz')
            # Or specify absolutely
            Base.resolve_name('foo.bar.Baz')

        @param name: string representation of a class with or without the
        partial or full namespace in dot notation
        @return: a list of classes matching C{name}

        """
        name = name.rsplit('.', 1)
        class_name = name[-1]
        if len(name) == 2:
            namespace = name[0]
            cls._auto_import(namespace)

        if cls.defined_models.has_key(class_name):
            classes = copy(cls.defined_models[class_name])

            # Filter by namespace if a namespace is queried
            if 'namespace' in locals():
                classes = [
                        kls
                        for kls in classes
                        if kls.__module__.endswith(namespace) ]

            return classes
        else:
            return []

    def _auto_import(cls, package):
        """
        Tries to import package by absolute path.  Fails silently on failure.

        """
        try:
            # Do an import Force absolute imports
            __import__(package, globals(), locals(), [], 0)
        except ImportError, err:
            pass

    def get_docstring(cls):
        doc_parts = []
        if cls._docstring:
            doc_parts.append(cls._docstring)
        doc_parts.append('\nData fields:')
        doc_parts += ['    %s' % attr
                      for attr in sorted(cls.defined_fields)]
        doc_parts.append('\nAssociations:')
        doc_parts += sorted([cls.describe_association(assoc_name)
                             for assoc_name in cls.defined_associations])
        doc_parts.append('\nFull documentation available at ' +
                'http://packages.python.org/pyperry/')
        return '\n'.join(doc_parts)

    def describe_association(cls, name):
        extra = None
        assoc = cls.defined_associations[name]
        type_ = assoc.type()
        type_width = str(len('belongs_to') + 3)

        if type_ == 'belongs_to' and assoc.polymorphic():
            extra = 'polymorphic'

        if type_ == 'has_many_through':
            type_ = 'has_many'
            extra = 'through ' + assoc.options['through']

        description = ('    %-' + type_width + 's %s') % (type_, name)
        if extra:
            description += ' (%s)' % extra
        return description


class Base(object):
    """
    The Base class for all models using pyperry.

    L{Base} defines the functionality of a pyperry model.  All models should
    inherit (directly or indirectly) from L{Base}.  For a basic overview of
    usage, check out the docs on the L{pyperry} module.

    Configuration Overview
    ======================

    Configuration is done through various class methods on the model.  These
    could be set anywhere, but conventionally they are set in a C{config}
    method on the class.  This method is run when a class is created with the
    newly created class as an argument.  Thus, configuration can be done like
    this::

        class Animal(pyperry.base.Base):
            id = Field()
            name = Field(type=str)
            mammal = Field()

            reader = MyAdapter()

            friendships = HasMany(class_name="Friendship")
            friends = HasMany(class_name="Friend", through='friendships')

            mammal = Scope(where= { 'mammal': True })

    Any class configuration can be done in this method.

    Querying
    ========

    Queries can be built by chaining calls to scopes or query methods.  For
    example::

        Person.where(first_name='Bob').order('last_name')

    This generates a query for all Person objects with the first name "Bob"
    ordered by their last name.  Each query method returns a new L{Relation}
    object with the new query parameters applied.  This allows the continued
    chaining.

    A L{Relation} object is a sequence-like object behaving much like a
    C{list}.  The query will be run the first time the object is treated like a
    list, and the records will be used for the expression.  For example::

        query = Animal.where(type='Platypus')

        # Array comprehensions and for loops
        for animal in query:
            print animal.name + " is a platypus.  They don't do much."

        # Compares type and attributes of objects for equality
        object in query
        object not in query

        # Indexing, slicing, step slicing
        query[0]
        query[0:3]
        query[0:3:2]

        # Other
        len(query)

    In this example the query is executed before running the for loop, and all
    subsequent calls use that result.  Queries will not be run until you need
    them so unused queries don't hurt performance.  If you would like to force
    a query to run and retreive the records in a C{list} object use the
    L{Relation.all()} method, or to receive the object itself in single result
    queries use the L{Relation.first()} method.

    Persistence
    ===========

    Pyperry provides an interface for creating, updating, and deleting models
    when a write adapter is configured.  A model can be initialized as a "new"
    record (default) or a "stored" record and is determined by the
    C{new_record} attribute.  This changes the behavior of the save operation.
    A "new" record is created and a "stored" record is updated.  Also, a "new"
    record cannot be deleted as it does not yet exist in the database.  See the
    individual L{persistence methods<save>} for more information

    Scopes
    ======

    Scopes allow you to specify prebuilt views of your data.  Scopes, like
    query methods, can be applied simply by chaining calls on instances of
    L{Relation} or the L{Base} class.  Scopes are created by setting a class
    level attribute of type L{Scope}.  Here are some examples::

        ordered = Scope(order=['type', 'name'])
        platypus = Scope({ 'where': { 'type': 'platypus' } })
        perrys = Scope(lambda(cls): cls.where(name='perry'))

        @Scope
        def type_is(cls, name):
            return cls.where(type=name)

    These scopes can now be used in queries along with query methods and
    chained together to make powerful queries::


    Associations
    ============

    Associations allow you to define foreign key relationships between two
    models, the target (model on which the association is defined) and the
    source (model from which the data will come).  There are two basic kinds of
    associations:  has and belongs.  A has relationship means the foreign_key
    lives on the source model.  A belongs relationship means the foreign_key
    lives on the target model.

    Imagine a blog.  A blog has many articles and an article belongs to an
    author.  You might model this structure with Blog, Article and Person
    classes.  Associations are conventionally defined in the C{_config} method
    for each class, but to save space we'll just show the association
    definition for each class::

        class Blog(pyperry.base.Base):
            id = Field()

            articles = HasMany(class_name='Article')

        class Article(pyperry.base.Base):
            id = Field()
            blog_id = Field()
            author_id = Field()

            blog = BelongsTo(class_name='Blog', foreign_key='blog_id')
            author = BelongsTo(class_name='Person', foreign_key='author_id')

    Assuming you have an instance of C{Blog} called C{blog} you could then
    reference these associations like this::

        # An ordered list of articles on this blog
        articles = blog.authors().ordered()
        # The author of the first article
        articles[0].author()

    Note that the L{HasMany} association returns a L{Relation} object allowing
    you to apply query methods and scopes to the association before executing
    the query.

    For more information on Associations see the individual classes within the
    %L{pyperry.association} module

    """

    __metaclass__ = BaseMeta
    _relation_class = Relation

    def __init__(self, fields=None, new_record=True, **kwargs):
        """
        Initialize a new pyperry object with specified fields

        Uses C{fields} dictionary to set fields on a new instance.
        Only keys that have been defined for the model will be set.  Defaults
        to a new record but can be overriden with C{new_record} param. You can
        also use C{kwargs} to specify the fields.

        @param fields: dictionary of fields to set on the new instance
        @param new_record: set new_record flag to C{True} or C{False} (this is
        an internal param and shouldn't be set directly unless you know what
        you're doing).

        """
        if fields is None:
            fields = {}
        fields.update(kwargs)

        self.saved = None
        self.errors = {}
        self._frozen = False
        self.new_record = new_record

        self.callback_manager.trigger(callbacks.before_load, self)

        self.fields = self.default_fields()

        if self.new_record:
            self.set_fields(fields)
        else:
            self.set_raw_fields(fields)

        self.callback_manager.trigger(callbacks.after_load, self)

    #{ Dict-like access
    def __getitem__(self, key):
        """
        Adds C{dict} like field reading

        Allows::

            person['id']
            person['name']

        Developer Note:  This method of accessing fields is used internally
        and should never be overridden by subclasses.

        @raise KeyError: If C{key} is not a defined field.

        @param key: name of the field to get

        """
        if key in self.defined_fields or key in self.defined_field_mappings:
            # Using get() here to avoid KeyError on uninitialized attrs
            return self.fields.get(key)
        else:
            raise KeyError("Undefined field '%s'" % key)

    def __setitem__(self, key, value):
        """
        Adds C{dict} like field writing

        Allows::

            animal['name'] = 'Perry'
            animal['type'] = 'Platypus'

        @raise KeyError: If C{key} is not a defined field.

        @param key: name of the field to set
        @param value: value to set C{key} field to

        """
        if key in self.defined_fields or key in self.defined_field_mappings:
            self.fields[key] = value
        else:
            raise KeyError("Undefined field '%s'" % key)

    def keys(self):
        """
        Returns list of valid fields accessible through get/set item methods

        """
        return self.defined_fields

    def has_key(self, key):
        """
        Mimicks behavior of dict.has_key()

        returns True when key exists and False when it doesn't

        @param key: key to check for
        """
        return key in self.keys()

    def __dir__(self):
        """
        Ignores _relation_delegates.  Otherwise normal functions.

        """
        excluded_attrs = self.__class__._relation_delegates
        return list(set( # removes duplicate entries
            [x for x in dir(self.__class__) if x not in excluded_attrs] +
            self.__dict__.keys()
        ))

    def pk_attr(self):
        """
        A shortcut method from retrieving the name of this model's primary key
        field.
        """
        return self.primary_key()

    def pk_value(self):
        """
        A shortcut method for retrieving the value stored in this model's
        primary key field.
        """
        return getattr(self, self.primary_key())
    #}

    #{ Persistence
    def default_fields(self):
        """
        Return a dict of fields and their default values.

        Only lists non-None defaults.

        """
        defaults = {}
        for field_name in self.defined_fields:
            if hasattr(self.__class__, field_name):
                field = getattr(self.__class__, field_name)
                if field.default is not None:
                    defaults[field_name] = field.default
        return defaults


    def set_fields(self, fields=None, **kwargs):
        """
        Set the fields of the object using the provided dictionary.

        Only fields listed in defined_fields will be set.  This method will
        route all setting through the Field construct, and is equivalent to
        setting each key to the equivalent attribute on the class::

            # This is equivalent:
            for field in fields:
                setattr(object, field, fields[field])

            # To this (except safety checks):
            object.set_fields(fields)

        Note:  Keys for fields that are not defined will simply be ignored
        Also Note: Associations can be set through this method and BelongsTo
        associations when set will also set the associated foreign_key field.

        @param fields: dictionary of fields

        """
        if fields is None:
            fields = {}
        fields.update(kwargs)

        for field in fields:
            if (field in self.defined_fields
                    or field in self.defined_associations):
                setattr(self, field, fields[field])
            elif (field in self.defined_field_mappings):
                setattr(self, self.defined_field_mappings[field],
                        fields[field])

    def set_raw_fields(self, fields=None, **kwargs):
        """
        Set the raw fields dict of the object using the provided dictionary.

        Like set_fields, only fields listed in _defined_fields will be set.
        This method will bypass all logic in the Field instance class and is
        the same as setting each key in `fields` via the subscript operator::

            # This is equivalent
            for field in fields:
                object[field] = fields[field]

            # To this (except safety checks):
            object.set_raw_fields(fields)

        Note:  Keys for fields that are not defined will simply be ignored

        @param fields: dictionary of fields

        """
        if fields is None:
            fields = {}
        fields.update(kwargs)

        for field in fields:
            if (field in self.defined_fields
                    or field in self.defined_field_mappings):
                self[field] = fields[field]


    def save(self, run_callbacks=True):
        """
        Save the current value of the model's data fields through the write
        adapter.

        If the save succeeds, the model's C{saved} attribute will be set to
        True. Also, if a read adapter is configured, the models data fields
        will be refreshed to ensure that you have the current values.

        If the save fails, the model's C{errors} will be set to a
        dictionary containing error messages and the C{saved} attribute will be
        set to False.

        @return: Returns C{True} on success or C{False} on failure

        """
        if not hasattr(self, 'writer'):
            raise errors.ConfigurationError(
                    "You must set `writer` attribute to an instance of "
                    "pyperry.adapters.AbstractAdapter in order to use save().")
        if self.frozen():
            raise errors.PersistenceError("cannot save a frozen model")
        if self.pk_value() is None and not self.new_record:
            raise errors.PersistenceError(
                    "cannot save model without a primary key value")

        create_operation = self.new_record

        # Before Callbacks
        if run_callbacks:
            self.callback_manager.trigger(callbacks.before_save, self)

            if create_operation:
                self.callback_manager.trigger(callbacks.before_create, self)
            else:
                self.callback_manager.trigger(callbacks.before_update, self)

        # Run the save
        self.writer.last_response = self.writer(model=self, mode='write')

        # After callbacks
        if run_callbacks:
            if create_operation:
                self.callback_manager.trigger(callbacks.after_create, self)
            else:
                self.callback_manager.trigger(callbacks.after_update, self)

            self.callback_manager.trigger(callbacks.after_save, self)

        return self.writer.last_response.success

    def update(self, **kwargs):
        """
        Save the record if it is not a new_record and raise PersistenceError
        otherwise.

        This will call %L{save()} if the record is not a %C{new_record} and
        raise a PersistenceError exception otherwise.

        @return: Returns C{True} on success or C{False} on failure

        """
        if self.new_record:
            raise errors.PersistenceError(
                    "update() must only be called on an existing record but "
                    "new_record attribute is True" )

        return self.save(**kwargs)

    def create(self, **kwargs):
        """
        Save the record iff it is a new_record and raise PersistenceError
        otherwise.

        This will call %L{save()} if the record is a %C{new_record} and
        raise a PersistenceError exception otherwise.

        @return: Returns C{True} on success or C{False} on failure

        """
        if not self.new_record:
            raise errors.PersistenceError(
                    "create() must only be called on a new record but "
                    "new_record attribute is False" )

        return self.save(**kwargs)

    def update_fields(self, fields=None, **kwargs):
        """
        Update the fields with the given dictionary or keywords and save
        the model.

        Has the same effect as calling::
            obj.set_fields(fields)
            obj.save()

        Requires either C{fields} or keyword arguments.  If both are
        provicded, C{fields} will be used and C{kwargs} will be ignored.

        @param fields: dictionary of fields to set
        @param kwargs: Optionally use keyword syntax instead of C{fields}
        @return: Returns C{True} on success or C{False} on failure

        """
        if fields is None:
            fields = {}
        fields.update(kwargs)

        self.set_fields(fields)

        return self.save()

    def delete(self, run_callbacks=True):
        """
        Removes this model from the data store

        If the call succeeds, the model will be marked as frozen and calling
        C{frozen} on the model will return True. Once a model is frozen, an
        exception will be raised if you attempt to call one of the persistence
        methods on it.

        If the call fails, the model's C{errors} attribute will be set to a
        dictionary of error messages describing the error.

        @return: C{True} on success or C{False} on failure

        """
        if not hasattr(self, 'writer'):
            raise errors.ConfigurationError(
                    "You must set `writer` attribute to an instance of "
                    "pyperry.adapters.AbstractAdapter in order to use "
                    "delete().")
        elif self.frozen():
            raise errors.PersistenceError('cannot delete a frozen model')
        elif self.new_record:
            raise errors.PersistenceError('cannot delete a new model')
        elif self.pk_value() is None:
            raise errors.PersistenceError(
                    'cannot delete a model without a primary key value')

        if run_callbacks:
            self.callback_manager.trigger(callbacks.before_delete, self)

        self.writer.last_response = self.writer(model=self, mode='delete')

        if run_callbacks:
            self.callback_manager.trigger(callbacks.after_delete, self)

        return self.writer.last_response.success

    #}

    def reload(self):
        """Refetch the fields for this object from the read adapter"""
        pk_condition = {self.pk_attr(): self.pk_value()}
        relation = self.scoped().where(pk_condition).fresh()
        self.fields = relation.first().fields

    def frozen(self):
        """Returns True if this instance is frozen and cannot be saved."""
        return self._frozen

    def freeze(self):
        """
        Marks this instance as being frozen, which will cause all future
        writes and deletes to fail.
        """
        self._frozen = True

    #{ Configuration
    @classmethod
    def primary_key(cls):
        """
        Returns the field name of the model's primary key.
        """
        return cls._primary_key

    @classmethod
    def set_primary_key(cls, attr_name):
        """
        Set the name of the primary key field for the model. The new
        primary key field must be one of the defined fields otherwise
        set_primary_key will raise an AttributeError.
        """
        if attr_name not in cls.defined_fields:
            raise AttributeError(
                    'an attribute must be defined to make it the primary key')
        cls._primary_key = attr_name
    #}

    @classmethod
    def fetch_records(cls, relation):
        """
        Execute query using relation on the read adapter stack

        @param relation: An instance of C{Relation} describing the query
        @return: list of records from adapter query data each with new_record
        set to false.  C{None} items are removed.

        """
        if not hasattr(cls, 'reader'):
            raise errors.ConfigurationError(
                    "You must set `reader` attribute to an instance of "
                    "pyperry.adapters.AbstractAdapter in order to call "
                    "fetch_records()")

        return cls.reader(relation=relation, mode='read')

    #{ Scoping
    @classmethod
    def relation(cls):
        """
        A base instance of C{Relation} for this model.

        All query scopes originate from this instance, and should not change
        this instance.

        @return: C{Relation} instance for this model

        """
        if not hasattr(cls, '_relation') or cls._relation.klass != cls:
            cls._relation = cls._relation_class(cls)
        return cls._relation

    @classmethod
    def current_scope(cls):
        """
        Base instance of C{Relation} after default scopes are applied.

        Returns an instance of Relation after applying the latest scope in
        the class variable _scoped_methods.

        @return: C{Relation} instance with default scopes applied if default
        scopes are present.  Otherwise returns C{None}.

        """
        if not hasattr(cls, '_scoped_methods'): cls._scoped_methods = []
        if len(cls._scoped_methods) > 0:
            return cls._scoped_methods[-1]

    @classmethod
    def scoped(cls):
        """
        Unique instance of C{Relation} to build queries on.

        If you want an instance of relation on this model you most likely want
        this method.

        @return: Cloned return value from C{current_scope} or C{relation}

        """
        if cls.current_scope() is None:
            return cls.relation().clone()
        else:
            return cls.relation().merge(cls.current_scope())

    @classmethod
    def unscoped(cls, function):
        """
        Execute C{function} without default scopes

        All default scoping is temporarily removed and the given function is
        then executed.  After the function is executed all previous default
        scopes are applied.

        @param function: function to execute

        """
        cls.current_scope() # Ensure _scoped_methods set
        current_scopes = cls._scoped_methods
        try:
            cls._scoped_methods = []
            function()
        finally:
            cls._scoped_methods = current_scopes

    #}

    @classmethod
    def _define_fields(cls, *fields):
        """
        Set specified attribute to the defined_fields `set`

        This method is automatically called when fields are set of type
        Field on the class.  Each call will union any new fields into
        the set of defined fields.

        This is only a tracking method and should not be called outside of this
        class.

        @param fields: list parameters as strings, or the first argument is
        a list of strings.

        """
        if fields[0].__class__ in [list, set, tuple]:
            fields = fields[0]
        cls.defined_fields |= set(fields)

    def __repr__(self):
        """Return a string representation of the object"""
        return "<%s object %s new_record=%s>" % (
                self.__class__.__name__,
                self.fields,
                self.new_record)

    def __eq__(self, compare):
        """Compare equality of an object by its fields"""
        if type(self) != type(compare):
            return False

        return self.fields == compare.fields


