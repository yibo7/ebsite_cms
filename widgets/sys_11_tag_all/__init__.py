"""查询所有标签部件 (sys_11)"""
from flask import render_template_string
from markupsafe import Markup

from bll.content_tags import ContentTags
from entity import tag_model
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class TagByAllWidget(WidgetBase):
    id = 'sys_11'
    name = '查询所有标签'
    info = '查询标签库所有的数据，但可指定查询条数'

    def temp_handler(self, model: WidgetsModel):
        bll = self.bll_handler()
        limit = model.limit
        order_by = model.order_by
        order_type = -1 if model.order_by_desc == 'DESC' else 1
        query_filter = {"article_count": {"$gt": 0}}
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

    def bll_handler(self):
        return ContentTags()