import tests
import unittest
import pydoc
from nose.plugins.skip import SkipTest

import pyperry
from pyperry.relation import Relation

from tests.fixtures.doc_models import *

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

    def test_class_dir(self):
        """
        should include the attributes included by default when calling dir() on
        a subclass of pyperry.Base in addition to the attributes delegated to
        the Relation class

        """
        attrs = dir(DirModel)

        for x in DirModel.__dict__.keys():
            self.assertTrue(x in attrs,
                    "expected '%s' to be in '%s'" % (x, attrs))

        for x in dir(DirModel.__bases__[0]):
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
        model = DirModel()
        attrs = dir(model)

        for x in model.__dict__.keys():
            self.assertTrue(x in attrs,
                    "expected '%s' to be in '%s'" % (x, attrs))

        class_attrs = [x for x in dir(model.__class__)
                if not x in DirModel._relation_delegates]
        for x in class_attrs:
            self.assertTrue(x in attrs,
                    "expected '%s' to be in '%s'" % (x, attrs))

        for x in list(model.defined_attributes):
            self.assertTrue(x in attrs,
                    "expected '%s' to be in '%s'" % (x, attrs))

        for x in list(model.defined_associations):
            self.assertTrue(x in attrs,
                    "expected '%s' to be in '%s'" % (x, attrs))

        for x in DirModel._relation_delegates:
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
            pydoc.TextDoc().docclass(DirModel)
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
        self.assertContains(HelpModel.__doc__, 'a model with a docstring')

    def test_attributes_included(self):
        """should include a model's attributes in __doc__"""
        self.assertContains(HelpModel.__doc__, '\nData attributes:')
        for attr in HelpModel.defined_attributes:
            self.assertContains(HelpModel.__doc__, '\t' + attr)

    def test_associations_included(self):
        """should include a model's associations in __doc__"""
        self.assertContains(HelpModel.__doc__, '\nAssociations:')
        self.assertContains(HelpModel.__doc__, '\tbelongs_to    ape')
        self.assertContains(HelpModel.__doc__, '\tbelongs_to    foo')
        self.assertContains(HelpModel.__doc__, '\thas_many      bars')
        self.assertContains(HelpModel.__doc__, '\thas_many      bananas')

    def test_link_to_docs(self):
        """should include a link to the full documentation"""
        self.assertContains(HelpModel.__doc__,
                'http://packages.python.org/pyperry/')

    def test_everything(self):
        """
        should included everything specified in __doc__ with proper formatting
        and sorted in correct order

        """
        self.assertEqual(HelpModel.__doc__,
"""a model with a docstring

Data attributes:
\tattr1
\tattr2

Associations:
\tbelongs_to    ape
\tbelongs_to    foo (polymorphic)
\thas_many      bananas
\thas_many      bars (through bananas)

Full documentation available at http://packages.python.org/pyperry/"""
        )


class DescribeAssociationTestCase(unittest.TestCase):

    def test_belongs_to(self):
        self.assertEqual(AssociationModel.describe_association('you'),
            "\tbelongs_to    you")

    def test_belongs_to_polymorphic(self):
        self.assertEqual(AssociationModel.describe_association('foo'),
            "\tbelongs_to    foo (polymorphic)")

    def test_has_one(self):
        self.assertEqual(AssociationModel.describe_association('bar'),
            "\thas_one       bar")

    def test_has_many(self):
        self.assertEqual(AssociationModel.describe_association('bizs'),
            "\thas_many      bizs")

    def test_has_many_through(self):
        self.assertEqual(AssociationModel.describe_association('bazs'),
            "\thas_many      bazs (through bizs)")
