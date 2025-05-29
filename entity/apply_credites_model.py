import time

from entity.entity_base import ModelBase, annotation


class ApplyCreditesModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.user_id = "" # 申请用户的ID
        self.username = "" # 申请人账号
        self.ni_name = ""  # 申请人昵称
        self.ip = ""        # 申请人IP
        self.credits:int = 0 # 申请多少积分
        self.remark = "" # 申请原因
        self.apply_ni_name = ""  # 审核人昵称
        self.apply_username = "" # 审核人账号
        self.is_apply = False # 是否通过审核
        self.false_reason = ""  # 不通过原因
        self.is_complate = False  # 是否已经处理
        self.apply_time = time.time() # 审核时间日期

    @annotation("是否处理")
    def a_is_complate(self):
        return "已处理" if self.is_complate else "未处理"

    @annotation("申请人账号")
    def b_username(self):
        return self.username

    @annotation("申请人昵称")
    def b_ni_name(self):
        return self.ni_name

    @annotation("申请积分")
    def c_credits(self):
        return self.credits

    @annotation("申请原因")
    def d_remark(self):
        return self.remark

    @annotation("审核人昵称")
    def e_apply_ni_name(self):
        return self.apply_ni_name

    @annotation("审核人账号")
    def f_apply_username(self):
        return self.apply_username

    @annotation("是否通过")
    def h_is_apply(self):
        return "是" if self.is_apply else "否"

    # @annotation("不通过原因")
    # def i_false_reason(self):
    #     return self.false_reason

    @annotation("审核时间")
    def j_apply_time(self):
        return self.apply_time

