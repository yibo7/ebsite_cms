from flask import render_template_string
from markupsafe import Markup

from bll.content_tags import ContentTags
from entity import tag_model
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class TagByAllWidgetModel(WidgetBase):

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