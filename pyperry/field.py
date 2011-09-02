
class Field(object):
    """
    An attribute descriptor to handle managing and casting fields on Base

    Designed to return a casted field when called from an instance of Base,
    or the instance of this Field class when called from the class.

    (see documentation on Python descriptors for more information)

    @attribute type: optionally set at instantiation -- if set all values will
    be cast when read and written to this value (by calling it with the value)
    @attribute name: set automatically by the class to the name of the
    attribute (by %L{MetaBase}).  This must be set or errors will happen.
    """

    def __init__(self, type=None, default=None, name=None):
        """
        Creates a new Field instance

        The `name` attribute must be set after instantiation!  In the designed
        workflow this happens automatically.

        @param type: optional cast method to force an attribute to be a
        certain type
        @param default: default value for this attribute (default is None)
        """
        self.type = type
        self.default = default
        # Set by the owner class after init
        self.name = name

    def __get__(self, instance, owner):
        """Get attribute descriptor"""
        # Called from the class (no instance)
        if instance is None:
            return self
        else:
            return self.deserialize(instance[self.name])

    def __set__(self, instance, value):
        """Set attribute descriptor"""
        instance[self.name] = self.serialize(value)

    def __delete__(self, instance):
        """Delete attribute descriptor"""
        del instance[self.name]

    def serialize(self, value):
        """
        Called when the attribute is set and stored in the attribute dict.

        The return value of this method will be the format it is stored in the
        database.  Default is to simply cast it to the specified type or if no
        type is set it is a no-op.  This provides a hook for subclasses to
        easily provide serialize/deserialize behavior.
        """
        return self.cast(value)

    def deserialize(self, value):
        """
        Called when the attribute is retreieved from the attribute dict.

        The return value of this method will be returned to the user.  Default
        is to simply cast it to the specified type or if no type is set it is a
        no-op.  This provides a hook for subclasses to easily provide
        serialize/deserialize behavior.
        """
        return self.cast(value)

    def cast(self, value):
        """
        Cast the value to self.type if set, otherwise just return value
        """
        if self.type is not None and value is not None:
            return self.type(value)
        else:
            return value

