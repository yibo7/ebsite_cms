import re
from typing import Tuple
from flask import g

from bson import ObjectId

import eb_cache
from bll.bll_base import BllBase
from bll.widget_discover import get_widget, get_all_widgets
from eb_utils.configs import SiteConstant
from eb_utils.mvc_pager import pager_html_admin
from entity.list_item import ListItem
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class WidgetBll(BllBase[WidgetsModel]):
    table_name = "Widgets" # rename for table
    def new_instance(self) -> WidgetsModel:
        return WidgetsModel()

    def get_desc_asc(self):
        lst = [ListItem(value='DESC', name='DESC'), ListItem(value='ASC', name='ASC')]
        return lst

    def get_content(self, _id: str) -> str:
        model = self.find_one_by_id(_id)
        if model:
            if model.cache_time > 0:  # 需要缓存处理
                lang = getattr(g, 'lang', 'zh')
                data_key = f'widget_code_{lang}_{_id}'
                temp_code = eb_cache.get(data_key)

                if not temp_code:
                    widget_type_model = self.get_type_by_id(model.temp_type)
                    temp_code = widget_type_model.temp_handler(model)
                    eb_cache.set_data(temp_code, model.cache_time, data_key)

            else:

                widget_type_model = self.get_type_by_id(model.temp_type)
                temp_code = widget_type_model.temp_handler(model)

            return temp_code or ''

        return 'err widget data'


    def get_types(self):
        """
        获取所有部件类型，通过注册表获取，无需反射。
        :return:
        """
        return get_all_widgets()


    def get_type_by_id(self, data_id: int | str) -> WidgetBase:
        """
        调用某个部件类型，前端调用频率高，所以采用缓存，减少重复查找。
        :param data_id: 部件 ID（字符串格式 sys_1 或旧 int 格式 1）
        :return:
        """
        data_key = f'get_type_by_id_{data_id}'
        record = eb_cache.get(data_key)
        if not record:
            record = get_widget(data_id)
            eb_cache.set_data(record, 0, data_key)  # 永久缓存
        return record


    def search_data(self, keyword: str, page_number: int) -> Tuple[list[WidgetsModel], int]:
        page_size = SiteConstant.PAGE_SIZE_AD
        s_where = {}

        if keyword:
            regex_pattern = re.compile(f'.*{re.escape(keyword)}.*', re.IGNORECASE)
            or_conditions = [{"name": {"$regex": regex_pattern}}]

            # 如果 keyword 可能是合法的 ObjectId，则添加一个直接匹配的条件
            try:
                object_id = ObjectId(keyword)
                or_conditions.append({"_id": object_id})
            except Exception:
                pass  # 不是合法 ObjectId 就忽略这个条件

            s_where = {"$or": or_conditions}

        datas, i_count = self.find_pages(page_number, page_size, s_where)
        pager = pager_html_admin(i_count, page_number, page_size, {'k': keyword})
        return datas, pager