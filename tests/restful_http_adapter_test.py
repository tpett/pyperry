import tests
import unittest
from copy import copy

import pyperry
from pyperry.adapter.http import RestfulHttpAdapter
from pyperry.response import Response
from tests.fixtures.association_models import Test as TestModel
import pyperry.errors as errors
import tests.helpers.http_test_server as http_server

def setup_module():
    """ensure the HTTP test server is running"""
    tests.run_http_server()

class HttpAdapterTestCase(unittest.TestCase):

    def setUp(self):
        self.config = {
            'host': 'localhost:8888',
            'service': 'widgets',
            'format': 'xml'
        }
        self.adapter = RestfulHttpAdapter(self.config, mode='read')
                       # adapter mode doesn't matter for these tests
                       # because we aren't using __call__
        self.model = TestModel({'id': 7})

    def tearDown(self):
        del self.config

class ConfigTestCase(HttpAdapterTestCase):

    def test_config_values_set(self):
        """should initialize config to correct values"""
        for option, value in self.config.items():
            self.assertEqual(getattr(self.adapter.config, option), value)

class UrlForMethodTestCase(HttpAdapterTestCase):

    def test_url_with_get(self):
        """should contruct a proper url for GET requests"""
        url = self.adapter.url_for('GET', self.model)
        self.assertEqual(url, '/widgets/7.xml')

    def test_url_with_post(self):
        """should contruct a proper url for POST requests"""
        url = self.adapter.url_for('POST', self.model)
        self.assertEqual(url, '/widgets.xml')

    def test_url_with_put(self):
        """should contruct a proper url for PUST requests"""
        url = self.adapter.url_for('PUT', self.model)
        self.assertEqual(url, '/widgets/7.xml')

    def test_url_with_delete(self):
        """should contruct a proper url for DELETE requests"""
        url = self.adapter.url_for('DELETE', self.model)
        self.assertEqual(url, '/widgets/7.xml')

    def test_missing_service(self):
        """should raise on missing service"""
        del self.config['service']
        adapter = RestfulHttpAdapter(self.config, mode='read')
        self.assertRaises(errors.ConfigurationError, adapter.url_for, 'GET',
                          self.model)

    def test_missing_format(self):
        """should use 'json' as the default format"""
        del self.config['format']
        adapter = RestfulHttpAdapter(self.config, mode='read')
        url = adapter.url_for('GET', self.model)
        self.assertEqual(url, '/widgets/7.json')

    def test_primary_key(self):
        """should use configured primary_key in url"""
        TestModel.attributes('id', 'foo')
        model = TestModel({'id':7, 'foo':12345})
        self.config['primary_key'] = 'foo'
        adapter = RestfulHttpAdapter(self.config, mode='read')
        url = adapter.url_for('GET', model)
        self.assertEqual(url, '/widgets/12345.xml')


class ParamsForMethodTestCase(HttpAdapterTestCase):

    def test_model_attributes(self):
        """should use model's attributes"""
        params = self.adapter.params_for(self.model)
        self.assertEqual(params, self.model.attributes)

    def test_with_wrapper(self):
        """should wrap the model's attributes with the given string"""
        self.config['params_wrapper'] = 'widget'
        adapter = RestfulHttpAdapter(self.config, mode='read')
        params = adapter.params_for(self.model)
        self.assertEqual(params, {'widget': self.model.attributes})

    def test_with_default_params(self):
        """should include the default_options with the attribuets"""
        self.config['default_params'] = {'foo': 'bar'}
        expected = copy(self.model.attributes)
        expected.update({'foo':'bar'})

        adapter = RestfulHttpAdapter(self.config, mode='read')
        params = adapter.params_for(self.model)
        self.assertEqual(params, expected)

    def test_with_default_params_and_params_wrapper(self):
        """should include the attributes inside the wrapper and the default
        params outside the wrapper"""
        self.config['default_params'] = {'foo': 'bar', 'widget': 5}
        self.config['params_wrapper'] = 'widget'
        expected = copy(self.config['default_params'])
        expected.update(copy({'widget':self.model.attributes}))

        adapter = RestfulHttpAdapter(self.config, mode='read')
        params = adapter.params_for(self.model)
        self.assertEqual(params, expected)

    def test_dont_modify_default_params(self):
        """should not modify the default_params when building params"""
        self.config['default_params'] = {'foo':'bar'}
        expected = copy(self.config['default_params'])

        adapter = RestfulHttpAdapter(self.config, mode='read')
        params = adapter.params_for(self.model)
        self.assertEqual(adapter.config.default_params, expected)


class RestfulParamsTestCase(HttpAdapterTestCase):

    def test_empty_dict(self):
        """should return an empty dict when given an empty dict"""
        expected = {}
        actual = self.adapter.restful_params({})
        self.assertEqual(actual, expected)

    def test_simple_dict(self):
        """should return an equivalent dict when given a dict with no nested
        dicts"""
        expected = {'foo':'bar', 'biz':'baz'}
        actual = self.adapter.restful_params(copy(expected))
        self.assertEqual(actual, expected)

    def test_nested_dict(self):
        """should modify keys on the nested dict so that there are no nested
        dicts"""
        input = {'download': {'file_name': 'foo', 'format':'json'}}
        expected = {'download[file_name]': 'foo', 'download[format]': 'json'}
        actual = self.adapter.restful_params(input)
        self.assertEqual(actual, expected)

    def test_multiply_nested_dict(self):
        """should modify keys on multiply nested dicts so there are no nested
        dicts"""
        input = {
            'foo': 'bar',
            'nested': {
                'biz': 'baz',
                'double-nested': {
                    'tomato': 'toe-maw-toe',
                    'potato': 'poe-taw-toe'
                }
            },
            'numbers': [1, 2, 3, 4, 5]
        }
        expected = {
            'foo': 'bar',
            'nested[biz]': 'baz',
            'nested[double-nested][tomato]': 'toe-maw-toe',
            'nested[double-nested][potato]': 'poe-taw-toe',
            'numbers': [1, 2, 3, 4, 5]
        }
        actual = self.adapter.restful_params(input)
        self.assertEqual(actual, expected)


class ReadTestCase(HttpAdapterTestCase):
    pass

class PersistenceTestCase(HttpAdapterTestCase):
    """
    Because the create, update, and delete test cases are so similar, the tests
    are defined generically in the PersistenceTestCase (base) class. Then the
    subclasses define a setUp() method to customize how the tests will run.
    Because we only want the tests to run in subclasses and not in the base
    class, we check for the base class and make an early return if we are in
    the base class. This means that the base class tests still get run and
    counted, but they do not make any assertions and should never fail.

    """

    def respond_with_success(self, **kwargs):
        http_server.set_response(**kwargs)

    def respond_with_failure(self, **kwargs):
        error_kwargs = {'status': 500, 'body': 'ERROR'}
        error_kwargs.update(kwargs)
        http_server.set_response(**error_kwargs)

    def test_success_response(self):
        """should return an initialized Response object indicating success"""
        if type(self) is PersistenceTestCase: return
        self.respond_with_success(headers={'foo':'bar'})
        response = self.adapter_method(object=self.model)
        self.assertEqual(type(response), Response)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.success, True)
        self.assertEqual(response.raw, 'OK')
        self.assertEqual(response.raw_format, 'xml')
        self.assertTrue('foo' in response.meta)
        self.assertEqual(response.meta['foo'], 'bar')

    def test_fail_response(self):
        """should return an initialized Response object indicating failure"""
        if type(self) is PersistenceTestCase: return
        self.respond_with_failure(headers={'foo':'bar'})
        response = self.adapter_method(object=self.model)
        self.assertEqual(type(response), Response)
        self.assertEqual(response.status, 500)
        self.assertEqual(response.success, False)
        self.assertEqual(response.raw, 'ERROR')
        self.assertEqual(response.raw_format, 'xml')
        self.assertTrue('foo' in response.meta)
        self.assertEqual(response.meta['foo'], 'bar')

    def test_request(self):
        """should include the appropriate method and headers in the HTTP
        request"""
        if type(self) is PersistenceTestCase: return
        self.respond_with_success()
        response = self.adapter_method(object=self.model)
        last_request = http_server.last_request()
        self.assertEqual(last_request['method'], self.http_method)
        self.assertEqual(last_request['headers']['accept'], 'application/xml')
        self.assertEqual(last_request['headers']['content-type'],
                         'application/x-www-form-urlencoded')


class CreateTestCase(PersistenceTestCase):
    """Run tests from PersistenceTestCase configured for creating a record"""

    def setUp(self):
        super(CreateTestCase, self).setUp()
        self.model.new_record = True
        self.http_method = 'POST'
        self.adapter_method = self.adapter.write
        print "\n\tCreateTestCase" # Will display if test fails, so we know
                                   # which test case the fail was from.


class UpdateTestCase(PersistenceTestCase):
    """Run tests from PersistenceTestCase configured for updating a record"""

    def setUp(self):
        super(UpdateTestCase, self).setUp()
        self.model.new_record = False
        self.http_method = 'PUT'
        self.adapter_method = self.adapter.write
        print "\n\tUpdateTestCase"

class DeleteTestCase(PersistenceTestCase):
    """Run tests from PersistenceTestCase configured for deleting a record"""

    def setUp(self):
        super(DeleteTestCase, self).setUp()
        self.model.new_record = False
        self.http_method = 'DELETE'
        self.adapter_method = self.adapter.delete
        print "\n\tDeleteTestCase"
