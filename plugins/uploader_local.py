import os
from datetime import datetime
from typing import Tuple

from entity.file_model import FileModel
from plugins.plugin_base import Uploader, plugin_attribute


@plugin_attribute("文件上传-本地", "1.0", "ebsite")
class UploaderLocal(Uploader):

    def __init__(self, current_app):
        # self.name = "文件上传-本地"
        self.info = "将文件上传到到本地uploadfile目录下"
        super().__init__(current_app)

    def ensure_dir(self,path):
        # 获取路径中的目录部分
        directory = os.path.dirname(path)

        # 检查目录是否存在，如果不存在，则创建它
        if not os.path.exists(directory):
            os.makedirs(directory)
    def upload(self, fileb_bytes, model:FileModel) -> Tuple[bool, str]:

        model.plugin_id = self.id
        model.plugin_name = self.name

        # model.content = fileb_bytes
        # 获取当前日期并格式化
        date_str = datetime.now().strftime('%Y%m%d')
        file_name = f'{date_str}/{model._id}{model.type}'

        model.url = f"/api/uploads/{file_name}"

        file_path = os.path.join(self.app.root_path, 'uploads',file_name)
        self.ensure_dir(file_path)
        # 手动保存文件
        with open(file_path, 'wb') as f:
            f.write(fileb_bytes)

        return True, model.url
