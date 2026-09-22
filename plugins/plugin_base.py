import hashlib
from abc import ABC, abstractmethod
from typing import Tuple, Union

from flask import Request, request

import eb_cache
import eb_utils
from entity.file_model import FileModel
from entity.pay_back_model import PayBackInfo
from entity.pay_link_result import PayLinkResult
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
        :param fileb_bytes: 上传接口获取到的文件bytes
        :param model: 文件模型，实现方负责填充 model.url（访问路径）
        :return: (成功, 提示信息)，如 (True, '上传成功') 或 (False, '磁盘空间不足')
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

    def read(self, model: 'FileModel') -> Tuple[bool, Union[bytes, str, None]]:
        """
        根据文件模型读取文件内容。
        子类可以覆写此方法实现各自的读取逻辑。

        :param model: 文件模型（从数据库查出，包含 _id、url、mimetype、content 等）
        :return: (True, bytes) 代理输出文件内容；
                 (True, 'redirect:https://...') 重定向到直读 URL；
                 (False, 错误信息) 文件无法读取
        """
        return False, 'not implemented'


'''
第三方登录基类

子类需实现：
  - login()        : 发起 OAuth 授权，返回第三方平台的授权页 URL
  - call_back()    : 处理第三方回调，返回标准化的用户信息

基类提供：
  - _generate_state()  : 生成防 CSRF 的 state 参数
  - _verify_state()    : 验证回调中的 state
  - get_call_back_url(): 构造当前插件的回调地址（子类可覆写）
'''
class OpenLoginBase(PluginBase):

    @abstractmethod
    def login(self) -> Tuple[bool, str]:
        """
        发起一个登录操作（OAuth 第一步）。

        成功时返回 (True, 第三方授权页 URL)，前端将用户浏览器重定向到该 URL。
        失败时返回 (False, 错误信息)。
        """
        pass

    @abstractmethod
    def call_back(self, request: Request) -> Tuple[bool, str, UserCallBackModel]:
        """
        处理第三方登录回调（OAuth 第二步）。

        校验 state、用 code 换取 access_token、获取用户信息都在此完成。
        :return: (是否成功, 错误信息, 标准化的用户信息模型)
        """
        pass

    # ------------------------------------------------------------------
    # 基类提供的通用能力
    # ------------------------------------------------------------------

    def _generate_state(self, expire_seconds: int = 300) -> str:
        """
        生成防 CSRF 攻击的 state 参数，并缓存。

        子类在 login() 中构造授权 URL 时调用此方法，
        将返回值作为 state 参数附加到授权 URL 中。

        :param expire_seconds: state 有效期（秒），默认 5 分钟
        :return: 安全的随机 state 字符串
        """
        safe_code = eb_utils.get_uuid()
        eb_cache.set_data('1', expire_seconds, safe_code)
        return safe_code

    def _verify_state(self, state: str) -> bool:
        """
        校验回调请求中的 state 参数是否合法。

        子类在 call_back() 中首先调用此方法验证 state，
        防止 CSRF 攻击。

        :param state: 用户回调时携带的 state 值
        :return: True 表示 state 有效，False 表示无效/已过期
        """
        return eb_cache.get(state) == '1'

    def get_call_back_url(self) -> str:
        """
        获取当前插件的回调地址（原始 URL，未编码）。

        第三方平台授权后会重定向到此地址，服务端在此处理回调逻辑。
        子类可覆写此方法以适配特殊平台要求（如 Apple 要求固定 HTTPS 回调地址）。

        :return: 完整的回调 URL 字符串（如需嵌入查询参数，调用方自行 URL 编码）
        """
        return f'{request.host_url}api/app/open_login_back?plugin={self.id}'


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
        pass


'''
AI 提供者插件基类

子类必须实现：
  - chat()         : 通用 AI 对话，返回文本回复

子类可选实现：
  - chat_stream()  : 流式对话，逐块 yield 文本

配置在子类 __init__ 中声明（如 api_key, model），
由插件管理后台统一填写，各消费模块无需单独配置。
'''
class AIProviderBase(PluginBase):
    """AI 提供者插件基类"""

    @abstractmethod
    def chat(
        self,
        messages: list,
        system_prompt: str = "",
        **kwargs,
    ) -> dict:
        """
        通用 AI 对话接口。

        :param messages: 对话历史
            [{"role": "user", "content": "你好"},
             {"role": "assistant", "content": "你好！有什么可以帮助你的？"}]
        :param system_prompt: 系统提示词
        :param kwargs: 扩展参数
            temperature=0.7, max_tokens=2048, response_format=None
        :return:
            {"reply": "AI 回复文本",
             "finish_reason": "stop",       # stop / length / null
             "usage": {"prompt_tokens": 100, "completion_tokens": 50}}
        """
        pass

    def chat_stream(
        self,
        messages: list,
        system_prompt: str = "",
        **kwargs,
    ):
        """
        流式对话（可选实现）。

        默认回退到 chat() 一次性返回全部文本。
        支持流式的子类应 yield 每个文本块。

        :param messages: 对话历史
        :param system_prompt: 系统提示词
        :param kwargs: 扩展参数
        :yield: str，每次 yield 一个文本块
        """
        result = self.chat(messages, system_prompt, **kwargs)
        yield result.get("reply", "")

'''
在线支付基类

子类必须实现：
  - create_pay_link()   : 创建支付凭证，返回 PayLinkResult
  - call_back()         : 处理支付平台异步回调，返回 PayBackInfo
  - notify_response()   : 返回支付平台要求的确认响应

子类可选实现：
  - query_order()       : 查询订单状态
  - refund_order()      : 申请退款
  - close_order()       : 关闭订单
'''

class PaymentBase(PluginBase):
    def __init__(self, current_app):
        super().__init__(current_app)
        # 支付平台回调通知地址（子类可覆写，或在配置中设置完整 URL）
        self.notify_url = f"/pay/notify_url/{self.id}"
        self.return_url = f"/pay/return_url/{self.id}"

    # ==================== 必选接口 ====================

    @abstractmethod
    def create_pay_link(
        self,
        order_id: str,
        amount: float,
        **kwargs,
    ) -> Tuple[bool, str, PayLinkResult]:
        """
        创建支付凭证。

        不同支付场景返回不同凭证类型，PayLinkResult 的三个字段互斥：
          - pay_url      : URL 跳转（支付宝 / PayPal / 微信 H5）
          - qr_code_url  : 二维码扫码（微信 NATIVE）
          - trade_params : JSAPI 参数（微信 JSAPI / 小程序）

        前端根据哪个字段非空来决定处理方式。

        :param order_id: 本系统订单号
        :param amount:   支付金额（元）
        :param kwargs:   扩展参数（如 subject, description, openid, client_ip 等）
        :return: (是否成功, 错误信息, 支付凭证)
        """
        pass

    @abstractmethod
    def call_back(
        self,
        request: Request,
    ) -> Tuple[bool, str, PayBackInfo]:
        """
        处理支付平台的异步回调通知。

        此方法由 /pay/notify_url/<plugin_id> 路由调用。
        必须返回标准化的 PayBackInfo，业务代码只依赖 PayBackInfo 处理订单。

        :param request: Flask 请求对象（含支付平台 POST 的数据）
        :return: (是否成功, 错误信息, 标准化的支付结果)
        """
        pass

    @abstractmethod
    def notify_response(self, notify_data: PayBackInfo) -> str:
        """
        返回支付平台要求的通知确认响应。

        微信返回 "success"（XML），支付宝返回 "success"（纯文本），
        各平台格式要求不同，子类自行处理。

        :param notify_data: call_back 处理后的支付结果
        :return: 支付平台要求的确认字符串
        """
        pass

    # ==================== 可选扩展接口 ====================

    def query_order(self, order_id: str) -> Tuple[bool, str, PayBackInfo]:
        """
        查询订单状态（可选实现）。

        :param order_id: 本系统订单号
        :return: (是否成功, 错误信息, 订单状态信息)
        """
        return False, '此插件未实现查询订单功能', PayBackInfo()

    def refund_order(
        self,
        order_id: str,
        amount: float,
        reason: str = "",
    ) -> Tuple[bool, str, PayBackInfo]:
        """
        申请退款（可选实现）。

        :param order_id: 本系统订单号
        :param amount:   退款金额（元）
        :param reason:   退款原因
        :return: (是否成功, 错误信息, 退款结果)
        """
        return False, '此插件未实现退款功能', PayBackInfo()

    def close_order(self, order_id: str) -> Tuple[bool, str]:
        """
        关闭订单（可选实现）。

        :param order_id: 本系统订单号
        :return: (是否成功, 错误信息)
        """
        return False, '此插件未实现关闭订单功能'