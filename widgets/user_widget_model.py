from bll.user import User
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class UserWidgetModel(WidgetBase):

    def __init__(self):
        super().__init__()
        self.id: int = 4
        self.name: str = '用户查询部件'
        # self.temp: str = 'widget_list_save_where.html'
        self.info: str = '查询并获取专题相关的数据'

    def temp_hanndler(self, model:WidgetsModel):
        return self.where_hannder(model)

    def bll_hanndler(self):
        return User()