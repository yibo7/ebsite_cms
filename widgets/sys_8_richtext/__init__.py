"""富文本编辑部件 (sys_8)"""
from markupsafe import Markup

from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class RichTextWidget(WidgetBase):
    id = 'sys_8'
    name = '富文本编辑框'
    info = 'WYSIWYG 富文本编辑器，可在线编辑图文内容'

    def temp_handler(self, model: WidgetsModel):
        return Markup(model.temp_code)