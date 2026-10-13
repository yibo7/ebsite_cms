from flask_caching.backends.base import BaseCache
from pymongo.errors import DuplicateKeyError
import pickle
import time


class MongoCache(BaseCache):
    #: 两次自动清理之间的最小间隔（秒）
    CLEANUP_INTERVAL = 3600

    def __init__(
            self,
            collection,
            default_timeout=300,
            **kwargs
    ):
        super().__init__(default_timeout)
        self.key_prefix = "ebcache"

        self.collection = collection
        # 进程内记录上次清理时间；多实例/多进程重复清理是幂等的
        self._last_cleanup = 0.0

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

    def _auto_cleanup(self):
        """
        机会式清理过期文档。

        Serverless（Vercel）没有常驻进程，无法用后台定时任务，因此在写入路径
        上按时间间隔顺带清理：每个进程/实例最多每小时清一次，代价可忽略，
        重复清理也是幂等的。清理失败不影响本次写入。
        """
        now = time.time()
        if now - self._last_cleanup < self.CLEANUP_INTERVAL:
            return
        self._last_cleanup = now
        try:
            self.cleanup_expired()
        except Exception:
            pass

    def get(self, key):
        key = self._get_prefix_key(key)
        data = self.collection.find_one({"_id": key})
        if data:
            # exp 缺失（早期 incr 写入的文档）视为永不过期，避免 KeyError
            exp = data.get("exp", 0)
            if exp == 0 or exp > time.time():
                value = data.get("val")
                # set()/set_obj() 写入的是 pickle 字节流，incr() 写入的是 int
                if isinstance(value, (bytes, bytearray)):
                    return pickle.loads(value)
                return value
            # 已过期：顺手删掉，让被访问过的键自然收敛
            try:
                self.collection.delete_one({"_id": key})
            except Exception:
                pass
        return None

    def set(self, key, value, timeout=None):
        self._auto_cleanup()
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

    def inc(self, key, delta=1, timeout=None):
        """
        原子自增（flask_caching 的标准接口名，对应 BaseCache.inc）。

        使用 MongoDB 的 ``$inc``，保证多进程/多实例并发时计数不丢失。

        :param delta: 增量，默认 1
        :param timeout: 新建键的过期时间（秒）；只在插入新文档时写入 exp，
                        不会刷新已有键的过期时间（固定窗口语义）
        """
        self._auto_cleanup()
        key = self._get_prefix_key(key)
        timeout = self._normalize_timeout(timeout)
        exp = 0 if timeout is None else (time.time() + timeout)
        try:
            after = self.collection.find_one_and_update(
                # 只对数字类型的 val 自增；val 非数字时该条件不匹配
                {"_id": key, "val": {"$type": "number"}},
                {
                    "$inc": {"val": delta},
                    # 插入新文档时补写 exp，避免 get() 取不到该字段
                    "$setOnInsert": {"exp": exp},
                },
                upsert=True,
                return_document=True
            )
        except DuplicateKeyError:
            # 文档已存在但 val 不是数字（旧版 get-then-set 写入的 pickle 值），
            # upsert 撞上同一 _id 会报重复键 —— 此时直接重置为数字计数
            after = self.collection.find_one_and_update(
                {"_id": key},
                {"$set": {"val": delta, "exp": exp}},
                upsert=True,
                return_document=True
            )
        if after is None or "val" not in after:
            return delta
        # find_one_and_update + $inc 返回的是更新后的文档
        return after["val"] if isinstance(after["val"], int) else int(after["val"])

    # 兼容旧调用名（原实现叫 incr，且从未被 flask_caching 的 Cache 暴露出来）
    incr = inc

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