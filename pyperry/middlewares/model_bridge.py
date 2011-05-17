class ModelBridge(object):

    def __init__(self, next, options={}):
        self.next = next
        self.options = options

    def __call__(self, **kwargs):
        results = self.next(**kwargs)
        if 'relation' in kwargs:
            relation = kwargs['relation']
            results = [relation.klass(record) for record in results]
        return results
