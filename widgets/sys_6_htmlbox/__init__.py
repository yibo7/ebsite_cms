"""HTML编辑框部件 (sys_6)"""
from markupsafe import Markup

from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class HtmlBoxWidget(WidgetBase):
    id = 'sys_6'
    name = 'HTML编辑框'
    info = '可以在线编辑html内容'

    def temp_handler(self, model: WidgetsModel):
        return Markup(model.temp_code)