import decimal
from decimal import Decimal

from bson import Decimal128, ObjectId

from entity.entity_base import ModelBase


class UserGroupModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.name: str = ""  # 用户组名称
        self.info: str = ""  # 介绍
        self.credits: int = 0  # 购买此用户组或获得积分
        self._price: Decimal128 = Decimal128('0.00')  # 购买此用户组价格

    @property  # 实现_price的getter
    def price(self) -> Decimal:
        if isinstance(self._price, Decimal):
            return self._price
        else:
            # 如果由于某种原因 _price 不是 Decimal，我们确保返回 Decimal
            return Decimal(str(self._price))

    @price.setter
    def price(self, value):
        if isinstance(value, Decimal):
            self._price = Decimal128(str(value))
        elif isinstance(value, Decimal128):
            self._price = value
        else:
            self._price = Decimal128(str(Decimal(value)))

