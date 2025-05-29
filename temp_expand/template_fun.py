"""
Custom global functions can be called in templates using the following method：
{{say_hello('cqs')}}
"""
from bson import ObjectId
from markupsafe import Markup

from bll.new_class import NewsClass
from bll.new_content import NewsContent
from bll.widgets import Widgets
from eb_utils import url_links
from entity.select_opt import SelectItem


def reg_temp_expand_fun(app):
    @app.template_global()
    def say_hello(msg: str):
        return Markup(f'<h1>你好呀:{msg}</h1>')

    @app.template_global()
    def get_class_link(cid: int):
        return url_links.get_class_url(cid)

    @app.template_global()
    def get_content_link(dataid: int):
        return url_links.get_content_url(dataid)

    @app.template_global()
    def build_sel_item(datas, value_key: str, name_key: str, sel_value: str):
        select_html = []
        for data in datas:
            name = 'none'
            value = 'none'
            # 检查 data 是字典还是类实例
            if isinstance(data, dict):
                # 如果是字典，使用 get 方法来获取值，如果键不存在则返回 'none'
                name = data.get(name_key, 'none')
                value = data.get(value_key, 'none')
            elif hasattr(data, name_key) and hasattr(data, value_key):
                # 如果是类实例，使用 getattr 方法来获取属性值
                name = getattr(data, name_key)
                value = getattr(data, value_key)
            else:
                # 如果 data 既不是字典也不是类实例，或者缺少必要的键/属性，跳过这个数据项
                continue


            if str(value) == str(sel_value):
                select_html.append(f'<option selected value="{value}">{name}</option>')
            else:
                select_html.append(f'<option  value="{value}">{name}</option>')

        return Markup(''.join(select_html))

    @app.template_global()
    def widget(data_id: str):
        return Widgets().get_content(data_id)

    @app.template_global()
    def get_sub_class(pid: str):
        return NewsClass().get_by_pid(pid)

    @app.template_global()
    def get_sub_content(class_id: int):
        datas = NewsContent().get_by_sub_class_id(class_id)
        # print(f"{class_id}:{len(datas)}")
        return datas