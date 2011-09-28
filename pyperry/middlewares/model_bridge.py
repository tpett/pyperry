from pyperry.errors import ConfigurationError
from pyperry import caching

class ModelBridge(object):
    """
    The C{ModelBridge} class is positioned between the processors and
    middlewares in the L{adapter's request/response call stack
    <AbstractAdapter>}. Before the response from an adapter call reaches the
    C{ModelBridge}, the middlewares can only reliable work with the raw
    response data. After the C{ModelBridge} handles the response, the
    processors that follow can now operate on model instances (subclasses of
    C{pyperry.Base}) instead of the raw response data.

    On adapter reads, the C{ModelBridge} takes the list of records returned by
    the adapter call and creates a model instance of the appropriate type for
    each record in the list.

    On adapter writes and deletes, the C{ModelBridge} class updates the state
    of the model instance being saved or deleted to reflect the data stored in
    the Response object returned by the adapter call. This includes things like
    updating a model's C{saved} and C{new_record} attributes in addition to
    putting error messages on the model if the adapter received an error
    response. Additionally, the C{ModelBridge} will refresh all of the model's
    data attributes (specified by setting a class attribute of type Field)
    after a successful write if a read adapter is configured for the model.

    """

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
            records = [relation.klass(record, False)
                       for record in records if record]
        return records

    def handle_write(self, response, **kwargs):
        """Updates a model after a save."""
        caching.reset()
        if 'model' in kwargs:
            model = kwargs['model']
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
        has_read_adapter = (hasattr(model, 'reader') and
                model.reader is not None)

        if model.new_record and has_read_adapter:
            setattr(model, model.pk_attr(),
                    response.model_attributes()[model.pk_attr()])

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
        caching.reset()
        if 'model' in kwargs:
            model = kwargs['model']
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

