from pyperry.errors import ConfigurationError

class CallbackManager(object):
    """
    Manage the callbacks for a model.

    Register a callback with the %L{register} method and trigger events with
    the %L{trigger} method.  An instance can be copied by passing it to
    %L{__init__}.

    @attribute callbacks: a dict of types mapped to lists of callbacks

    """

    def __init__(self, instance=None):
        """
        Constructor

        Takes an optional instance of %L{CallbackManager} to be copied.

        @param instance: instance of %L{CallbackManager}

        """
        self.callbacks = {}

        if instance is not None:
            if isinstance(instance, CallbackManager):
                self.callbacks.update(instance.callbacks)
            else:
                raise ConfigurationError("CallbackManager type expected.")

    def register(self, callback):
        """
        Register the given callback with this manager

        @param callback: Instance of %L{Callback} to register

        """
        callback_type = type(callback)

        if not self.callbacks.get(callback_type):
            self.callbacks[callback_type] = []

        self.callbacks[callback_type].append(callback)

    def trigger(self, callback_type, *args):
        """
        Trigger all registered callbacks of the given callback type

        @param callback_type: type of callback

        """
        if self.callbacks.has_key(callback_type):
            for cb in self.callbacks[callback_type]:
                cb(*args)

class Callback(object):
    """
    Base abstract class for all callbacks.

    @attribute action: String representation of the action
        ('update', 'create', 'destroy', 'save', 'loaded)

    @attribute when: String representation of when the callback should run
        ('before', or 'after')

    @attribute callback: callable that is called on the event.  (arity = 1)
    """

    def __init__(self, callback):
        self.action = None
        self.when = None
        self.callback = callback

        if not callable(self.callback):
            raise ConfigurationError(
                    "Callback must be initialized with a callable." )

    def __call__(self, instance):
        return self.callback(instance)

##
# Explicitly define each of the possible callbacks:
##

class before_load(Callback):
    def __init__(self, callback):
        super(before_load, self).__init__(callback)
        self.action = 'load'
        self.when = 'before'

class after_load(Callback):
    def __init__(self, callback):
        super(after_load, self).__init__(callback)
        self.action = 'load'
        self.when = 'after'

class before_create(Callback):
    def __init__(self, callback):
        super(before_create, self).__init__(callback)
        self.action = 'create'
        self.when = 'before'

class after_create(Callback):
    def __init__(self, callback):
        super(after_create, self).__init__(callback)
        self.action = 'create'
        self.when = 'after'

class before_update(Callback):
    def __init__(self, callback):
        super(before_update, self).__init__(callback)
        self.action = 'update'
        self.when = 'before'

class after_update(Callback):
    def __init__(self, callback):
        super(after_update, self).__init__(callback)
        self.action = 'update'
        self.when = 'after'

class before_save(Callback):
    def __init__(self, callback):
        super(before_save, self).__init__(callback)
        self.action = 'save'
        self.when = 'before'

class after_save(Callback):
    def __init__(self, callback):
        super(after_save, self).__init__(callback)
        self.action = 'save'
        self.when = 'after'

class before_delete(Callback):
    def __init__(self, callback):
        super(before_delete, self).__init__(callback)
        self.action = 'delete'
        self.when = 'before'

class after_delete(Callback):
    def __init__(self, callback):
        super(after_delete, self).__init__(callback)
        self.action = 'delete'
        self.when = 'after'

