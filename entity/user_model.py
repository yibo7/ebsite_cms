import time

import eb_utils
from entity.entity_base import ModelBase, annotation


class UserModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.ni_name = ""
        self.username = ""
        self.password = ""
        self.mobile_number = ""
        self.email_address = ""
        self.is_locked = False
        self.last_login_date = time.time()
        self.last_login_ip = ""
        self.credits:int = 0 # 总积分
        self.reg_remark = ""
        self.login_count = 0
        self.id: int = 0
        self.group_id = ""
        self.avatar = "/images/default_avatar.png"
        self.openid:str = ""  # 第三方平台绑定的用户ID
        self.credits_frozen: int = 0  # 被占用（冻结）的积分
        self.version:int = 0 # 乐观锁，主要是用在修改用户积分时用

    def credits_can_use(self) -> int:
        """
        获取当前用户可用积分
        @return:
        """
        return self.credits - self.credits_frozen

    def to_short_dic(self):
        """将实体对象转换为字典，只包含特定字段，并处理 ObjectId"""
        return {
            '_id': str(self._id),
            'id': self.id,
            'username': self.username,
            'ni_name': self.ni_name,
            'mobile_number': self.mobile_number,
            'email_address': self.email_address,
            'last_login_date': self.last_login_date,
            'credits': self.credits,
            'credits_frozen': self.credits_frozen,
            'group_id': self.group_id,
            'avatar': self.avatar
        }

    # 如下配置，需要在表格中显示的列,命名[a-z]是为了排序用：

    @annotation("用户名")
    def a_username(self):
        return eb_utils.cutstr(self.username,50)

    @annotation("昵称")
    def b_ni_name(self):
        return eb_utils.cutstr(self.ni_name,50)

    @annotation("用户组|to_user_group_name")
    def c_group_id(self):
        return self.group_id

    @annotation("手机号")
    def d_mobile_number(self):
        return self.mobile_number

    @annotation("邮箱地址")
    def e_email_address(self):
        return self.email_address

    @annotation("锁定|to_bool_name")
    def f_is_locked(self):
        return self.is_locked

    @annotation("积分情况")
    def g_credits(self):
        return f'总共:<font color="#ff0000">{self.credits}</font> 冻结:{self.credits_frozen} 可用:<font color="#FDA900">{self.credits_can_use()}</font>'

    @annotation("最后登录时间|to_time_name")
    def h_last_login_date(self):
        return self.last_login_date

    @annotation("最后登录IP")
    def i_last_login_ip(self):
        return self.last_login_ip

    @annotation("登录次数")
    def j_login_count(self):
        return self.login_count

    # @annotation("备注")
    # def k_reg_remark(self):
    #     return self.reg_remark

    @annotation("用户ID")
    def l_id(self):
        return f'【{self._id}】{self.id}'

    # @annotation("唯一ID")
    # def m_id(self):
    #     return self._id

    @annotation("注册时间|to_time_name")
    def n_add_time(self):
        return self.add_time
