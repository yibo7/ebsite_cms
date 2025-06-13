from model_controls.control_base import ControlBase


class MultilineInput(ControlBase):

    def __init__(self):
        super().__init__()
        self.id: int = 2
        self.name: str = '多行文本输入框'
        self.info: str = '简单多行文本输入框'

    def get_control_temp(self, field_model: dict) -> str:
        show_name = field_model.get('show_name')
        name = field_model.get('name')
        temp = ('<div class="mb-3">'
                              f'<label>{show_name}</label>'
                              f'<textarea name="{name}" style="max-width:500px" class="form-control" rows="4" cols="50">[[model.{name}]]</textarea>'
                              '</div>')
        return temp