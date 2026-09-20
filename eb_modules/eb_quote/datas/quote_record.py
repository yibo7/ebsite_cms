"""
报价单数据模型与业务层

无需登录即可生成报价单，方便发送给客户。
"""
import time
from typing import Optional

from bson import ObjectId
from flask import Flask
from pymongo import ASCENDING

from bll.bll_base import BllBase
from entity.entity_base import ModelBase

# 报价单状态
QUOTE_STATUS = {
    "pending_review": "已创建-待审核",
    "approved":       "审核成功-待支付",
    "paid":           "已支付-待发货",
    "completed":      "交易完成",
    "failed":         "交易失败",
}

STATUS_CLASS = {
    "pending_review": "pending",
    "approved":       "paid",
    "paid":           "shipped",
    "completed":      "done",
    "failed":         "closed",
}


class ShopQuoteRecordModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.record_id: str = ""
        self.session_id: str = ""
        self.user_id: str = ""
        self.user_account: str = ""
        self.status: str = "pending_review"
        self.fail_reason: str = ""          # 交易失败原因

        self.contact: dict = {
            "name": "",
            "phone": "",
            "email": "",
            "company": "",
            "address": "",
            "remark": "",
        }

        self.items: list[dict] = []
        self.total_original: float = 0.0
        self.total_discount: float = 0.0
        self.total_final: float = 0.0
        self.discount_rate: float = 0.10
        self.item_count: int = 0
        self.total_qty: int = 0


class ShopQuoteRecord(BllBase[ShopQuoteRecordModel]):
    def __init__(self, app: Optional[Flask] = None):
        super().__init__(app)

    def new_instance(self) -> ShopQuoteRecordModel:
        model = ShopQuoteRecordModel()
        model.record_id = self._generate_record_id()
        return model

    @staticmethod
    def _generate_record_id() -> str:
        """使用 MongoDB ObjectId 作为 record_id，全局唯一且不可枚举"""
        return str(ObjectId())

    def save_record(self, model: ShopQuoteRecordModel) -> str:
        model.add_time = int(time.time())
        doc = model.to_dict()
        doc.pop("_id", None)
        doc.pop("id", None)
        self.table.insert_one(doc)
        return model.record_id

    def get_by_record_id(self, record_id: str) -> Optional[ShopQuoteRecordModel]:
        return self.find_one_by_where({"record_id": record_id})

    def update_contact(self, record_id: str, contact: dict) -> bool:
        result = self.table.update_one(
            {"record_id": record_id},
            {"$set": {"contact": contact}}
        )
        return result.modified_count > 0

    def update_status(self, record_id: str, status: str, fail_reason: str = "") -> bool:
        """更新报价单状态"""
        update = {"status": status}
        if status == "failed" and fail_reason:
            update["fail_reason"] = fail_reason
        result = self.table.update_one(
            {"record_id": record_id},
            {"$set": update}
        )
        return result.modified_count > 0

    def find_by_user(self, user_id: str, page: int = 1, page_size: int = 20):
        """查询用户的报价单列表"""
        where = {"user_id": user_id}
        return self.find_pager(page, page_size, f"/my_quotes?p={{0}}", where,
                               sort_key="add_time", sort_direction=-1)

    def find_all_pager(self, page: int = 1, page_size: int = 20, keyword: str = ""):
        """管理员查询所有报价单"""
        where = {}
        if keyword:
            import re
            pat = {"$regex": re.escape(keyword), "$options": "i"}
            where["$or"] = [
                {"record_id": pat},
                {"user_account": pat},
                {"contact.name": pat},
                {"contact.phone": pat},
            ]
        return self.find_pager(page, page_size, "/shop/shop_quotes?p={{0}}", where,
                               sort_key="add_time", sort_direction=-1)

    def create_index_record_id(self):
        """record_id 随 ObjectId 生成已全局唯一，无需额外唯一索引"""
        pass