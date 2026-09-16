
from typing import Tuple, Union

from entity.file_model import FileModel
from plugins.plugin_base import Uploader, plugin_attribute


@plugin_attribute("文件上传-MongoDb", "1.0", "ebsite")
class UploaderMongoDb(Uploader):

    def __init__(self, current_app):
        # self.name = "文件上传-MongoDb"
        self.info = "将文件上传到MongoDb数据库，默认会采用这个上传插件"
        super().__init__(current_app)


    def upload(self, fileb_bytes, model:FileModel) -> Tuple[bool, str]:

        model.plugin_id = self.id
        model.plugin_name = self.name
        model.url = ""
        model.content = fileb_bytes

        return True, '上传成功'

    def read(self, model: FileModel) -> Tuple[bool, Union[bytes, str, None]]:
        """
        从 MongoDB 中读取文件内容
        """
        if model.content:
            return True, model.content
        # content 字段可能因 projection 排除而未加载，重新查询
        from bll.file_upload import FileUpload
        fresh = FileUpload().find_one_by_id(model._id)
        if fresh and fresh.content:
            return True, fresh.content
        return False, '文件内容不存在'


