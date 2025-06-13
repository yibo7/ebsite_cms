from bll.new_class import NewsClass
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class ClassWidgetModel(WidgetBase):

    def __init__(self):
        super().__init__()
        self.id: int = 1
        self.name: str = '分类查询部件'
        # self.temp: str = 'widget_list_save_where.html'
        self.info: str = '此部件用来获取分类相关的数据'

    def temp_hanndler(self, model:WidgetsModel):
        return self.where_hannder(model)

    def bll_hanndler(self):
        return NewsClass()