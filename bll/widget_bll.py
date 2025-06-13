import re
from typing import Tuple

from bson import ObjectId

import eb_cache
from bll.bll_base import BllBase
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
                data_key = f'widget_code_{_id}'
                temp_code = eb_cache.get(data_key)

                if not temp_code:
                    widget_type_model = self.get_type_by_id(model.temp_type)
                    temp_code = widget_type_model.temp_hanndler(model)
                    eb_cache.set_data(temp_code, model.cache_time, data_key)

            else:

                widget_type_model = self.get_type_by_id(model.temp_type)
                temp_code = widget_type_model.temp_hanndler(model)

            return temp_code or ''

        return 'err widget data'


    def get_types(self):
        """
        获取所有部件类型，采用反射比较占用性能，如果前端经常调用考虑缓存，不过目前调用频率不高
        :return:
        """
        # 通过反射获取获取直接子类，应该采用缓存
        subclasses = WidgetBase.__subclasses__()

        # 创建一个列表来存储所有子类的实例
        instances = []
        # 遍历所有子类，并为每个子类创建一个实例
        for subclass in subclasses:
            instance = subclass()
            instances.append(instance)
        return instances


    def get_type_by_id(self, data_id: int) -> WidgetBase:
        """
        调用某个部件类型，前端调用频率高，所以采用缓存，减少对get_types的调用
        :param data_id:
        :return:
        """
        data_key = f'get_type_by_id_{data_id}'
        record = eb_cache.get(data_key)
        if not record:
            wg_types = self.get_types()
            record = next((item for item in wg_types if item.id == data_id), None)
            eb_cache.set_data(record,0,data_key)  # 永久缓存
            # print(f'永久缓存：{data_key}')
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