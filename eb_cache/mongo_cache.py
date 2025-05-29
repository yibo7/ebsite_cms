from flask_caching.backends.base import BaseCache
import pickle
import time


class MongoCache(BaseCache):
    def __init__(
            self,
            collection,
            default_timeout=300,
            **kwargs
    ):
        super().__init__(default_timeout)
        self.key_prefix = "ebcache"

        self.collection = collection



    @classmethod
    def factory(cls, app, config, args, kwargs):

        kwargs["collection"] = app.db['cache_collection']
        return cls(*args, **kwargs)

    def _get_prefix_key(self, key):
        return f"{self.key_prefix}{key}"

    def get(self, key):
        key = self._get_prefix_key(key)
        data = self.collection.find_one({"_id": key})
        if data:
            if data['exp'] == 0 or data['exp'] > time.time():
                return pickle.loads(data['val'])
        return None

    def set(self, key, value, timeout=None):
        key = self._get_prefix_key(key)
        timeout = self._normalize_timeout(timeout)
        exp = 0 if timeout is None else (time.time() + timeout)

        self.collection.update_one(
            {"_id": key},
            {"$set": {"val": pickle.dumps(value), "exp": exp}},
            upsert=True
        )
        return True

    def delete(self, key):
        key = self._get_prefix_key(key)
        self.collection.delete_one({"_id": key})
        return True

    def has(self, key):
        return self.get(key) is not None

    def clear(self):
        self.collection.delete_many({})
        return True

    def add(self, key, value, timeout=None):
        key = self._get_prefix_key(key)
        timeout = self._normalize_timeout(timeout)
        exp = 0 if timeout is None else (time.time() + timeout)
        result = self.collection.update_one(
            {"_id": key, "exp": {"$lt": time.time()}},
            {"$set": {"val": pickle.dumps(value), "exp": exp}},
            upsert=True
        )
        return result.upserted_id is not None

    def get_many(self, *keys):
        return [self.get(key) for key in keys]

    def set_many(self, mapping, timeout=None):
        for key, value in mapping.items():
            self.set(key, value, timeout)
        return True

    def delete_many(self, *keys):
        for key in keys:
            self.delete(key)
        return True