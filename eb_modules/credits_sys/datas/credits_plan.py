from decimal import Decimal, ROUND_HALF_UP

from bson import Decimal128

from bll.bll_base import BllBase
from entity.entity_base import ModelBase, annotation


class CreditsPlanModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.title = ""
        self._price: Decimal128 = Decimal128('0.0')  # 原价格
        self._real_price: Decimal128 = Decimal128('0.0')  # 实际付款
        self.credits: int = 0  # 可得积分
        self.info:str = "" # 介绍
        self.ico_tag:str = "" # 图标标记号

    def to_short_dic(self):
        """将实体对象转换为字典，只包含特定字段，并处理 ObjectId"""
        return {
            'id': str(self._id),
            'title': self.title,
            'price': self.price,
            'real_price': self.real_price,
            'credits': self.credits,
            'info': self.info,
            'ico_tag': self.ico_tag
        }
    # 如下配置，需要在表格中显示的列,命名[a-z]是为了排序用

    @annotation("套餐名称")
    def a_title(self):
        return self.title

    @annotation("原价")
    def b_price(self):
        return self._price

    @annotation("实际价")
    def c_real_price(self):
        return self._real_price

    @annotation("可得积分")
    def d_credits(self):
        return self.credits


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

    @property  # 实现_price的getter
    def real_price(self) -> Decimal:
        if isinstance(self._real_price, Decimal):
            return self._real_price
        else:
            # 如果由于某种原因 _price 不是 Decimal，我们确保返回 Decimal
            return Decimal(str(self._real_price))

    @real_price.setter
    def real_price(self, value):
        """
        实际价格
        :param value:
        :return:
        """
        if isinstance(value, Decimal):
            self._real_price = Decimal128(str(value))
        elif isinstance(value, Decimal128):
            self._real_price = value
        else:
            self._real_price = Decimal128(str(Decimal(value)))


class CreditsPlanBll(BllBase[CreditsPlanModel]):

    def new_instance(self) -> CreditsPlanModel:
        return CreditsPlanModel()