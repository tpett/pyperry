class ConfigurationError(Exception):
    pass

class ArgumentError(Exception):
    pass

class BrokenAdapterStack(Exception):
    pass

class ModelNotDefined(Exception):
    pass

class AmbiguousClassName(Exception):
    pass

class PersistenceError(Exception):
    pass

class MalformedResponse(Exception):
    pass

class AssociationNotFound(Exception):
    pass

class AssociationPreloadNotSupported(Exception):
    pass

class RecordNotFound(Exception):
    pass
