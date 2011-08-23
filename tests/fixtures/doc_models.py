import pyperry
from pyperry.attribute import Attribute
from pyperry.association import BelongsTo, HasOne, HasMany, HasManyThrough

class DirModel(pyperry.Base):
    id = Attribute()
    foo = Attribute()
    bar = Attribute()

    owner = BelongsTo()
    children = HasMany()

class HelpModel(pyperry.Base):
    """a model with a docstring"""
    attr1 = Attribute()
    attr2 = Attribute()

    foo = BelongsTo(polymorphic=True)
    ape = BelongsTo()
    bars = HasManyThrough(through='bananas')
    bananas = HasMany()

class AssociationModel(pyperry.Base):
    you = BelongsTo()
    foo = BelongsTo(polymorphic=True)
    bar = HasOne()
    bizs = HasMany()
    bazs = HasManyThrough(through='bizs')

