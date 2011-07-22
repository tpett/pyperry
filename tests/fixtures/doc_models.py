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
        cls.belongs_to('foo')
        cls.belongs_to('ape')
        cls.has_many('bars')
        cls.has_many('bananas')
