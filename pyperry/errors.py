class PerryError(Exception):
    pass

class ConfigurationError(PerryError):
    pass

class ArgumentError(PerryError):
    pass

class BrokenAdapterStack(PerryError):
    pass

class ModelNotDefined(PerryError):
    pass

class AmbiguousClassName(PerryError):
    pass

class PersistenceError(PerryError):
    pass

class MalformedResponse(PerryError):
    pass

class AssociationNotFound(PerryError):
    pass

class AssociationPreloadNotSupported(PerryError):
    pass

class RecordNotFound(PerryError):
    pass

