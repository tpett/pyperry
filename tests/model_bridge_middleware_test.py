import tests
import unittest

import pyperry
from pyperry.middlewares import ModelBridge
from pyperry.field import Field
from tests.fixtures.test_adapter import TestAdapter
from tests.fixtures.test_adapter import SuccessAdapter
from tests.fixtures.test_adapter import FailureAdapter
from tests.fixtures.association_models import Test

class ModelBridgeBaseTestCase(unittest.TestCase):
    pass


class ModelBridgeMiddlewareTestCase(ModelBridgeBaseTestCase):

    def test_params(self):
        """should take an argument for next item in the call stack"""
        mb = ModelBridge('foo')
        self.assertEqual(mb.next, 'foo')

    def test_optional_params(self):
        """should take optional configuration options"""
        mb = ModelBridge('foo', { 'bar': 'baz' })
        self.assertEqual(mb.options, { 'bar': 'baz' })


class ModelBridgeReadTestCase(ModelBridgeBaseTestCase):

    def setUp(self):
        class FakeAdapter(object):
            def __init__(self):
                self.called = False
                self.args = None
                self.return_value = [{ 'id': 1 }]

            def __call__(self, **kwargs):
                self.called = True
                self.args = kwargs
                return self.return_value

        self.adapter = FakeAdapter()
        self.bridge = ModelBridge(self.adapter, {})
        self.relation = Test.scoped()
        self.stack_opts = { 'relation': self.relation, 'mode': 'read' }

    def test_call_stack(self):
        """should always call the next middleware/adapter in the stack"""
        self.bridge(**self.stack_opts)
        self.assertTrue(self.adapter.called)

    def test_args_passing(self):
        """should pass kwargs to next middleware/adapter in the stack"""
        self.bridge(**self.stack_opts)
        self.assertTrue('relation' in self.adapter.args)

    def test_init_records(self):
        """should create instances of the records returned from call"""
        result = self.bridge(**self.stack_opts)
        self.assertEqual(result[0].__class__, self.relation.klass)

    def test_no_relation(self):
        """should do nothing to result if no relation is given"""
        result = self.bridge(mode='read')
        self.assertEqual(result, [{ 'id': 1 }])

    def test_records_have_none_types(self):
        """should exclude none type records from results"""
        self.adapter.return_value = [None, {'id': 1}, None]
        result = self.bridge(**self.stack_opts)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].fields, {'id': 1})

    def test_new_record_false(self):
        """returned records should have their new_record attr set to false"""
        result = self.bridge(**self.stack_opts)
        self.assertEqual(result[0].new_record, False)


class BridgeTest(Test):
    id = Field()
    reader = TestAdapter()


class ModelBridgeWriteTestCase(ModelBridgeBaseTestCase):

    def setUp(self):
        self.model_class = BridgeTest
        self.model_class.reader = TestAdapter()
        self.model = self.model_class({})
        self.model.reader.data = { 'id': 42 }
        self.options = { 'model': self.model, 'mode': 'write' }

    def tearDown(self):
        try:
            self.model.reader.reset_calls()
        except:
            pass


class WriteExistingRecordsTestCase(ModelBridgeWriteTestCase):

    def test_saved_on_success(self):
        """should set model's saved attribute to true on success"""
        ModelBridge(SuccessAdapter())(**self.options)
        self.assertEqual(self.model.saved, True)

    def test_saved_on_fail(self):
        """should set model's saved attribute to false on failure"""
        ModelBridge(FailureAdapter())(**self.options)
        self.assertEqual(self.model.saved, False)

    def test_reload_on_success(self):
        """should reload the model on success"""
        ModelBridge(SuccessAdapter())(**self.options)
        self.assertEqual(len(TestAdapter.calls), 1)

    def test_reload_on_fail(self):
        """should not reload the model on failure"""
        ModelBridge(FailureAdapter())(**self.options)
        self.assertEqual(len(TestAdapter.calls), 0)

    def test_errors_on_fail(self):
        """should add error messages to the model on failure"""
        adapter = FailureAdapter()
        adapter.response.parsed = { 'errors': { 'base': 'record invalid' } }
        ModelBridge(adapter)(**self.options)
        self.assertEqual(self.model.errors, { 'base': 'record invalid' })

    def test_always_errors_on_fail(self):
        """should add error messages to the model even if the response has no
        errors"""
        adapter = FailureAdapter()
        adapter.response.parsed = None
        ModelBridge(adapter)(**self.options)
        self.assertEqual(self.model.errors, { 'base': 'record not saved' })

    def test_skip_reload(self):
        """should not reload the model if no read adapter is available"""
        del self.model_class.reader
        ModelBridge(SuccessAdapter())(**self.options)
        self.assertEqual(len(TestAdapter.calls), 0)


class WriteNewRecordsTestCase(ModelBridgeWriteTestCase):

    def setUp(self):
        super(WriteNewRecordsTestCase, self).setUp()
        self.model.new_record = True

    def test_set_key(self):
        """should set the model's primary_key attribute on success"""
        ModelBridge(SuccessAdapter())(**self.options)
        self.assertEqual(self.model.id, 42)

    def test_new_record_success(self):
        """should set the model's new_record attribute to false on success"""
        ModelBridge(SuccessAdapter())(**self.options)
        self.assertEqual(self.model.new_record, False)


    def test_new_record_fail(self):
        """should keep the model's new_record attribute as true on failure"""
        ModelBridge(FailureAdapter())(**self.options)
        self.assertEqual(self.model.new_record, True)

    def test_exception_when_no_key(self):
        """should thrown an exception if the response does not have a value for
        the primary_key attribute"""
        adapter = SuccessAdapter()
        adapter.response.parsed = None
        bridge = ModelBridge(adapter)
        self.assertRaises(KeyError, bridge, **self.options)

    def test_no_exception_without_read(self):
        """should not throw an exception if no read adapter is configured"""
        del self.model_class.reader
        adapter = SuccessAdapter()
        adapter.response.parsed = None
        ModelBridge(adapter)(**self.options)


class ModelBridgeDeleteTestCase(ModelBridgeWriteTestCase):

    def setUp(self):
        super(ModelBridgeDeleteTestCase, self).setUp()
        self.options['mode'] = 'delete'

    def test_freeze(self):
        """should freeze the model on success"""
        ModelBridge(SuccessAdapter())(**self.options)
        self.assertEqual(self.model.frozen(), True)

    def test_not_freeze_on_fail(self):
        """should not freeze the model on failure"""
        ModelBridge(FailureAdapter())(**self.options)
        self.assertEqual(self.model.frozen(), False)

    def test_add_errors(self):
        """should add error messages to the model on failure"""
        adapter = FailureAdapter()
        adapter.response.parsed = { 'errors': { 'base': 'record not found' } }
        ModelBridge(adapter)(**self.options)
        self.assertEqual(self.model.errors, { 'base': 'record not found' })

    def test_add_default_errors(self):
        """should add a default error message to the model on failure even when
        the response has no error messages"""
        adapter = FailureAdapter()
        adapter.response.parsed = None
        ModelBridge(adapter)(**self.options)
        self.assertEqual(self.model.errors, { 'base': 'record not deleted' })
