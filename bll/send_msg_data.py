import re
from typing import Tuple

import pymongo
from bson import ObjectId

from bll.bll_base import BllBase
from eb_utils.configs import SiteConstant
from eb_utils.mvc_pager import pager_html_admin
from entity.file_model import FileModel
from entity.send_msg_model import SendMsgModel


class SendMsgData(BllBase[SendMsgModel]):

    def new_instance(self) -> SendMsgModel:
        model = SendMsgModel()
        model._id = ObjectId()
        return model

    def search_content(self, keyword: str, plugin_id: str, page_index: int) -> Tuple[list[SendMsgModel], str]:
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

    def search_data(self, keyword: str, plugin_id: str, page_number: int) -> Tuple[list[SendMsgModel], int]:
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
                    {"title": {"$regex": regex_pattern}},
                    {"bodystr": {"$regex": regex_pattern}},
                    {"to": {"$regex": regex_pattern}},
                    {"ip": {"$regex": regex_pattern}}

                ]
            }

        if plugin_id:
            s_where['type'] = int(plugin_id)
        datas, i_count = self.find_pages(page_number, page_size, s_where)
        return datas, i_count