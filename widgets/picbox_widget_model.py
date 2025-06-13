from flask import render_template_string
from markupsafe import Markup

from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class PicBoxWidgetModel(WidgetBase):

    def __init__(self):
        super().__init__()
        self.id: int = 7
        self.name: str = '图集模板'
        self.temp: str = 'widget_list_save_pic.html'
        self.info: str = '通用图集模板，可上传图片并绑定图片列表，可制作幻灯片轮播图。'

    def temp_hanndler(self, model:WidgetsModel):
        if model.info:
            pics = model.info.split(',')
            return Markup(render_template_string(model.temp_code, data=pics))
        return '还没上传图片'