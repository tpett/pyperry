class Scope(object):
    """
    Defines a query shortcut.

    A scope can be defined in one of several ways:

    Dictionary or Keyword Arguments

    If your scope is simply setting a few static query arguments than this
    is the easiest option.  Here are a few examples::

        # With a dictionary
        ordered = Scope({ 'order': 'name' })

        # With keyword arguments
        awesome = Scope(where={'awesome': 1})
        latest = Scope(order="created_at DESC", limit=1)

    With a Callable (as decorators)

    When your scope involves chaining other scopes, delayed values (such as
    a relative time), or if it takes arguments then this is the preferred
    method.  Here are a few examples::

        @Scope
        def awesome_ordered(cls):
            return cls.ordered().awesome()

        # Returns a scope dynamically generating condition using fictional
        # minutes_ago function.  Without the lambda this wouldn't update
        # each time the scope is used, but only when the code was reloaded.

        @Scope
        def recent(cls):
            return cls.where('created_at > %s' % minutes_ago(5))

        # You can also pass arguments at runtime!

        @Scope
        def name_like(cls, word):
            return cls.where(["name LIKE '%?%", word])

    These scopes can be chained. Like so::

        # Returns a max of 5 records that have a name containing 'bob'
        # ordered
        Model.name_like('bob').ordered().limit(5)

    """

    def __init__(self, dict_or_callable=None, **kwargs):
        if callable(dict_or_callable):
            self.callable = dict_or_callable
            self.__name__ = self.callable.__name__
        elif isinstance(dict_or_callable, dict):
            kwargs.update(dict_or_callable)
        elif dict_or_callable is not None:
            raise Exception(
                    "Invalid Scope parameter %s.  Must be dict or callable"
                    % dict_or_callable)

        if not hasattr(self, '__name__'):
            self.__name__ = None

        # Set when the attribute is fetched through __get__
        self.model = None
        self.finder_options = kwargs

    def __get__(self, instance, owner):
        if instance is None:
            self.model = owner
            return self
        else:
            raise Exception("Scopes cannot be applied on an instance.")

    def __call__(self, *args, **kwargs):
        if hasattr(self, 'callable'):
            return self.callable(self.model, *args, **kwargs)
        else:
            return self.model.scoped().apply_finder_options(
                    self.finder_options)


class DefaultScope(Scope):
    """
    Add a default scoping for this model.  Same interface as Scope.

    All queries will be built based on the default scope of this model.  Only
    specify a default scope if you I{always} want the scope applied.
    Attributes set with C{DefaultScope} aggregate.  So each call will append to
    options from previous calls.

    Note: You can bypass default scopings using the L{unscoped()} method.

    Similar to arguments accepted by L{Scope}.  The only thing not
    supported is lambdas/functions accepting additional arguments. Here are
    some examples::

        DefaultScope(where={'type': 'Foo'})
        DefaultScope({ 'order': 'name DESC' })

        @DefaultScope
        def _default(cls):
            return cls.where('foo')

    """
    pass
