import pyperry
from datetime import datetime, timedelta
import hashlib

from pyperry.relation import Relation
from pyperry import caching

class CacheStore(object):

    def __init__(self, interval):
        self.default_interval = timedelta(seconds=interval)
        self.store = {}

    def read(self, key):
        if self.store.has_key(key):
            if self.store[key][1] > datetime.now():
                return self.store[key][0]
            else:
                del self.store[key]

    def write(self, key, val, expire_at=None):
        self.clear()
        self.store[key] = (val,
                expire_at or (datetime.now() + self.default_interval))

    def clear(self, key=None):
        if key:
            del self.store[key]
        else:
            now = datetime.now()
            for key in self.store.keys():
                if self.store[key][1] < now:
                    del self.store[key]

    def empty(self):
        del self.store
        self.store = {}


class LocalCache(object):
    """ LocalCache middleware

    Caches results of queries in memory returning the previous result of
    repeated queries until the entry expires.  Entries are cached based on
    the query used.

    Config options:
        - interval: The interval in seconds that a given cache entry will be
          considered fresh
        - max_entry_size: Max len of results that will be cached.  If set only
          results less than this value will be stored in the cache.  All others
          will be refetched every time.

    Importing this module adds the fresh query option to Relation.  This allows
    the developer to easily force a query to be fresh::

        # This query will always fetch fresh data
        Person.where({ 'name': 'bob' }).fresh()

    """
    # Initialize store with default interval of 5 minutes
    cache_store = CacheStore(300)

    def __init__(self, next, options=None):
        if not options:
            options = {}
        self.next = next
        self.options = options

    def __call__(self, **kwargs):
        rel = kwargs['relation']
        key = hashlib.sha1("%s--%s" % (rel.klass, rel.query())).hexdigest()

        result = self.cache_store.read(key)

        if (not result or rel.params['fresh']) and caching.enabled:
            # Call the next item in the stack to get a fresh result
            result = self.next(**kwargs)
        else:
            pyperry.logger.info('CACHE: %s' % kwargs['relation'].query())


        # Use configured cache expiry interval if set
        expires_at = None
        if self.options.has_key('interval'):
            expires_at = (datetime.now() +
                timedelta(seconds=self.options.get('interval')))

        # Only store records < configured max_entry_size if set
        if (not self.options.has_key('max_entry_size') or
                self.options['max_entry_size'] > len(result)):
            self.cache_store.write(key, result, expires_at)

        return result

cache_store = LocalCache.cache_store

caching.register(cache_store.empty)

##
# Add features to Relation needed for caching
#
if not Relation.singular_query_methods.count('fresh'):
    Relation.singular_query_methods.append('fresh')

    def fresh(self, value=True):
        self = self.clone()
        self.params['fresh'] = value
        self._query = None
        self._records = None
        return self

    setattr(Relation, 'fresh', fresh)

