from bll.new_special import NewsSpecial
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class SpecialWidgetModel(WidgetBase):

    def __init__(self):
        super().__init__()
        self.id: int = 3
        self.name: str = '专题查询部件'
        # self.temp: str = 'widget_list_save_where.html'
        self.info: str = '查询并获取专题相关的数据'

    def temp_hanndler(self, model:WidgetsModel):
        return self.where_hannder(model)

    def bll_hanndler(self):
        return NewsSpecial()