import tests
import unittest
import pyperry
import tests.helpers.http_test_server as http_server
from pyperry.adapter.http import RestfulHttpAdapter
from pyperry.middlewares.model_bridge import ModelBridge

def setup_module():
    tests.run_http_server()

class TestModel(pyperry.Base):
    def _config(c):
        c.attributes('id', 'foo')
        c.configure('write', adapter=RestfulHttpAdapter,
                service='test_model', host='localhost:8888')

class PersistenceIntegrationTestCase(unittest.TestCase):

    def test_middleware(self):
        """should include the ModelBridge in the adapter middlewares"""
        middlewares = TestModel.adapter('write').middlewares
        self.assertEqual(len(middlewares), 1)
        self.assertEqual(middlewares[0][0], ModelBridge)

    def test_adapter_mode(self):
        """should have correct mode for each adapter"""
        self.assertEqual(TestModel.adapter('write').mode, 'write')

    def test_create_success(self):
        """should create a model through the RestfulHttpAdapter"""
        http_server.set_response(body='{"id":42,"foo":"bar"}')
        model = TestModel({})
        self.assertEqual(model.new_record, True)
        self.assertEqual(model.save(), True)
        self.assertEqual(model.new_record, False)
        self.assertEqual(model.saved, True)

    def test_create_failure(self):
        """should handle a failed create appropriately"""
        http_server.set_response(body='{"errors":{"foo":"is not bar"}}',
                status=500)
        model = TestModel({})
        self.assertEqual(model.new_record, True)
        self.assertEqual(model.save(), False)
        self.assertEqual(model.new_record, True)
        self.assertEqual(model.saved, False)
        self.assertEqual(model.errors['foo'], 'is not bar')

    def test_update_attributes_with_keywords(self):
        """should update a model through the RestfulHttpAdapter"""
        http_server.set_response(body='{"id":7,"foo":"bar"}')
        model = TestModel({}, False)
        self.assertEqual(model.update_attributes(id=7, foo='bar'), True)
        self.assertEqual(model.saved, True)
        self.assertEqual(model.new_record, False)
        self.assertEqual(model.id, 7)
        self.assertEqual(model.foo, 'bar')

    def test_update_attributes_with_dict(self):
        """should update a model through the RestfulHttpAdapter"""
        http_server.set_response(body='{"id":7,"foo":"bar"}')
        model = TestModel({}, False)
        self.assertEqual(model.update_attributes({'id':7, 'foo':'bar'}), True)
        self.assertEqual(model.saved, True)
        self.assertEqual(model.new_record, False)
        self.assertEqual(model.id, 7)
        self.assertEqual(model.foo, 'bar')

    def test_update_attributes_failure(self):
        """should handle a failed update appropriately"""
        http_server.set_response(body='{"errors":{"foo":"is not bar"}}',
                status=500)
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

    def test_delete_failure(self):
        """should handle a failed delete appropriately"""
        http_server.set_response(status=500)
        model = TestModel({'id':1}, False)
        self.assertEqual(model.delete(), False)
        self.assertEqual(model.frozen(), False)
        self.assertEqual(model.errors['base'], 'record not deleted')

##
# TODO: these next three tests can be unit tests
##
    def test_raise_on_read_when_frozen(self): pass
    def test_raise_on_write_when_frozen(self): pass
    def test_raise_on_delete_when_frozen(self): pass
    def test_raise_on_delete_when_new_record(self): pass
    def test_raise_on_write_when_no_id_and_not_new_record(self): pass
    def test_raise_on_delete_when_no_id(self): pass
