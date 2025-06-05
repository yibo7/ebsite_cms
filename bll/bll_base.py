import re
import time
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar, Tuple, Optional, List

import pymongo
from bson import ObjectId
from pymongo.client_session import ClientSession

from eb_utils import http_helper
from eb_utils.configs import SiteConstant
from eb_utils.mvc_pager import pager_html_admin, MvcPager

T = TypeVar('T')  # 定义一个类型变量 T
from flask import current_app, Flask


class BllBase(Generic[T], ABC):
    def __init__(self, app: Optional[Flask] = None):
        self.table_name = type(self).__name__

        cur_app = app if app else current_app
        self.app = cur_app
        self.db_client = cur_app.db_client
        self.db = cur_app.db
        self.configs = cur_app.config
        self.table = self.db[self.table_name]


    def create_index(self, col_name):
        """
        创建唯一索引，如果同一个col_name重复调用此方法，将只会操作一次
        :param col_name:
        :return:
        """
        self.table.create_index([(col_name, pymongo.ASCENDING)], unique=True)

    def get_int_id(self):
        """
        获取一个自增ID
        """
        # return generate_next_id(self.table_name)
        return self.get_next_sequence()

    def get_next_sequence(self):
        """
        用表SequenceIds来维护所有表的自增Id
        find_one_and_update,查询并执行更新增加1，如果没有记录就添加一个
        """
        result = self.db["SequenceIds"].find_one_and_update(
            {"_id": self.table_name},
            {"$inc": {"seq_value": 1}},
            upsert=True,
            return_document=True
        )
        return result["seq_value"]

    def exist_table(self):
        return self.table_name in self.db.list_collection_names()

    def exist_data(self, key_name: str, k_value: str) -> bool:
        return self.find_one_by_where({f'{key_name}': k_value})

    # def get_dic(self):
    #     data = self.__dict__
    #     data.pop("table_name")
    #     return data

    def add(self, model: T) -> ObjectId:
        """
        添加数据，添加时可以指定一个Id
        @param model:
        @return:
        """
        if not model._id:
            model._id = ObjectId()

        if hasattr(model, 'id'):
            model.id = self.get_int_id()
        data_dic = model.__dict__
        result = self.db[self.table_name].insert_one(data_dic)
        return result.inserted_id

    def add_trans(self, model: T, session: Optional[ClientSession]) -> ObjectId:

        model._id = ObjectId()
        if hasattr(model, 'id'):
            model.id = self.get_int_id()
        data_dic = model.__dict__
        result = self.db[self.table_name].insert_one(data_dic, session=session)
        return result.inserted_id

    def update_trans(self, model: T, session: Optional[ClientSession], version=-1) -> bool:
        """
        更新一条数据--事务处理
        :param model: 是一个document对象
        :return: 是否更新成功
        @param version: 乐观锁号
        @param session: 事务session
        """
        if not model._id:
            raise Exception("更新数据传递对象的_id不能为空")
        where = {"_id": model._id}

        if version>-1:
            where["version"] = version
            model.version = version+1

        new_values = {"$set": model.__dict__}
        if where:
            result = self.db[self.table_name].update_one(where, new_values,session=session)
            return result.modified_count > 0
        return False

    def update(self, model: T) -> bool:
        """
        更新一条数据
        :param model: 是一个document对象
        :return: 是否更新成功
        """
        if not model._id:
            raise Exception("更新数据传递对象的_id不能为空")
        where = {"_id": model._id}
        new_values = {"$set": model.__dict__}
        if where:
            result = self.db[self.table_name].update_one(where, new_values)
            return result.modified_count > 0
        return False

    def update_add(self, model: T) -> bool:
        """
        更新一条数据,与update的不同在于，如果不存在将添加一条新数据
        :param model: 这是一个实体对象，不是document
        :return: 是否更新成功
        """
        if not model._id:
            model._id = ObjectId()

        where = {"_id": model._id}
        new_values = {"$set": model.__dict__}
        if where:
            result = self.db[self.table_name].update_one(where, new_values, upsert=True) # upsert=True 表示，如果没有此数据，就添加一条数据
            return result.upserted_id is not None or result.modified_count > 0
        return False

    # def update_add_where(self, model: T, col_name, col_value) -> bool:
    #     """
    #     更新一条数据,与update的不同在于，如果不存在将添加一条新数据
    #     :return: 是否更新成功
    #     @param model: 这是一个实体对象，不是document
    #     @param col_value:
    #     @param col_name:
    #     """
    #     if not col_name:
    #         raise Exception("更新或添加数据col_name的不能为空")
    #     if not col_value:
    #         raise Exception(f"更新或添加数据{col_name}的值col_value不能为空")
    #
    #     if not model._id:
    #         model._id = ObjectId()
    #
    #     where = {col_name: col_value}  # 注意调用update_one，如果匹配到多条数据，也只更新第一条，使用update_many可以更新所有匹配到的数据
    #     print(where)
    #     new_values = {"$set": model.__dict__}
    #     if where:
    #         result = self.db[self.table_name].update_one(where, new_values, upsert=True) # upsert=True 表示，如果没有此数据，就添加一条数据
    #         return result.upserted_id is not None or result.modified_count > 0
    #     return False

    def delete_by_id(self, _id):
        # 删除单个文档
        if isinstance(_id, str):
            _id = ObjectId(_id)
        s_where = {"_id": _id}
        return self.db[self.table_name].delete_one(s_where)

    def delete_by_ids(self, ids: [str]):
        """
        同时删除多个指定id的记录
        :param ids: id 列表，如 ["_id1", "_id2", "_id3"]
        :return:
        """
        # 构建筛选条件
        new_ids = []
        for data_id in ids:
            new_ids.append(ObjectId(data_id))
        s_where = {"_id": {"$in": new_ids}}
        # 执行删除操作
        return self.delete_by_where(s_where)

    # @admin_action_log("删除用户")
    def delete_from_page(self, s_id):
        if s_id:
            a_id = s_id.split(',')
            if 'on' in a_id:
                a_id.remove('on')
            self.delete_by_ids(a_id)

    def delete_by_where(self, d_where):
        """
        删除指定条件下的记录
        :param d_where: 条件，如 {"_id": {"$in": ids}}
        :return:
        """
        # 执行删除操作
        try:
            # print(d_where)
            result = self.db[self.table_name].delete_many(d_where)
            # print(f"Deleted {result.deleted_count} documents.")
            return result
        except Exception as e:
            print(f"MongoDb Delete err: {str(e)}")

    def save(self, model: T) -> ObjectId:
        """
        保存数据，如果存在model._id，将视为更新数据，并且如果不存在model._id的记录，将添加一条新的记录
        @param model:
        @return:
        """
        inserted_id = None
        if model:
            if model._id:
                self.update(model)
                inserted_id = model._id
            else:
                inserted_id = self.add(model)
        return inserted_id


    def find_one_first(self) -> T:
        # 查询单个文档
        document = self.db[self.table_name].find_one()
        return self.build_model(document)

    def find_one_by_id(self, _id: str) -> T:
        # 查询单个文档
        # document = mongo_db[self.table_name].find_one({"_id": ObjectId(_id)})
        # return self.build_model(document)
        data_id = ObjectId()
        if _id != "":
            data_id = ObjectId(_id)
        return self.find_one_by_where({"_id": data_id})

    def find_one_by_where(self, where: {}) -> T:
        # 查询单个文档
        document = self.db[self.table_name].find_one(where)
        if document:
            return self.build_model(document)
        return None

    def find_list_by_where(self, where: {}, sort_key="_id", sort_direction=pymongo.DESCENDING, limit: int = 100000) -> \
            list[
                T]:
        """
        查询列表
        :param where: 查询条件 如：{"name":"ctt"}
        :param limit: 查询数量 如：10
        :param sort_key: 要用哪个字段排序，默认使用_id
        :param sort_direction: 排序方式，默认使用 pymongo.DESCENDING 降序排序
        :return: 结果列表，可以通过 for data in datas 遍历
        """

        if not where:
            where = {}
        datas = self.db[self.table_name].find(where).limit(limit).sort(sort_key, sort_direction)
        lst = []
        for document in datas:
            lst.append(self.build_model(document))
        return lst  # list(datas)

    # def find_list_by_where(self, where: {}, sort_key="_id", sort_direction=pymongo.DESCENDING) -> list[T]:
    #     """
    #     查询列表
    #     :param where: 查询条件 如：{"name":"ctt"}
    #     :param sort_key: 要用哪个字段排序，默认使用_id
    #     :param sort_direction: 排序方式，默认使用 pymongo.DESCENDING 降序排序
    #     :return: 结果列表，可以通过 for data in datas 遍历
    #     """
    #     if not where:
    #         where = {}
    #     datas = mongo_db[self.table_name].find(where).sort(sort_key, sort_direction)
    #     lst = []
    #     for document in datas:
    #         lst.append(self.build_model(document))
    #     return lst  # list(datas)

    def find_all(self) -> list[T]:
        """
        查询列表-所有
        :return: 结果列表，可以通过 for data in datas 遍历
        """
        return self.find_list_by_where({})

    def count(self, s_where: {}):
        c = self.db[self.table_name].count_documents(s_where)
        return c

    def find_pages(self, page_number: int, page_size: int, where=None, sort_key="_id",
                   sort_direction=pymongo.DESCENDING,projection=None) -> Tuple[list[T], int]:
        """
        分页查询列表
        :param projection: 要排除的字段，如果字段内容太多，不想在查询中返回排除后会提高速度，projection = {'content': 0}
        :param page_size: 每页的记录数
        :param page_number: 页码，从1开始
        :param where: 查询条件 如：{"name":"ctt"} 默认不填写将查询全部
        :param sort_key: 要用哪个字段排序，默认使用_id
        :param sort_direction: 排序方式，默认使用 pymongo.DESCENDING 降序排序
        :return: 结果列表，可以通过 for data in datas 遍历
        """

        # 计算跳过的文档数量
        if not where:
            where = {}
        skip_count = (page_number - 1) * page_size
        # projection = {'content': 0}
        # 执行分页查询并排序
        datas = self.db[self.table_name].find(where, projection).skip(skip_count).limit(page_size).sort(sort_key, sort_direction)
        lst = []
        i_count = 0
        if datas:
            i_count = self.count(where)
            # lst = []
            for document in datas:
                lst.append(self.build_model(document))

        return lst, i_count

    def find_pager(self, page_number: int, page_size: int, rewrite_rule: str, where=None, sort_key="_id",
                   sort_direction=pymongo.DESCENDING) -> Tuple[list[T], str]:
        """
        分页查询列表
        :param page_size: 每页的记录数
        :param page_number: 页码，从1开始
        :param rewrite_rule: 分页的地址重写规则，规则中的{0}是页码
        :param where: 查询条件 如：{"name":"ctt"} 默认不填写将查询全部
        :param sort_key: 要用哪个字段排序，默认使用_id
        :param sort_direction: 排序方式，默认使用 pymongo.DESCENDING 降序排序
        :return: 结果列表，可以通过 for data in datas 遍历
        """

        datas, i_count = self.find_pages(page_number, page_size, where, sort_key, sort_direction)
        # pager = pager_html_admin(i_count, page_number, page_size, where)
        pager = ''
        if i_count > page_size:
            pg = MvcPager()
            pg.current_page = page_number
            pg.total_count = i_count
            pg.page_size = page_size
            pg.params = None
            pg.ShowCodeNum = 10
            pg.rewrite_rule = rewrite_rule
            pager = pg.show_pages()

        return datas, pager

    def search(self, keyword: str, page_number: int, key_name: str) -> Tuple[list[T], str]:
        """
        模糊搜索
        :param keyword: 搜索的关键词, 不传入会搜索所有
        :param page_number: 页面码
        :param key_name: 要模糊搜索的字段
        :return:
        """
        page_size = SiteConstant.PAGE_SIZE_AD

        s_where = {}
        if keyword:
            regex_pattern = re.compile(f'.*{re.escape(keyword)}.*', re.IGNORECASE)  # IGNORE CASE 忽略大小写
            s_where = {key_name: {'$regex': regex_pattern}}

        datas, i_count = self.find_pages(page_number, page_size, s_where)

        pager = pager_html_admin(i_count, page_number, page_size, {'k': keyword})
        return datas, pager

    @abstractmethod
    def new_instance(self) -> T:
        pass

    def build_model(self, dic_data: dict):
        model = self.new_instance()
        model.dict_to_model(dic_data)
        return model

    def get_by_int_id(self, int_id: int) -> T:
        # 查询单个文档
        return self.find_one_by_where({"id": int_id})

    def to_dicts(self, models: list[T], exclude_fields: Optional[List[str]] = None):
        """
         将模型列表转换为可序列化的字典-解决MongoDb中ObjectId，Decimal128无法序列化的问题
         :param exclude_fields: 需要排除的字段列表
         :param models: 模型列表
        """
        models_dicts = [model.to_dict(exclude_fields) for model in models]
        return models_dicts


    def clean_mongo_search_keywords(self, key_words: str,is_clear_re_dos = True) -> str:
        return http_helper.clean_keywords(key_words, is_clear_re_dos)