"""专题查询部件 (sys_3)"""
from bll.new_special import NewsSpecial
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class SpecialWidget(WidgetBase):
    id = 'sys_3'
    name = '专题查询部件'
    info = '查询并获取专题相关的数据'

    def temp_handler(self, model: WidgetsModel):
        return self._render_query(model)

    def bll_handler(self):
        return NewsSpecial()