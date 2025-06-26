import time
from typing import Any, Optional, Tuple

from bson import ObjectId, Decimal128
from flask import Flask
from pymongo import ASCENDING

from bll.bll_base import BllBase
from eb_utils.order_id_generator import OrderIdGenerator
from entity.entity_base import ModelBase, annotation


ORDER_STATUS_MAP = {
    -1: '失败',
     0: '等待支付',
     1: '等待发货',
     2: '等待收货',
     3: '完成'
}

class ShopOrderModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.order_id:str =  ""
        self.remark: str = "" # 备注
        self.address:dict = {}  # 收货地址信息
        self.products = [] # 产品信息
        self.pay_date = None # 支付时间
        self.send_date = None  # 发货时间
        self.finish_date = None # 收货时间
        self.order_status: int = 0 # -1(失败-可查看原因)，0新下单（等待支付）,1支付完成(等待发货),2已发货(等待收货),3完成(已收货)
        self.close_reason: str = "" # 失败原因
        self.user_id: ObjectId = ""   # 购买用户ID

        self.total_weight: Decimal128 = Decimal128("0.0")  # 重量
        self.freight:Decimal128  = Decimal128("0.0") # 运费
        self.delivery_number:str = "" # 快递单号
        self.delivery_name:str = "" # 快递或物流名称
        self.payment_name:str = "未支付"  # 支付方式名称
        self.payment_free:Decimal128  = Decimal128("0.0") # 支付手续费

        self.total_market_price:Decimal128  = Decimal128("0.0") # 市场价格
        self.total_price:Decimal128  = Decimal128("0.0") # 实际销售价格
        self.discount:Decimal128  = Decimal128("0.0") # 折扣率（百分比）
        self.discount_info:str = "" # 折扣原因
        self.total_cost_price:Decimal128 = Decimal128("0.0") # 成本价格
        self.profit:Decimal128 = Decimal128("0.0") # 订单毛利

    @property
    def order_statu_name(self):
        return ORDER_STATUS_MAP.get(self.order_status, '未知状态')

class ShopOrder(BllBase[ShopOrderModel]):
    def __init__(self, app: Optional[Flask] = None):
        super().__init__(app)
    def new_instance(self) -> ShopOrderModel:
        generator = OrderIdGenerator()
        model = ShopOrderModel()
        model.order_id = generator.generate()
        return model

    def get_by_user_id(self,p_number:int, user_id: ObjectId) -> Tuple[list[ShopOrderModel], str]:

        rewrite_rule = '/shop/my_orders?p={{0}}'
        return self.find_pager(p_number, 20, rewrite_rule, {'user_id': user_id})

    def get_by_order_id(self,order_id:str) -> ShopOrderModel:
        return self.find_one_by_where({'order_id': order_id})

    def create_index_order_id(self):
        """
        创建 order_id 的唯一索引
        """
        self.table.create_index([("order_id", ASCENDING)], unique=True)
        print("create_index : ShopOrder.order_id")
