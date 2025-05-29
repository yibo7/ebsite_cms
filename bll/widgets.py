from typing import Tuple

import eb_cache
from bll.bll_base import BllBase
from bll.widget_types import WidgetTypeModel
from entity.list_item import ListItem
from entity.widgets_model import WidgetsModel


class Widgets(BllBase[WidgetsModel]):
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
        subclasses = WidgetTypeModel.__subclasses__()

        # 创建一个列表来存储所有子类的实例
        instances = []
        # 遍历所有子类，并为每个子类创建一个实例
        for subclass in subclasses:
            instance = subclass()
            instances.append(instance)
        return instances

        # return [
        #     {'id': 1, 'name': '分类查询部件','temp':'widget_list_save_where.html', 'info': '此部件用来获取分类相关的数据', 'bll': NewsClass()},
        #     {'id': 2, 'name': '内容查询部件','temp':'widget_list_save_where.html', 'info': '获取内容相关的数据', 'bll': NewsContent()},
        #     {'id': 3, 'name': '专题查询部件','temp':'widget_list_save_where.html', 'info': '查询并获取专题相关的数据', 'bll': NewsSpecial()},
        #     {'id': 4, 'name': '用户查询部件','temp':'widget_list_save_where.html', 'info': '查询并获取用户相关的数据', 'bll': User()},
        #     {'id': 5, 'name': '文本框内容','temp':'widget_list_save_text.html', 'info': '简单的文本框输入，并将内容呈现在模板', 'bll':None},
        #     {'id': 6, 'name': 'HTML编辑框','temp':'widget_list_save_html.html', 'info': '可以在线编辑html内容', 'bll':None},
        #     {'id': 7, 'name': '图集模板', 'temp': 'widget_list_save_pic.html', 'info': '通用图集模板，可上传图片并绑定图片列表，可制作幻灯片轮播图。', 'bll': None},
        # ]

    def get_type_by_id(self, data_id: int) -> WidgetTypeModel:
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
