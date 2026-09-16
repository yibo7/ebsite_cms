import os
from typing import Tuple, Union

from entity.file_model import FileModel
from plugins.plugin_base import Uploader, plugin_attribute


@plugin_attribute("文件上传-本地", "1.0", "ebsite")
class UploaderLocal(Uploader):

    def __init__(self, current_app):
        # self.name = "文件上传-本地"
        self.info = "将文件上传到到本地uploadfile目录下"
        super().__init__(current_app)

    def _get_subdir(self) -> str:
        """从 setting.json 读取文件保存子目录名"""
        base_settings = self.app.config.get('base_settings', {})
        return base_settings.get('FileStorageSubdir', '').strip()

    def upload(self, fileb_bytes, model: FileModel) -> Tuple[bool, str]:

        model.plugin_id = self.id
        model.plugin_name = self.name

        subdir = self._get_subdir()
        if subdir:
            file_name = f'{subdir}/{model.md5}{model.type}'
            file_path = os.path.join(self.app.root_path, 'uploads', file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        else:
            file_name = f'{model.md5}{model.type}'
            file_path = os.path.join(self.app.root_path, 'uploads', file_name)

        model.url = f"/uploads/{file_name}"

        try:
            with open(file_path, 'wb') as f:
                f.write(fileb_bytes)
        except OSError as e:
            return False, f'文件写入失败: {str(e)}'

        return True, '上传成功'

    def read(self, model: FileModel) -> Tuple[bool, Union[bytes, str, None]]:
        """
        从本地磁盘读取文件内容。
        """
        file_path = os.path.join(self.app.root_path, model.url.lstrip('/'))

        if not os.path.exists(file_path):
            return False, '文件不存在'

        try:
            with open(file_path, 'rb') as f:
                return True, f.read()
        except Exception as e:
            return False, f'读取文件失败: {str(e)}'
