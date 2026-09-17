"""用户查询部件 (sys_4)"""
from bll.user import User
from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class UserWidget(WidgetBase):
    id = 'sys_4'
    name = '用户查询部件'
    info = '查询并获取用户相关的数据'

    def temp_handler(self, model: WidgetsModel):
        return self._render_query(model)

    def bll_handler(self):
        return User()