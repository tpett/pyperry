import datetime
import types
from copy import deepcopy, copy

from pyperry import errors
from pyperry.relation import Relation
from pyperry.adapter.abstract_adapter import AbstractAdapter
from pyperry.association import BelongsTo, HasMany, HasOne

class BaseMeta(type):
    """
    The Metaclass for Base

    This allows for tracking all models defined using perry.Base as well as
    dynamic class level methods.  Class methods are delegated to an instance of
    L{pyperry.relation.Relation} if it knows how to handle them.

    """

    defined_models = {}

    def __new__(mcs, name, bases, dict_):
        """
        Called any time a new Base class is created using this metaclass

        Models names are tracked in order to allow quick lookup of the model's
        class by its name.

        """

        # Interpret _config as __configmodel__ effectively obfiscating it
        if dict_.has_key('_config'):
            dict_['__configmodel__'] = classmethod(dict_['_config'])
            del dict_['_config']

        # Create the new class
        new = type.__new__(mcs, name, bases, dict_)

        # Deepcopy adapter configs from ancestor or create a base configset
        if hasattr(new, 'adapter_config'):
            new.adapter_config = deepcopy(new.adapter_config)
        else:
            new.adapter_config = {}

        # Create fresh adapter dict
        new._adapters = {}

        # Define any attributes set during class definition
        new.defined_attributes = set()

        # Define any associations set during class definition
        if not hasattr(new, 'defined_associations'):
            new.defined_associations = {}
        else:
            new.defined_associations = deepcopy(new.defined_associations)

        if hasattr(new, '__configmodel__'):
            new.__configmodel__()

        # Track model definitions by name
        if not mcs.defined_models.has_key(name):
            mcs.defined_models[name] = []
        mcs.defined_models[name].append(new)

        return new

    def __getattr__(cls, key):
        """Allow delegation to Relation or raise AttributeError"""
        relation_delegation = (
                Relation.singular_query_methods +
                Relation.plural_query_methods +
                ['all', 'first'] )
        if key in relation_delegation:
            return getattr(cls.scoped(), key)
        else:
            raise AttributeError("Undefined attribute '%s'" % key)

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
            def config(cls):
                cls.attributes 'id', 'name', 'mammal'
                cls.configure('read', type='bertrpc')
                cls.add_middleware('read', MyMiddleware, config1='val')

                cls.has_many('friendships', class_name='Friendship')

                cls.scope('mammal', where={ 'mammal': true })

    Any class configuration can be done in this method.

    Querying
    ========

    TODO

    Persistence
    ===========

    TODO

    Scopes
    ======

    TODO

    Associations
    ============

    TODO

    """

    __metaclass__ = BaseMeta

    def __init__(self, attributes, new_record=True):
        """
        Initialize a new pyperry object with attributes

        Uses C{attributes} dictionary to set attributes on a new instance.
        Only keys that have been defined for the model will be set.  Defaults
        to a new record but can be overriden with C{new_record} param

        @param attributes: dictionary of attributes to set on the new instance
        @param new_record: set new_record flag to C{True} or C{False}.

        """
        self.attributes = {}
        self.set_attributes(attributes)
        self.new_record = new_record
        self.saved = None
        self.errors = {}
        self._frozen = False

    #{ Attribute access
    def __getitem__(self, key):
        """
        Adds C{dict} like attribute reading

        Allows::

            person['id']
            person['name']

        Developer Note:  This method of accessing attributes is used internally
        and should never be overridden by subclasses.

        @raise KeyError: If C{key} is not a defined attribute.

        @param key: name of the attribute to get

        """
        if key in self.defined_attributes:
            # Using get() here to avoid KeyError on uninitialized attrs
            return self.attributes.get(key)
        else:
            raise KeyError("Undefined attribute '%s'" % key)

    def __setitem__(self, key, value):
        """
        Adds C{dict} like attribute writing

        Allows::

            animal['name'] = 'Perry'
            animal['type'] = 'Platypus'

        @raise KeyError: If C{key} is not a defined attribute.

        @param key: name of the attribute to set
        @param value: value to set C{key} attribute to

        """
        if key in self.defined_attributes:
            self.attributes[key] = value
        else:
            raise KeyError("Undefined attribute '%s'" % key)

    def __getattr__(self, key):
        """
        Dynamic attribute / association reading

        Properties or Methods are not created for attributes or associations,
        and are instead handled by this method.  This allows a model to
        override the default behavior of attribute or association access by
        creating a property or method (respectively) of the same name.

        Allows::

            animal.name
            animal.friends()

        @raise AttributeError: if key is not a defined attribute or
        association.

        @param key: name of the attribute attempting to be accessed

        """
        if key in self.defined_attributes:
            return self[key]
        elif key in self.defined_associations.keys():
            def method():
                return self.defined_associations[key](self)
            method.__name__ = key
            return method
        else:
            raise AttributeError("object '%s' has no attribute '%s'" %
                (self.__class__.__name__, key))

    def __setattr__(self, key, value):
        """
        Dynamic attribute setting

        Properties are not created for setting attributes.  This method allows
        setting any defined attributes through the standard writer interface.

        Allows::

            animal.name = "Perry"
            animal.type = "Platypus

        @param key: name of the attribute to set
        @param value: value to set the C{key} attribute to

        """
        if(key in self.defined_attributes
                and not self._has_writer_property(key)):
            self[key] = value
        else:
            object.__setattr__(self, key, value)
    #}

    #{ Persistence
    def set_attributes(self, attributes):
        """
        Set the attributes of the object using the provided dictionary.

        Only attributes defined using define_attributes will be set.

        @param attributes: dictionary of attributes

        """
        for field in attributes.keys():
            if field in self.defined_attributes:
                self[field] = attributes[field]

    def save(self):
        """
        Save the current state of the model through the write adapter

        @return: Returns C{True} on success or C{False} on failure

        """
        return self.adapter('write')(model=self)

    def update_attributes(self, attributes=None, **kwargs):
        """
        Update the attributes with the given dictionary or keywords and save
        the model.

        Has the same effect as calling::
            obj.set_attributes(attributes)
            obj.save()

        Requires either C{attributes} or keyword arguments.  If both are
        provicded, C{attributes} will be used and C{kwargs} will be ignored.

        @param attributes: dictionary of attributes to set
        @param kwargs: Optionally use keyword syntax instead of C{attributes}
        @return: Returns C{True} on success or C{False} on failure

        """
        if not attributes:
            attributes = kwargs

        self.set_attributes(attributes)

        return self.save()

    def destroy(self):
        """
        Calls write adapter with delete keyword True.

        The result of this is dependent on the adapter used, but conventionally
        it removes the current record from the data store.

        @return: C{True} on success or C{False} on failure

        """
        return self.adapter('write')(model=self, delete=True)
    delete = destroy
    #}

    def reload(self):
        self.attributes = self.scoped().where({'id': 1}).first().attributes

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
    def configure(cls, adapter_type, config=None, **kwargs):
        """
        Method for setting adapter configuration options.

        Accepts a dictionary argument or keyword arguments, but not both.
        Configuration specified will be merged with all previous calls to
        C{configure} for this C{adapter_type}

        @param adapter_type: specify the type of adapter ('read' or 'write')
        @param config: dictionary of configuration parameters
        @param kwargs: alternate specification of configuration

        """
        if adapter_type not in AbstractAdapter.adapter_types:
            raise errors.ConfigurationError(
                    "Unrecognized adapter type: %s" % adapter_type)

        new_dict = config or kwargs

        if not cls.adapter_config.has_key(adapter_type):
            cls.adapter_config[adapter_type] = {}

        cls.adapter_config[adapter_type].update(new_dict)

    @classmethod
    def add_middleware(cls, adapter_type, klass, options=None, **kwargs):
        """
        Add a middleware to the given adapter

        Interface for appending a middleware to an adapter stack.  For more
        information on middlewares see docs on
        L{pyperry.adapter.abstract_adapter.AbstractAdapter}.

        @param adapter_type: specify type of adapter ('read' or 'write')
        @param klass: specify the class to use as the middleware
        @param options: specify an options dictionary to pass to middleware
        @param kwargs: specify options with keyword arguments instead of
        options.

        """
        if cls.adapter_config.has_key(adapter_type):
            middlewares = cls.adapter_config[adapter_type].get('_middlewares')
        if not 'middlewares' in locals() or not middlewares:
            middlewares = []

        middlewares.append( (klass, options or kwargs or {}) )

        cls.configure(adapter_type, _middlewares=middlewares)

    @classmethod
    def adapter(cls, adapter_type):
        """
        Returns the adapter specified by C{adapter_type}

        If the adapter has not been configured correctly C{ConfigurationError}
        will be raised.

        @param adapter_type: type of adapter ('read' or 'write')
        @return: the adapter specified by C{adapter_type}

        """
        if cls._adapters.has_key(adapter_type):
            return cls._adapters[adapter_type]

        if not cls.adapter_config.has_key(adapter_type):
            raise errors.ConfigurationError("You must configure the %s adapter"
                    % (adapter_type) )

        adapter_klass = cls.adapter_config[adapter_type].get('adapter')
        if not adapter_klass:
            raise errors.ConfigurationError("You must specify the 'adapter' "
                    "option in the %s configuration" % adapter_type)

        cls._adapters[adapter_type] = adapter_klass(
                cls.adapter_config[adapter_type], mode=adapter_type)

        return cls._adapters[adapter_type]

    @classmethod
    def define_attributes(cls, *attributes):
        """
        Define available attributes for a model.

        This method is automatically called when the attributes var is set on
        the class during definition.  Each call will union any new attributes
        into the set of defined attributes.

        aliased as C{attributes}

        @param attributes: list parameters as strings, or the first argument is
        a list of strings.

        """
        if attributes[0].__class__ in [list, set, tuple]:
            attributes = attributes[0]
        cls.defined_attributes |= set(attributes)
    attributes = define_attributes
    #}

    @classmethod
    def fetch_records(cls, relation):
        """
        Execute query using relation on the read adapter stack

        @param relation: An instance of C{Relation} describing the query
        @return: list of records from adapter query data each with new_record
        set to false.  C{None} items are removed.

        """
        return cls.read_adapter()(relation=relation)

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
            cls._relation = Relation(cls)
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
        if cls.current_scope():
            return cls.relation().merge(cls.current_scope())
        else:
            return cls.relation().clone()

    @classmethod
    def default_scope(cls, *args, **kwargs):
        """
        Add a default scoping for this model.

        All queries will be built based on the default scope of this model.
        Only specify a default scope if you I{always} want the scope
        applied.  Calls to C{default_scope} aggregate.  So each call will append
        to options from previous calls.

        Note: You can bypass default scopings using the L{unscoped} method.

        Similar to arguments accepted by L{scope}.  The only thing not
        supported is lambdas/functions accepting additional arguments. Here are
        some examples::

            Model.default_scope(where={'type': 'Foo'})
            Model.default_scope({ 'order': 'name DESC' })

        """
        options = cls._parse_scope_options(*args, **kwargs)
        base_scope = cls.current_scope() or cls.relation()
        rel = cls._apply_scope_options(base_scope, options)

        if rel:
            cls._scoped_methods.append(rel)

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

    @classmethod
    def define_scope(cls, name_or_func, *args, **kwargs):
        """
        Defines a scope on the given model.

        A scope can be defined in one of several ways:

        Dictionary or Keyword Arguments

        If your scope is simply setting a few static query arguments than this
        is the easiest option.  Here are a few examples::

            # With a dictionary
            Model.scope('ordered', { 'order': "name" })

            # With keyword arguments
            Model.scope('awesome', where={'awesome': 1})
            Model.scope('latest', order="created_at DESC", limit=1)

        With a Lambda or Function

        When your scope involves chaining other scopes, delayed values (such as
        a relative time), or if it takes arguments then this is the preferred
        method.  Here are a few examples::

            Model.scope('awesome_ordered', lambda(cls): cls.ordered().awesome())

            # Returns a scope dynamically generating condition using fictional
            # minutes_ago function.  Without the lambda this wouldn't update
            # each time the scope is used, but only when the code was reloaded.
            Model.scope('recent', lambda(cls): cls.where(
                    'created_at > %s' % minutes_ago(5))

            # You can also use the method as a decorator!  Whatever you call
            # your method will be the name of the scope.  Make sure it's unique.
            @Model.scope
            def name_like(cls, word):
                return cls.where(["name LIKE '%?%", word])

        These scopes can be chained. Like so::

            # Returns a max of 5 records that have a name containing 'bob'
            # ordered
            Model.name_like('bob').ordered().limit(5)

        """
        if not hasattr(cls, 'scopes'): cls.scopes = {}

        if type(name_or_func).__name__ == 'function':
            name = name_or_func.__name__
        elif isinstance(name_or_func, str):
            name = name_or_func

        def scope(cls, *inargs, **inkwargs):
            if type(name_or_func).__name__ == 'function':
                delayed = name_or_func
            elif len(args) > 0 and type(args[0]).__name__ == 'function':
                delayed = args[0]
            else:
                delayed = None

            if delayed:
                options = cls._parse_scope_options(
                        delayed(cls, *inargs, **inkwargs))
            elif isinstance(name_or_func, str):
                options = cls._parse_scope_options(*args, **kwargs)

            rel = cls._apply_scope_options(cls.scoped(), options)

            return rel

        scope.__name__ = name

        cls.scopes[name] = scope
        setattr(cls, name, types.MethodType(scope, cls, cls.__class__))

        return scope
    scope = define_scope
    #}

    #{ Association Declaration
    @classmethod
    def belongs_to(cls, id, **kwargs):
        """
        Create a belongs association

        Defines a belongs association by the name specified by C{id}, and you
        can access the association through a method by this name will be
        created.  A call to this method will run the query for this association
        and return the result, or, if this query has been run previously (or if
        it was eager loaded), it will return the cached result.

        In addition to keywords listed below this method also accepts all of
        the query finder options specified on (TODO: Insert Link)

        @param id: name of the association
        @keyword class_name: Unambiguous name (string) of source class
        (required).
        @keyword klass: Can be used in place of C{class_name} -- the source
        class.
        @keyword primary_key: Primary key of source model (default: primary key
        of source model)
        @keyword foreign_key: Foreign key of this model (default: id + '_id')
        @keyword polymorphic: Set to True if this is a polymorphic association.
        Class name will be looked for in the (id + '_type') field. (default:
        False)
        @keyword namespace: For polymorphic associations set the full or
        partial namespace to prepend to the '_type' field. (default: None)
        @return: None

        """
        cls._create_external_association(BelongsTo(cls, id, **kwargs))

    @classmethod
    def has_many(cls, id, **kwargs):
        """
        Create has collection association

        Defines a has association by the name specified by C{id}.  After adding
        this association you will be able to access it through a method named
        the same as the association.  This method will return an instance of
        L{Relation} representing the query to be run.  You can treat the
        resulting object as a list of results, and the query will be executed
        whenever necessary.  This allows you to chain additional scopes on the
        query before executing (e.g.  person.addresses().primary()).

        In addition to keywords listed below this method also accepts all of
        the query finder options specified on (TODO: Insert Link)

        @param id: name of the association
        @keyword class_name: Unambiguous name (string) of source class
        (required).
        @keyword klass: Can be used in place of C{class_name} -- the source
        class.
        @keyword primary_key: Primary key of source model (default: primary key
        of source model)
        @keyword foreign_key: Foreign key of this model (default: id + '_id')
        @keyword as_: When source is polymorphic this will specify the class
        name to use (required when source is polymorphic).
        @return: None

        """
        cls._create_external_association(HasMany(cls, id, **kwargs))

    @classmethod
    def has_one(cls, id, **kwargs):
        """
        Create singular has association

        Defines a has association by the name specified by C{id}, and allows
        access to the association by a method of the same name.  A call to that
        method will run the query for this association and return the resulting
        object, or, if the query has been run previously (or it was eager
        loaded), it will return the cached result.

        In addition to keywords listed below this method also accepts all of
        the query finder options specified on (TODO: Insert Link)

        @param id: name of the association
        @keyword class_name: Unambiguous name (string) of source class
        (required).
        @keyword klass: Can be used in place of C{class_name} -- the source
        class.
        @keyword primary_key: Primary key of source model (default: primary key
        of source model)
        @keyword foreign_key: Foreign key of this model (default: id + '_id')
        @keyword as_: When source is polymorphic this will specify the class
        name to use (required when source is polymorphic).
        @return: None

        """
        cls._create_external_association(HasOne(cls, id, **kwargs))
    #}

    @classmethod
    def _create_external_association(cls, association):
        cls.defined_associations[association.id] = association

    def _has_writer_property(self, key):
        """Return True iff key is a property with a setter"""
        value = self.__class__.__dict__.get(key)
        if value and hasattr(value, 'fset') and getattr(value, 'fset'):
            return True
        else:
            return False

    @classmethod
    def _parse_scope_options(cls, *args, **kwargs):
        """Common method for parsing out scope options"""
        if len(args) > 0 and not kwargs:
            if isinstance(args[0], dict) or isinstance(args[0], Relation):
                options = args[0]
            else:
                options = None
        elif len(args) == 0 and kwargs:
            options = kwargs
        else:
            options = None

        if not options:
            raise errors.ArgumentError("Invalid scoping arguments (%s, %s)"
                    % (args, kwargs))

        return options

    @classmethod
    def _apply_scope_options(cls, relation, options):
        if isinstance(options, dict):
            return relation.apply_finder_options(options)
        elif isinstance(options, Relation):
            return relation.merge(options)


    def __repr__(self):
        """Return a string representation of the object"""
        return "<%s object %s new_record=%s>" % (
                self.__class__.__name__,
                self.attributes,
                self.new_record)

