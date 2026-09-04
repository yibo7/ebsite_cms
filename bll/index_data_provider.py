from typing import Optional

import pymongo
from flask import Flask, current_app

from bll.new_content import NewsContent


class IndexDataProvider:
    """首页模板数据提供类"""

    def __init__(self, app: Optional[Flask] = None):
        self._bll = NewsContent(app)

    # ── 推荐数据（is_good = True） ──────────────────────────────
    def getRecDatas(self, top: int) -> list:
        """
        获取推荐数据（is_good=True）
        不限制分类，按 hits 降序
        :param top: 最多返回记录数
        """
        return self._bll.get_good_datas(None, top)

    # ── 热门数据（按 hits 降序） ────────────────────────────────
    def getHotDatas(self, top: int) -> list:
        """
        获取热门数据（按 hits 降序）
        不限制分类
        :param top: 最多返回记录数
        """
        return self._bll.find_list_by_where(
            where={},
            sort_key="hits",
            sort_direction=pymongo.DESCENDING,
            limit=top,
        )

    # ── 最新数据（按 _id 降序，等价于 add_time 倒序） ─────────
    def getNewDatas(self, top: int) -> list:
        """
        获取最新数据（按 _id 降序，即添加时间倒序）
        不限制分类
        :param top: 最多返回记录数
        """
        return self._bll.find_list_by_where(
            where={},
            sort_key="_id",
            sort_direction=pymongo.DESCENDING,
            limit=top,
        )