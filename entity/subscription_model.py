from bson import ObjectId

from entity.entity_base import ModelBase


class SubscriptionModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.user_id: ObjectId = None  # 订阅者（粉丝）
        self.subscribe_user_id: ObjectId = None  # 被订阅者（关注的人）