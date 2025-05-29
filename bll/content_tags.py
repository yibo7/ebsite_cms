import datetime
import hashlib
import time

from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

import eb_utils
from bll.bll_base import BllBase
from entity.tag_model import TagModel



class ContentTags(BllBase[TagModel]):

    def new_instance(self) -> TagModel:
        model = TagModel()
        # model._id = ObjectId()
        return model

    @staticmethod
    def _generate_tag_id(tag_name):
        """
        生成标签ID(MD5哈希)

        :param tag_name: 标签名称
        :return: MD5哈希字符串
        """
        return hashlib.md5(tag_name.encode('utf-8')).hexdigest()

    def increment_tags(self, tag_names):
        """增加标签计数"""
        self._update_tag_counts(tag_names, increment=1, allow_upsert=True)

    def decrement_tags(self, tag_names):
        """减少标签计数（安全版本）"""
        self._update_tag_counts(tag_names, increment=-1, allow_upsert=False)

    def _update_tag_counts(self, tag_names, increment, allow_upsert):
        """
        通用标签计数更新方法

        :param tag_names: 标签列表
        :param increment: 增量（1或-1）
        :param allow_upsert: 是否允许创建新标签
        """
        if not tag_names:
            return

        # 去重处理
        unique_tags = set(tag.strip() for tag in tag_names if tag.strip())
        if not unique_tags:
            return

        operations = []
        current_time = time.time()

        for tag in unique_tags:
            tag_id = self._generate_tag_id(tag)
            update_op = {
                '$inc': {'article_count': increment}
            }

            # 只有增加计数且允许upsert时才设置初始值
            if increment > 0 and allow_upsert:
                update_op['$setOnInsert'] = {
                    'name': tag,
                    'add_time': current_time
                }

            # 对于减少操作，添加条件防止负值
            filter_criteria = {'_id': tag_id}
            if increment < 0:
                filter_criteria['article_count'] = {'$gt': 0}

            operations.append(UpdateOne(
                filter_criteria,
                update_op,
                upsert=allow_upsert
            ))

        try:
            if operations:
                self.table.bulk_write(operations, ordered=False)
        except BulkWriteError as e:
            print(f"标签更新失败: {e.details}")
            raise

    def cleanup_unused_tags(self):
        """
        清理没有文章引用的标签(article_count <= 0)

        :return: 删除的标签数量
        """
        result = self.table.delete_many({'article_count': {'$lte': 0}})
        return result.deleted_count


    def find_one_by_id(self, _id: str) -> TagModel:
        document = self.table.find_one({"_id": _id})
        if document:
            model = TagModel()
            model.dict_to_model(document,False)
            return model
        return None

    def build_model(self, dic_data: dict):
        model = self.new_instance()
        model.dict_to_model(dic_data,False)
        return model