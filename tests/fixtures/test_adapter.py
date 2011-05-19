from pyperry.adapter.abstract_adapter import AbstractAdapter
from pyperry.response import Response
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


class SuccessAdapter(object):
    """Adapter-like class where __call__ always returns a success response"""

    def __init__(self):
        self.response = Response(**{
            'success': True,
            'parsed': { 'id': 42 }
        })

    def __call__(self, **kwargs):
        return self.response


class FailureAdapter(object):
    """Adapter-like class where __call__ always returns a failure response"""

    def __init__(self):
        self.response = Response(**{
            'success': False,
            'parsed': { 'base': 'record invalid', 'name': "can't be blank" }
        })

    def __call__(self, **kwargs):
        return self.response
