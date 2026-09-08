from typing import Optional, Tuple, List

import pymongo
from bson import ObjectId
from flask import Flask, current_app

from bll.favorite import Favorite
from bll.new_content import NewsContent
from bll.subscription import Subscription
from bll.user import User


class TempDataProvider:
    """模板数据提供类"""

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

    # ── 相关推荐（按共同标签匹配） ──────────────────────────────
    def get_related_by_tags(self, model_id, top: int = 10) -> list:
        """
        根据当前内容的标签，查找具有共同标签的相关记录，按 hits 降序
        :param model_id: 当前内容的 _id（ObjectId 或字符串）
        :param top: 最多返回记录数，默认 10
        :return: 相关记录列表
        """
        # 统一转为字符串
        if isinstance(model_id, ObjectId):
            model_id = str(model_id)

        # 获取当前内容的标签
        current = self._bll.find_one_by_id(model_id)
        if not current or not current.tags:
            return []

        # 查询至少匹配一个共同标签、且排除自身的记录
        return self._bll.find_list_by_where(
            where={
                "_id": {"$ne": ObjectId(model_id)},
                "tags": {"$in": current.tags},
            },
            sort_key="hits",
            sort_direction=pymongo.DESCENDING,
            limit=top,
        )

    # ── 获取用户信息 ──────────────────────────────────────────
    def get_user_info(self, user_id) -> Optional[dict]:
        """
        根据用户 _id 获取用户基本信息（昵称、头像等）
        :param user_id: 用户的 _id（ObjectId 或字符串）
        :return: 用户信息字典，或 None
        """
        if isinstance(user_id, ObjectId):
            user_id = str(user_id)
        try:
            user_bll = User()
            user = user_bll.find_one_by_id(user_id)
            if user:
                return {
                    "ni_name": user.ni_name or user.username,
                    "avatar": user.avatar or "/images/default_avatar.png",
                    "username": user.username,
                }
        except Exception:
            pass
        return None

    # ── 获取用户的内容列表（分页） ────────────────────────────
    def get_user_content_list(self, user_id, page: int = 1, page_size: int = 20):
        """
        根据用户 _id 获取该用户发布的内容列表（分页）
        :param user_id: 用户的 _id（ObjectId 或字符串）
        :param page: 页码，默认 1
        :param page_size: 每页数量，默认 20
        :return: (data_list, pager_html)
        """
        if isinstance(user_id, ObjectId):
            user_id = str(user_id)
        rewrite_rule = f'/u{user_id}p{{0}}.html'
        return self._bll.find_pager(
            page,
            page_size,
            rewrite_rule,
            {"user_id": ObjectId(user_id)},
        )

    # ── 获取用户自己的内容（个人中心首页用，分页） ──────────
    def get_my_content_list(self, user_id, page: int = 1, page_size: int = 12):
        """
        获取当前用户自己发布的内容（分页），用于个人中心首页
        :param user_id: 当前用户的 _id（ObjectId 或字符串）
        :param page: 页码，默认 1
        :param page_size: 每页数量，默认 12
        :return: (data_list, pager_html)
        """
        if isinstance(user_id, ObjectId):
            user_id = str(user_id)
        rewrite_rule = f'/user/index?p={{0}}'
        return self._bll.find_pager(
            page,
            page_size,
            rewrite_rule,
            {"user_id": ObjectId(user_id)},  # NewsContent 存储的 user_id 为 ObjectId
            sort_key="add_time",
            sort_direction=pymongo.DESCENDING,
        )

    # ── 获取用户内容统计 ────────────────────────────────────
    def get_user_content_stats(self, user_id) -> dict:
        """
        获取用户内容统计信息
        :param user_id: 用户的 _id（ObjectId 或字符串）
        :return: 统计字典
        """
        if isinstance(user_id, ObjectId):
            user_id = str(user_id)
        stats = {
            "total": 0,
            "total_hits": 0,
            "favorites": 0,
        }
        # 获取用户发布的内容列表
        content_list = self._bll.find_list_by_where(
            {"user_id": ObjectId(user_id)},  # NewsContent 存储的 user_id 为 ObjectId
            limit=10000,
        )
        stats["total"] = len(content_list)
        stats["total_hits"] = sum(getattr(c, "hits", 0) or 0 for c in content_list)

        # 统计当前用户收藏的内容数量（我的收藏）
        bll_fav = Favorite()
        stats["favorites"] = bll_fav.count({"user_id": ObjectId(user_id)})
        return stats

    # ── 获取当前用户订阅的用户列表 ─────────────────────────
    def get_subscribed_users(self, user_id, page: int = 1, page_size: int = 20) -> Tuple[
        List[dict], str]:
        """
        获取当前用户订阅的用户列表，附带用户信息
        :param user_id: 当前用户的 _id（ObjectId 或字符串）
        :param page: 页码
        :param page_size: 每页数量
        :return: (用户信息列表, pager_html)
        """
        if isinstance(user_id, ObjectId):
            user_id = str(user_id)
        bll_sub = Subscription()
        rewrite_rule = f'/user/subscriptions?p={{0}}'
        sub_list, pager = bll_sub.find_pager(page, page_size, rewrite_rule, user_id)

        user_bll = User()
        result = []
        for sub in sub_list:
            suid = sub.subscribe_user_id
            if isinstance(suid, ObjectId):
                suid = str(suid)
            user_info = user_bll.find_one_by_id(suid)
            if user_info:
                # 统计该用户的内容数量
                content_count = self._bll.count({"user_id": ObjectId(suid)})
                result.append({
                    "_id": str(user_info._id),
                    "ni_name": user_info.ni_name or user_info.username,
                    "username": user_info.username,
                    "avatar": user_info.avatar or "/images/default_avatar.png",
                    "content_count": content_count,
                    "sub_time": sub.add_time,
                })
        return result, pager