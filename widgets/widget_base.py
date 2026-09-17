"""
部件抽象基类。

设计原则：
  - 每个部件是一个自包含的文件夹，包含 __init__.py 和 admin.html
  - ID 采用字符串格式：模块名_序号（如 sys_1、shop_1）
  - 继承该类时会通过 __init_subclass__ 自动注册到发现引擎
"""

import ast
import sys
import warnings
from abc import ABC, abstractmethod
from pathlib import Path

import pymongo
from flask import render_template_string
from markupsafe import Markup

from bll.widget_discover import register
from entity.widgets_model import WidgetsModel


class WidgetBase(ABC):
    """部件抽象基类。

    子类只需声明类属性 id（字符串格式），其余自动推导。
    每个子类应放在独立的文件夹中，同目录下放置 admin.html。
    """

    # ── 子类必须定义 ──────────────────────────────────────
    id: str = ''          # 字符串 ID，如 'sys_1', 'shop_1'
    name: str = ''        # 中文名称，如 '分类查询部件'
    info: str = ''        # 描述说明

    def __init_subclass__(cls, **kwargs):
        """子类定义时自动注册到发现引擎。"""
        super().__init_subclass__(**kwargs)
        if cls.id:
            register(cls)

    # ── 模板管理 ──────────────────────────────────────────

    # 通用表单骨架：extends base_admin + 表单结构 + 缓存/保存等通用字段
    # <!-- FORMTIP --> 可被子类 admin.html 第一行替换以自定义提示文字
    # <!-- BODY -->   被子类的特有字段替换
    _FORM_SKELETON = """\
{% extends 'base_admin.html' %}
{% block content %}
<div class="row eb-box">
    <div class="col-sm-12 col-md-12 ">
        <div class="block-flat">
            <div class="boxheader">
                <h3>添加或修改部件</h3>
            </div>
            <div class="content">
                <form method="post">
                    <div class="mb-3">
                        <label>部件名称</label>
                        <input name="name" value="{{model.name}}" style="max-width:300px" class="form-control" required>
                    </div>
<!-- BODY -->
                    <div class="mb-3">
                        <label>缓存时间(秒)</label>
                        <input name="cache_time" value="{{model.cache_time}}" style="max-width:100px" type="number" class="form-control" required>
                    </div>
<!-- FORMTIP -->
                    <input hidden value="{{model._id}}" name="_id" >
                    <input hidden value="{{model.temp_type}}" name="temp_type" >
                    <button class="btn btn-primary mb-3" type="submit">   保  存   </button>
                    {% if err %}
                        <div class="alert alert-danger">{{ err }}</div>
                    {% endif %}
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

    # 默认表单提示
    _DEFAULT_FORM_TIP = '<div class="tips">默认0表示不缓存，缓存可减少部件模板渲染处理频率。</div>'

    @classmethod
    def get_admin_html(cls) -> str:
        """读取同目录下的 admin.html 作为部件特有配置字段，
        并自动包裹通用表单骨架（extends、缓存设置、保存按钮等）。

        admin.html 中只放部件特有的表单字段 HTML 片段即可，
        无需写 {% extends %}、form 标签、缓存、保存按钮等重复代码。
        如果第一行以 <!-- tip: 开头，会替换默认的提示文字。
        """
        module = sys.modules.get(cls.__module__)
        if not module or not hasattr(module, '__file__') or not module.__file__:
            return ''

        body_file = Path(module.__file__).parent / 'admin.html'
        if not body_file.exists():
            return ''

        body = body_file.read_text(encoding='utf-8')

        # 提取自定义提示（如 <!-- tip: 自定义提示文字 -->）
        form_tip = cls._DEFAULT_FORM_TIP
        if body.startswith('<!-- tip:'):
            end_idx = body.find('-->')
            if end_idx != -1:
                form_tip = body[4:end_idx].strip()
                body = body[end_idx + 3:].lstrip()

        result = cls._FORM_SKELETON.replace('<!-- BODY -->', body)
        result = result.replace('<!-- FORMTIP -->', form_tip)
        return result

    # ── 前台渲染接口 ──────────────────────────────────────

    @abstractmethod
    def temp_handler(self, model: WidgetsModel) -> Markup:
        """【必须实现】模板数据处理，返回渲染后的 HTML。"""
        ...

    # ── 可选的钩子方法 ────────────────────────────────────

    def saving(self, model: WidgetsModel):
        """保存前回调，可用于从请求中提取额外参数存入 model。"""
        pass

    def bll_handler(self):
        """返回业务层对象，供 _render_query 使用。"""
        return None

    # ── 通用查询渲染 ──────────────────────────────────────

    def _render_query(self, model: WidgetsModel) -> Markup:
        """基于 MongoDB 条件查询的通用渲染方法。

        从 model.where_query 中解析查询条件，
        配合 order_by / limit 等参数调用 BLL 查询后渲染。
        """
        s_where = self._parse_where_query(model)
        order_by = model.order_by
        desc_asc = pymongo.DESCENDING if model.order_by_desc == 'DESC' else pymongo.ASCENDING
        int_limit = model.limit

        bll = self.bll_handler()
        data = bll.find_list_by_where(s_where, order_by, desc_asc, int_limit)

        if not data:
            return Markup('')

        return Markup(render_template_string(model.temp_code, data=data))

    def _parse_where_query(self, model: WidgetsModel) -> dict:
        """安全解析 model.where_query（JSON / Python 字典语法）。"""
        if not model.where_query:
            return {}
        try:
            import json
            return json.loads(model.where_query)
        except (json.JSONDecodeError, ValueError):
            pass
        try:
            result = ast.literal_eval(model.where_query)
            if isinstance(result, dict):
                return result
        except Exception:
            pass
        raise ValueError(
            f"部件查询条件解析失败 (部件ID: {model._id})。"
            f"请使用 JSON 格式，例如: {{\"status\": 1}}"
        )

    # ── 向后兼容（旧方法名重定向） ────────────────────────

    def temp_hanndler(self, model: WidgetsModel) -> Markup:
        """已废弃，请使用 temp_handler。"""
        warnings.warn("temp_hanndler 已废弃，请改为 temp_handler", DeprecationWarning, stacklevel=2)
        return self.temp_handler(model)

    def bll_hanndler(self):
        """已废弃，请使用 bll_handler。"""
        warnings.warn("bll_hanndler 已废弃，请改为 bll_handler", DeprecationWarning, stacklevel=2)
        return self.bll_handler()

    def where_hannder(self, model: WidgetsModel) -> Markup:
        """已废弃，请使用 _render_query。"""
        warnings.warn("where_hannder 已废弃，请改为 _render_query", DeprecationWarning, stacklevel=2)
        return self._render_query(model)