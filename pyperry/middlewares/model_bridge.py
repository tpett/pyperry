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
        """Create perry.Base instances from the raw records dictionaries."""
        if 'relation' in kwargs:
            relation = kwargs['relation']
            records = [relation.klass(record) for record in records if record]
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
        """
        Updates the model's state attributes and retrieves a fresh version of
        the data attributes if a read adapter is configured.

        """
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
        """Updates the model instance when a save fails"""
        model.saved = False
        self.add_errors(response, model, 'record not saved')

    def handle_delete(self, response, **kwargs):
        """Updates the model instance after a delete"""
        if 'object' in kwargs:
            model = kwargs['object']
            if response.success:
                model.freeze()
            else:
                self.add_errors(response, model, 'record not deleted')
        return response

    def add_errors(self, response, model, default_message):
        """
        Copies the response errors to the model or uses a default error
        message if the response errors are empty.

        """
        errors = response.errors()
        if len(errors) == 0:
            errors =  { 'base': default_message }
        model.errors = errors

