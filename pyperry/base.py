import datetime
import types
from copy import deepcopy, copy

from pyperry import errors
from pyperry.relation import Relation
from pyperry.adapter.abstract_adapter import AbstractAdapter
from pyperry.association import BelongsTo, HasMany, HasOne

class BaseMeta(type):
    """The Metaclass for Base"""

    defined_models = {}

    def __new__(mcs, name, bases, dict_):
        """
        Called any time a new Base class is created using this metaclass
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
        """Allow delegation to Relation"""
        relation_delegation = (
                Relation.singular_query_methods +
                Relation.plural_query_methods +
                ['all', 'first'] )
        if key in relation_delegation:
            return getattr(cls.scoped(), key)
        else:
            raise AttributeError("Undefined attribute '%s'" % key)

    def resolve_name(cls, name):
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
    """The Base class for all models using the pyperry"""

    __metaclass__ = BaseMeta

    def __init__(self, attributes, new_record=True):
        """Initialize a new pyperry object with attributes"""
        self.attributes = {}
        self.set_attributes(attributes)
        self.new_record = new_record

    ##
    # Add access to attributes through hash indexing and the normal
    # object accessors
    #
    # This allows cool stuff like:
    #
    #   project['id']
    #   project['name'] = "Foo"
    #   project.id
    #   project.name = "Foo"
    #
    # Any methods named the same as an attribute and declared as properties
    # will be called automatically.  The [_key_] method of accessing should
    # never be shadowed
    #
    def __getitem__(self, key):
        if key in self.defined_attributes:
            # Using get() here to avoid KeyError on uninitialized attrs
            return self.attributes.get(key)
        else:
            raise KeyError("Undefined attribute '%s'" % key)

    def __setitem__(self, key, val):
        if key in self.defined_attributes:
            self.attributes[key] = val
        else:
            raise KeyError("Undefined attribute '%s'" % key)

    def __getattr__(self, key):
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
        if(key in self.defined_attributes
                and not self._has_writer_property(key)):
            self[key] = value
        else:
            object.__setattr__(self, key, value)


    def set_attributes(self, attributes):
        """
        Set the attributes of the object using the provided dictionary.  Only
        attributes defined using define_attributes will be set.
        """
        for field in attributes.keys():
            if field in self.defined_attributes:
                self[field] = attributes[field]

    def save(self):
        """Save the current state of the model through the write adapter"""
        return self.adapter('write')(model=self)

    def update_attributes(self, attrs=None, **kwargs):
        """
        Update the attributes with the given dictionary or keywords and save
        the model.
        """
        if not attrs:
            attrs = kwargs

        self.set_attributes(attrs)

        return self.save()

    def destroy(self):
        """
        Call the write adapter with delete=True.  Removes the record from the
        data store
        """
        return self.adapter('write')(model=self, delete=True)
    delete = destroy

    @classmethod
    def configure(cls, adapter_type, *args, **kwargs):
        """
        Method for generically setting adapter configuration options.  Accepts a
        dictionary argument or keyword arguments, but not both.
        """
        if adapter_type not in AbstractAdapter.adapter_types:
            raise errors.ConfigurationError(
                    "Unrecognized adapter type: %s" % adapter_type)

        if len(args) == 1 and args[0].__class__ is dict:
            new_dict = args[0]
        else:
            new_dict = kwargs

        if not cls.adapter_config.has_key(adapter_type):
            cls.adapter_config[adapter_type] = {}

        cls.adapter_config[adapter_type].update(new_dict)

    @classmethod
    def add_middleware(cls, adapter_type, klass, options=None, **kwargs):
        if cls.adapter_config.has_key(adapter_type):
            middlewares = cls.adapter_config[adapter_type].get('_middlewares')
        if not 'middlewares' in locals() or not middlewares:
            middlewares = []

        middlewares.append( (klass, options or kwargs or {}) )

        cls.configure(adapter_type, _middlewares=middlewares)

    @classmethod
    def configure_read(cls, *args, **kwargs):
        """Alias to configure('read', ...)"""
        cls.configure('read', *args, **kwargs)

    @classmethod
    def adapter(cls, adapter_type):
        """Returns the adapter specified by type"""
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
    def read_adapter(cls):
        """
        Returns the read adapter for this model.
        """
        return cls.adapter('read')

    @classmethod
    def define_attributes(cls, *attrs):
        """
        Define available attributes for a model.  This method is automatically
        called when the attributes var is set on the class during definition.
        Each call will union any new attributes into the set of defined
        attributes.
        """
        if attrs[0].__class__ in [list, set, tuple]:
            attrs = attrs[0]
        cls.defined_attributes |= set(attrs)
    attributes = define_attributes

    @classmethod
    def fetch_records(cls, relation):
        """
        Actually makes the call to the adapter to pull records from the data
        source.  This method returns an array of objects.  None results are
        ignored.
        """
        return [ cls(item, False) for item in
                cls.read_adapter()(relation=relation) if item ]

    # Scoping methods
    @classmethod
    def relation(cls):
        """
        A base instance of `Relation` for this model.  All query scopes
        originate from this instance.
        """
        if not hasattr(cls, '_relation'): cls._relation = Relation(cls)
        return cls._relation

    @classmethod
    def current_scope(cls):
        """
        Returns an instance of Relation after applying the latest scope in
        the class variable _scoped_methods.  Practically, this applies any
        scopes defined in default_scope calls.
        """
        if not hasattr(cls, '_scoped_methods'): cls._scoped_methods = []
        if len(cls._scoped_methods) > 0:
            return cls._scoped_methods[-1]

    @classmethod
    def scoped(cls):
        """
        Returns either the `current_scope` value or `relation` depending on
        whether or not `current_scope` exists.  If you want an instance of
        relation on this model you most likely want this method.
        """
        if cls.current_scope():
            return cls.relation().merge(cls.current_scope())
        else:
            return cls.relation().clone()

    @classmethod
    def default_scope(cls, *args, **kwargs):
        """
        Setup a default scoping of this model.  You can pass a dictionary of
        finder_options or a relation.  Those query values will be merged into
        all queries on this model.

        Note:  All calls to default_scope aggregate, so each call will append
        to the default query options
        """
        options = cls._parse_scope_options(*args, **kwargs)
        base_scope = cls.current_scope() or cls.relation()
        rel = cls._apply_scope_options(base_scope, options)

        if rel:
            cls._scoped_methods.append(rel)

    @classmethod
    def unscoped(cls, func):
        """
        All default scoping will be removed and the passed function/lambda will
        be evaluated.  After its execution all previous scopes will be
        reapplied.
        """
        cls.current_scope() # Ensure _scoped_methods set
        current_scopes = cls._scoped_methods
        try:
            cls._scoped_methods = []
            func()
        finally:
            cls._scoped_methods = current_scopes

    @classmethod
    def define_scope(cls, name_or_func, *args, **kwargs):
        """Defines a scope on the given model.
        A scope can be defined in one of several ways:

        Dictionary or Keyword Arguments

        If your scope is simply setting a few static query arguments than this
        is the easiest option.  Here are a few examples:

            # With a dictionary
            Model.scope('ordered', { 'order': "name" })

            # With keyword arguments
            Model.scope('awesome', where={'awesome': 1})
            Model.scope('latest', order="created_at DESC", limit=1)

        With a Lambda or Function

        When your scope involves chaining other scopes, delayed values (such as
        a relative time), or if it takes arguments then this is the preferred
        method.  Here are a few examples:

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

        These scopes can be chained. Like so:

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

    @classmethod
    def belongs_to(cls, id, **kwargs):
        cls._create_external_association(BelongsTo(cls, id, **kwargs))

    @classmethod
    def has_many(cls, id, **kwargs):
        cls._create_external_association(HasMany(cls, id, **kwargs))

    @classmethod
    def has_one(cls, id, **kwargs):
        cls._create_external_association(HasOne(cls, id, **kwargs))

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

