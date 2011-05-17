import tests
import unittest

import pyperry
from pyperry.middlewares import ModelBridge
from tests.fixtures.test_adapter import TestAdapter

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

            def __call__(self, **kwargs):
                self.called = True
                self.args = kwargs
                return [{ 'id': 1 }]

        self.adapter = FakeAdapter()
        self.bridge = ModelBridge(self.adapter, {})
        self.relation = pyperry.Base.scoped()
        self.stack_opts = { 'relation': self.relation }

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
        result = self.bridge()
        self.assertEqual(result, [{ 'id': 1 }])

class ModelBridgeWriteTestCase(ModelBridgeBaseTestCase):

    def setUp(self):
        pass

    def test_saved_on_success(self):
        """should set model's saved attribute to true on success"""
        pass

    def test_saved_on_fail(self):
        """should set model's saved attribute to false on failure"""
        pass

    def test_reload_on_success(self):
        """should reload the model on success"""
        pass

    def test_reload_on_fail(self):
        """should not reload the model on failure"""
        pass

    def test_errors_on_fail(self):
        """should add error messages to the model on failure"""
        pass

    def test_always_errors_on_fail(self):
        """should add error messages to the model even if the response has no
        errors"""
        pass

    def test_skip_reload(self):
        """should not reload the model if no read adapter is available"""
        pass

class ModelBridgeWriteNewRecordsTestCase(ModelBridgeWriteTestCase):

    def test_set_key(self):
        """should set the model's primary_key attribute on success"""
        pass

    def test_new_record_success(self):
        """should set the model's new_record attribute to true on success"""
        pass

    def test_new_record_fail(self):
        """should set the model's new_record attribute to false on failure"""
        pass

    def test_exception_when_no_key(self):
        """should thrown an exception if the response does not have a value for
        the primary_key attribute"""
        pass

    def test_no_exception_without_read(self):
        """should not throw an exception if no read adapter is configured"""
        pass

class ModelBridgeDeleteTestCase(ModelBridgeBaseTestCase):

    def test_freeze(self):
        """should freeze the model on success"""
        pass

    def test_no_freeze_on_fail(self):
        """should not freeze the model on failure"""
        pass

    def test_add_errors(self):
        """should add error messages to the model on failure"""
        pass

    def test_add_default_errors(self):
        """should add a default error message to the model on failure even when
        the response has no error messages"""
        pass
