from bll.new_content import NewsContent
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class ContentWidgetModel(WidgetBase):

    def __init__(self):
        super().__init__()
        self.id: int = 2
        self.name: str = '内容查询部件'
        # self.temp: str = 'widget_list_save_where.html'
        self.info: str = '获取内容相关的数据'

    def temp_hanndler(self, model:WidgetsModel):
        return self.where_hannder(model)

    def bll_hanndler(self):
        return NewsContent()