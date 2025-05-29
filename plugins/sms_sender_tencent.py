import random
import string
import time
from typing import Tuple

import eb_utils
from eb_utils import http_utils
from plugins.plugin_base import SMSSender, plugin_attribute


def generate_random_code(length):
    return ''.join(random.choices(string.digits, k=length))


def get_time_stamp(flg):
    """
    获取时间戳格式

    :param flg: 多少位的时间戳
    :return: 时间戳
    """
    if flg == 10:
        # 10位时间戳
        return int(time.time())
    elif flg == 13:
        # 13位时间戳
        return int(time.time() * 1000)
    else:
        raise ValueError("不支持的时间戳长度，只支持10位或13位")

@plugin_attribute("腾讯手机短信发送", "1.0", "ebsite")
class TencentSMSSender(SMSSender):
    def __init__(self, current_app):
        # self.name = "腾讯手机短信发送"
        self.app_id: str = ""
        self.app_key: str = ""
        self.template_id: str = ""
        self.msg_sign_name: str = "我的签名"
        self.info = "使用腾讯手机短信发送平台发送短信"
        super().__init__(current_app)

    def send_sms(self, mobi_number: str, content_msg: str) -> Tuple[bool, str]:
        # 这里实现腾讯云短信发送的具体逻辑
        print(f'发送【{content_msg}】到【{mobi_number}】')
        # print(self.app_id)
        # return True,''
        if not all([self.app_id, self.app_key, self.template_id, self.template_id]):
            raise ValueError("配置信息不完整")

        random_code = generate_random_code(10)
        timestamp = get_time_stamp(10)
        string_to_sign = f"appkey={self.app_key}&random={random_code}&time={timestamp}&mobile={mobi_number}"
        signature = eb_utils.sha256(string_to_sign)

        send_data = {
            'ext': '',
            'extend': '',
            'params': [content_msg],
            'sig': signature,
            'sign': self.msg_sign_name,
            'tel': {
                'mobile': mobi_number,
                'nationcode': '86'
            },
            'time': timestamp,
            'tpl_id': self.template_id
        }

        url = f"https://yun.tim.qq.com/v5/tlssmssvr/sendsms?sdkappid={self.app_id}&random={random_code}"
        result = http_utils.postJsonContent(url, send_data)
        print(result)
        return True, result

    def params_temp(self):
        """
        在后台保存插件配置时，实现在模板中添加保存参数
        :return: 模板字符串
        """
        return '''
        <div class="mb-3">
            <label>AppId</label>
            <input name="app_id" value="{{model.app_id}}"  style="max-width:300px" class="form-control" required>
        </div>
        <div class="mb-3">
            <label>AppKey</label>
            <input name="app_key" value="{{model.app_key}}"  style="max-width:300px" class="form-control" required>
        </div>
        <div class="mb-3">
            <label>模板ID</label>
            <input name="template_id" value="{{model.template_id}}"  style="max-width:300px" class="form-control" required>
        </div>
        <div class="mb-3">
            <label>短信签名</label>
            <input name="msg_sign_name" value="{{model.msg_sign_name}}"  style="max-width:300px" class="form-control" required>
        </div>
        '''
