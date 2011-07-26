import pyperry

class DirModel(pyperry.Base):
    def _config(cls):
        cls.attributes('id', 'foo', 'bar')
        cls.belongs_to('owner')
        cls.has_many('children')

class HelpModel(pyperry.Base):
    """a model with a docstring"""
    def _config(cls):
        cls.attributes('attr1', 'attr2')
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
