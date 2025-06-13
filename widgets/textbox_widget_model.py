from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class TextBoxWidgetModel(WidgetBase):

    def __init__(self):
        super().__init__()
        self.id: int = 5
        self.name: str = '文本框内容'
        self.temp: str = 'widget_list_save_text.html'
        self.info: str = '简单的文本框输入，并将内容呈现在模板'

    def temp_hanndler(self, model:WidgetsModel):
        return model.temp_code