from pyperry.errors import ConfigurationError

class _Callback(object):
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

class before_load(_Callback):
    def __init__(self, callback):
        super(before_load, self).__init__(callback)
        self.action = 'load'
        self.when = 'before'

class after_load(_Callback):
    def __init__(self, callback):
        super(after_load, self).__init__(callback)
        self.action = 'load'
        self.when = 'after'

class before_create(_Callback):
    def __init__(self, callback):
        super(before_Create, self).__init__(callback)
        self.action = 'create'
        self.when = 'before'

class after_create(_Callback):
    def __init__(self, callback):
        super(after_create, self).__init__(callback)
        self.action = 'create'
        self.when = 'after'

class before_update(_Callback):
    def __init__(self, callback):
        super(before_update, self).__init__(callback)
        self.action = 'update'
        self.when = 'before'

class after_update(_Callback):
    def __init__(self, callback):
        super(after_update, self).__init__(callback)
        self.action = 'update'
        self.when = 'after'

class before_save(_Callback):
    def __init__(self, callback):
        super(before_save, self).__init__(callback)
        self.action = 'save'
        self.when = 'before'

class after_save(_Callback):
    def __init__(self, callback):
        super(after_save, self).__init__(callback)
        self.action = 'save'
        self.when = 'after'

class before_destroy(_Callback):
    def __init__(self, callback):
        super(before_destroy, self).__init__(callback)
        self.action = 'destroy'
        self.when = 'before'

class after_destroy(_Callback):
    def __init__(self, callback):
        super(after_destroy, self).__init__(callback)
        self.action = 'destroy'
        self.when = 'after'

