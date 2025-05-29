
from typing import Tuple

from eb_utils.email_utils import EmailUtils
from plugins.plugin_base import EmailSender, plugin_attribute

@plugin_attribute("默认邮件发送", "1.0", "ebsite")
class DefaultEmailSender(EmailSender):

    def __init__(self, current_app):
        # self.name = "默认邮件发送"
        self.smtp_server: str = "smtp.exmail.qq.com"
        self.smtp_port: int = 25
        self.sender_email: str = ""
        self.password: str = ""
        self.use_ssl: bool = False
        self.max_workers: int = 1

        self.info = "一般情况下，如果不使用第三方平台来发送邮件可直接使用这个，支持队列与多线程处理"

        self.email_hannder:EmailUtils = None
        self.create_email_hannder()

        super().__init__(current_app)

    def create_email_hannder(self):
        self.email_hannder = EmailUtils(self.smtp_server, self.smtp_port, self.sender_email, self.password, self.use_ssl)

    def on_refushed_config(self):
        self.create_email_hannder()

    def send_email(self, to: str, title: str, body: str) -> Tuple[bool, str]:
        # 将加到email发送队列
        print(f'发送【{title}】到【{to}】')
        self.email_hannder.add_to_queue(to, title, body)
        return True, ''

    def params_temp(self):
        """
        在后台保存插件配置时，实现在模板中添加保存参数
        :return: 模板字符串
        """
        return '''
        <div class="mb-3">
            <label>SMTP服务器</label>
            <input name="smtp_server" value="{{model.smtp_server}}"  style="max-width:300px" class="form-control" required>
        </div>
        <div class="mb-3">
            <label>SMTP端口</label>
            <input name="smtp_port" value="{{model.smtp_port}}"  type="number" style="max-width:80px" class="form-control" required>
        </div>
        <div class="mb-3">
            <label>发送人EMAIL</label>
            <input name="sender_email" value="{{model.sender_email}}"  style="max-width:300px" class="form-control" required>
        </div>
        <div class="mb-3">
            <label>发送人密码</label>
            <input name="password" value="{{model.password}}"  style="max-width:300px" class="form-control" required>
        </div> 
        <div class="mb-3">
            <label>
                <input name="use_ssl" type="checkbox" {% if model.use_ssl %}checked{% endif %}>是否启用SSL
            </label>
        </div>
        <div class="mb-3">
            <label>处理线程数</label>
            <input name="max_workers" value="{{model.max_workers}}"  type="number" style="max-width:80px" class="form-control" required>
        </div>
        
        '''
