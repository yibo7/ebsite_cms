import inspect
from typing import Optional

from bson import ObjectId
from flask import Flask

from bll.bll_base import BllBase
from entity.address_model import AddressModel

class Address(BllBase[AddressModel]):
    def __init__(self, app: Optional[Flask] = None):
        super().__init__(app)
    def new_instance(self) -> AddressModel:
        return AddressModel()

    def get_by_user_id(self, user_id: ObjectId) -> list[AddressModel]:
        return self.find_list_by_where({"user_id": user_id})