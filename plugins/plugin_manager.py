from typing import Tuple

import eb_utils.flask_utils
from bll.send_msg_data import SendMsgData
from plugins.plugin_base import PluginBase, SMSSender, EmailSender, Uploader, OpenLoginBase, SearchBase, PaymentBase
from temp_expand import reg_temp_expand


class PluginManager:
    def __init__(self,app):
        self.plugins = []
        self.app = app
        self.plugin_types = [
            {"name":"短信发送","ClassName":"SMSSender"},
            {"name":"Email发送","ClassName":"EmailSender"},
            {"name":"文件上传","ClassName":"Uploader"},
            {"name": "三方登录", "ClassName": "OpenLoginBase"},
            {"name": "在线支付", "ClassName": "PaymentBase"},
            {"name": "内容搜索", "ClassName": "SearchBase"}
        ]

    def reg_plugin(self, plugin_class:PluginBase):
        self.plugins.append(plugin_class)


    def get_by_id(self, plugin_id: str) -> PluginBase:
        """
        查找出属于某个ID的插件
        :param plugin_id: 插件的Id
        :return:
        """
        # 遍历 self.plugins 列表
        for plugin in self.plugins:
            if plugin.id == plugin_id:
                return plugin
        return None
    def get_by_uploader_plugins(self):
        """
        获取所有上传插件
        :return:
        """
        return self.get_by_type(Uploader)
        # return [plugin for plugin in self.plugins if isinstance(plugin, Uploader)]

    def get_by_sms_plugins(self):
        """
        获取所有短信发送类的插件
        :return:
        """
        return self.get_by_type(SMSSender) # [plugin for plugin in self.plugins if isinstance(plugin, SMSSender)]

    def get_by_payment_plugins(self):
        """
        获取所有支付插件
        :return:
        """
        return self.get_by_type(PaymentBase)

    def get_by_email_plugins(self):
        """
        获取所有EMAIL发送类的插件
        :return:
        """
        return self.get_by_type(EmailSender) # [plugin for plugin in self.plugins if isinstance(plugin, EmailSender)]

    def get_by_type(self, type_class):
        """
        获取所有EMAIL发送类的插件
        :return:
        """
        if type_class:
            return [plugin for plugin in self.plugins if isinstance(plugin, type_class)]
        return []

    def get_by_type_name(self, type_class_name):
        """
        :return:
        """
        # {"name": "短信发送", "ClassName": "SMSSender"},
        # {"name": "Email发送", "ClassName": "EmailSender"},
        # {"name": "文件上传", "ClassName": "Uploader"},
        # {"name": "三方登录", "ClassName": "OpenLoginBase"},
        # {"name": "在线支付", "ClassName": "PaymentBase"},
        # {"name": "内容搜索", "ClassName": "SearchBase"}
        obj_name = None
        if type_class_name == 'SMSSender':
            obj_name = SMSSender
        elif type_class_name == 'EmailSender':
            obj_name = EmailSender
        elif type_class_name == 'Uploader':
            obj_name = Uploader
        elif type_class_name == 'OpenLoginBase':
            obj_name = OpenLoginBase
        elif type_class_name == 'PaymentBase':
            obj_name = PaymentBase
        elif type_class_name == 'SearchBase':
            obj_name = SearchBase
        return self.get_by_type(obj_name)


    def send_sms(self, phone_number: str, message: str) -> Tuple[bool, str]:
        """
        发送短信
        :param phone_number: 接收短信的电话号码
        :param message: 短信内容
        :return: 发送是否成功
        """
        sms_sender_id = self.app.config['sms_sender_id']
        provider = self.get_by_id(sms_sender_id)

        bll = SendMsgData()
        model = bll.new_instance()
        model.type = 1
        model.title = message
        model.to = phone_number
        model.bodystr = message
        model.provider_id = provider.id if provider else '找不到'
        model.ip = eb_utils.flask_utils.get_client_ip()
        model.is_send = True
        bll.add(model)
        if provider:
            return provider.send_sms(phone_number, message)
        return False, '找不到相应的短信发送插件！'

    def send_email(self, to: str, title: str, body: str) -> Tuple[bool, str]:
        email_sender_id = self.app.config['email_sender_id']
        provider = self.get_by_id(email_sender_id)
        bll = SendMsgData()
        model = bll.new_instance()
        model.type = 2
        model.to = to
        model.title = title
        model.bodystr = body
        model.provider_id = provider.id if provider else '找不到'
        model.ip = eb_utils.flask_utils.get_client_ip()
        model.is_send = True
        bll.add(model)
        if provider:
            return provider.send_email(to, title, body)
        return False, '找不到相应的邮件发送插件！'

    def upfile(self, fileb_bytes, model) -> Tuple[bool, str]:
        uploader_id = self.app.config['uploader_id']
        provider = self.get_by_id(uploader_id)
        if provider:
            return provider.upload(fileb_bytes, model)
        return False, '找不到相应的邮件发送插件！'
