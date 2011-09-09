from copy import copy, deepcopy
from pyperry.errors import ArgumentError, RecordNotFound, PersistenceError
from pyperry.errors import ConfigurationError

class DelayedMerge(object):
    """
    This little class takes a Relation object, and a function that returns a
    Relation object when initialized.  When it is called it passes the params
    on to the function and executes it merging the result on to the original
    Relation object.  This enables chaining scope methods.
    """
    def __init__(self, obj, func):
        self.obj = obj
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.obj.merge(self.func(*args, **kwargs))

class Relation(object):
    """
    Relations
    =========

    The C{Relation} class represents an abstract query for a data store. It
    provides a set of query methods and a set of finder methods that allow you
    to build and execute a query respectively.  While the method names and
    terminology used in this class are representative of SQL queries, the
    resulting query may be used for non-SQL data stores given that an
    appropriate adapter has been written for that data store.

    Method delgation
    ----------------

    L{pyperry.Base} delegates any calls to query methods or finder methods to a
    pre-initialized C{Relation} class. That means that if you have a Person
    model, instead of having to write C{Relation(Person).order('last_name')}
    to create a relation, you can simply write C{Person.order('last_name')}.

    Method chaining
    ---------------

    All query methods can be chained. That means that every query method
    returns a new C{Relation} instance that is a copy of the old relation
    relation merged with the result of calling the current query method. This
    saves a lot of typing when writing longer queries like
    C{Person.order('last_name').limit(10).offset(100).where(age=24).all()}
    Once you call one of the finder methods, the query gets executed and the
    result of that query is returned, which breaks the method chain.

    Query methods
    -------------

    There are two kinds of query methods: singular and plural. Singular query
    methods only store one value in the underlying relation, so succesive calls
    to a singular query method overwrite the old value with the new value. Plural
    query methods may have multiple values, so successive calls to a plural
    query method append or merge the old value with the new value so that all
    values are present in the resulting query. Please note that not all query
    methods will apply to all data stores.

    Singular query methods
    ~~~~~~~~~~~~~~~~~~~~~~

        - B{limit:} (int) limit the number of records returned by the data
          store to the value specified
        - B{offset:} (int) exclude the first N records from the result where
          N is the value passed to offset
        - B{from:} (string) specify the source of the records within the data
          store, such as a table name in a SQL database
        - B{from_:}  alias of C{from}

    Plural query methods
    ~~~~~~~~~~~~~~~~~~~~

        - B{select:} (string) only include the given attributes in the
          resulting records
        - B{where:} (string, dict) specify conditions that the records must
          meet to be included in the result
        - B{order:} (string) order the records by the given values
        - B{joins:} (string) a full SQL join clause
        - B{includes:} (string, dict) L{eager load <PreloadAssociations>} any
          associations matching the given values. Include values may be nested
          in a dict.
        - B{conditions:} alias of C{where}
        - B{group:} (string) group the records by the given values
        - B{having:} (string) specify conditions that apply only to the group
          values
        - B{modifiers:} (dict) include any additional information in the
          relation. Modfiers allow you to include data in your queries that may
          be useful to a L{processor or
          middleware<pyperry.adapter.abstract_adapter>} you write. The
          modifiers value is not included in the dictionary returned by the
          L{query} method, so the modifiers will not be passed on to the data
          store.

    Finder methods
    ==============

        - B{L{first}:} return all records represented by the current relation
        - B{L{all}:} return only the first record represented by the currennt
          relation

    Finder options
    ==============

    The finder methods will also accept a dictionary or keyword arguments
    that specify a query without you having to actually call the query methods.
    The keys should be named the same as the corresponding query methods and
    the values should be the same values you would normally pass to those query
    methods. For example, the following to queries are equivalent::

        Person.order('last_name').limit(10).all()
        Person.all({'order': 'last_name', 'limit': 10})

    Some other methods also accept finder options as a dictionary or keyword
    arguments such as the C{scope} method and association methods on
    L{pyperry.Base}.

    """

    singular_query_methods = ['limit', 'offset', 'from', 'sql']
    plural_query_methods = ['select', 'group', 'order', 'joins', 'includes',
            'where', 'having']
    aliases = { 'from_': 'from', 'conditions': 'where' }

    def __init__(self, klass_or_relation):
        """Set klass this relation object is mapped to"""
        self.params = {}
        self._query = None
        self._records = None

        if isinstance(klass_or_relation, Relation):
            # Copy constructor
            relation = klass_or_relation
            self.klass = relation.klass
            self.params.update(relation.params)
            self.params = self._copy_params(self.params)
        else:
            # assume a Base instance
            self.klass = klass_or_relation

            for method in self.singular_query_methods:
                self.params[method] = None
            for method in self.plural_query_methods:
                self.params[method] = []
            self.params['modifiers'] = []

    # Dynamically create the query methods as they are needed
    def __getattr__(self, key):
        """Delegate missing attributes to appropriate places"""
        if key in self.singular_query_methods:
            self.create_singular_method(key)
            return getattr(self, key)
        elif key in self.plural_query_methods:
            self.create_plural_method(key)
            return getattr(self, key)
        elif key in self.aliases.keys():
            return getattr(self, self.aliases[key])
        # TODO: Investigate why the BALLS I can't just say self.klass here
        # without infinite recursion...
        elif key in self.__dict__['klass'].scopes.keys():
            return DelayedMerge(self, getattr(self.__dict__['klass'], key))
        else:
            raise AttributeError

    # Allows use of iterator like structures on the Relation model.
    # (like for loops, array comprehensions, etc.)
    def __iter__(self):
        for item in self.fetch_records():
            yield(item)

    # Delgates array indexing and splicing to records list
    def __getitem__(self, index):
        return self.fetch_records().__getitem__(index)

    # Delegates len() to the records list
    def __len__(self):
        return len(self.fetch_records())

    # Allow appending two relation's results into a single list
    def __add__(self, b):
        return list(self) + list(b)


    def first(self, options={}, **kwargs):
        """Apply a limit scope of 1 and return the resulting singular value"""
        options.update({ 'limit': 1 })
        records = self.all(options, **kwargs)
        if len(records) > 0:
            return records[0]
        else:
            return None

    def all(self, options={}, **kwargs):
        """
        Apply any finder options passed and execute the query returning the
        list of records
        """
        return self.apply_finder_options(options, **kwargs).fetch_records()

    def find(self, pks_or_mode, options={}, **kwargs):
        """
        Returns a record or list of records matching the primary key or array
        of primary keys given as its first argument. If the first argument is
        one of 'first' or 'all', the C{first} or C{all} finder methods
        respectively are called with the given finder options from the second
        argument.
        """
        if pks_or_mode == 'all':
            return self.all(options, **kwargs)
        elif pks_or_mode == 'first':
            return self.first(options, **kwargs)
        elif isinstance(pks_or_mode, list):
            result = self.where({self.klass.primary_key(): pks_or_mode})
            if len(result) < len(pks_or_mode):
                raise RecordNotFound(
                        self._record_not_found_message(pks_or_mode, result))
            return result
        elif isinstance(pks_or_mode, str) or isinstance(pks_or_mode, int):
            result = self.where({self.klass.primary_key(): pks_or_mode}).first()
            if not result:
                raise RecordNotFound('could not find a record for %s with'
                        'primary key %s' % (self.klass.__name__, pks_or_mode) )
            return result
        else:
            raise ArgumentError('unkown arguments for find method')

    def update_all(self, args=None, **kwargs):
        if args is None:
            args = {}
        args.update(kwargs)

        for arg in args:
            if arg not in self.klass.defined_fields:
                raise PersistenceError(
                        "You cannot batch update a field that is not defined")

        self._ensure_batch_write_allowed(action='update_all')

        self.klass.writer.last_response = self.klass.writer(
                mode='write', where=self.query().get('where'), fields=args)

        return self.klass.writer.last_response.success

    def delete_all(self):
        self._ensure_batch_write_allowed(action='delete_all')
        self.klass.writer.last_response = self.klass.writer(
                mode='delete', where=self.query().get('where'))
        return self.klass.writer.last_response.success

    def _ensure_batch_write_allowed(self, action='batch actions'):
        if not hasattr(self.klass, 'writer') or self.klass.writer is None:
            raise ConfigurationError("Write adapter is not configured")

        if not self.klass.writer.features['batch_write']:
            raise ConfigurationError(
                    "Write adapter does not support %s" % (action))

    def _record_not_found_message(self, pk_array, results):
        err = "Couldn't find %s records for all primary key values in %s. "
        err += "(expected %d records but only found %d)"
        n = len(pk_array)
        m = len(results)
        return err % (self.klass.__name__, str(pk_array), n, m)

    def apply_finder_options(self, options={}, **kwargs):
        """Apply given dictionary as finder options returning a new relation"""
        self = self.clone()
        options = copy(options)
        options.update(kwargs)

        valid_methods = (
                self.singular_query_methods +
                self.plural_query_methods +
                self.aliases.keys() +
                ['modifiers'])

        for method in set(valid_methods) & set(options.keys()):
            if self.aliases.get(method):
                value = options[method]
                method = self.aliases[method]
            else:
                value = options[method]

            if value:
                self = getattr(self, method)(value)

        return self


    def merge(self, relation):
        """Merge given relation onto self returning a new relation"""
        self = self.clone()

        query_methods = (self.singular_query_methods +
                         self.plural_query_methods +
                         ['modifiers'])

        for method in query_methods:
            value = relation.params[method]
            if value and isinstance(value, list):
                self = getattr(self, method)(*value)
            elif value:
                self = getattr(self, method)(value)

        return self

    def query(self):
        """
        Return the query dictionary.  This is used to form the dictionary of
        values used in the fetch_records call.
        """
        if self._query: return self._query

        self._query = {}
        query_methods = [method for method in
                (self.plural_query_methods + self.singular_query_methods)
                if method is not 'includes']

        for method in query_methods:
            value = self.params[method]
            if value:
                self._query[method] = self._eval_lambdas(value)

        value = self.includes_value()
        if value:
            self._query['includes'] = value

        return self._query

    def fetch_records(self):
        """Perform the query and return the resulting list (aliased as list)"""
        if self._records is None:
            self._records = self.klass.fetch_records(self)
        return self._records
    list = fetch_records

    def includes_value(self):
        """
        Combines arguments passed to includes into a single dict to support
        nested includes.

        For example, the following query::

            r = relation.includes('foo')
            r = r.includes({'bar': 'baz'})
            r = r.includes('boo', {'bar': 'biz'})

        will result in an includes dict like this::

            {
                'foo': {},
                'bar': {'biz': {}, 'baz': {}},
                'boo': {}
            }

        """
        values = self.params['includes']
        if not values: return

        values = [(v() if callable(v) else v) for v in values]
        nested_includes = self._get_includes_value(values)
        return nested_includes

    def _get_includes_value(self, value):
        """does the dirty work for includes value"""
        includes = {}

        if not value: # leaf node
            pass
        elif hasattr(value, 'iteritems'): # dict
            for k, v in value.iteritems():
                v = {k: self._get_includes_value(v)}
                includes = self._deep_merge(includes, v)
        elif hasattr(value, '__iter__'): # list, but not string
            for v in value:
                v = self._get_includes_value(v)
                includes = self._deep_merge(includes, v)
        else: # string
            includes.update({value: {}})

        return includes

    def _deep_merge(self, a, b):
        """
        Recursively merges dict b into dict a, such that if a[x] is a dict and
        b[x] is a dict, b[x] is merged into a[x] instead of b[x] overwriting
        a[x].

        """
        a = a.copy()
        for k, v in b.iteritems():
            if k in a and hasattr(v, 'iteritems'):
                a[k] = self._deep_merge(a[k], v)
            else:
                a[k] = v
        return a

    def _copy_params(self, params):
        """
        Recursively copy structure with dict or list elements.  This was added
        because deepmerge() doesn't work correctly with re objects.
        """
        if isinstance(params, dict):
            params = copy(params)
            for key in params:
                params[key] = self._copy_params(params[key])
            return params
        elif isinstance(params, list):
            params = copy(params)
            for i in range(len(params)):
                params[i] = self._copy_params(params[i])
            return params
        else:
            return copy(params)


    def modifiers(self, value):
        """
        A pseudo query method used to store additional data on a relation.

        modifiers expects its value to be either a dict or a lambda that
        returns a dict. Successive calls to modifiers will 'merge' the values
        it receives into a single dict. The modifiers method behaves almost
        identical to a plural query method. You can even use the modifiers
        method in your scopes. The only difference is that the modifiers value
        is not included in the dict returned by the query() method. The purpose
        of having a modifiers query method is to include additional data in the
        query that may be of interest to middlewares or adapters but is not
        inherent to the query itself.

        """
        rel = self.clone()
        if value is None:
            rel.params['modifiers'] = []
        else:
            rel.params['modifiers'].append(value)
        return rel

    def modifiers_value(self):
        """
        Returns the combined dict of all values passed to the modifers method.
        """
        if hasattr(self, '_modifiers'):
            return self._modifiers

        self._modifiers = {}
        for value in self.params['modifiers']:
            if callable(value):
                value = value()
            try:
                self._modifiers.update(value)
            except:
                raise TypeError(
                        'modifier values must evaluate to dict-like objects')

        return self._modifiers

    def create_singular_method(self, key):
        """
        Create a default singular method with the given key.  For special
        functionality you can create a explicit method that will shadow this
        implementation.  These methods will be created dynamically at runtime.
        """
        def method(self, value):
            self = self.clone()
            self.params[key] = value
            return self

        method.__name__ = key
        setattr(self.__class__, key, method)

    def create_plural_method(self, key):
        """
        Create a default plural method with the given key.  For special
        functionality you can create a explicit method that will shadow this
        implementation.  These methods will be created dynamically at runtime.
        """
        def method(self, *value, **kwargs):
            self = self.clone()
            self.params[key] += list(value)
            if len(kwargs) > 0:
                self.params[key].append(kwargs)
            return self

        method.__name__ = key
        setattr(self.__class__, key, method)

    def clone(self):
        return self.__class__(self)

    def reset(self):
        self._records = None
        self._query = None

    def __repr__(self):
        return("<Relation for %s Query: %s>" %
                (self.klass.__name__, str(self.params)) )

    def _eval_lambdas(self, value):
        if type(value).__name__ == 'list':
            return [ self._eval_lambdas(item) for item in value ]
        elif callable(value):
            return value()
        else:
            return value
