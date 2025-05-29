import re
from collections import deque
from typing import Tuple, Optional

import pymongo
from bson import ObjectId
from flask import Flask

from bll.bll_base import BllBase
from bll.content_tags import  ContentTags
from eb_utils.configs import SiteConstant
from eb_utils.mvc_pager import pager_html_admin, MvcPager
from entity.news_content_model import NewsContentModel
from signals import content_saving, content_saved


class NewsContent(BllBase[NewsContentModel]):
    def __init__(self, app: Optional[Flask] = None):
        super().__init__(app)
    def new_instance(self) -> NewsContentModel:
        model = NewsContentModel()
        model.column_1 = ''
        model.column_2 = ''
        model.column_3 = ''
        model.column_4 = ''
        model.column_5 = ''
        model.column_6 = ''
        model.column_7 = ''
        model.column_8 = ''
        model.column_9 = ''
        model.column_10 = ''
        model.column_11 = ''
        model.column_12 = ''
        model.column_13 = ''
        model.column_14 = ''
        model.column_15 = ''
        model.column_16 = ''
        model.column_17 = ''
        model.column_18 = ''
        model.column_19 = ''
        model.column_20 = ''
        model.column_21 = ''

        return model

    def get_new_datas(self, class_id: str, top: int) -> list[NewsContentModel]:
        """
        获取最新数据
        :param class_id: 分类ID
        :param top: 最多数据数
        :return:
        """

        s_where = {
            'class_id': class_id
        }

        datas = self.find_list_by_where(s_where, sort_key="_id", sort_direction=pymongo.DESCENDING, limit=top)

        return datas

    def get_hot_datas(self, class_id: str, top: int) -> list[NewsContentModel]:
        """
        获取排行榜数据
        :param class_id: 分类ID
        :param top: 最多数据数
        :return:
        """

        s_where = {
            'class_id': class_id
        }

        datas = self.find_list_by_where(s_where, sort_key="hits", sort_direction=pymongo.DESCENDING, limit=top)

        return datas

    def get_good_datas(self, class_id: str, top: int) -> list[NewsContentModel]:
        """
        获取推荐数据
        :param class_id: 分类ID,如果为None将获取所有数据
        :param top: 最多数据数
        :return:
        """

        s_where = {
            'is_good': True
        }
        if class_id:
            s_where["class_id"] = class_id

        datas = self.find_list_by_where(s_where, sort_key="hits", sort_direction=pymongo.DESCENDING, limit=top)

        return datas

    def search_content(self, keyword: str, class_id: str, page_number: int) -> Tuple[list[NewsContentModel], str]:
        """
        模糊搜索
        :param keyword: 搜索的关键词, 不传入会搜索所有
        :param page_number: 页面码
        :param key_name: 要模糊搜索的字段
        :return:
        """
        # page_size = SiteConstant.PAGE_SIZE_AD
        #
        # s_where = {}
        # if keyword:
        #     regex_pattern = re.compile(f'.*{re.escape(keyword)}.*', re.IGNORECASE)  # IGNORE CASE 忽略大小写
        #     # s_where = {'title': {'$regex': regex_pattern}}
        #     # 构建查询条件
        #     s_where = {
        #         "$or": [
        #             {"title": {"$regex": regex_pattern}},
        #             {"info": {"$regex": regex_pattern}}
        #         ]
        #     }
        #
        # if class_id:
        #     s_where['class_id'] = class_id

        # datas, i_count = self.find_pages(page_number, page_size, s_where)

        datas, i_count = self.search_data(keyword, class_id, page_number)
        page_size = SiteConstant.PAGE_SIZE_AD
        pager = pager_html_admin(i_count, page_number, page_size, {'k': keyword})
        return datas, pager

    def search_data(self, keyword: str, class_id: str, page_number: int) -> Tuple[list[NewsContentModel], int]:
        """
        模糊搜索
        :param keyword: 搜索的关键词, 不传入会搜索所有
        :param page_number: 页面码
        :param class_id: 分类ID
        :return:
        """
        page_size = SiteConstant.PAGE_SIZE_AD

        s_where = {}
        if keyword:
            regex_pattern = re.compile(f'.*{re.escape(keyword)}.*', re.IGNORECASE)  # IGNORE CASE 忽略大小写
            # s_where = {'title': {'$regex': regex_pattern}}
            # 构建查询条件
            s_where = {
                "$or": [
                    {"title": {"$regex": regex_pattern}},
                    {"info": {"$regex": regex_pattern}}
                ]
            }

        if class_id:
            s_where['class_id'] = class_id

        datas, i_count = self.find_pages(page_number, page_size, s_where)
        return datas, i_count

    def get_by_class_id(self, class_id: str, page_number: int) -> Tuple[list[NewsContentModel], int]:
        """
        获取分类下的数据
        @param class_id:
        @param page_number:
        @return:
        """
        s_where = {'class_id':class_id}
        page_size = SiteConstant.PAGE_SIZE_AD
        datas, i_count = self.find_pages(page_number, page_size, s_where)
        return datas, i_count

    def get_by_sub_class_id(self, class_id: int) -> list:
        """
        递归地查找无限级别的子分类下的内容 NewsContent。
        参数：
            bll：业务逻辑层对象，要求有 db 连接；
            class_id：NewsClass 中的 id（整数）；
        返回：
            NewsContent 列表。
        """
        db = self.db
        class_collection = db["NewsClass"]
        content_collection = db["NewsContent"]

        # 1. 先找到对应 class_id 的 _id (ObjectId)
        root_class = class_collection.find_one({"id": class_id}, {"_id": 1, "id": 1})
        if not root_class:
            return []

        root_oid = root_class["_id"]

        # 2. 递归找所有子分类（parent_id 存的是 ObjectId 转字符串）
        all_class_ids = set()
        queue = deque([root_oid])

        while queue:
            current_oid = queue.popleft()

            # 找到 current_oid 对应的分类id
            cls = class_collection.find_one({"_id": current_oid}, {"id": 1})
            if cls and "id" in cls:
                all_class_ids.add(cls["id"])

            # 找子分类，parent_id 存的是父级 _id 的字符串
            children = class_collection.find({"parent_id": str(current_oid)}, {"_id": 1})
            for child in children:
                queue.append(child["_id"])

        if not all_class_ids:
            return []

        # 3. 查询 NewsContent
        contents = list(content_collection.find({
            "class_n_id": {"$in": list(all_class_ids)}
        }))

        return contents

    def get_by_user(self, user_id: str, page_number: int) -> Tuple[list[NewsContentModel], int]:
        """
        模糊搜索
        :param user_id: 用户ID
        :param page_number: 页面码
        :return:数据列表，总共页数
        """
        page_size = SiteConstant.PAGE_SIZE_AD

        s_where = {
            'user_id': ObjectId(user_id)
        }

        datas, i_count = self.find_pages(page_number, page_size, s_where)
        return datas, i_count

    def del_article_by_id(self, _id: str):
        """
        删除指定id的记录
        :param _id: id
        :return:
        """
        article_id = ObjectId(_id)
        # 构建筛选条件
        # 获取文章标签
        article = self.table.find_one(
            {'_id': article_id},
            {'tags': 1}
        )

        if not article:
            return 0

        tags = article.get('tags', [])
        # print("标签"+tags)
        # 减少标签计数
        if tags:
            tag_bll = ContentTags()
            tag_bll.decrement_tags(tags)

        return self.delete_by_id(article_id)

    def delete_from_page2(self, s_id):
        if s_id:
            a_id = s_id.split(',')
            if 'on' in a_id:
                a_id.remove('on')
            for data_id in a_id:
                self.del_article_by_id(data_id)
            # self.delete_by_ids(a_id)

    def save_content(self, model: NewsContentModel):

        results =  content_saving.send(model) # 保存前触发事件
        for receiver, result in results:  # 遍历所有接收者的返回结果
            if not result:
                raise TypeError(f"接收者 {receiver.__name__} 没有返回 (bool,str)类型")
            is_successful, err = result
            if not is_successful:
                raise Exception(f"保存前被接收者 {receiver.__name__} 阻止: {err}")

        if model.title:
            data_id = self.save(model)
            if data_id: # 保存成功触发事件
                model._id = data_id
                content_saved.send(model)
                # 更新标签计数
                if model.tags:
                    tag_bll = ContentTags()
                    # 计算标签变化
                    old_tags = model.old_tags # 如果是新添加的记得，这个值将为空，所以后面计算出来的tags_to_add一般是全部的新标签
                    new_tags = model.tags
                    tags_to_add = list(set(new_tags) - set(old_tags))
                    tags_to_remove = list(set(old_tags) - set(new_tags))
                    # 更新标签计数
                    if tags_to_add:
                        tag_bll.increment_tags(tags_to_add)
                    if tags_to_remove:
                        tag_bll.decrement_tags(tags_to_remove)
        else:
            raise Exception("标题为能为空！")


    def search_full(self, key_word: str, page_number: int, page_size: int,rewrite_rule:str) -> Tuple[list[NewsContentModel], str]:

        # 清理输入
        keyword = self.clean_mongo_search_keywords(key_word)

        # 构建正则查询
        query = {
            "$or": [
                {"title": {"$regex": keyword, "$options": "i"}},  # 忽略大小写
                {"info": {"$regex": keyword, "$options": "i"}}
            ]
        }

        # 获取总数量
        total = self.table.count_documents(query)
        if total == 0:
            return [], ""

        # 获取分页数据
        results = list(self.table.find(query)
                       .skip((page_number - 1) * page_size)
                       .limit(page_size))


        lst = []
        if results:
            for document in results:
                lst.append(self.build_model(document))

        pager = ''
        if total > page_size:
            pg = MvcPager()
            pg.current_page = page_number
            pg.total_count = total
            pg.page_size = page_size
            pg.params = None
            pg.ShowCodeNum = 10
            pg.rewrite_rule = rewrite_rule
            pager = pg.show_pages()

        return lst, pager
