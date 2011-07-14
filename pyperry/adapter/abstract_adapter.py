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

    def __init__(self, config, mode=None, middlewares=None, processors=[]):
        """
        Create a new adapter object with the given configuration running as a
        `mode` adapter
        """
        if not middlewares:
            middlewares = [(ModelBridge, {})]

        self.config = DelayedConfig(config)
        self.mode = mode
        self.middlewares = middlewares
        self.processors = processors
        self._stack = None

        if hasattr(self.config, 'timeout'):
            socket.setdefaulttimeout(self.config.timeout)
        elif socket.getdefaulttimeout() is None:
            socket.setdefaulttimeout(10)

        # Add in configured middlewares
        if hasattr(self.config, '_middlewares'):
            self.middlewares = self.middlewares + self.config._middlewares
        if hasattr(self.config, '_processors'):
            self.processors = self.processors + self.config._processors

        if not mode in self.adapter_types:
            raise errors.ConfigurationError("Adapter requires `mode` keyword")

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
        pyperry.logger.debug('%s: %s' % (self.mode, kwargs.keys()))
        if 'mode' not in kwargs:
            kwargs.update(mode=self.mode)
        result = self.stack(**kwargs)

        if self.mode is 'read' and not hasattr(result, '__iter__'):
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
