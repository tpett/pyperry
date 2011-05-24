import tests
import unittest
import json

from pyperry.response import Response

class ResponseBaseTestCase(unittest.TestCase):

    def setUp(self):
        self.response = Response()

class ResponseClassTestCase(ResponseBaseTestCase):

    def test_get_success(self):
        """success attribute should default to False"""
        self.assertFalse(self.response.success)

    def test_get_status(self):
        """status attribute should default to None"""
        self.assertEqual(self.response.status, None)

    def test_get_meta(self):
        """meta attribute should default to empty dict"""
        self.assertEqual(self.response.meta, {})

    def test_get_raw(self):
        """raw attribute should default to None"""
        self.assertEqual(self.response.raw, None)

    def test_get_raw_format(self):
        """raw format attribute should default to JSON"""
        self.assertEqual(self.response.raw_format, 'json')

    def test_parsed_method(self):
        """parsed method should default to None"""
        self.assertEqual(self.response.parsed(), None)

    def test_model_attributes_method(self):
        """model_attributes method should default to an empty dict"""
        self.assertEqual(self.response.model_attributes(), {})

    def test_errors_method(self):
        """errors method should default to an empty dict"""
        self.assertEqual(self.response.errors(), {})

    def test_init(self, **kwargs):
        """should set response attributes to values in kwargs"""
        args = {
            'success': True,
            'status': 200,
            'meta': { 'content-length': 1024 },
            'raw': 'OK',
            'raw_format': '.html'
        }
        response = Response(**args)
        for k, v in args.items():
            self.assertEqual(v, response.__getattribute__(k))


class ResponseParsingTestCase(ResponseBaseTestCase):

    def test_set_parsed(self):
        """
        should define a setter for parsed that does not override the parsed
        method

        """
        self.response.parsed = 42
        self.assertEqual(self.response.parsed(), 42)

    def test_parse_raw_json(self):
        """should parse a raw JSON response into native python objects"""
        obj = { 'id': 1, 'occurrences': [1, 2, 3] }
        self.response.raw_format = 'json'
        self.response.raw = json.dumps(obj)
        self.assertEqual(self.response.parsed(), obj)

    def test_parse_no_data(self):
        """parsed should return None when raw is None"""
        self.response.raw_format = 'json'
        self.assertEqual(self.response.parsed(), None)

    def test_raise_no_parser(self):
        """parsed should raise if no parser available for the raw_format"""
        self.response.raw_format = 'asdf'
        self.assertRaises(KeyError, self.response.parsed)

    def test_invalid_format(self):
        """should return None and not raise if raw response can't be parsed"""
        self.response.raw = '}'
        self.assertEqual(self.response.parsed(), None)


class ModelAttributesMethodTest(ResponseBaseTestCase):

    def test_single_item_dict(self):
        """should have one attribute"""
        parsed = { 'foo': 'bar' }
        self.response.parsed = parsed
        self.assertEqual(self.response.model_attributes(), parsed)

    def test_multi_item_dict(self):
        """should have multiple attributes"""
        parsed = { 'foo': 'bar', 'numbers': [1, 2, 3], 'pi': 3.1415927 }
        self.response.parsed = parsed
        self.assertEqual(self.response.model_attributes(), parsed)

    def test_single_item_nested_dict(self):
        """should use keys from nested dict for attributes"""
        parsed = { 'foo': { 'bar': 'baz', 'opts': { 'life': 42 } } }
        self.response.parsed = parsed
        self.assertEqual(self.response.model_attributes(), parsed['foo'])

    def test_multi_item_nested_dict(self):
        """should use top-level keys for attributes"""
        parsed = { 'foo': { 'bar': 'baz' }, 'opts': { 'life': 42 } }
        self.response.parsed = parsed
        self.assertEqual(self.response.model_attributes(), parsed)

    def test_bad_response(self):
        """should return an empty dict if parsed response is not recognized"""
        self.response.parsed = 'ugh!'
        self.assertEqual(self.response.model_attributes(), {})

class ErrorsMethodTest(ResponseBaseTestCase):

    def test_dict(self):
        """should use the parsed response dict as the errors by default"""
        parsed = { 'base': 'record invalid' }
        self.response.parsed = parsed
        self.assertEqual(self.response.errors(), parsed)

    def test_nested_errors(self):
        """should use the errors key to get the errors dict"""
        parsed = { 'errors': { 'base': 'record invalid' } }
        self.response.parsed = parsed
        self.assertEqual(self.response.errors(), parsed['errors'])

    def test_errors_not_really_nested(self):
        """should not use the errors key if it's value is not a dict"""
        parsed = { 'errors': 'for real', 'base': 'record invalid' }
        self.response.parsed = parsed
        self.assertEqual(self.response.errors(), parsed)

    def test_bad_response(self):
        """should return a empty dict if parsed response is not recognized"""
        self.response.parsed = 'ugh!'
        self.assertEqual(self.response.errors(), {})
