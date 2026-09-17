"""分类查询部件 (sys_1)"""
from bll.new_class import NewsClass
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class ClassWidget(WidgetBase):
    id = 'sys_1'
    name = '分类查询部件'
    info = '此部件用来获取分类相关的数据'

    def temp_handler(self, model: WidgetsModel):
        return self._render_query(model)

    def bll_handler(self):
        return NewsClass()