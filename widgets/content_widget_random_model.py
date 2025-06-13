import ast
import random

import pymongo
from flask import render_template_string
from markupsafe import Markup

from bll.new_content import NewsContent
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class ContentWidgetRandomModel(WidgetBase):

    def __init__(self):
        super().__init__()
        self.id: int = 12
        self.name: str = '随机查询内容'
        # self.temp: str = 'widget_list_save_where.html'
        self.info: str = '随机查询内容数据'

    def temp_hanndler(self, model:WidgetsModel):
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

        bll = self.bll_hanndler()  # get_type_by_id(model.temp_type).get('bll')

        data = bll.find_list_by_where(s_where, order_by, desc_asc, int_limit)

        return Markup(render_template_string(model.temp_code, data=data))


    def bll_hanndler(self):
        return NewsContent()