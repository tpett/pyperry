from bertrpc import Service
from pyperry.adapter.abstract_adapter import AbstractAdapter

class BERTRPC(AbstractAdapter):
    """
    Adapter for accesing data over BERTRPC
    Takes these configuration keywords:
        * base_options: options that will be included with every request
        * namespace: the module that the call lives in
        * procedure: the remote procedure to call
    """

    def read(self, **kwargs):
        options = kwargs['relation'].query()
        options.update(self.config.base_options)
        request = self.service.request('call')
        module = request.__getattr__(self.config.namespace)
        procedure = module.__getattr__(self.config.procedure)
        return procedure(options)

    @property
    def service(self):
        if not hasattr(self, '_service'):
            self._service = Service(self.config.server, self.config.port)
        return self._service

