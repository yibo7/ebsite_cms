import ast

from flask import render_template_string, request
from markupsafe import Markup

import eb_utils
from bll import content_tags
from bll.new_class import NewsClass
from bll.new_content import NewsContent
from bll.new_special import NewsSpecial
from bll.content_tags import ContentTags
from bll.user import User
from bll.widget_type_model import WidgetTypeModel
from eb_utils import http_helper
from entity import tag_model
from entity.widgets_model import WidgetsModel


class ClassWidgetModel(WidgetTypeModel):

    def __init__(self):
        super().__init__()
        self.id: int = 1
        self.name: str = '分类查询部件'
        # self.temp: str = 'widget_list_save_where.html'
        self.info: str = '此部件用来获取分类相关的数据'

    def temp_hanndler(self, model:WidgetsModel):
        return self.where_hannder(model)

    def bll_hanndler(self):
        return NewsClass()


class ContentWidgetModel(WidgetTypeModel):

    def __init__(self):
        super().__init__()
        self.id: int = 2
        self.name: str = '内容查询部件'
        # self.temp: str = 'widget_list_save_where.html'
        self.info: str = '获取内容相关的数据'

    def temp_hanndler(self, model:WidgetsModel):
        return self.where_hannder(model)

    def bll_hanndler(self):
        return NewsContent()


class SpecialWidgetModel(WidgetTypeModel):

    def __init__(self):
        super().__init__()
        self.id: int = 3
        self.name: str = '专题查询部件'
        # self.temp: str = 'widget_list_save_where.html'
        self.info: str = '查询并获取专题相关的数据'

    def temp_hanndler(self, model:WidgetsModel):
        return self.where_hannder(model)

    def bll_hanndler(self):
        return NewsSpecial()


class UserWidgetModel(WidgetTypeModel):

    def __init__(self):
        super().__init__()
        self.id: int = 4
        self.name: str = '用户查询部件'
        # self.temp: str = 'widget_list_save_where.html'
        self.info: str = '查询并获取专题相关的数据'

    def temp_hanndler(self, model:WidgetsModel):
        return self.where_hannder(model)

    def bll_hanndler(self):
        return User()

class TextBoxWidgetModel(WidgetTypeModel):

    def __init__(self):
        super().__init__()
        self.id: int = 5
        self.name: str = '文本框内容'
        self.temp: str = 'widget_list_save_text.html'
        self.info: str = '简单的文本框输入，并将内容呈现在模板'

    def temp_hanndler(self, model:WidgetsModel):
        return model.temp_code


class HtmlBoxWidgetModel(WidgetTypeModel):

    def __init__(self):
        super().__init__()
        self.id: int = 6
        self.name: str = 'HTML编辑框'
        self.temp: str = 'widget_list_save_html.html'
        self.info: str = '可以在线编辑html内容'

    def temp_hanndler(self, model:WidgetsModel):
        return Markup(model.temp_code)

class PicBoxWidgetModel(WidgetTypeModel):

    def __init__(self):
        super().__init__()
        self.id: int = 7
        self.name: str = '图集模板'
        self.temp: str = 'widget_list_save_pic.html'
        self.info: str = '通用图集模板，可上传图片并绑定图片列表，可制作幻灯片轮播图。'

    def temp_hanndler(self, model:WidgetsModel):
        if model.info:
            pics = model.info.split(',')
            return Markup(render_template_string(model.temp_code, data=pics))
        return '还没上传图片'


# class ClassContentWidgetModel(WidgetTypeModel):
#
#     def __init__(self):
#         super().__init__()
#         self.id: int = 8
#         self.name: str = '分类内容查询部件'
#         self.temp: str = 'widget_list_save_class_content.html'
#         self.info: str = '此部件用来获取分类及分类下的内容'
#
#
#     def bll_hanndler(self):
#         return NewsClass()
#
#     def saving(self, model: WidgetsModel):
#         limit2 = http_helper.get_prams_int("limit2")
#         order_by2 = http_helper.get_prams("order_by2")
#         order_by_desc2 = http_helper.get_prams("order_by_desc2")
#         model.other = {
#             "limit":limit2,
#             "order_by":order_by2,
#             "order_by_desc":order_by_desc2
#         }
#
#     def temp_hanndler(self, model:WidgetsModel):
#
#         bll = self.bll_hanndler()
#
#         s_where = {}
#         if model.where_query:
#             try:
#                 s_where = ast.literal_eval(model.where_query)
#             except Exception:
#                 raise Exception(f"部件查询条件错误:{model.where_query}不是python下合法的mongodb语句,来自部件ID:{model._id}")
#         order_by_class = -1 if model.order_by_desc == 'DESC' else 1
#         limit_class = model.limit
#
#         order_by_content = -1 if model.other["order_by_desc"] == 'DESC' else 1
#         limit_content = model.other["limit"]
#
#         # 定义聚合管道
#         pipeline = [
#             {
#                 '$match': s_where
#             },
#             {
#                 '$sort': {
#                     '_id': order_by_class  # 按 _id 降序排序
#                 }
#             },
#             {
#                 '$limit': limit_class
#             },
#             {
#                 '$lookup': {
#                     'from': 'NewsContent',
#                     'let': {'class_n_id': '$id'},
#                     'pipeline': [
#                         {
#                             '$match': {
#                                 '$expr': {'$eq': ['$class_n_id', '$$class_n_id']}
#                             }
#                         },
#                         {
#                             '$sort': {'_id': order_by_content}  # 对 news_content 按 _id 降序排序
#                         },
#                         {
#                             '$limit': limit_content  # 限制到前 10 条记录
#                         }
#                     ],
#                     'as': 'news_content'
#                 }
#             }
#         ]
#
#         # 执行聚合操作并获取结果
#         result = list(bll.table.aggregate(pipeline))
#         # print(result)
#
#         return Markup(render_template_string(model.temp_code, data=result))


class TagByClassWidgetModel(WidgetTypeModel):

    def __init__(self):
        super().__init__()
        self.id: int = 9
        self.name: str = '查询分类标签'
        self.temp: str = 'widget_list_save_tag_class.html'
        self.info: str = '查询指定分类ID下的所有标签'

    def saving(self, model: WidgetsModel):
        class_ids = http_helper.get_prams("class_ids")
        model.other = {
            "class_ids":class_ids
        }

    def temp_hanndler(self, model:WidgetsModel):
        bll = self.bll_hanndler()
        class_id_str = model.other["class_ids"]
        if class_id_str == "0":
            class_id_str = str(request.view_args.get('id')) # 自动适应ID

        class_ids = [int(cid.strip()) for cid in class_id_str.split(",") if cid.strip()]

        limit = model.limit
        order_by = model.order_by
        order_type = -1 if model.order_by_desc == 'DESC' else 1

        pipeline = [
            {"$match": {"class_n_id": {"$in": class_ids}}},
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags"}},
            {"$sort": {order_by: order_type}},  # 按标签名称升序排序
            {"$limit": limit},  # 只取前 10 条
            {"$project": {"_id": 0, "tag": "$_id"}}
        ]

        cursor = bll.table.aggregate(pipeline)
        tag_list = [
            {
                "name": doc["tag"],
                "url": tag_model.get_tag_page_link(doc["tag"])
            }
            for doc in cursor
        ]
        return Markup(render_template_string(model.temp_code, data=tag_list))

    def bll_hanndler(self):
        return NewsContent()

class TagByAllWidgetModel(WidgetTypeModel):

    def __init__(self):
        super().__init__()
        self.id: int = 11
        self.name: str = '查询所有标签'
        self.temp: str = 'widget_list_save_tag_all.html'
        self.info: str = '查询标签库所有的数据，但可指定查询条数'


    def temp_hanndler(self, model: WidgetsModel):
        bll = self.bll_hanndler()
        limit = model.limit
        order_by = model.order_by
        order_type = -1 if model.order_by_desc == 'DESC' else 1
        query_filter = {"article_count": {"$gt": 0}} # 查询文章数大于0的标签
        cursor = bll.table.find(query_filter).sort(order_by, order_type).limit(limit)

        tag_list = [
            {
                "name": doc["name"],
                "count": doc["article_count"],
                "url": tag_model.get_tag_page_link(doc["name"])
            }
            for doc in cursor
        ]

        return Markup(render_template_string(model.temp_code, data=tag_list))

    def bll_hanndler(self):
        return ContentTags()

# class TagByContentWidgetModel(WidgetTypeModel):
#
#     def __init__(self):
#         super().__init__()
#         self.id: int = 10
#         self.name: str = '查询内容标签'
#         self.temp: str = 'widget_list_save_tag_content.html'
#         self.info: str = '自动适应内容标签，只适用于内容模板'
#
#
#     def temp_hanndler(self, model: WidgetsModel):
#         bll = self.bll_hanndler()
#         content_id = request.view_args.get('id')
#         doc = bll.table.find_one({"id": content_id}, {"tags": 1})
#         if not doc or "tags" not in doc:
#             return []
#         limit = model.limit
#         tag_list = [
#             {
#                 "name": tag,
#                 "url": tag_model.get_tag_page_link(tag)
#             }
#             for tag in doc["tags"][:limit]
#         ]
#         return Markup(render_template_string(model.temp_code, data=tag_list))
#
#     def bll_hanndler(self):
#         return NewsContent()

