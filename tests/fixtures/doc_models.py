import pyperry
from pyperry.attribute import Attribute

class DirModel(pyperry.Base):
    id = Attribute()
    foo = Attribute()
    bar = Attribute()

    def _config(cls):
        cls.belongs_to('owner')
        cls.has_many('children')

class HelpModel(pyperry.Base):
    """a model with a docstring"""
    attr1 = Attribute()
    attr2 = Attribute()

    def _config(cls):
        cls.belongs_to('foo', polymorphic=True)
        cls.belongs_to('ape')
        cls.has_many('bars', through='bananas')
        cls.has_many('bananas')

class AssociationModel(pyperry.Base):
    def _config(cls):
        cls.belongs_to('you')
        cls.belongs_to('foo', polymorphic=True)
        cls.has_one('bar')
        cls.has_many('bizs')
        cls.has_many('bazs', through='bizs')
