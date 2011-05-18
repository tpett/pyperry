import tests
import unittest
from datetime import datetime, timedelta

import pyperry
from pyperry.middlewares import LocalCache
from tests.fixtures.test_adapter import TestAdapter
from pyperry.middlewares.local_cache import CacheStore

class LocalCacheBaseTestCase(unittest.TestCase):
    pass

class LocalCacheInitTestCase(LocalCacheBaseTestCase):

    def test_params(self):
        """should take argument for next item in call stack"""
        l = LocalCache('foo')
        self.assertEqual(l.next, 'foo')

    def test_optional_params(self):
        """should take optional configuration options"""
        l = LocalCache('foo', { 'bar': 'baz'})
        self.assertEqual(l.options, { 'bar': 'baz' })


class LocalCacheInstalledTestCase(LocalCacheBaseTestCase):

    def setUp(self):
        TestAdapter.data = { 'id': 1 }
        TestAdapter.count = 1
        self.cache = pyperry.middlewares.local_cache.cache_store
        class Test(pyperry.Base):
            def _config(cls):
                cls.attributes('id')
                cls.configure('read', adapter=TestAdapter)
                cls.add_middleware('read', LocalCache)
        self.Test = Test

    def tearDown(self):
        self.cache.empty()
        TestAdapter.reset()

    def test_empty_cache(self):
        """should return adapter result when cache is empty"""
        record = self.Test.first()
        self.assertEqual(record.id, 1)

    def test_stores_result_in_cache(self):
        """should store the result from adapter in the cache"""
        self.assertEqual(len(self.cache.store.keys()), 0)
        record = self.Test.first()
        self.assertEqual(len(self.cache.store.keys()), 1)
        self.assertEqual(self.cache.store.values()[0][0], [record.attributes])

    def test_recalls_result_from_cache(self):
        """should recall stored value from cache"""
        record1 = self.Test.first()
        TestAdapter.data = { 'id': 2 }
        record2 = self.Test.first()

        self.assertEqual(record1.attributes, record2.attributes)

    def test_unique_results(self):
        """should only return from cache of same query"""
        record1 = self.Test.first()
        TestAdapter.data = { 'id': 2 }
        record2 = self.Test.where('foo').first()
        self.assertNotEqual(record1.attributes, record2.attributes)

    def test_interval_option(self):
        """should use interval option for longevity of new entries"""
        self.Test.adapter('read', ).middlewares[0] = (LocalCache, { 'interval': 0 })
        self.Test.first()
        self.Test.first()
        self.assertEqual(len(TestAdapter.calls), 2)

    def test_max_entry_size_option(self):
        """should only allow max_entry_size entries if set"""
        self.Test.adapter('read', ).middlewares[0] = (
                LocalCache, { 'max_entry_size': 2 })
        TestAdapter.count = 3
        self.Test.first()
        self.Test.first()
        self.assertEqual(len(TestAdapter.calls), 2)

    def test_adds_fresh_to_relation(self):
        """should add fresh method to Relation and it should force fresh"""
        self.assertTrue(pyperry.Relation.singular_query_methods.count('fresh'))
        records = self.Test.where('foo')
        records.fetch_records()
        records = records.fresh()
        self.assertEqual(records._records, None)
        self.assertEqual(records._query, None)
        self.assertEqual(records.params['fresh'], True)



    def test_force_cache_refresh(self):
        """should force cache refresh if fresh query option present"""
        rel = self.Test.scoped()
        rel.fresh().first()
        rel.fresh().first()
        self.assertEqual(len(TestAdapter.calls), 2)


##
# Test the in memory caching structure
#
class CacheStoreBaseTestCase(unittest.TestCase):
    def setUp(self):
        self.store = CacheStore(10)

class CacheStoreInitMethodTestCase(CacheStoreBaseTestCase):

    def test_params(self):
        """should take a default caching interval in seconds"""
        store = CacheStore(500)
        self.assertEqual(store.default_interval.seconds, 500)

class CacheStoreWriteMethodTestcase(CacheStoreBaseTestCase):

    def test_params(self):
        """should take a key, value"""
        self.store.write('foo', 'barbarbar')
        self.assertTrue(self.store.store.has_key('foo'))
        self.assertEqual(self.store.store['foo'][0], 'barbarbar')

    def test_optional_expire_time(self):
        """should take optional expire time"""
        expire = datetime.now()
        self.store.write('foo', 'bar', expire)
        self.assertEqual(self.store.store['foo'], ('bar', expire))

    def test_sets_expire_default(self):
        """should set expire based on default if not set"""
        expire = datetime.now() + timedelta(seconds=10)
        self.store.write('foo', 'bar')
        diff = abs(self.store.store['foo'][1] - expire)
        self.assertTrue(diff < timedelta(seconds=1))

    def test_expire(self):
        """should remove any expired items from the cache"""
        self.store.write('foo', 'bar', datetime.now() - timedelta(seconds=11))
        self.store.write('baz', 'apple')
        self.assertTrue( not self.store.store.has_key('foo') )

class CacheStoreReadMethodTestCase(CacheStoreBaseTestCase):

    def test_params(self):
        """should take a key"""
        assert hasattr(self.store, 'read')
        self.store.write('foo', 'bar')
        self.assertEqual(self.store.read('foo'), 'bar')

    def test_return_none_if_expired(self):
        self.store.write('foo', 'bar', datetime.now() - timedelta(seconds=11))
        self.assertEqual(self.store.read('foo'), None)

class CacheStoreClearMethodTestCase(CacheStoreBaseTestCase):

    def test_params(self):
        """should be callable with no options"""
        self.store.write('foo', 'bar', datetime.now() - timedelta(seconds=11))
        self.store.clear()
        self.assertFalse(self.store.store.has_key('foo'))

    def test_optional_params(self):
        """should take optional key to remove a key"""
        self.store.write('foo', 'bar')
        self.store.clear('foo')
        self.assertFalse(self.store.store.has_key('foo'))

class CacheStoreEmptyMethodTestCase(CacheStoreBaseTestCase):

    def test_empty_cache(self):
        """should clear out the cache"""
        self.store.write('foo', 'poop')
        self.store.write('bar', 'barf', datetime.now())
        self.store.write('baz', 'blah', datetime.now() + timedelta(hours=5))
        self.store.empty()
        self.assertEqual(len(self.store.store.keys()), 0)

