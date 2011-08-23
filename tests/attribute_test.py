import tests
import unittest
from nose.plugins.skip import SkipTest
import copy

import pyperry
from pyperry import errors

from pyperry.field import Field

from tests.fixtures.test_adapter import TestAdapter
import tests.fixtures.association_models

class CustomField(Field):

    def serialize(self, value):
        return str(value)

    def deserialize(self, value):
        return int(value)


class AttributeTestCase(unittest.TestCase):
    pass

class InitMethodTestCase(AttributeTestCase):

    def test_keywords(self):
        """should accept keywords type and default"""
        attr = Field(type=str, default=6)
        self.assertEqual(attr.type, str)
        self.assertEqual(attr.default, 6)

    def test_sets_name_to_none(self):
        """should set name attribute to None"""
        attr = Field()
        self.assertEqual(attr.name, None)

class DescriptorTestCase(AttributeTestCase):

    def setUp(self):
        super(DescriptorTestCase, self).setUp()

        class DictLike(object):

            def __init__(self):
                self.dict = {}

            def __getitem__(self, key):
                return self.dict[key]

            def __setitem__(self, key, value):
                self.dict[key] = value

            def __delitem__(self, key):
                del self.dict[key]

        self.DictLike = DictLike
        self.owner = DictLike()


class BasicDescriptorTestCase(DescriptorTestCase):

    def test_get_gets(self):
        """__get__ should pull from __getitem__ on owner"""
        self.owner['foo'] = "FunTimes!"
        attr = Field()
        attr.name = 'foo'
        self.owner.__class__.foo = attr
        self.assertEqual(self.owner.foo, 'FunTimes!')

    def test_set_sets(self):
        """__set__ should push to __setitem__ on owner"""
        attr = Field()
        attr.name = 'bar'
        self.owner.__class__.bar = attr
        self.owner.bar = "Setting this thing!"
        self.assertEqual(self.owner['bar'], 'Setting this thing!')

    def test_del_dels(self):
        """__delete__ should call __delitem__ on owner"""
        attr = Field()
        self.owner['baz'] = 42
        attr.name = 'baz'
        self.owner.__class__.baz = attr
        del self.owner.baz
        assert not self.owner.dict.has_key('baz')

class DescriptorWithTypeTestCase(DescriptorTestCase):

    def test_get_gets_with_type(self):
        """__get__ should cast value retreived to `type` if set"""
        attr = Field(type=int)
        attr.name = 'id'
        self.owner.__class__.id = attr
        self.owner['id'] = '123'
        self.assertEqual(self.owner.id, 123)

    def test_set_sets_with_type(self):
        attr = Field(type=int)
        attr.name = 'id'
        self.owner.__class__.id = attr
        self.owner.id = '123'
        self.assertEqual(self.owner.dict['id'], 123)


class CustomSerializeTestCase(DescriptorTestCase):
    """
    This test case uses the CustomField class fixture to test setting
    custom serialize and deserialize methods for creating powerful custom
    attribute behavior

    Custom behavior is:
        stores as str
        reads as int
    """

    def setUp(self):
        super(CustomSerializeTestCase, self).setUp()
        self.attr = CustomField()
        self.attr.name = 'test_attr'
        self.owner.__class__.test_attr = self.attr

    def test_get_deserializes(self):
        """should pass get through the deserialize method"""
        self.owner['test_attr'] = '123'
        self.assertEqual(self.owner.test_attr, 123)

    def test_set_deserializes(self):
        """should pass set through the serialize method"""
        self.owner.test_attr = 123
        self.assertEqual(self.owner['test_attr'], '123')


