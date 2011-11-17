import pyperry
from bertrpc import Service
from pyperry.adapter.abstract_adapter import AbstractAdapter
from pyperry.response import Response

class BERTRPC(AbstractAdapter):
    """
    Adapter for accesing data over BERTRPC

    Takes these configuration keywords:

        - namespace: the module that the call lives in (required)
        - procedure: the remote procedure to call (required)
        - base_options: options that will be included with every request

    """

    def __init__(self, *args, **kwargs):
        super(BERTRPC, self).__init__(*args, **kwargs)
        self.features['batch_write'] = True

    def read(self, **kwargs):
        options = kwargs['relation'].query()
        options.update(self.config['base_options'])
        options['mode'] = 'read'

        pyperry.logger.info('RPC.%s: %s' % (self.config['procedure'], options))

        return self._call_server(options)

    def write(self, **kwargs):
        model = kwargs.get('model')
        options = self.config['base_options'].copy()

        if model:
            options['fields'] = model.fields.copy()

            if model.new_record:
                options['mode'] = 'create'
            else:
                options['mode'] = 'update'
                options['where'] = [{ model.pk_attr(): model.pk_value() }]
        else:
            options['mode'] = 'update'
            options['where'] = kwargs['where']
            options['fields'] = kwargs['fields']

        return self._parse_response(self._call_server(options))

    def delete(self, **kwargs):
        model = kwargs.get('model')
        options = self.config['base_options'].copy()
        options['mode'] = 'delete'

        if model:
            options['where'] = [{ model.pk_attr(): model.pk_value() }]
        else:
            options['where'] = kwargs['where']

        return self._parse_response(self._call_server(options))


    def _call_server(self, options):
        request = self.service.request('call')
        module = getattr(request, self.config['namespace'])
        procedure = getattr(module, self.config['procedure'])
        return procedure(options)

    def _parse_response(self, raw):
        response = Response()
        response.raw = raw
        response._parsed = raw

        if raw.has_key('fields'):
            response.success = True
            response._model_attributes = raw['fields']
        elif raw.has_key('success'):
            response.success = raw['success']

        return response

    @property
    def service(self):
        return Service(self.config['server'], self.config['port'])

