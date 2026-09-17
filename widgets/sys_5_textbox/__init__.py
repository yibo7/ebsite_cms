"""文本框内容部件 (sys_5)"""
from markupsafe import Markup

from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class TextBoxWidget(WidgetBase):
    id = 'sys_5'
    name = '文本框内容'
    info = '简单的文本框输入，并将内容呈现在模板'

    def temp_handler(self, model: WidgetsModel):
        return model.temp_code