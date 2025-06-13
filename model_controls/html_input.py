from model_controls.control_base import ControlBase


class HtmlInput(ControlBase):

    def __init__(self):
        super().__init__()
        self.id: int = 3
        self.name: str = '富文本编辑框'
        self.info: str = '富文本编辑框'

    def get_control_temp(self, field_model: dict) -> str:
        show_name = field_model.get('show_name')
        name = field_model.get('name')
        temp = ('<div class="mb-3">'
                              f'<label>{show_name}</label>'
                              f'<script type="text/plain" id="{name}" name="{name}" style="width:100%;height:100%;">[[model.{name}|safe]]</script>'
                              f'<script>var um = UM.getEditor("{name}");</script>'
                              '</div>')
        return temp