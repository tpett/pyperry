import tests
import unittest
try:
    import json
except:
    import simplejson as json
import pyperry
import tests.helpers.http_test_server as http_server
from pyperry.adapter.http import RestfulHttpAdapter
from pyperry.middlewares.model_bridge import ModelBridge

def setup_module():
    tests.run_http_server()

class TestModel(pyperry.Base):
    def _config(c):
        c.attributes('id', 'foo')
        adapter_conf = {
            'adapter': RestfulHttpAdapter,
            'service': 'test_models',
            'host': 'localhost:8888'
        }
        c.configure('read', **adapter_conf)
        c.configure('write', **adapter_conf)

class RestfulIntegrationTestCase(unittest.TestCase):

    def setUp(self):
        http_server.set_response(method='GET',
                body=json.dumps([{"id": 42, "foo": "bar"}]))

    def tearDown(self):
        http_server.clear_responses()

    def test_middleware(self):
        """should include the ModelBridge in the adapter middlewares"""
        middlewares = TestModel.adapter('write').middlewares
        self.assertEqual(len(middlewares), 1)
        self.assertEqual(middlewares[0][0], ModelBridge)

    def test_adapter_mode(self):
        """should have correct mode for each adapter"""
        self.assertEqual(TestModel.adapter('write').mode, 'write')

    def test_query(self):
        records = [
            {'id': 1, 'foo': 'bar'},
            {'id': 2, 'foo': 'bar'},
            {'id': 3, 'foo': 'bar'}
        ]
        http_server.set_response(method='GET', body=json.dumps(records))
        models = TestModel.where({'foo': 'bar'}).limit(3).all()
        self.assertEqual(len(models), 3)
        for i, model in enumerate(models):
            self.assertEqual(type(model), TestModel)
            self.assertEqual(model.new_record, False)
            self.assertEqual(model.id, records[i]['id'])
            self.assertEqual(model.foo, records[i]['foo'])

    def test_create_success(self):
        """should create a model through the RestfulHttpAdapter"""
        http_server.set_response(body=json.dumps({"id": 42, "foo": "bar"}))
        model = TestModel({})
        self.assertEqual(model.new_record, True)
        self.assertEqual(model.save(), True)
        self.assertEqual(model.new_record, False)
        self.assertEqual(model.saved, True)

    def test_create_failure(self):
        """should handle a failed create appropriately"""
        http_server.set_response(status=500, body=json.dumps({
            "errors": {"foo": "is not bar"}
        }))
        model = TestModel({})
        self.assertEqual(model.new_record, True)
        self.assertEqual(model.save(), False)
        self.assertEqual(model.new_record, True)
        self.assertEqual(model.saved, False)
        self.assertEqual(model.errors['foo'], 'is not bar')

    def test_update_attributes_with_keywords(self):
        """
        should update a model with the attributes given as keyword args through
        the RestfulHttpAdapter
        """
        attrs = {"id": 7, "foo": "bar"}
        http_server.set_response(body=json.dumps(attrs))
        http_server.set_response(method='GET', body=json.dumps([attrs]))
        model = TestModel({}, False)
        self.assertEqual(model.update_attributes(id=7, foo='bar'), True)
        self.assertEqual(model.saved, True)
        self.assertEqual(model.new_record, False)
        self.assertEqual(model.id, 7)
        self.assertEqual(model.foo, 'bar')

    def test_update_attributes_with_dict(self):
        """
        should update a model with given attribute dict through the
        RestfulHttpAdapter
        """
        attrs = {"id": 7, "foo": "bar"}
        http_server.set_response(body=json.dumps(attrs))
        http_server.set_response(method='GET', body=json.dumps([attrs]))
        model = TestModel({}, False)
        self.assertEqual(model.update_attributes({'id':7, 'foo':'bar'}), True)
        self.assertEqual(model.saved, True)
        self.assertEqual(model.new_record, False)
        self.assertEqual(model.id, 7)
        self.assertEqual(model.foo, 'bar')

    def test_update_attributes_failure(self):
        """should handle a failed update appropriately"""
        http_server.set_response(status=500, body=json.dumps({
            "errors":{"foo":"is not bar"}
        }))
        model = TestModel({}, False)
        self.assertEqual(model.update_attributes({'id':7, 'foo':'boo'}), False)
        self.assertEqual(model.saved, False)
        self.assertEqual(model.errors['foo'], 'is not bar')

    def test_delete(self):
        """should delete a model through the RestfulHttpAdapter"""
        http_server.set_response()
        model = TestModel({'id':1}, False)
        self.assertEqual(model.delete(), True)
        self.assertEqual(model.frozen(), True)
        self.assertEqual(http_server.last_request()['method'], 'DELETE')

    def test_delete_failure(self):
        """should handle a failed delete appropriately"""
        http_server.set_response(status=500)
        model = TestModel({'id':1}, False)
        self.assertEqual(model.delete(), False)
        self.assertEqual(model.frozen(), False)
        self.assertEqual(model.errors['base'], 'record not deleted')
