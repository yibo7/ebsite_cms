"""内容查询部件 (sys_2)"""
from bll.new_content import NewsContent
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class ContentWidget(WidgetBase):
    id = 'sys_2'
    name = '内容查询部件'
    info = '获取内容相关的数据'

    def temp_handler(self, model: WidgetsModel):
        return self._render_query(model)

    def bll_handler(self):
        return NewsContent()