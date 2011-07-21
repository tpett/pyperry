import tests
import unittest
import pydoc
from nose.plugins.skip import SkipTest

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

    def test_class_dir_for_help(self):
        """
        should not cause pydoc.TextDoc().docclass() to raise AttributeError.
        This method is used internally by the help() function, and if it cannot
        resolve the class of even one attribute (as in the case of the
        attributes delegated to the Relation class), the help text will be
        blank. I know this is a huge hack, so if you can think of a better way
        to do it, please do so!

        """
        try:
            pydoc.TextDoc().docclass(self.TestModel)
        except AttributeError as ex:
            self.fail('expected call not to raise an exception.\n' +
                      'Exception was: %s' % repr(ex))


class HelpMethodTestCase(unittest.TestCase):
    """
    We need to include additional information about attributes and associations
    for subclasses of pyperry.Base so python's built-in help() method is
    useful. To accomplish this, we are setting __doc__ in BaseMeta.__new__, so
    that is what we are testing here.

    """

    def assertContains(self, subject, search_string):
        """assert that the search_string is a substring of the subject"""
        subject = str(subject)
        self.assertTrue(subject.find(search_string) >= 0,
                "expected to find '%s' in '%s'" % (search_string, subject))

    def test_docstring_included(self):
        """should include the model's docstring in __doc__"""
        class Model(pyperry.Base):
            """a model with a docstring"""
            pass
        self.assertContains(Model.__doc__, 'a model with a docstring')

    def test_attributes_included(self):
        """should include a model's attributes in __doc__"""
        class Model(pyperry.Base):
            def _config(cls):
                cls.attributes('attr1', 'attr2')
        self.assertContains(Model.__doc__, '\nData attributes:')
        for attr in Model.defined_attributes:
            self.assertContains(Model.__doc__, '\t' + attr)

    def test_associations_included(self):
        """should include a model's associations in __doc__"""
        class Model(pyperry.Base):
            def _config(cls):
                cls.belongs_to('foo')
                cls.has_many('bars')
        self.assertContains(Model.__doc__, '\nAssociations:')
        self.assertContains(Model.__doc__, '\tbelongs_to foo')
        self.assertContains(Model.__doc__, '\thas_many bars')

    def test_everything(self):
        """
        should included everything specified in __doc__ with proper formatting
        and sorted in correct order

        """
        class Model(pyperry.Base):
            """a model with a docstring"""
            def _config(cls):
                cls.attributes('attr1', 'attr2')
                cls.belongs_to('foo')
                cls.belongs_to('ape')
                cls.has_many('bars')
                cls.has_many('bananas')
        self.assertEqual(Model.__doc__,
"""a model with a docstring

Data attributes:
\tattr1
\tattr2

Associations:
\tbelongs_to ape
\tbelongs_to foo
\thas_many bananas
\thas_many bars"""
        )

    def test_afterthoughts(self):
        """
        should included attributes and associations defined after the class
        definition is closed

        """
        raise SkipTest # As far as I can tell, this is not possible to do
        # without updating __doc__ every time a new attribute or assocation is
        # defined on the model.
        class Model(pyperry.Base):
            pass
        Model.attributes('foo')
        Model.has_many('bars')
        self.assertContains(Model.__doc__, 'foo')
        self.assertContains(Model.__doc__, 'has_many bars')


class DescribeAssociationTestCase(unittest.TestCase):
    pass
