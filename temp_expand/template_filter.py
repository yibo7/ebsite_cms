"""
Custom filters, such as the "to_str" function, can be called in templates using the following method：
{% if item.get("_id")|to_str == model.reg_group_id %}
"""
from datetime import datetime
from functools import lru_cache

from bll.user_group import UserGroup 

from bll.widget_bll import WidgetBll


def reg_temp_expand_filter(app):
    @app.template_filter()
    def to_str(value):
        return str(value)

    @app.template_filter()
    @lru_cache(maxsize=256)
    def to_user_group_name(gid):
        model = UserGroup().find_one_by_id(gid)
        if model:
            return model.name
        return '不存在'

    @app.template_filter()
    def to_bool_name(truefalse):
        """把字段值渲染成“是 / 否”。

        同一个字段在不同数据里可能是布尔值 True/False、字符串 'true'/'false'
        或 0/1（历史数据、表单提交、模型控件各不一致），因此这里统一兼容，
        避免出现 "'bool' object has no attribute 'lower'" 之类的报错。
        """
        if isinstance(truefalse, str):
            return '是' if truefalse.strip().lower() in ('true', '1', 'yes') else '否'
        return '是' if truefalse else '否'

    @app.template_filter()
    def adminer_status(truefalse: int):
        if truefalse == 1:
            return '正常'
        else:
            return '不正常'

    @app.template_filter()
    @lru_cache(maxsize=256)
    def widget_type_name(data_id):
        t = WidgetBll().get_type_by_id(data_id)
        if t:
            return t.name
        return 'can`t find type'

    @app.template_filter()
    def to_time_name(timestamp):
        dt = datetime.fromtimestamp(float(timestamp))
        formatted_time = dt.strftime("%Y-%m-%d %H:%M")
        return formatted_time
