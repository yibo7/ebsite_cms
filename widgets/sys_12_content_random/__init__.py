"""随机查询内容部件 (sys_12)"""
import ast
import random

import pymongo
from flask import render_template_string
from markupsafe import Markup

from bll.new_content import NewsContent
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class ContentWidgetRandom(WidgetBase):
    id = 'sys_12'
    name = '随机查询内容'
    info = '随机查询内容数据'

    def temp_handler(self, model: WidgetsModel):
        s_where = {}
        if model.where_query:
            try:
                s_where = ast.literal_eval(model.where_query)
            except Exception:
                raise Exception(
                    f"部件查询条件错误:{model.where_query}不是python下合法的mongodb语句,来自部件ID:{model._id}")
        r = random.random()
        s_where["rand_num"] = {"$gte": r}
        order_by = model.order_by
        desc_asc = pymongo.DESCENDING if model.order_by_desc == 'DESC' else pymongo.ASCENDING
        int_limit = model.limit

        bll = self.bll_handler()
        data = bll.find_list_by_where(s_where, order_by, desc_asc, int_limit)

        return Markup(render_template_string(model.temp_code, data=data))

    def bll_handler(self):
        return NewsContent()