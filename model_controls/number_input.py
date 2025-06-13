from model_controls.control_base import ControlBase


class NumberInput(ControlBase):

    def __init__(self):
        super().__init__()
        self.id: int = 4
        self.name: str = '数字输入框'
        self.info: str = '数字输入框'

    def get_control_temp(self, field_model: dict) -> str:
        show_name = field_model.get('show_name')
        name = field_model.get('name')
        temp = ('<div class="mb-3">'
                              f'<label>{show_name}</label>'
                              f'<input type="number" name="{name}" value="[[model.{name}]]" minlength="3" style="max-width:100px" class="form-control" required>'
                              '</div>')
        return temp