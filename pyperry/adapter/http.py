import urllib
import httplib
import mimetypes

from pyperry.adapter.abstract_adapter import AbstractAdapter
from pyperry.errors import ConfigurationError
from pyperry.response import Response

ERRORS = {
    'host': "you must configure the 'host' for the RestfulHttpAdapter",
    'service': "you must configure the 'service' for the RestfulHttpAdapter"
}

class RestfulHttpAdapter(AbstractAdapter):

    #def read(self, **kwargs):
        #"""performs an HTTP GET request using the relation hash to construct
        #query parameters"""
        #response = self.request('GET', **kwargs)
        #return response.parsed()

    def write(self, **kwargs):
        model = kwargs['model']
        if model.new_record:
            method = 'POST'
        else:
            method = 'PUT'

        return self.request(method, **kwargs)

    def delete(self, **kwargs):
        return self.request('DELETE', **kwargs)

    def request(self, http_method, **kwargs):
        model = kwargs['model']
        url = self.url_for(http_method, model)
        params = self.restful_params(self.params_for(model))
        http_response, body = self.http_request(http_method, url, params)
        return self.response(http_response, body)

    def response(self, http_response, response_body):
        r = Response()
        r.status = http_response.status
        r.success = r.status == 200
        r.raw = response_body
        r.raw_format = self.config_value('format', 'json')
        r.meta = dict(http_response.getheaders())
        return r

    def http_request(self, http_method, url, params, **kwargs):
        encoded_params = urllib.urlencode(params)
        headers = {}

        mime_type = mimetypes.guess_type('_.' +
                    self.config_value('format', 'json'))[0]
        if mime_type is not None:
            headers['accept'] = mime_type

        if http_method != 'GET':
            headers['content-type'] = 'application/x-www-form-urlencoded'


        conn = httplib.HTTPConnection(self.config_value('host'))
        try:
            conn.request(http_method, url, encoded_params, headers)
            http_response = conn.getresponse()
            response_body = http_response.read()
            # read() must be called before the connection is closed or it will
            # return an empty string.
        finally:
            conn.close()

        return (http_response, response_body)

    def url_for(self, http_method, model):
        """Constructs the URL for the request"""
        self.config_value('service')

        service = self.config.service
        primary_key = self.config_value('primary_key', 'id')
        pk_value = getattr(model, primary_key)
        format = self.config_value('format', 'json')

        if http_method is 'POST':
            url_tmpl = "/%s.%s"
            tmpl_args = (service, format)
        else:
            url_tmpl = "/%s/%s.%s"
            tmpl_args = (service, pk_value, format)

        return url_tmpl % tmpl_args

    def params_for(self, model):
        """Builds and encodes a parameters dict for the request"""
        params = {}

        if hasattr(self.config, 'default_params'):
            params.update(self.config.default_params)

        if hasattr(self.config, 'params_wrapper'):
            params.update({self.config.params_wrapper: model.attributes})
        else:
            params.update(model.attributes)

        return params

    def restful_params(self, params, key_prefix=None):
        """
        Recursively flattens nested hases so they can be understood by our
        web services.

        In particular, our webservices require nested dicts to be transformed
        to a format where the nesting is indiciated by a key naming syntax
        where there are no nested dicts. Instead, the nested dicts are
        'flattened' by using a key naming syntax where the nested keys are
        enclosed in brackets and preceded by the non-nested key.

        The best way to understand this format is by example:

        Example input:
        {
          'key': 'value',
          'foo': {
            'nested': 'value',
            'bar': {
              'double-nested': 'value'
            }
          }
        }

        Example output:
        {
          'key': 'value',
          'foo[nested]': 'value',
          'foo[bar][double-nested]': 'value'
        }

        Considerations:
         - You still must pass this to the urllib.urlencode() function before
           using it in an HTTP call.
         - This implementation does not support converting array values.

        """
        restful = {}
        for k, v in params.items():
            if isinstance(v, dict):
                k1 = k
                if key_prefix is not None:
                    k1 = '%s[%s]' % (key_prefix, k)
                restful.update(self.restful_params(v, k1))
            else:
                k2 = k
                if key_prefix is not None:
                    k2 = '%s[%s]' % (key_prefix, k)
                restful[k2] = v
        return restful

    def response_for(self, status, headers, body):
        """Build a pyperry Response from the raw HTTP response components"""
        pass

    def config_value(self, option, default=None):
        if hasattr(self.config, option):
            value = getattr(self.config, option)
        elif default is not None:
            value = default
        else:
            raise ConfigurationError, ERRORS[option]
        return value
