"""查询分类标签部件 (sys_9)"""
from flask import request, render_template_string
from markupsafe import Markup

import eb_cache
from bll.new_content import NewsContent
from eb_utils import http_helper
from entity import tag_model
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class TagByClassWidget(WidgetBase):
    id = 'sys_9'
    name = '查询分类标签'
    info = '查询指定分类ID下的所有标签'

    def saving(self, model: WidgetsModel):
        class_ids = http_helper.get_prams("class_ids")
        model.other = {
            "class_ids": class_ids
        }

    def temp_handler(self, model: WidgetsModel):
        class_id_str = model.other.get("class_ids", "0")
        if not class_id_str or class_id_str in ("0", "None"):
            class_id_str = str(request.view_args.get('id', '0'))

        class_ids = [int(cid.strip()) for cid in class_id_str.split(",")
                     if cid.strip() and cid.strip() not in ("None", "")]
        class_ids.sort()

        limit = model.limit
        order_by = model.order_by
        order_type = -1 if model.order_by_desc == 'DESC' else 1

        cache_key = f"tag_agg_cache:{model._id}:{class_id_str}:{limit}:{order_by}:{order_type}"
        tag_list = eb_cache.get(cache_key)
        if tag_list is not None:
            return Markup(render_template_string(model.temp_code, data=tag_list))

        bll = self.bll_handler()
        pipeline = [
            {"$match": {"class_n_id": {"$in": class_ids}}},
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags"}},
            {"$sort": {order_by: order_type}},
            {"$limit": limit},
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

        eb_cache.set_data(tag_list, ex_second=300, key=cache_key)

        rendered = render_template_string(model.temp_code, data=tag_list)
        return Markup(rendered)

    def bll_handler(self):
        return NewsContent()