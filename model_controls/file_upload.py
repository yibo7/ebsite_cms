from model_controls.control_base import ControlBase


class FileUpload(ControlBase):

    def __init__(self):
        super().__init__()
        self.id: int = 6
        self.name: str = '单文件上传控件'
        self.info: str = '单文件上传控件'

    def get_control_temp(self, field_model: dict) -> str:
        show_name = field_model.get('show_name')
        name = field_model.get('name')
        temp = ('<div class="mb-3">'
                              f'<label>{show_name}</label>'
                              f'<input type="hidden" name="{name}" id="{name}" value="[[model.{name}]]" />'
                              f"<div class='bduploader'>"
                              f"    <div id='div_files_{name}' class='uploader-filelist'></div>"
                              f"    <div id='btn_upload_file_{name}'>选择文件</div>"
                              f'</div>'
                              f"<script>InitFileUpload('btn_upload_file_{name}','div_files_{name}','{name}',false);</script>"
                              '</div>')
        return temp