from model_controls.control_base import ControlBase


class ImgUpload(ControlBase):

    def __init__(self):
        super().__init__()
        self.id: int = 5
        self.name: str = '单图上传控件'
        self.info: str = '单图上传控件'

    def get_control_temp(self, field_model: dict) -> str:
        show_name = field_model.get('show_name')
        name = field_model.get('name')
        temp = ('<div class="mb-3">'
                              f'<label>{show_name}</label>'
                              f'<input type="hidden" name="{name}" id="{name}" value="[[model.{name}]]" />'
                              f"<div class='bduploader'>"
                              f"    <div><div id='imglisttbuUploadImg_{name}' class='uploader-imglist'></div></div>"
                              f"    <div id='filedatatbuUploadImg_{name}'>选择图片</div>"
                              f'</div>'
                              f"<script>InitImgUpload('filedatatbuUploadImg_{name}','imglisttbuUploadImg_{name}','{name}',80,80,false);</script>"
                              '</div>')
        return temp