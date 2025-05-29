import re
from typing import Tuple

import pymongo
from bson import ObjectId

from bll.bll_base import BllBase
from eb_utils.configs import SiteConstant
from eb_utils.mvc_pager import pager_html_admin
from entity.file_model import FileModel

# ALLOWED_EXTENSIONS = {'.gif', '.png', '.jpg', '.jpeg', '.bmp', '.rar','.zip','.txt','.pdf','.doc','.docx','.XLS','.XLSX','.PPT','.PPTX','.CSV','.MP3','.MP4','.AVI','.MOV','.WMV'}
# MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
#
#
# def allowed_file(f_type):
#     return f_type.lower() in ALLOWED_EXTENSIONS


class FileUpload(BllBase[FileModel]):

    def new_instance(self) -> FileModel:
        model = FileModel()
        model._id = ObjectId()
        return model
    #
    # def upload(self, model: FileModel):
    #
    #
    #     data = {"originalName": '', "name": '', "url": '', "size": 0, "state": 'unknown err', "type": ''}
    #
    #     model_old = self.find_one_by_where({"md5":model.md5})
    #     if not model_old:
    #         file_extension = model.original_name.rsplit('.', 1)[1].lower()
    #         model.type = f'.{file_extension}'
    #         if not allowed_file(model.type):  # 非法文件检查
    #             data["state"] = f"Not allowed file type:{model.type}"
    #             return data
    #
    #         model.size = len(model.content)
    #
    #         if model.size > MAX_FILE_SIZE:  # 文件大小检查
    #             data["state"] = 'File size exceeds the limit of 5MB.'
    #             return data
    #
    #         model.url = f"{model._id}{model.type}"  # /api/upload/
    #         self.add(model)
    #     else:
    #         model = model_old
    #         print(f'已经存在MD5：{model.md5}')
    #
    #     data["originalName"] = model.original_name
    #     data["name"] = model.original_name
    #     data["url"] = f'/api/upfile/{model.url}'
    #     data["size"] = model.size
    #     data["state"] = "SUCCESS"
    #     data["type"] = model.type
    #
    #     return data

    def search_content(self, keyword: str, plugin_id: str, page_index: int) -> Tuple[list[FileModel], str]:
        """
        模糊搜索
        :param keyword: 搜索的关键词, 不传入会搜索所有
        :param page_index: 页面码
        :param plugin_id: 上传插件ID
        :return:
        """
        datas, i_count = self.search_data(keyword, plugin_id, page_index)
        page_size = SiteConstant.PAGE_SIZE_AD
        pager = pager_html_admin(i_count, page_index, page_size, {'k': keyword})
        return datas, pager

    def search_data(self, keyword: str, plugin_id: str, page_number: int) -> Tuple[list[FileModel], int]:
        """
        模糊搜索
        :param keyword: 搜索的关键词, 不传入会搜索所有
        :param page_number: 页面码
        :param plugin_id: 上传插件ID
        :return:
        """
        page_size = SiteConstant.PAGE_SIZE_AD

        s_where = {}
        if keyword:
            regex_pattern = re.compile(f'.*{re.escape(keyword)}.*', re.IGNORECASE)  # IGNORE CASE 忽略大小写
            # s_where = {'title': {'$regex': regex_pattern}}
            # 构建查询条件
            s_where = {
                "$or": [
                    {"original_name": {"$regex": regex_pattern}},
                    {"url": {"$regex": regex_pattern}}
                ]
            }

        if plugin_id:
            s_where['plugin_id'] = plugin_id
        projection = {'content': 0} # content字段的内容太大排除掉
        datas, i_count = self.find_pages(page_number, page_size, s_where,"_id",
                   pymongo.DESCENDING,projection)
        return datas, i_count