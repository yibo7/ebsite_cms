import time

from entity.entity_base import ModelBase, annotation


class SendMsgModel(ModelBase):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.bodystr = ""
        self.type = 1  # 1 为手机短信，2为email
        self.to = ""   # 发送目标，手机号或EMAIL地址
        self.ip = ''
        self.provider_id = '' # 插件ID
        self.is_send = False  # 是否已发送完成

    # 如下配置，需要在表格中显示的列,命名[a-z]是为了排序用：

    @annotation("标题")
    def a_title(self):
        return self.title

    @annotation("类型")
    def b_type(self):
        return "手机短信" if self.type==1 else "EMAIL"

    @annotation("发送目标")
    def c_to(self):
        return self.to

    @annotation("用户IP")
    def d_ip(self):
        return self.ip

    @annotation("内容")
    def e_bodystr(self):
        return self.bodystr

    @annotation("发送插件")
    def f_provider_id(self):
        return self.provider_id

    @annotation("时间|to_time_name")
    def n_add_time(self):
        return self.add_time
