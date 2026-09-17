from flask import render_template_string

from model_controls.control_base import ControlBase


class HtmlInput(ControlBase):

    def __init__(self):
        super().__init__()
        self.id: str = 'sys_3'
        self.name: str = '富文本编辑框-Quill'
        self.info: str = '富文本编辑框（基于 Quill v2）'

    def get_control_temp(self, field_model: dict) -> str:
        show_name = field_model.get('show_name')
        name = field_model.get('name')

        # control_size: 1=simple, 2=standard(默认), 3=powerful
        control_size = field_model.get('control_size', 2)
        try:
            control_size = int(control_size)
        except (ValueError, TypeError):
            control_size = 2

        mode_map = {1: 'simple', 2: 'standard', 3: 'powerful'}
        mode = mode_map.get(control_size, 'standard')

        # 用占位符渲染宏，后续替换为 CMS 模板变量语法 [[model.{name}|safe]]
        placeholder = f'__MODEL_VAL_{name}__'
        macro_html = render_template_string(
            '{% from "jinja2_ctrs/_quill_macro.html" import quill_editor %}'
            '{{ quill_editor(name, content, "300px", "请输入内容...", mode) }}',
            name=name,
            content=placeholder,
            mode=mode
        )

        # 用 CMS 模板变量替换占位符，注意 |tojson 已自带双引号，无需再加
        # 注：[[…]] 会被 site_model.py 替换为 {{…}} 后再 Jinja2 渲染
        #     tojson 会正确转义内容中的引号、换行等特殊字符
        macro_html = macro_html.replace(
            f'"{placeholder}"',
            f'[[model.{name}|tojson]]'
        )

        return f'''<div class="mb-3">
    <label>{show_name}</label>
    {macro_html}
</div>'''