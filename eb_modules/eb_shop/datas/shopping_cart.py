from typing import Any, Optional

from bson import ObjectId, Decimal128
from flask import Flask

from bll.bll_base import BllBase
from eb_utils import url_links
from entity.entity_base import ModelBase, annotation
from decimal import Decimal

class ShoppingCartModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.content_title: str = "" # 商品名称
        self.content_id:str = ""  # 内容ID
        self.content_n_id: int = 0  # 内容ID
        self.small_pic: str = ""  # 商品封面图片地址
        self.class_name: str = "" # 分类名称
        self.class_n_id: int = 0  # 分类ID
        self.user_id: ObjectId    # 用户ID

        self.product_name: str = ""  #商品规格名称
        self.product_sku: str = ""   # 商品SKU（货号）
        self.product_id: str = ""  # 商品ID,product_sku的MD5值
        self.market_price: Decimal128  = Decimal128("0.0") # 市场价格
        self.price: Decimal128 = Decimal128("0.0") # 实际销售价格
        self.quantity:int = 0 # 订购的数量
        self.weight:Decimal128 = Decimal128("0.0")  # 重量
        self.cost_price:Decimal128 = Decimal128("0.0")  # 成本

    @property
    def total_market_price(self):
        return Decimal(str(self.market_price)) * self.quantity

    @property
    def total_price(self):
        t_price = Decimal(str(self.price)) * self.quantity
        return t_price

    @property
    def total_weight(self):
        return Decimal(str(self.weight)) * self.quantity

    @property
    def total_cost_price(self):
        return Decimal(str(self.cost_price)) * self.quantity

    @property
    def get_url(self):
        return url_links.get_content_url(self.content_n_id)


class ShoppingCartBll(BllBase[ShoppingCartModel]):
    def __init__(self, app: Optional[Flask] = None):
        super().__init__(app)
    def new_instance(self) -> ShoppingCartModel:
        return ShoppingCartModel()