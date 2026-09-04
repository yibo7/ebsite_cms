from model_controls.control_base import ControlBase


class ScoreTypeSelect(ControlBase):

    def __init__(self):
        super().__init__()
        self.id: int = 10
        self.name: str = '乐谱类型'
        self.info: str = '乐谱类型下拉选择'

    def get_control_temp(self, field_model: dict) -> str:
        show_name = field_model.get('show_name')
        name = field_model.get('name')
        control_size = field_model.get('control_size')
        control_size = int(control_size)
        temp = ('<div class="mb-3">'
                f'<label>{show_name}</label>'
                f'<select name="{name}" class="form-control" style="max-width:{control_size * 100}px" required>'
                '<option value="">请选择乐谱类型</option>'
                f'<option value="1" {{% if model.{name} == "1" %}}selected{{% endif %}}>总谱</option>'
                f'<option value="2" {{% if model.{name} == "2" %}}selected{{% endif %}}>吉他独奏</option>'
                f'<option value="3" {{% if model.{name} == "3" %}}selected{{% endif %}}>钢琴独奏</option>'
                f'<option value="4" {{% if model.{name} == "4" %}}selected{{% endif %}}>架子鼓独奏</option>'
                f'<option value="5" {{% if model.{name} == "5" %}}selected{{% endif %}}>贝斯独奏</option>'
                f'<option value="6" {{% if model.{name} == "6" %}}selected{{% endif %}}>尤克里里独奏</option>'
                '</select>'
                '</div>')
        return temp