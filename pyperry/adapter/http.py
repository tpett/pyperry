import urllib
import httplib
import mimetypes

from pyperry.adapter.abstract_adapter import AbstractAdapter
from pyperry.errors import ConfigurationError, MalformedResponse
from pyperry.response import Response

ERRORS = {
    'host': "you must configure the 'host' for the RestfulHttpAdapter",
    'service': "you must configure the 'service' for the RestfulHttpAdapter"
}

class RestfulHttpAdapter(AbstractAdapter):
    """
    Adapter for communicating with REST web services over HTTP

    B{Required configuration keywords:}

        - B{host:} the host of the remote server, such as C{github.com} or
          C{192.0.0.1}

        - B{service:} the name of the service corresponding to your model.

          The service will depend on what services the host server has
          available, but it is typically the lowercase, plural version of your
          model's class name.  So if you have a model named C{Duck}, your
          service name will typically be C{ducks}.

    B{Optional configuration keywords:}

        - B{format}: expected data format of the response body, such as
          C{'xml'} or C{'csv'}. Default is C{'json'}

        - B{primary_key}: an alternate primary_key to use when generating URLs.
          Defaults to C{model.pk_attr()}

        - B{params_wrapper:} used to wrap your model's attributes before encoding
          them for your request.

          For example, if you have a model C{m = Model({'id': 4, 'name':
          'foo'})} with C{params_wrapper='mod'}, the data encoded for the HTTP
          request will include C{mod[id]=4&mod[name]=foo}

        - B{default_params}: a python dict of additional paramters to include
          alongside the models attributes in any write or delete request.

          These parameters will not be wrapped in the C{params_wrapper} if that
          option is also present. One thing C{default_params} are useful for
          is including an api key with every request.

        - B{serializer}: a callable that takes an attribute value as its only
          argument and returns a serialized version of that value suitable for
          sending over HTTP. The default serializer serializes C{None} as
          C{''}, C{True} as C{'true'} and C{False} as C{'false'}.

    """

    def read(self, **kwargs):
        """
        Performs an HTTP GET request and uses the relation dict to construct
        the query string parameters

        """
        relation = kwargs['relation']
        url = self.url_for('GET')

        query_string = self.query_string_for(relation)
        if query_string is not None:
            url += query_string


        http_response, body = self.http_request('GET', url, {}, **kwargs)
        response = self.response(http_response, body)
        records = response.parsed()
        if not isinstance(records, list):
            raise MalformedResponse('parsed response is not a list')
        return records

    def write(self, **kwargs):
        model = kwargs['model']
        if model.new_record:
            method = 'POST'
        else:
            method = 'PUT'

        return self.persistence_request(method, **kwargs)

    def delete(self, **kwargs):
        return self.persistence_request('DELETE', **kwargs)

    def persistence_request(self, http_method, **kwargs):
        model = kwargs['model']
        url = self.url_for(http_method, model)
        params = self.restful_params(self.params_for(model))
        http_response, body = self.http_request(http_method, url, params)
        return self.response(http_response, body)

    def response(self, http_response, response_body):
        r = Response()
        r.status = http_response.status
        r.success = r.status >= 200 and r.status < 400
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

    def url_for(self, http_method, model=None):
        """Constructs the URL for the request"""
        self.config_value('service')

        service = self.config['service']
        if model is not None:
            primary_key = self.config_value('primary_key', model.pk_attr())
            pk_value = getattr(model, primary_key)
        format = self.config_value('format', 'json')

        if http_method is 'POST' or model is None:
            url_tmpl = "/%s.%s"
            tmpl_args = (service, format)
        else:
            url_tmpl = "/%s/%s.%s"
            tmpl_args = (service, pk_value, format)

        return url_tmpl % tmpl_args

    def params_for(self, model):
        """Builds and encodes a parameters dict for the request"""
        params = {}

        if 'default_params' in self.config.keys():
            params.update(self.config['default_params'])

        if 'params_wrapper' in self.config.keys():
            params.update({self.config['params_wrapper']: model.fields})
        else:
            params.update(model.fields)

        return params

    def query_string_for(self, relation):
        """
        Encodes the relation and any query modifiers into a query string
        suitable for use in a URL. Includes the '?' as part of the query string
        and returns None if there are no parameters.

        """
        query = relation.query()
        mods = relation.modifiers_value()
        if 'query' in mods:
            query.update(mods['query'])

        params = self.restful_params(query)
        if len(params) > 0:
            return '?' + urllib.urlencode(params)

    def config_value(self, option, default=None):
        """
        Returns the value of the configuration option named by option.

        If the option is not configured, this method will use the default value
        if given. Otherwise a ConfigurationError will be thrown.

        """
        if option in self.config.keys():
            value = self.config[option]
        elif default is not None:
            value = default
        else:
            raise ConfigurationError, ERRORS[option]
        return value

    def restful_params(self, params, key_prefix=''):
        """
        Recursively flattens nested dicts into a list of (key, value) tuples
        so they can be encoded as a query string that can be understood by our
        webservices.

        In particular, our webservices require nested dicts to be transformed
        to a format where the nesting is indiciated by a key naming syntax
        where there are no nested dicts. Instead, the nested dicts are
        'flattened' by using a key naming syntax where the nested keys are
        enclosed in brackets and preceded by the non-nested key.

        The best way to understand this format is by example:

        Example input::

            {
              'key': 'value',
              'foo': {
                'list': [1, 2, 3],
                'bar': {
                  'double-nested': 'value'
                }
              }
            }

        Example output::

            [
              ('key', 'value'),
              ('foo[list][]', 1), ('foo[list][]', 2), ('foo[list][]', 3),
              ('foo[bar][double-nested]', 'value')
            ]

        When calling the urlencode on the result of this method, you will
        generate a query string similar to the following. The order of the
        parameters may vary except that successive array elements will also
        be successive in the query string::

            'key=value&foo[list][]=1&foo[list][]=2&foo[list][]=3&foo[bar][double-nested]=value'

        """
        restful = self.params_for_dict(params, [], '')
        return restful

    def params_for_dict(self, params, params_list, key_prefix=''):
        for key, value in params.iteritems():
            new_key_prefix = self.key_for_params(key, value, key_prefix)

            if isinstance(value, dict):
                self.params_for_dict(value, params_list, new_key_prefix)
            elif isinstance(value, list):
                self.params_for_list(value, params_list, new_key_prefix)
            else:
                params_list.append((new_key_prefix, self.params_value(value)))

        return params_list

    def params_for_list(self, params, params_list, key_prefix=''):
        for value in params:
            if isinstance(value, dict):
                self.params_for_dict(value, params_list, key_prefix)
            elif isinstance(value, list):
                self.params_for_list(value, params_list, key_prefix + '[]')
            else:
                params_list.append((key_prefix, self.params_value(value)))

    def key_for_params(self, key, value, key_prefix=''):
        if len(key_prefix) > 0:
            new_key_prefix = '%s[%s]' % (key_prefix, key)
        else:
            new_key_prefix = key

        if isinstance(value, list):
            new_key_prefix += '[]'

        return new_key_prefix

    def params_value(self, value):
        serializer = self.config_value('serializer', self._default_serializer)
        return serializer(value)

    def _default_serializer(self, value):
        if value is None:
            value = ''
        elif value is True:
            value = 'true'
        elif value is False:
            value = 'false'
        return value
