
from typing import Tuple

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
        model.url = f"/api/upfile/{model._id}{model.type}"
        model.content = fileb_bytes

        return True, model.url


