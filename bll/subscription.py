from typing import Optional, Tuple, List

from bson import ObjectId
from flask import Flask

from bll.bll_base import BllBase
from entity.subscription_model import SubscriptionModel


class Subscription(BllBase[SubscriptionModel]):
    def __init__(self, app: Optional[Flask] = None):
        super().__init__(app)

    def new_instance(self) -> SubscriptionModel:
        return SubscriptionModel()

    def get_subscribed_users(self, user_id: str) -> List[SubscriptionModel]:
        """
        获取当前用户订阅（关注）的所有用户记录
        :param user_id: 当前用户 _id 字符串
        """
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        return self.find_list_by_where(
            {"user_id": user_id},
            sort_key="add_time",
            sort_direction=-1,
        )

    def find_pager(self, page_number: int, page_size: int, rewrite_rule: str, user_id: str) -> Tuple[List[SubscriptionModel], str]:
        """
        分页获取当前用户订阅的用户列表
        :param page_number: 页码
        :param page_size: 每页数量
        :param rewrite_rule: 分页 URL 重写规则
        :param user_id: 当前用户 _id 字符串
        """
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        return super().find_pager(
            page_number, page_size, rewrite_rule,
            {"user_id": user_id},
            sort_key="add_time",
            sort_direction=-1,
        )

    def is_subscribed(self, user_id: str, subscribe_user_id: str) -> bool:
        """检查是否已订阅"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        if isinstance(subscribe_user_id, str):
            subscribe_user_id = ObjectId(subscribe_user_id)
        return self.find_one_by_where({
            "user_id": user_id,
            "subscribe_user_id": subscribe_user_id,
        }) is not None

    def subscribe(self, user_id: str, subscribe_user_id: str) -> bool:
        """添加订阅"""
        if self.is_subscribed(user_id, subscribe_user_id):
            return False
        model = self.new_instance()
        model.user_id = ObjectId(user_id)
        model.subscribe_user_id = ObjectId(subscribe_user_id)
        self.add(model)
        return True

    def unsubscribe(self, user_id: str, subscribe_user_id: str) -> bool:
        """取消订阅"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        if isinstance(subscribe_user_id, str):
            subscribe_user_id = ObjectId(subscribe_user_id)
        result = self.delete_by_where({
            "user_id": user_id,
            "subscribe_user_id": subscribe_user_id,
        })
        return result.deleted_count > 0