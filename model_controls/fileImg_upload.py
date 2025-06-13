from model_controls.control_base import ControlBase


class FileImgUpload(ControlBase):

    def __init__(self):
        super().__init__()
        self.id: int = 9
        self.name: str = '单图上传-显示路径'
        self.info: str = '单图上传-显示路径'

    def get_control_temp(self, field_model: dict) -> str:
        show_name = field_model.get('show_name')
        name = field_model.get('name')
        temp = ('<div class="mb-3">'
                              f'<label>{show_name}</label>' 
                              f'<div class="input-group mb-3">'
                              f'<input name="{name}" id="{name}" value="[[model.{name}]]"   style="max-width:300px" class="form-control">'
                              f'<button style="background-color: #00B7EE" class="btn btn-outline-secondary bduploader" type="button" id="btn_upload_file_{name}">选择图片</button>'                               
                              f'</div>' 
                              f"<script>InitImgUpload('btn_upload_file_{name}','','{name}',0,0,false);</script>"                                                                                                              
                              '</div>')
        return temp