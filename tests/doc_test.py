import tests
import unittest

import pyperry
from pyperry.relation import Relation

class DirMethodTestCase(unittest.TestCase):
    """
    I'm trying to add to the list of attributes returned by calling dir() by
    overriding __dir__. However, there does not seem to be a straightforward
    way to do this in python 2.x. It seems like overriding __dir__ is somewhat
    of a dark art as you can't just do

        class MyClass(object):
            def __dir__(self):
                return dir(super(MyClass, self)) + ['foo', 'bar']

    because dir(super...) does not provide the same list of attributes as if
    you called dir() on an instance of MyClass that does not provide a __dir__.

    That being said, I found this list on what dir() returns by default and
    will adhere to its claims:

    http://mail.python.org/pipermail/python-dev/2006-November/069865.html

    """

    def setUp(self):
        class TestModel(pyperry.Base):
            def _config(cls):
                cls.attributes('id', 'foo', 'bar')
                cls.belongs_to('owner')
                cls.has_many('children')

        self.TestModel = TestModel

    def test_class_dir(self):
        """
        should include the attributes included by default when calling dir() on
        a subclass of pyperry.Base in addition to the attributes delegated to
        the Relation class

        """
        attrs = dir(self.TestModel)

        for x in self.TestModel.__dict__.keys():
            self.assertTrue(x in attrs,
                    "expected '%s' to be in '%s'" % (x, attrs))

        for x in dir(self.TestModel.__bases__[0]):
            self.assertTrue(x in attrs,
                    "expected '%s' to be in '%s'" % (x, attrs))

        delegated_methods = pyperry.base.BaseMeta._relation_delegates
        for x in delegated_methods:
            self.assertTrue(x in attrs,
                    "expected '%s' to be in '%s'" % (x, attrs))

    def test_instance_dir(self):
        """
        should include the attributes included by default when calling dir() on
        an instance of pyperry.Base in addition to the defined_attributes and
        defined_associations for the pyperry model.

        """
        model = self.TestModel()
        attrs = dir(model)

        for x in model.__dict__.keys():
            self.assertTrue(x in attrs,
                    "expected '%s' to be in '%s'" % (x, attrs))

        class_attrs = [x for x in dir(model.__class__)
                if not x in self.TestModel._relation_delegates]
        for x in class_attrs:
            self.assertTrue(x in attrs,
                    "expected '%s' to be in '%s'" % (x, attrs))

        for x in list(model.defined_attributes):
            self.assertTrue(x in attrs,
                    "expected '%s' to be in '%s'" % (x, attrs))

        for x in list(model.defined_associations):
            self.assertTrue(x in attrs,
                    "expected '%s' to be in '%s'" % (x, attrs))

        for x in self.TestModel._relation_delegates:
            self.assertTrue(x not in attrs,
                    "expected '%s' NOT to be in '%s'" % (x, attrs))
