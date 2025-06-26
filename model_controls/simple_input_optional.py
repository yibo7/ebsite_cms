from model_controls.control_base import ControlBase


class SimpleInputOptional(ControlBase):

    def __init__(self):
        super().__init__()
        self.id: int = 11
        self.name: str = '单行文本输入框-选填'
        self.info: str = '简单单行文本输入框，可以不用填写'

    def get_control_temp(self, field_model: dict) -> str:

        show_name = field_model.get('show_name')
        name = field_model.get('name')
        control_size = field_model.get('control_size')
        control_size = int(control_size)
        temp = ('<div class="mb-3">'
                f'<label>{show_name}</label>'
                f'<input name="{name}" value="[[model.{name}]]"  style="max-width:{control_size * 100}px" class="form-control">'
                '</div>')
        return temp