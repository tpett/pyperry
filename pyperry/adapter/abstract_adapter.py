"""
Adapter Overview
================

Adapters provide the bridge between the mapped object and the data store.
There are several layers to an adapter request and response::

     Req  Resp
  pyperry.base.Base
      |     ^
      V     |
    Processors
      |     ^
      V     |
    Model Bridge
      |     ^
      V     |
    Middlewares
      |     ^
      V     |
      Adapter
        \/
      Database

The request is initiated by the L{pyperry.base.Base} class and passes through
the adapter stack returning a response.  Within the stack the request goes
through a series of configurable stack items: processors, and middlewares
before being passed to the appropriate adapter method.  That adapter method
then executes the requested action and returns the results back through the
stack until returning to Base.

Processors and middlewares are ways of customizing requests and responses.
There is a middleware that is always installed called the ModelBridge.  It
takes the raw response of the adapter and converts it to mapped objects.  The
only difference between a middleware and a processor is that the objects
returned to a processor are always instantiated records whereas middlewares
receive the raw response.

"""
from copy import copy
import socket

import pyperry
from pyperry import errors
from pyperry.middlewares.model_bridge import ModelBridge

class DelayedConfig(object):
    """
    Simple class that takes kwargs or a dictionary in initializer and sets
    values to the `config` dictionary.  Any values set as callables with an
    arity of 0 will be evaluated when they are accessed. If the callables arity
    is greater than 0, it will not be called automatically.
    """

    def __init__(self, *args, **kwargs):
        """Set values in kwargs to attributes"""
        self.config = {}

        if len(args) == 1 and isinstance(args[0], DelayedConfig):
            self.config = args[0].config.copy()
        elif len(args) == 1 and isinstance(args[0], dict):
            kwargs.update(args[0])

        for k, v in kwargs.items():
            self.config[k] = v

    def __getitem__(self, key):
        value = self.config[key]

        if callable(value) and value.func_code.co_argcount == 0:
            value = value()

        return value

    def __setitem__(self, key, value):
        self.config[key] = value

    def update(self, config):
        if isinstance(config, DelayedConfig):
            config = config.config

        self.config.update(config)

    def keys(self):
        return self.config.keys()


class AbstractAdapter(object):
    """The base class for all adapters"""

    adapter_types = ['read', 'write']

    def __init__(self, config={}, **kwargs): #middlewares=None, processors=[]):
        """
        Create a new adapter object with the given configuration.
        """
        if isinstance(config, AbstractAdapter):
            self.middlewares = config.middlewares
            self.processors = config.processors
            config = config.config
        else:
            self.middlewares = kwargs.get('middlewares') or [(ModelBridge, {})]
            self.processors = kwargs.get('processors') or []
            config.update(kwargs)

        self.config = DelayedConfig(config)
        self._stack = None

        if 'timeout' in self.config.keys():
            socket.setdefaulttimeout(self.config['timeout'])

        # Add in configured middlewares
        if '_middlewares' in self.config.keys():
            self.middlewares = self.middlewares + self.config['_middlewares']
        if '_processors' in self.config.keys():
            self.processors = self.processors + self.config['_processors']

    @property
    def stack(self):
        """
        Setup the stack plumbing with the configured stack items

        Wrap each stack item (processors and middleware) in reverse order
        around the call to the adapter method. This will allow stack items to
        intercept requests, modify query information and pass it along, do
        things with the results of the query or any combination of these
        things.

        """
        if self._stack: return self._stack

        self._stack = self.execute
        stack_items = copy(self.processors) + copy(self.middlewares)
        stack_items.reverse()

        for (klass, config) in stack_items:
            self._stack = klass(self._stack, config)

        return self._stack

    def reset(self):
        """Clear out the stack causing it to be rebuilt on the next request"""
        self._stack = None

    def __call__(self, **kwargs):
        """Makes a request to the stack"""
        if 'mode' not in kwargs:
            raise errors.ConfigurationError("Must pass `mode` to adapter call")
        pyperry.logger.debug('%s: %s' % (kwargs['mode'], kwargs.keys()))
        result = self.stack(**kwargs)

        if kwargs['mode'] is 'read' and not hasattr(result, '__iter__'):
            raise errors.BrokenAdapterStack(
                    "The adapter stack failed to return an iterable object" )

        return result

    def execute(self, **kwargs):
        """Call read, write, or delete according to the mode kwarg."""
        return getattr(self, kwargs['mode'])(**kwargs)

    def read(self, **kwargs):
        """Read from the datastore with the provided options"""
        raise NotImplementedError("You must define this method in subclasses")

    def write(self, **kwargs):
        """Write object's attributes to the datastore"""
        raise NotImplementedError("You must define this method in subclasses")

    def delete(self, **kwargs):
        """Delete the object from the datastore"""
        raise NotImplementedError("You must define this method in subclasses")

    def merge(self, source={}, **kwargs):
        new = self.__class__(self)

        if isinstance(source, AbstractAdapter):
            new.config.update(source.config)
            new.middlewares += source.middlewares
            new.processors += source.processors
        elif isinstance(source, dict):
            source.update(kwargs)
            new.config.update(source)

        return new

