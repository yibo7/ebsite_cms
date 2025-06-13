from flask import request, render_template_string
from markupsafe import Markup

from bll.new_content import NewsContent
from eb_utils import http_helper
from entity import tag_model
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class TagByClassWidgetModel(WidgetBase):

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