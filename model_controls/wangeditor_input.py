# from flask import render_template_string
#
# from model_controls.control_base import ControlBase
#
#
# class WangeditorInput(ControlBase):
#
#     def __init__(self):
#         super().__init__()
#         self.id: str = 'sys_10'
#         self.name: str = '富文本编辑框（wangEditor）'
#         self.info: str = '富文本编辑框（基于 wangEditor-next v6）'
#
#     def get_control_temp(self, field_model: dict) -> str:
#         show_name = field_model.get('show_name')
#         name = field_model.get('name')
#
#         # control_size: 编辑器高度，默认 500px
#         control_size = field_model.get('control_size', '500px')
#         height = f'{control_size}px' if str(control_size).isdigit() else str(control_size)
#
#         # 用占位符渲染宏，后续替换为 CMS 模板变量语法 [[model.{name}|tojson]]
#         placeholder = f'__MODEL_VAL_{name}__'
#         macro_html = render_template_string(
#             '{% from "jinja2_ctrs/_wangeditor_macro.html" import wangeditor_editor %}'
#             '{{ wangeditor_editor(name, content, height, "请输入内容...") }}',
#             name=name,
#             content=placeholder,
#             height=height
#         )
#
#         # 用 CMS 模板变量替换占位符，|tojson 已自带双引号，无需再加
#         # 注：[[…]] 会被 site_model.py 替换为 {{…}} 后再 Jinja2 渲染
#         #     tojson 会正确转义内容中的引号、换行等特殊字符
#         macro_html = macro_html.replace(
#             f'"{placeholder}"',
#             f'[[model.{name}|tojson]]'
#         )
#
#         return f'''<div class="mb-3">
#     <label>{show_name}</label>
#     {macro_html}
# </div>'''