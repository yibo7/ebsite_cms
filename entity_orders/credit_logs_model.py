import decimal
import time

from entity.entity_base import ModelBase, annotation


class CreditLogsModel(ModelBase):
    """
    积分流水,记录积分的增加与减少
    """

    def __init__(self):
        super().__init__()
        self.user_id = ""
        self.username: str = ""
        self.user_ip: str = ""  # 付款用户的ip
        self.credits: int = 0  # 本次操作积分，增加为正数，消费为负数
        self.info: str = ""  # 备注信息
        self.type_id: int = 0  # 自定义类型区分，比如 1 消费，2. 购买 3 连续包月奖励 4 申请通过积分 5 赠送积分
        self.credits_balance: int = 0 # 当前用户积分余额

    @annotation("积分增减")
    def a_credits(self):
        add_tag = ""
        if self.credits>0:
            add_tag = "+"
        return f"{add_tag}{self.credits}"

    @annotation("变动前积分")
    def b_credits_balance(self):
        return self.credits_balance

    @annotation("变动后积分")
    def b_credits_balance2(self):
        return self.credits_balance + self.credits

    @annotation("类型")
    def b_type_id(self):
        return {1: "消费", 2: "购买积分", 3: "连续包月奖励", 4: "申请积分", 5: "注册赠送"}.get(self.type_id, "未知")

    @annotation("用户账号")
    def c_username(self):
        return self.username

    @annotation("备注信息")
    def d_info(self):
        return self.info

    @annotation("时间|to_time_name")
    def c_add_time(self):
        return self.add_time