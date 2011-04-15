from copy import copy

import pyperry
from pyperry import errors

class DelayedConfig(object):
    """
    Simple class that takes kwargs or a dictionary in initializer and sets
    values to the class dictionary.  Any values set as lambdas will be
    evaluated when they are accessed.
    """

    def __init__(self, *args, **kwargs):
        """Set values in kwargs to attributes"""
        if not kwargs and len(args) is 1:
            kwargs = args[0]

        for k, v in kwargs.items():
            self.__dict__[k] = v

    def __getattribute__(self, key):
        attr = object.__getattribute__(self, key)
        if type(attr).__name__ == 'function':
            attr = attr()
        return attr


class AbstractAdapter(object):
    """The base class for all adapters"""

    adapter_types = ['read', 'write']

    def __init__(self, config, mode=None, middlewares=None):
        """
        Create a new adapter object with the given configuration running as a
        `mode` adapter
        """
        if not middlewares:
            middlewares = []

        self.config = DelayedConfig(config)
        self.mode = mode
        self.middlewares = middlewares
        self._stack = None

        # Add in configured middlewares
        if hasattr(self.config, '_middlewares'):
            self.middlewares = self.middlewares + self.config._middlewares

        if not mode in self.adapter_types:
            raise errors.ConfigurationError("Adapter requires `mode` keyword")

    @property
    def stack(self):
        """
        Setup the stack plumbing with the configured middleware

        Wrap each middleware in reverse order around the call to the adapter
        method.  This will allow middlewares to intercept requests, modify
        query information and pass it along, do things with the results of the
        query or any combination of these things.
        """
        if self._stack: return self._stack

        self._stack = getattr(self, self.mode)
        middlewares = copy(self.middlewares)
        middlewares.reverse()

        for (klass, config) in middlewares:
            self._stack = klass(self._stack, config)

        return self._stack

    def reset(self):
        """Clear out the stack causing it to be rebuilt on the next request"""
        self._stack = None

    def __call__(self, **kwargs):
        """Makes a request to the stack"""
        pyperry.logger.info('%s: %s' % (self.mode, kwargs.keys()))
        result = self.stack(**kwargs)

        if self.mode is 'read' and not hasattr(result, '__iter__'):
            raise errors.BrokenAdapterStack(
                    "The adapter stack failed to return an iterable object" )

        return result

    def read(self, **kwargs):
        """Read from the datastore with the provided options"""
        raise NotImplementedError("You must define this method in subclasses")

    def write(self, **kwargs):
        """Write object's attributes to the datastore"""
        raise NotImplementedError("You must define this method in subclasses")

