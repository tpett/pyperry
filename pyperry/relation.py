from copy import deepcopy

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
                self.aliases.keys() )

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

        for method in self.singular_query_methods + self.plural_query_methods:
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
        for method in self.singular_query_methods + self.plural_query_methods:
            value = self.params[method]
            if value:
                self._query[method] = self._eval_lambdas(value)

        return self._query

    def fetch_records(self):
        """Perform the query and return the resulting list (aliased as list)"""
        if not self._records:
            self._records = self.klass.fetch_records(self)
        return self._records
    list = fetch_records

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

