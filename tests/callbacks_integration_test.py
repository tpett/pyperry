import tests
import unittest

import pyperry
from pyperry import callbacks


class CallbacksIntegrationTestCase(unittest.TestCase):

    def test_hierarchy(self):
        """each class should be independent"""
        class A(pyperry.Base):
            @callbacks.before_save
            def foo(self):
                pass

        class B(A):
            @callbacks.before_save
            def bar(self):
                pass

        class C(A):
            @callbacks.before_save
            def baz(self):
                pass


        self.assertEqual(
                A.callback_manager.callbacks[callbacks.before_save],
                [A.foo.callback] )

        self.assertEqual(
                B.callback_manager.callbacks[callbacks.before_save],
                [A.foo.callback, B.bar.callback] )

        self.assertEqual(
                C.callback_manager.callbacks[callbacks.before_save],
                [A.foo.callback, C.baz.callback] )
