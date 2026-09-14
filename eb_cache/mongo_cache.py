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

        # 在集合上创建索引
        # 1) exp 索引：加速过期查询和清理
        # 2) _id 前缀查询索引：加速 clear() 按前缀删除
        try:
            self.collection.create_index("exp")
        except Exception:
            pass



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

    def incr(self, key, initial=0):
        """
        原子自增操作（使用 $inc）。
        若键不存在则先插入初始值再自增。
        """
        key = self._get_prefix_key(key)
        after = self.collection.find_one_and_update(
            {"_id": key},
            {"$inc": {"val": 1}},
            upsert=True,
            return_document=True
        )
        # 如果返回的文档没有 val（刚 upsert 但 $inc 没反应到返回里）
        # 兜底：手动读一次
        if after is None or "val" not in after:
            self.collection.update_one(
                {"_id": key, "val": {"$exists": False}},
                {"$set": {"val": initial, "exp": 0}},
                upsert=True
            )
            return initial + 1
        # find_one_and_update + $inc 返回的是更新后的文档
        return after["val"] if isinstance(after["val"], int) else int(after["val"])

    def cleanup_expired(self, batch_size=100):
        """
        清理已过期的缓存条目（配合 exp 索引使用）。
        返回本次清理的文档数。
        """
        now = time.time()
        result = self.collection.delete_many(
            {"exp": {"$gt": 0, "$lte": now}}
        )
        return result.deleted_count