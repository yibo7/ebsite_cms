import datetime
import decimal
import time
from decimal import Decimal, ROUND_HALF_UP

from bson import Decimal128

import eb_utils
from entity.entity_base import ModelBase, annotation


class CreditsOrderModel(ModelBase):
    """
    创建积分订单
    当在支付通知页面正常处理后，将is_complete修改为True,并同时将积分更新到用户表
    """

    def __init__(self):
        super().__init__()
        self.user_id = ""
        self.username: str = ""
        self.user_niame: str = ""  # 用户昵称
        self.user_ip: str = ""  # 付款用户的ip
        self.add_credits: int = 0  # 本次付款获得积分
        self.info: str = ""  # 备注信息
        self._price: Decimal128 = Decimal128('0.0')  # 原价格
        self._real_price: Decimal128 = Decimal128('0.0')  # 实际付款
        self.order_name: str = ""  # 订单名称，比如，购买【连续包月VIP】
        self.pay_type: int = 0  # 支付方式，比如 1 微信，2 支付宝
        self.is_complete: bool = False  # 是否结束订单
        self.is_payed: bool = False  # 是否支付成功
        self.complete_date = time.time()  # 完成支付的时间
        self.sign: str = ""  # 签名，user_id+user_ip+add_credits+order_id+real_price  在更新到用户表积分时要验证
        self.payment_prams = {}
        self.plan_id: str = "" # 来自积分套餐的ID，如果有此ID，说明此订单购买自积分套餐

        # self.order_type_id: str = ""  # 订单Id，比如购买VIP会员，就是可以是VIP所属的Id
        # self.type_id: int = 0  # 主要是给二次开发定义的分类，比如 1是购买VIP，2是直接下单

    @annotation("订单ID")
    def a_id(self):
        return self._id

    @annotation("订单名称")
    def b_order_name(self):
        return self.order_name

    @annotation("购买积分")
    def c_type_id(self):
        return self.add_credits

    @annotation("支付方式")
    def d_pay_type(self):
        return '微信' if self.pay_type == 1 else '支付宝 '

    @annotation("下单人账号")
    def e_username(self):
        return self.username

    @annotation("下单人昵称")
    def f_user_niame(self):
        return self.user_niame

    @annotation("订单金额")
    def g_price(self):
        return self._price

    @annotation("实际支付")
    def h_real_price(self):
        return self.real_price

    @annotation("下单人IP")
    def i_user_ip(self):
        return self.user_ip

    @annotation("是否支付")
    def j_is_is_payed(self):
        return '已支付' if self.is_payed else '未支付 '

    @annotation("处理状态")
    def k_is_complete(self):
        return '完成' if self.is_complete else '等处理 '
    @annotation("完成时间|to_time_name")
    def l_complete_date(self):
        return self.complete_date



    def sign_data(self):
        return eb_utils.md5(f'{self.user_ip}-{self.user_id}-{self.add_credits}-{self.real_price}-{self._id}')

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
        只精确到3位数
        :param value:
        :return:
        """
        rounded_value = Decimal(str(value)).quantize(Decimal('.001'), rounding=ROUND_HALF_UP)
        self._real_price = Decimal128(str(rounded_value))
