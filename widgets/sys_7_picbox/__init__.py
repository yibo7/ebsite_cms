"""图集模板部件 (sys_7)"""
from flask import render_template_string
from markupsafe import Markup

from entity.widgets_model import WidgetsModel
from widgets.widget_base import WidgetBase


class PicBoxWidget(WidgetBase):
    id = 'sys_7'
    name = '图集模板'
    info = '通用图集模板，可上传图片并绑定图片列表，可制作幻灯片轮播图。'

    def temp_handler(self, model: WidgetsModel):
        if model.info:
            pics = model.info.split(',')
            return Markup(render_template_string(model.temp_code, data=pics))
        return '还没上传图片'