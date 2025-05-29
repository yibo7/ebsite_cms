import datetime
import decimal
import time

from entity.entity_base import ModelBase, annotation


class VipCreditUpdate(ModelBase):
    """
    根据这个表的数据，定期更新包年包月用户积分
    这个表应该不需要，因为包年包月应该会调用支付页面的通知URL,在那里已经实现了积分的更新
    """

    def __init__(self):
        super().__init__()
        self.user_id = ""  # 根据用户Id查找对应的用户组，并获取更新的积分及更新周期
        self.username: str = ""
        self.next_credits_update = time.time()  # 在包月或包年的VIP用户里，积分会定期更新，这里是下一次更新积分的时间
        self.last_order_id: str = ""  # 最后开通包年包月会员的订单Id，对应UserOrders表购买连接包年包月VIP会员会员的订单Id
        self.last_order_time = time.time()  # 最后订单的记录
