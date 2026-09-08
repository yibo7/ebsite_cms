# 发布项目默认备份还原的表
import json
import os

import pymongo
from bson import json_util
from flask import current_app, request

from bll.user import User
from eb_utils import http_utils
from eb_utils.configs import WebPaths

default_tables = ['AdminMenus', 'AdminRole', 'AdminUser', 'SiteModel', 'Templates', 'UserGroup', 'Widgets', 'NewsClass',
                  'NewsContent','ContentTags','NewsSpecial','CustomForm','SiteSettings','SequenceIds']


class DataBakup:
    """
    初始化系统数据用
    """
    def __init__(self):
        self.db = current_app.db
        self.back_path = "db_backup/"

    def OutputDefaultData(self):
        """
        备份表
        """
        for table_name in default_tables:
            # 获取数据库和集合
            collection = self.db[table_name]

            # 查询集合中的所有文档
            cursor = collection.find({})
            data = [document for document in cursor]
            data = json_util.dumps(data)

            with open(f'{self.back_path}{table_name}.json', 'w', encoding='utf-8') as file:
                file.write(data)

    def OutputAllData(self):
        """
        备份表
        """
        collection_list = self.db.list_collection_names()
        for table_name in collection_list:
            # 获取数据库和集合
            collection = self.db[table_name]

            # 查询集合中的所有文档
            cursor = collection.find({})
            data = [document for document in cursor]
            data = json_util.dumps(data)

            with open(f'{self.back_path}{table_name}.json', 'w', encoding='utf-8') as file:
                file.write(data)
    def re_build_index(self):

        # NewsContent 全文搜索的索引
        NewsContent = self.db["NewsContent"]
        NewsContent.drop_indexes()  # 清除所有索引

        # 全文搜索索引（用于搜索页面的 $text 查询，比 $regex 快 10~100 倍）
        NewsContent.create_index([
            ('title', pymongo.TEXT),
            ('info', pymongo.TEXT)
        ], name='news_chinese_text_search_index', default_language='none')

        # 1. 为title和info字段创建普通索引（对前缀匹配有效）
        NewsContent.create_index("title")
        NewsContent.create_index("info")
        # 2. 创建复合索引（如果经常同时搜索多个字段）
        NewsContent.create_index([("title", 1), ("info", 1)])

        NewsContent.create_index([("tags", pymongo.ASCENDING)])
        # 分类列表页查询复合索引：按 class_id 筛选 + _id 降序排序
        NewsContent.create_index([("class_id", pymongo.ASCENDING), ("_id", pymongo.DESCENDING)])
        # 分类列表页排序索引：按 class_id 筛选 + order_id + _id 降序排序（支持自定义排序）
        NewsContent.create_index([("class_id", pymongo.ASCENDING), ("order_id", pymongo.DESCENDING), ("_id", pymongo.DESCENDING)])
        # 标签聚合索引：按 class_n_id 筛选 + tags 字段（加速 $unwind + $group 聚合）
        NewsContent.create_index([("class_n_id", pymongo.ASCENDING), ("tags", pymongo.ASCENDING)])
        # 用户内容列表索引：按 user_id 筛选 + add_time 降序排序（加速个人中心查询）
        NewsContent.create_index([("user_id", pymongo.ASCENDING), ("add_time", pymongo.DESCENDING)])
        # 热门排序索引：hits 降序（加速首页热门曲谱查询）
        NewsContent.create_index([("hits", pymongo.DESCENDING)])
        # 推荐排序索引：is_good + hits 降序（加速首页推荐查询）
        NewsContent.create_index([("is_good", pymongo.ASCENDING), ("hits", pymongo.DESCENDING)])
        # 内容自增ID索引：id（加速专题页面按 id 查询内容）
        NewsContent.create_index([("id", pymongo.ASCENDING)])
        # NewsContent.create_index([("ClassId", 1), ("rand_num", 1)])
        NewsContent.create_index("rand_num")

    def is_exist_all_table(self):
        """
        检查默认表是否都存在，
        @return:
        """
        for table_name in default_tables:
            collection_list = self.db.list_collection_names()
            if table_name not in collection_list:
                return False

        return True

    def InitDefaultData(self):
        """
        还原必要数据表的默认数据
        """
        # bll_user = User()
        # if not bll_user.exist_table():
        #     bll_user.create_indexs()

        for table_name in default_tables:
            collection_list = self.db.list_collection_names()
            if table_name not in collection_list:
                json_file = f"{self.back_path}{table_name}.json"
                # csv_file = f"{request.host_url}{WebPaths.ADMIN_PATH}db_init/{table_name}.json"
                # txt = http_utils.getText(csv_file)
                # 获取 CSV 文件的表名(去除文件扩展名)
                # collection_name = os.path.splitext(os.path.basename(csv_file))[0]
                collection_name = table_name
                collection = self.db[collection_name]

                # 创建唯一索引
                if collection_name == 'User':
                    collection.create_index([('username', pymongo.ASCENDING)], unique=True)
                    collection.create_index([('mobile_number', pymongo.ASCENDING)], unique=True)
                    collection.create_index([('email_address', pymongo.ASCENDING)], unique=True)

                if collection_name == 'AdminUser':
                    collection.create_index([('user_name', pymongo.ASCENDING)], unique=True)
                try:
                    # json_data = json.loads(txt, object_hook=json_util.object_hook)
                    with open(json_file, "r") as file:
                        json_data = json.load(file, object_hook=json_util.object_hook)
                        collection.insert_many(json_data)
                except Exception as e:
                    print(f"导入数据出错：{e}，来自:{json_file}")