import hashlib
from abc import ABC, abstractmethod
from typing import Tuple
from urllib.parse import quote

from flask import Request, request

from entity.file_model import FileModel
from entity.pay_back_model import PayBackInfo
from entity.user_call_back_model import UserCallBackModel

def plugin_attribute(description, version, author, priority=999):
    def decorator(cls):
        cls._extension_info = {
            'description': description,
            'version': version,
            'author': author,
            'priority': priority
        }
        return cls
    return decorator

'''
插件基类
'''
class PluginBase(ABC):
    def __init__(self,current_app):
        self.app = current_app
        self.table = current_app.db['PluginSettings']
        self.id = self.__class__.__name__
        # self.info = '插件说明'  # 插件说明介绍
        self.refush_config(None)

    def on_refushed_config(self):
        """
        修改配置后触发
        :return:
        """
        pass

    def refush_config(self, config: dict):
        if not config:
            config = self.get_configs()
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.on_refushed_config()

    def get_configs(self)->dict:
        """
        获取插件配置
        :return:
        """
        model = self.table.find_one({"_id": self.id})
        if not model:
            model = self.__dict__

        return model

    def set_configs(self, model:dict):
        """
        在系统后台调用的方法，用来保存插件配置
        :param model: 从模板中获取的插件参数
        :return:
        """
        model['_id'] = self.id
        self.table.update_one({"_id": self.id}, {"$set": model}, upsert=True)  # 如果没有就添加
        self.refush_config(model)

    # @abstractmethod
    def params_temp(self) -> str:
        """
        在后台保存插件配置时，实现在模板中添加保存参数
        :return: 模板字符串
        """
        return ""

    @property
    def name(self):
        return self._extension_info['description']

    @property
    def version(self):
        return self._extension_info['version']

    @property
    def author(self):
        return self._extension_info['author']

    @property
    def priority(self):
        return self._extension_info['priority']

'''
短信发送插件
'''
class SMSSender(PluginBase):
    @abstractmethod
    def send_sms(self, phone_number: str, message: str) -> Tuple[bool, str]:
        """
        发送短信的抽象方法
        :param phone_number: 接收短信的电话号码
        :param message: 短信内容
        :return: 发送是否成功，错误信息
        """
        pass

'''
邮件发送插件
'''
class EmailSender(PluginBase):
    @abstractmethod
    def send_email(self, to: str, title: str, body: str) -> Tuple[bool, str]:
        """
        发送Email的抽象方法
        :param body: 邮件内容
        :param to: 接收邮件的email地址
        :param title: EMAIL内容
        :return: 发送是否成功，错误信息
        """
        pass

'''
文件上传插件
'''
class Uploader(PluginBase):
    def __init__(self, current_app):
        self.file_server: str = ""  # 访问文件时的域名
        super().__init__(current_app)


    @abstractmethod
    def upload(self, fileb_bytes, model:FileModel) -> Tuple[bool, str]:
        """
        上传文件
        :param fileb_bytes: 上传接口获取到的文件，在Python 3中是bytes类型，调用file.read()它会读取文件的内容并返回一个字符串，但这是一个字节序列，而不是一个普通的字符串。

        :return: 是否成功，错误信息或上传后的文件相对路径
        """
        pass

    # @property
    # @abstractmethod
    # def server_url(self) -> str:
    #     """
    #     属性，返回文件服务器的域名，方便拼接出完整的文件访问路径
    #     :return:
    #     """
    #     pass

    def get_file_md5(self, content_value) -> str:
        """
        获取内容的MD5值
        :param content_value:
        :return:
        """
        hash_md5 = hashlib.md5()
        hash_md5.update(content_value)
        md5_value = hash_md5.hexdigest()
        return md5_value


'''
三方登录
'''
class OpenLoginBase(PluginBase):
    @abstractmethod
    def login(self) -> Tuple[bool, str]:
        """
        发起一个登录操作
        :return: 是否成功，错误信息或如果成功是引导用户登录的重定向URL
        """
        pass

    @abstractmethod
    def call_back(self, request: Request) -> Tuple[bool, str, UserCallBackModel]:
        """
        登录通用页面的回调方法
        :return: 是否成功|错误信息或如果成功是引导用户登录的重定向URL|如果成功，返回用户的信息
        """
        pass

    def get_call_back_url(self):
        """
        获取当前插件的回调地址
        :return:
        """
        return quote(f'{request.host}/api/open_login_back?plugin={self.id}')


'''
内容搜索插件
'''
class SearchBase(PluginBase):
    @abstractmethod
    def query(self,key_word:str, page_size:int, page_index: int, order_by:int, class_name="") -> Tuple[dict,int]:
        """
        内容搜索
        :param key_word: 关键词
        :param page_size: 一页显示的数量
        :param page_index: 当前页码
        :param order_by: 数据的排序方式 1.按最新排序，2.按最热门排序
        :param class_name: 是否指定查询某个分类下的内容
        :return: 数据列表|总共有多少条数据
        """

'''
在线支付
'''

class PaymentBase(PluginBase):
    def __init__(self, current_app):
        super().__init__(current_app)
        self.notify_url = f"/pay/notify_url/{self.id}"
        self.return_url = f"/pay/return_url/{self.id}"

    @abstractmethod
    def create_pay_link(self, order_id: str, amount: float, **kwargs) -> Tuple[bool, str]:
        """
        构建一个支付连接串,根据不同的支付平台构建一个支付连接地址，用户选择此插件开始支付会跳转到这个连接地址完成支付操作。
        :return: 是否成功，错误信息或如果成功是引导用户登录的重定向URL
        """
        pass

    @abstractmethod
    def call_back(self, request: Request) -> Tuple[bool, str, PayBackInfo]:
        """
        支付完成后，在通知地址服务里会调用到这个方法，并获取这个方法处理结果，发出发送给监听程序更新订单状态。
        开发时应该严格返回标准的PayBackInfo数据
        :return: 是否成功|错误信息|如果成功，返回支付信息
        data = request.form.to_dict() or request.args.to_dict()
        """
        pass

    @abstractmethod
    def notify_response(self,notify_data:PayBackInfo):
        """
        根据当前支付平台要求，在通知页面返回处理的结果，notify_data中有通知处理后的结果数据，但不同的平台可能对通知结果格式有不一样的要求
        """
        pass