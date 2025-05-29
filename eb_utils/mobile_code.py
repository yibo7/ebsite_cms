
import random

from flask import current_app

import eb_cache
import eb_utils


class MobileCode:
    """
    验证码处理
    """
    def __init__(self):
        st = current_app.config['base_settings']
        if 'APP_KEY' in st:
            self.app_key = st['APP_KEY']
        else:
            raise ValueError('请设置APP-KEY')
        self.key_prefix = 'safe_mb_'

    def _random_code(self):
        """
        生成4位随机数字
        :return:
        """
        return str(random.randint(1000, 9999))
    def get_full_key(self, mobile: str):
        md5_content = f'{self.app_key}{mobile}'
        return f'{self.key_prefix}{eb_utils.md5(md5_content)}'

    def send_code(self, mobile) -> bool:
        safe_code = self._random_code()
        # cache_key = eb_utils.get_uuid()

        is_succesful, msg = current_app.pm.send_sms(mobile, safe_code)
        if is_succesful:
            eb_cache.set_ex_minutes(safe_code, 10, self.get_full_key(mobile))
        return is_succesful


    def check_code(self,code_key, code:str) -> str:
        """
        验证安全码
        :param code_key:
        :param code:
        :return: 返回空值表示成功
        """
        if not all([code_key, code]):
            return '请传入code_key与code'
        safe_code = eb_cache.get(self.get_full_key(code_key))
        if not safe_code:
            return '验证码无效或过期'

        if safe_code.lower() != code.lower():
            return '验证码不正确'
        eb_cache.delete(self.get_full_key(code_key))
        return ''

