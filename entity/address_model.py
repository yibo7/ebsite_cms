from typing import Any

from bson import ObjectId

from eb_utils import url_links
from entity.entity_base import ModelBase, annotation


class AddressModel(ModelBase):
    def __init__(self):
        super().__init__()

        self.user_id: ObjectId
        self.user_name:  str = "" # 收件人
        self.phone: str = ""  # 联系电话
        self.email: str = ""
        self.post_code: str = "" # 邮编
        self.address_info: str = "" # 具体的收货地址
 