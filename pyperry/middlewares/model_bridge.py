from pyperry.errors import ConfigurationError

class ModelBridge(object):

    def __init__(self, next, options={}):
        self.next = next
        self.options = options

    def __call__(self, **kwargs):
        results = self.next(**kwargs)
        mode = kwargs['mode']

        if mode == 'read':
            results = self.handle_read(results, **kwargs)
        elif mode == 'write':
            results = self.handle_write(results, **kwargs)
        elif mode == 'delete':
            results = self.handle_delete(results, **kwargs)

        return results

    def handle_read(self, records, **kwargs):
        if 'relation' in kwargs:
            relation = kwargs['relation']
            records = [relation.klass(record) for record in records]
        return records

    def handle_write(self, response, **kwargs):
        if 'object' in kwargs:
            model = kwargs['object']
            if response.success:
                self.handle_write_success(response, model)
            else:
                self.handle_write_failure(response, model)
        return response

    def handle_write_success(self, response, model):
        has_read_adapter = True
        try:
            model.read_adapter()
        except ConfigurationError:
            has_read_adapter = False

        if model.new_record and has_read_adapter:
            model.id = response.model_attributes()['id']

        if has_read_adapter:
            model.reload()

        model.saved = True
        model.new_record = False

    def handle_write_failure(self, response, model):
        model.saved = False
        errors = response.errors()
        if len(errors) == 0:
            errors = { 'base': 'record not saved' }
        model.errors = errors

    def handle_delete(self, response, **kwargs):
        return response
