from pyperry.adapter.abstract_adapter import AbstractAdapter
from copy import deepcopy

class TestAdapter(AbstractAdapter):
    """Adapter used for running tests"""

    calls = []
    data = {}
    count = 1
    return_val = True

    def __init__(self, *args, **kwargs):
        AbstractAdapter.__init__(self, *args, **kwargs)

    def read(self, **kwargs):
        self.calls.append(kwargs['relation'].query())
        return [ self.data for i in range(self.count) ]

    def write(self, **kwargs):
        self.calls.append(('write', deepcopy(kwargs)))
        return self.return_val


    @classmethod
    def reset(cls):
        """Reset the adapter"""
        cls.calls = []
        cls.data = {}
        cls.count = 1

