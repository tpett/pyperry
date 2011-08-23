import pyperry
from pyperry.field import Field
from pyperry.association import BelongsTo, HasOne, HasMany, HasManyThrough

class DirModel(pyperry.Base):
    id = Field()
    foo = Field()
    bar = Field()

    owner = BelongsTo()
    children = HasMany()

class HelpModel(pyperry.Base):
    """a model with a docstring"""
    attr1 = Field()
    attr2 = Field()

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

