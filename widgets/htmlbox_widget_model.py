from markupsafe import Markup

from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class HtmlBoxWidgetModel(WidgetBase):

    def __init__(self):
        super().__init__()
        self.id: int = 6
        self.name: str = 'HTML编辑框'
        self.temp: str = 'widget_list_save_html.html'
        self.info: str = '可以在线编辑html内容'

    def temp_hanndler(self, model:WidgetsModel):
        return Markup(model.temp_code)