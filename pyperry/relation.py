from copy import copy, deepcopy

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

    singular_query_methods = ['limit', 'offset', 'from', 'sql']
    plural_query_methods = ['select', 'group', 'order', 'joins', 'includes',
            'where', 'having']
    aliases = { 'from_': 'from', 'conditions': 'where' }

    def __init__(self, klass):
        """Set klass this relation object is mapped to"""
        self.klass = klass
        self.params = {}
        self._query = None
        self._records = None

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


    def first(self, options={}):
        """Apply a limit scope of 1 and return the resulting singular value"""
        options.update({ 'limit': 1 })
        return self.all(options)[0]

    def all(self, options={}):
        """
        Apply any finder options passed and execute the query returning the
        list of records
        """
        return self.apply_finder_options(options).fetch_records()

    def apply_finder_options(self, options):
        """Apply given dictionary as finder options returning a new relation"""
        self = self.clone()

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
        a = copy(a)
        for k, v in b.iteritems():
            if k in a and hasattr(v, 'iteritems'):
                a[k] = self._deep_merge(a[k], v)
            else:
                a[k] = v
        return a

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
        def method(self, *value):
            self = self.clone()
            # If they are passing in a list rather than a tuple
            if len(value) == 1 and isinstance(value[0], list):
                value = value[0]
            self.params[key] += list(value)
            return self

        method.__name__ = key
        setattr(self.__class__, key, method)

    def clone(self):
        return deepcopy(self)

    def __repr__(self):
        return repr(self.fetch_records())
        # return("<Relation for %s Query: %s>" %
        #         (self.klass.__name__, str(self.params)) )

    def _eval_lambdas(self, value):
        if type(value).__name__ == 'list':
            return [ self._eval_lambdas(item) for item in value ]
        elif type(value).__name__ == 'function':
            return value()
        else:
            return value
